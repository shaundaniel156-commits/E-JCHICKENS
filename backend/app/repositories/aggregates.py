"""Every derived quantity in the system is computed here — one source of truth.

Services and reports call these helpers instead of writing their own SQL, so the
dashboard, the reports module and the validation checks can never disagree.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Dict, Iterable, Optional, Tuple

from sqlalchemy import Select, and_, func, select
from sqlalchemy.orm import Session

from app.models.bird import BirdBatch, HealthRecord, MortalityRecord
from app.models.enums import HealthStatus, PaymentStatus
from app.models.feed import FeedConsumption, FeedPurchase, FeedType
from app.models.finance import Expense, Sale
from app.utils.money import ZERO, to_decimal

# --------------------------------------------------------------------------- filters

def _date_filter(column, start: Optional[date], end: Optional[date]):
    clauses = []
    if start:
        clauses.append(column >= start)
    if end:
        clauses.append(column <= end)
    return clauses


def live_sales() -> Select:
    """Sales that count towards revenue and bird reduction."""
    return select(Sale).where(
        Sale.is_deleted.is_(False), Sale.payment_status != PaymentStatus.CANCELLED
    )


# --------------------------------------------------------------------------- birds

def deaths_by_batch(db: Session, batch_ids: Optional[Iterable[int]] = None) -> Dict[int, int]:
    stmt = (
        select(MortalityRecord.batch_id, func.coalesce(func.sum(MortalityRecord.quantity), 0))
        .where(MortalityRecord.is_deleted.is_(False))
        .group_by(MortalityRecord.batch_id)
    )
    if batch_ids is not None:
        stmt = stmt.where(MortalityRecord.batch_id.in_(list(batch_ids)))
    return {row[0]: int(row[1]) for row in db.execute(stmt)}


def sold_by_batch(db: Session, batch_ids: Optional[Iterable[int]] = None) -> Dict[int, int]:
    stmt = (
        select(Sale.batch_id, func.coalesce(func.sum(Sale.quantity), 0))
        .where(Sale.is_deleted.is_(False), Sale.payment_status != PaymentStatus.CANCELLED)
        .group_by(Sale.batch_id)
    )
    if batch_ids is not None:
        stmt = stmt.where(Sale.batch_id.in_(list(batch_ids)))
    return {row[0]: int(row[1]) for row in db.execute(stmt)}


def sick_by_batch(db: Session, batch_ids: Optional[Iterable[int]] = None) -> Dict[int, int]:
    """Only open health records count, so a bird is never counted sick twice."""
    stmt = (
        select(HealthRecord.batch_id, func.coalesce(func.sum(HealthRecord.sick_count), 0))
        .where(
            HealthRecord.is_deleted.is_(False),
            HealthRecord.status.in_(
                [HealthStatus.SICK, HealthStatus.UNDER_TREATMENT, HealthStatus.CRITICAL]
            ),
        )
        .group_by(HealthRecord.batch_id)
    )
    if batch_ids is not None:
        stmt = stmt.where(HealthRecord.batch_id.in_(list(batch_ids)))
    return {row[0]: int(row[1]) for row in db.execute(stmt)}


def batch_deaths(db: Session, batch_id: int, exclude_record_id: Optional[int] = None) -> int:
    stmt = select(func.coalesce(func.sum(MortalityRecord.quantity), 0)).where(
        MortalityRecord.batch_id == batch_id, MortalityRecord.is_deleted.is_(False)
    )
    if exclude_record_id:
        stmt = stmt.where(MortalityRecord.id != exclude_record_id)
    return int(db.execute(stmt).scalar_one())


def batch_sold(db: Session, batch_id: int, exclude_sale_id: Optional[int] = None) -> int:
    stmt = select(func.coalesce(func.sum(Sale.quantity), 0)).where(
        Sale.batch_id == batch_id,
        Sale.is_deleted.is_(False),
        Sale.payment_status != PaymentStatus.CANCELLED,
    )
    if exclude_sale_id:
        stmt = stmt.where(Sale.id != exclude_sale_id)
    return int(db.execute(stmt).scalar_one())


def batch_sick(db: Session, batch_id: int, exclude_record_id: Optional[int] = None) -> int:
    stmt = select(func.coalesce(func.sum(HealthRecord.sick_count), 0)).where(
        HealthRecord.batch_id == batch_id,
        HealthRecord.is_deleted.is_(False),
        HealthRecord.status.in_(
            [HealthStatus.SICK, HealthStatus.UNDER_TREATMENT, HealthStatus.CRITICAL]
        ),
    )
    if exclude_record_id:
        stmt = stmt.where(HealthRecord.id != exclude_record_id)
    return int(db.execute(stmt).scalar_one())


def batch_available(
    db: Session,
    batch: BirdBatch,
    exclude_sale_id: Optional[int] = None,
    exclude_mortality_id: Optional[int] = None,
) -> int:
    """Birds physically left in a batch right now."""
    deaths = batch_deaths(db, batch.id, exclude_record_id=exclude_mortality_id)
    sold = batch_sold(db, batch.id, exclude_sale_id=exclude_sale_id)
    return batch.initial_quantity - deaths - sold - (batch.adjustment_quantity or 0)


def mortality_rate(initial: int, adjustment: int, deaths: int) -> float:
    """Deaths as a share of the birds that were actually exposed to risk."""
    exposed = initial - (adjustment or 0)
    if exposed <= 0:
        return 0.0
    return round(deaths / exposed * 100, 2)


def deaths_in_period(db: Session, start: Optional[date], end: Optional[date]) -> int:
    stmt = select(func.coalesce(func.sum(MortalityRecord.quantity), 0)).where(
        MortalityRecord.is_deleted.is_(False),
        *_date_filter(MortalityRecord.record_date, start, end),
    )
    return int(db.execute(stmt).scalar_one())


# --------------------------------------------------------------------------- feed

def feed_purchased_kg(
    db: Session,
    feed_type_id: Optional[int] = None,
    start: Optional[date] = None,
    end: Optional[date] = None,
) -> Decimal:
    stmt = select(
        func.coalesce(func.sum(FeedPurchase.quantity_bags * FeedPurchase.bag_weight_kg), 0)
    ).where(FeedPurchase.is_deleted.is_(False), *_date_filter(FeedPurchase.purchase_date, start, end))
    if feed_type_id:
        stmt = stmt.where(FeedPurchase.feed_type_id == feed_type_id)
    return to_decimal(db.execute(stmt).scalar_one())


def feed_consumed_kg(
    db: Session,
    feed_type_id: Optional[int] = None,
    start: Optional[date] = None,
    end: Optional[date] = None,
) -> Decimal:
    stmt = select(func.coalesce(func.sum(FeedConsumption.quantity_kg), 0)).where(
        FeedConsumption.is_deleted.is_(False),
        *_date_filter(FeedConsumption.consumption_date, start, end),
    )
    if feed_type_id:
        stmt = stmt.where(FeedConsumption.feed_type_id == feed_type_id)
    return to_decimal(db.execute(stmt).scalar_one())


def feed_stock_kg(db: Session, feed_type_id: int, exclude_consumption_id: Optional[int] = None,
                  exclude_purchase_id: Optional[int] = None) -> Decimal:
    purchased_stmt = select(
        func.coalesce(func.sum(FeedPurchase.quantity_bags * FeedPurchase.bag_weight_kg), 0)
    ).where(FeedPurchase.is_deleted.is_(False), FeedPurchase.feed_type_id == feed_type_id)
    if exclude_purchase_id:
        purchased_stmt = purchased_stmt.where(FeedPurchase.id != exclude_purchase_id)

    consumed_stmt = select(func.coalesce(func.sum(FeedConsumption.quantity_kg), 0)).where(
        FeedConsumption.is_deleted.is_(False), FeedConsumption.feed_type_id == feed_type_id
    )
    if exclude_consumption_id:
        consumed_stmt = consumed_stmt.where(FeedConsumption.id != exclude_consumption_id)

    purchased = to_decimal(db.execute(purchased_stmt).scalar_one())
    consumed = to_decimal(db.execute(consumed_stmt).scalar_one())
    return purchased - consumed


def feed_totals_by_type(db: Session) -> Dict[int, Tuple[Decimal, Decimal, Decimal]]:
    """{feed_type_id: (purchased_kg, consumed_kg, total_cost)}"""
    purchases = db.execute(
        select(
            FeedPurchase.feed_type_id,
            func.coalesce(func.sum(FeedPurchase.quantity_bags * FeedPurchase.bag_weight_kg), 0),
            func.coalesce(func.sum(FeedPurchase.total_cost), 0),
        )
        .where(FeedPurchase.is_deleted.is_(False))
        .group_by(FeedPurchase.feed_type_id)
    ).all()
    consumption = db.execute(
        select(
            FeedConsumption.feed_type_id,
            func.coalesce(func.sum(FeedConsumption.quantity_kg), 0),
        )
        .where(FeedConsumption.is_deleted.is_(False))
        .group_by(FeedConsumption.feed_type_id)
    ).all()

    totals: Dict[int, Tuple[Decimal, Decimal, Decimal]] = {}
    for feed_type_id, purchased, cost in purchases:
        totals[feed_type_id] = (to_decimal(purchased), ZERO, to_decimal(cost))
    for feed_type_id, consumed in consumption:
        purchased, _, cost = totals.get(feed_type_id, (ZERO, ZERO, ZERO))
        totals[feed_type_id] = (purchased, to_decimal(consumed), cost)
    return totals


def feed_cost(db: Session, start: Optional[date] = None, end: Optional[date] = None) -> Decimal:
    stmt = select(func.coalesce(func.sum(FeedPurchase.total_cost), 0)).where(
        FeedPurchase.is_deleted.is_(False), *_date_filter(FeedPurchase.purchase_date, start, end)
    )
    return to_decimal(db.execute(stmt).scalar_one())


def average_bag_weight(db: Session, feed_type: FeedType) -> Decimal:
    weight = to_decimal(feed_type.default_bag_weight_kg)
    return weight if weight > 0 else Decimal("50")


# --------------------------------------------------------------------------- money

def total_expenses(db: Session, start: Optional[date] = None, end: Optional[date] = None) -> Decimal:
    stmt = select(func.coalesce(func.sum(Expense.amount), 0)).where(
        Expense.is_deleted.is_(False), *_date_filter(Expense.expense_date, start, end)
    )
    return to_decimal(db.execute(stmt).scalar_one())


def total_revenue(db: Session, start: Optional[date] = None, end: Optional[date] = None) -> Decimal:
    stmt = select(func.coalesce(func.sum(Sale.total_amount), 0)).where(
        Sale.is_deleted.is_(False),
        Sale.payment_status != PaymentStatus.CANCELLED,
        *_date_filter(Sale.sale_date, start, end),
    )
    return to_decimal(db.execute(stmt).scalar_one())


def cash_collected(db: Session, start: Optional[date] = None, end: Optional[date] = None) -> Decimal:
    stmt = select(func.coalesce(func.sum(Sale.amount_paid), 0)).where(
        Sale.is_deleted.is_(False),
        Sale.payment_status != PaymentStatus.CANCELLED,
        *_date_filter(Sale.sale_date, start, end),
    )
    return to_decimal(db.execute(stmt).scalar_one())


def birds_sold(db: Session, start: Optional[date] = None, end: Optional[date] = None) -> int:
    stmt = select(func.coalesce(func.sum(Sale.quantity), 0)).where(
        Sale.is_deleted.is_(False),
        Sale.payment_status != PaymentStatus.CANCELLED,
        *_date_filter(Sale.sale_date, start, end),
    )
    return int(db.execute(stmt).scalar_one())


def expenses_by_category(
    db: Session, start: Optional[date] = None, end: Optional[date] = None
) -> list[tuple[int, str, Decimal, int]]:
    from app.models.finance import ExpenseCategory

    stmt = (
        select(
            ExpenseCategory.id,
            ExpenseCategory.name,
            func.coalesce(func.sum(Expense.amount), 0),
            func.count(Expense.id),
        )
        .join(Expense, Expense.category_id == ExpenseCategory.id)
        .where(Expense.is_deleted.is_(False), *_date_filter(Expense.expense_date, start, end))
        .group_by(ExpenseCategory.id, ExpenseCategory.name)
        .order_by(func.sum(Expense.amount).desc())
    )
    return [(row[0], row[1], to_decimal(row[2]), int(row[3])) for row in db.execute(stmt)]
