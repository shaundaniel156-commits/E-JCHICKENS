"""Reports. Every report reuses the same aggregate helpers as the dashboard,
so the two can never disagree.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.bird import BirdBatch
from app.models.enums import PaymentStatus
from app.models.feed import FeedType
from app.models.finance import Sale
from app.repositories import aggregates as agg
from app.schemas.dashboard import (
    BirdReport,
    BirdReportRow,
    ExpenseReport,
    FarmPerformanceReport,
    FeedReport,
    FeedReportRow,
    ProfitLossReport,
    ReportPeriod,
    SalesReport,
    SalesReportRow,
)
from app.services import (
    dashboard_service,
    expense_service,
    finance_service,
)
from app.utils.money import ZERO, money, percentage, safe_divide, to_decimal


def _period(start: Optional[date], end: Optional[date]) -> ReportPeriod:
    return ReportPeriod(start_date=start, end_date=end)


def bird_report(
    db: Session,
    start: Optional[date] = None,
    end: Optional[date] = None,
    batch_id: Optional[int] = None,
) -> BirdReport:
    stmt = select(BirdBatch).where(BirdBatch.is_deleted.is_(False))
    if batch_id:
        stmt = stmt.where(BirdBatch.id == batch_id)
    if start:
        stmt = stmt.where(BirdBatch.acquisition_date >= start)
    if end:
        stmt = stmt.where(BirdBatch.acquisition_date <= end)
    batches = list(db.execute(stmt.order_by(BirdBatch.acquisition_date)).scalars().all())

    ids = [batch.id for batch in batches]
    deaths_map = agg.deaths_by_batch(db, ids) if ids else {}
    sold_map = agg.sold_by_batch(db, ids) if ids else {}
    sick_map = agg.sick_by_batch(db, ids) if ids else {}

    rows: List[BirdReportRow] = []
    for batch in batches:
        deaths = deaths_map.get(batch.id, 0)
        sold = sold_map.get(batch.id, 0)
        losses = batch.adjustment_quantity or 0
        current = max(batch.initial_quantity - deaths - sold - losses, 0)
        rows.append(
            BirdReportRow(
                batch_id=batch.id,
                batch_code=batch.batch_code,
                breed=batch.breed,
                acquisition_date=batch.acquisition_date,
                initial_quantity=batch.initial_quantity,
                deaths=deaths,
                sold=sold,
                other_losses=losses,
                current_quantity=current,
                sick_count=min(sick_map.get(batch.id, 0), current),
                mortality_rate=agg.mortality_rate(batch.initial_quantity, losses, deaths),
                acquisition_cost=money(batch.cost_per_bird * batch.initial_quantity),
            )
        )

    initial = sum(row.initial_quantity for row in rows)
    deaths = sum(row.deaths for row in rows)
    losses = sum(row.other_losses for row in rows)
    totals = BirdReportRow(
        batch_id=0,
        batch_code="TOTAL",
        breed="All batches",
        acquisition_date=min((row.acquisition_date for row in rows), default=date.today()),
        initial_quantity=initial,
        deaths=deaths,
        sold=sum(row.sold for row in rows),
        other_losses=losses,
        current_quantity=sum(row.current_quantity for row in rows),
        sick_count=sum(row.sick_count for row in rows),
        mortality_rate=agg.mortality_rate(initial, losses, deaths),
        acquisition_cost=sum((row.acquisition_cost for row in rows), ZERO),
    )
    return BirdReport(period=_period(start, end), rows=rows, totals=totals)


def feed_report(
    db: Session, start: Optional[date] = None, end: Optional[date] = None
) -> FeedReport:
    feed_types = list(db.execute(select(FeedType).order_by(FeedType.name)).scalars().all())
    rows: List[FeedReportRow] = []

    for feed_type in feed_types:
        bag_weight = agg.average_bag_weight(db, feed_type)
        purchased = agg.feed_purchased_kg(db, feed_type.id, start, end)
        consumed = agg.feed_consumed_kg(db, feed_type.id, start, end)
        # Stock is a running position, so it always reflects every record, not just the period.
        stock = agg.feed_stock_kg(db, feed_type.id)
        cost = _feed_cost_for_type(db, feed_type.id, start, end)
        if not purchased and not consumed and not stock:
            continue
        rows.append(
            FeedReportRow(
                feed_type_id=feed_type.id,
                feed_type=feed_type.name,
                purchased_bags=round(purchased / bag_weight, 2) if bag_weight else ZERO,
                purchased_kg=round(purchased, 2),
                consumed_bags=round(consumed / bag_weight, 2) if bag_weight else ZERO,
                consumed_kg=round(consumed, 2),
                stock_kg=round(stock, 2),
                stock_bags=round(stock / bag_weight, 2) if bag_weight else ZERO,
                total_cost=cost,
            )
        )

    return FeedReport(
        period=_period(start, end),
        rows=rows,
        total_purchased_kg=round(sum((row.purchased_kg for row in rows), ZERO), 2),
        total_consumed_kg=round(sum((row.consumed_kg for row in rows), ZERO), 2),
        total_stock_kg=round(sum((row.stock_kg for row in rows), ZERO), 2),
        total_cost=sum((row.total_cost for row in rows), ZERO),
    )


def _feed_cost_for_type(
    db: Session, feed_type_id: int, start: Optional[date], end: Optional[date]
) -> Decimal:
    from sqlalchemy import func

    from app.models.feed import FeedPurchase

    stmt = select(func.coalesce(func.sum(FeedPurchase.total_cost), 0)).where(
        FeedPurchase.is_deleted.is_(False), FeedPurchase.feed_type_id == feed_type_id
    )
    if start:
        stmt = stmt.where(FeedPurchase.purchase_date >= start)
    if end:
        stmt = stmt.where(FeedPurchase.purchase_date <= end)
    return to_decimal(db.execute(stmt).scalar_one())


def expense_report(
    db: Session, start: Optional[date] = None, end: Optional[date] = None
) -> ExpenseReport:
    rows = expense_service.category_breakdown(db, start, end)
    return ExpenseReport(
        period=_period(start, end),
        rows=rows,
        total=sum((row.amount for row in rows), ZERO),
    )


def sales_report(
    db: Session,
    start: Optional[date] = None,
    end: Optional[date] = None,
    batch_id: Optional[int] = None,
) -> SalesReport:
    stmt = select(Sale).where(
        Sale.is_deleted.is_(False), Sale.payment_status != PaymentStatus.CANCELLED
    )
    if batch_id:
        stmt = stmt.where(Sale.batch_id == batch_id)
    if start:
        stmt = stmt.where(Sale.sale_date >= start)
    if end:
        stmt = stmt.where(Sale.sale_date <= end)
    sales = list(db.execute(stmt.order_by(Sale.sale_date)).scalars().all())

    rows = [
        SalesReportRow(
            sale_id=sale.id,
            reference=sale.reference,
            sale_date=sale.sale_date,
            batch_code=sale.batch.batch_code if sale.batch else "",
            customer=sale.customer.name if sale.customer else None,
            quantity=sale.quantity,
            unit_price=sale.unit_price,
            total_amount=sale.total_amount,
            amount_paid=sale.amount_paid,
            payment_status=sale.payment_status.value,
        )
        for sale in sales
    ]
    return SalesReport(
        period=_period(start, end),
        rows=rows,
        total_birds_sold=sum(row.quantity for row in rows),
        total_revenue=sum((row.total_amount for row in rows), ZERO),
        total_collected=sum((row.amount_paid for row in rows), ZERO),
        customers=len({sale.customer_id for sale in sales if sale.customer_id}),
    )


def profit_loss_report(
    db: Session, start: Optional[date] = None, end: Optional[date] = None
) -> ProfitLossReport:
    revenue = agg.total_revenue(db, start, end)
    expenses = agg.total_expenses(db, start, end)
    net = money(revenue - expenses)
    return ProfitLossReport(
        period=_period(start, end),
        total_revenue=revenue,
        total_expenses=expenses,
        expenses_by_category=expense_service.category_breakdown(db, start, end),
        net_profit_or_loss=net,
        is_profit=net >= 0,
        profit_margin_percent=percentage(net, revenue),
        trend=finance_service.monthly_trend(db, start, end),
    )


def farm_performance_report(
    db: Session, start: Optional[date] = None, end: Optional[date] = None
) -> FarmPerformanceReport:
    birds = dashboard_service.bird_summary(db)
    feed = dashboard_service.feed_summary(db)
    finance = finance_service.financial_summary(db, start, end)
    sold = agg.birds_sold(db, start, end)
    revenue = agg.total_revenue(db, start, end)

    return FarmPerformanceReport(
        period=_period(start, end),
        birds=birds,
        feed=feed,
        finance=finance,
        feed_cost_per_bird=safe_divide(feed.total_feed_cost, birds.initial_birds),
        cost_per_bird_sold=safe_divide(finance.total_expenses, sold),
        revenue_per_bird_sold=safe_divide(revenue, sold),
        average_sale_price=safe_divide(revenue, sold),
    )
