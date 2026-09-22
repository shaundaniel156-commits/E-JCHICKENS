"""Dashboard payload — assembled entirely from recorded transactions."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.bird import BirdBatch, MortalityRecord
from app.models.enums import PaymentStatus
from app.models.feed import FeedConsumption, FeedPurchase
from app.models.finance import Sale
from app.models.user import User
from app.repositories import aggregates as agg
from app.schemas.dashboard import (
    BirdSummary,
    DashboardCharts,
    DashboardSummary,
    FeedSummary,
    SeriesPoint,
)
from app.schemas.system import ActivityLogOut, NotificationOut
from app.services import (
    activity_service,
    bird_service,
    expense_service,
    feed_service,
    finance_service,
    mortality_service,
    notification_service,
    settings_service,
)
from app.utils.dates import label_month, month_series
from app.utils.money import ZERO, to_decimal


def bird_summary(db: Session) -> BirdSummary:
    totals = bird_service.farm_totals(db)
    return BirdSummary(**totals)


def feed_summary(db: Session) -> FeedSummary:
    stock = feed_service.stock_summary(db)
    settings = settings_service.get_settings(db)
    threshold = to_decimal(settings.low_feed_threshold_bags)

    purchased_bags = to_decimal(
        db.execute(
            select(func.coalesce(func.sum(FeedPurchase.quantity_bags), 0)).where(
                FeedPurchase.is_deleted.is_(False)
            )
        ).scalar_one()
    )
    consumed_bags = to_decimal(
        db.execute(
            select(func.coalesce(func.sum(FeedConsumption.quantity_bags), 0)).where(
                FeedConsumption.is_deleted.is_(False)
            )
        ).scalar_one()
    )

    return FeedSummary(
        stock_bags=stock.total_stock_bags,
        stock_kg=stock.total_stock_kg,
        purchased_bags=round(purchased_bags, 2),
        purchased_kg=stock.total_purchased_kg,
        consumed_bags=round(consumed_bags, 2),
        consumed_kg=stock.total_consumed_kg,
        total_feed_cost=stock.total_feed_cost,
        low_stock=stock.total_stock_bags < threshold,
        low_stock_threshold_bags=threshold,
    )


def _bird_population_series(db: Session, months: int = 12) -> List[SeriesPoint]:
    """Flock size at the end of each month, rebuilt from acquisitions, deaths and sales."""
    today = date.today()
    batches = list(
        db.execute(
            select(BirdBatch.acquisition_date, BirdBatch.initial_quantity, BirdBatch.adjustment_quantity)
            .where(BirdBatch.is_deleted.is_(False))
        ).all()
    )
    if not batches:
        return []

    earliest = min(row[0] for row in batches)
    points = month_series(max(earliest, _months_ago(today, months - 1)), today, months)

    deaths = db.execute(
        select(MortalityRecord.record_date, MortalityRecord.quantity).where(
            MortalityRecord.is_deleted.is_(False)
        )
    ).all()
    sales = db.execute(
        select(Sale.sale_date, Sale.quantity).where(
            Sale.is_deleted.is_(False), Sale.payment_status != PaymentStatus.CANCELLED
        )
    ).all()

    series: List[SeriesPoint] = []
    for point in points:
        cutoff = _month_end(point)
        acquired = sum(row[1] for row in batches if row[0] <= cutoff)
        losses = sum(row[2] or 0 for row in batches if row[0] <= cutoff)
        died = sum(int(row[1]) for row in deaths if row[0] <= cutoff)
        sold = sum(int(row[1]) for row in sales if row[0] <= cutoff)
        series.append(
            SeriesPoint(
                period=label_month(point),
                value=float(max(acquired - died - sold - losses, 0)),
                secondary=float(died),
            )
        )
    return series


def _feed_usage_series(db: Session, months: int = 12) -> List[SeriesPoint]:
    """Bags purchased against bags consumed, per month."""
    today = date.today()
    purchases = db.execute(
        select(FeedPurchase.purchase_date, FeedPurchase.quantity_bags).where(
            FeedPurchase.is_deleted.is_(False)
        )
    ).all()
    consumption = db.execute(
        select(FeedConsumption.consumption_date, FeedConsumption.quantity_bags).where(
            FeedConsumption.is_deleted.is_(False)
        )
    ).all()
    if not purchases and not consumption:
        return []

    dates = [row[0] for row in purchases] + [row[0] for row in consumption]
    points = month_series(max(min(dates), _months_ago(today, months - 1)), today, months)

    series: List[SeriesPoint] = []
    for point in points:
        key = (point.year, point.month)
        purchased = sum(
            float(row[1]) for row in purchases if (row[0].year, row[0].month) == key
        )
        consumed = sum(
            float(row[1]) for row in consumption if (row[0].year, row[0].month) == key
        )
        series.append(SeriesPoint(period=label_month(point), value=purchased, secondary=consumed))
    return series


def _months_ago(value: date, months: int) -> date:
    from app.utils.dates import add_months

    return add_months(value, -months)


def _month_end(value: date) -> date:
    from app.utils.dates import month_end

    return month_end(value)


def summary(db: Session, user: User) -> DashboardSummary:
    settings = settings_service.get_settings(db)
    birds = bird_summary(db)
    feed = feed_summary(db)
    finance = finance_service.financial_summary(db)
    trend = finance_service.monthly_trend(db)

    charts = DashboardCharts(
        bird_population=_bird_population_series(db),
        mortality=mortality_service.series(db, grouping="day", days=30),
        expenses_by_category=expense_service.category_breakdown(db),
        revenue_vs_expenses=trend,
        profit_trend=trend,
        feed_usage=_feed_usage_series(db),
    )

    has_data = bool(
        birds.total_batches
        or feed.purchased_kg
        or finance.total_expenses
        or finance.total_revenue
    )

    return DashboardSummary(
        generated_at=date.today(),
        farm_name=settings.farm_name,
        currency=settings.currency,
        birds=birds,
        feed=feed,
        finance=finance,
        charts=charts,
        recent_activity=[
            ActivityLogOut.model_validate(row) for row in activity_service.recent(db, limit=8)
        ],
        alerts=[
            NotificationOut.model_validate(row)
            for row in notification_service.alerts(db, user.id, limit=5)
        ],
        has_data=has_data,
    )
