"""Feed types, purchases and consumption, with stock that can never go negative."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.exceptions import (
    ConflictError,
    DuplicateError,
    InsufficientStockError,
    NotFoundError,
)
from app.models.enums import (
    ActivityAction,
    ExpenseSource,
    NotificationSeverity,
    NotificationType,
)
from app.models.feed import FeedConsumption, FeedPurchase, FeedType
from app.models.user import User
from app.repositories import aggregates as agg
from app.schemas.feed import (
    FeedConsumptionCreate,
    FeedConsumptionOut,
    FeedConsumptionUpdate,
    FeedPurchaseCreate,
    FeedPurchaseOut,
    FeedPurchaseUpdate,
    FeedStockSummary,
    FeedTypeCreate,
    FeedTypeOut,
    FeedTypeUpdate,
)
from app.services import activity_service, expense_service, notification_service, settings_service
from app.utils.money import ZERO, money, to_decimal
from app.utils.pagination import paginate

MODULE = "feed"

DEFAULT_FEED_TYPES = [
    ("Broiler Starter", "Fed from day 1 to about week 2", Decimal("50")),
    ("Broiler Grower", "Fed from about week 3 to week 4", Decimal("50")),
    ("Broiler Finisher", "Fed from about week 5 until sale", Decimal("50")),
    ("Layer Mash", "Feed for laying birds", Decimal("70")),
]


def ensure_default_feed_types(db: Session) -> None:
    existing = {name.lower() for (name,) in db.execute(select(FeedType.name)).all()}
    for name, description, weight in DEFAULT_FEED_TYPES:
        if name.lower() not in existing:
            db.add(FeedType(name=name, description=description, default_bag_weight_kg=weight))
    db.flush()


# --------------------------------------------------------------------------- feed types

def get_feed_type(db: Session, feed_type_id: int) -> FeedType:
    feed_type = db.get(FeedType, feed_type_id)
    if feed_type is None:
        raise NotFoundError("Feed type not found.")
    return feed_type


def feed_type_out(db: Session, feed_type: FeedType, totals=None, threshold: Optional[Decimal] = None) -> FeedTypeOut:
    if totals is None:
        purchased = agg.feed_purchased_kg(db, feed_type.id)
        consumed = agg.feed_consumed_kg(db, feed_type.id)
    else:
        purchased, consumed, _cost = totals

    bag_weight = agg.average_bag_weight(db, feed_type)
    stock_kg = purchased - consumed
    stock_bags = (stock_kg / bag_weight) if bag_weight else ZERO
    if threshold is None:
        threshold = to_decimal(settings_service.get_settings(db).low_feed_threshold_bags)

    return FeedTypeOut(
        id=feed_type.id,
        name=feed_type.name,
        description=feed_type.description,
        default_bag_weight_kg=bag_weight,
        stock_kg=round(stock_kg, 2),
        stock_bags=round(stock_bags, 2),
        purchased_kg=round(purchased, 2),
        consumed_kg=round(consumed, 2),
        is_low_stock=stock_bags < threshold,
    )


def list_feed_types(db: Session) -> List[FeedTypeOut]:
    rows = list(db.execute(select(FeedType).order_by(FeedType.name)).scalars().all())
    totals = agg.feed_totals_by_type(db)
    threshold = to_decimal(settings_service.get_settings(db).low_feed_threshold_bags)
    return [
        feed_type_out(db, row, totals.get(row.id, (ZERO, ZERO, ZERO)), threshold) for row in rows
    ]


def create_feed_type(db: Session, payload: FeedTypeCreate, actor: Optional[User]) -> FeedTypeOut:
    name = payload.name.strip()
    if db.execute(select(FeedType).where(FeedType.name == name)).scalars().first():
        raise DuplicateError(f"A feed type called “{name}” already exists.")
    feed_type = FeedType(
        name=name,
        description=payload.description,
        default_bag_weight_kg=payload.default_bag_weight_kg,
    )
    db.add(feed_type)
    db.flush()
    activity_service.record(
        db,
        user=actor,
        action=ActivityAction.CREATE,
        module=MODULE,
        description=f"Added feed type {name}",
        entity_id=feed_type.id,
    )
    db.commit()
    db.refresh(feed_type)
    return feed_type_out(db, feed_type)


def update_feed_type(
    db: Session, feed_type_id: int, payload: FeedTypeUpdate, actor: Optional[User]
) -> FeedTypeOut:
    feed_type = get_feed_type(db, feed_type_id)
    data = payload.model_dump(exclude_unset=True)
    if "name" in data and data["name"]:
        clash = db.execute(
            select(FeedType).where(FeedType.name == data["name"].strip(), FeedType.id != feed_type.id)
        ).scalars().first()
        if clash:
            raise DuplicateError(f"A feed type called “{data['name']}” already exists.")
    for field, value in data.items():
        if value is not None:
            setattr(feed_type, field, value)
    activity_service.record(
        db,
        user=actor,
        action=ActivityAction.UPDATE,
        module=MODULE,
        description=f"Updated feed type {feed_type.name}",
        entity_id=feed_type.id,
    )
    db.commit()
    db.refresh(feed_type)
    return feed_type_out(db, feed_type)


def delete_feed_type(db: Session, feed_type_id: int, actor: Optional[User]) -> None:
    feed_type = get_feed_type(db, feed_type_id)
    used = db.execute(
        select(FeedPurchase.id).where(
            FeedPurchase.feed_type_id == feed_type.id, FeedPurchase.is_deleted.is_(False)
        ).limit(1)
    ).scalars().first()
    if used:
        raise ConflictError("This feed type has purchases recorded against it.")
    db.delete(feed_type)
    activity_service.record(
        db,
        user=actor,
        action=ActivityAction.DELETE,
        module=MODULE,
        description=f"Deleted feed type {feed_type.name}",
        entity_id=feed_type_id,
    )
    db.commit()


# --------------------------------------------------------------------------- purchases

def get_purchase(db: Session, purchase_id: int) -> FeedPurchase:
    purchase = db.get(FeedPurchase, purchase_id)
    if purchase is None or purchase.is_deleted:
        raise NotFoundError("Feed purchase not found.")
    return purchase


def purchase_out(purchase: FeedPurchase) -> FeedPurchaseOut:
    return FeedPurchaseOut(
        id=purchase.id,
        feed_type_id=purchase.feed_type_id,
        feed_type_name=purchase.feed_type.name if purchase.feed_type else None,
        purchase_date=purchase.purchase_date,
        brand=purchase.brand,
        quantity_bags=purchase.quantity_bags,
        bag_weight_kg=purchase.bag_weight_kg,
        quantity_kg=purchase.quantity_kg,
        cost_per_bag=purchase.cost_per_bag,
        total_cost=purchase.total_cost,
        supplier=purchase.supplier,
        lot_number=purchase.lot_number,
        notes=purchase.notes,
    )


def list_purchases(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 20,
    feed_type_id: Optional[int] = None,
    search: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    sort: str = "purchase_date",
    order: str = "desc",
):
    stmt = select(FeedPurchase).where(FeedPurchase.is_deleted.is_(False))
    if feed_type_id:
        stmt = stmt.where(FeedPurchase.feed_type_id == feed_type_id)
    if search:
        pattern = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                FeedPurchase.brand.ilike(pattern),
                FeedPurchase.supplier.ilike(pattern),
                FeedPurchase.lot_number.ilike(pattern),
            )
        )
    if start_date:
        stmt = stmt.where(FeedPurchase.purchase_date >= start_date)
    if end_date:
        stmt = stmt.where(FeedPurchase.purchase_date <= end_date)

    sortable = {
        "purchase_date": FeedPurchase.purchase_date,
        "quantity_bags": FeedPurchase.quantity_bags,
        "total_cost": FeedPurchase.total_cost,
    }
    column = sortable.get(sort, FeedPurchase.purchase_date)
    stmt = stmt.order_by(column.desc() if order == "desc" else column.asc(), FeedPurchase.id.desc())

    rows, meta = paginate(db, stmt, page, page_size)
    return [purchase_out(row) for row in rows], meta


def create_purchase(
    db: Session, payload: FeedPurchaseCreate, actor: Optional[User]
) -> FeedPurchaseOut:
    feed_type = get_feed_type(db, payload.feed_type_id)
    total_cost = money(payload.quantity_bags * payload.cost_per_bag)

    purchase = FeedPurchase(
        feed_type_id=feed_type.id,
        purchase_date=payload.purchase_date,
        brand=payload.brand,
        quantity_bags=payload.quantity_bags,
        bag_weight_kg=payload.bag_weight_kg,
        cost_per_bag=money(payload.cost_per_bag),
        total_cost=total_cost,
        supplier=payload.supplier,
        lot_number=payload.lot_number,
        notes=payload.notes,
        created_by_id=actor.id if actor else None,
    )
    db.add(purchase)
    db.flush()

    _sync_purchase_expense(db, purchase, feed_type.name, actor)
    activity_service.record(
        db,
        user=actor,
        action=ActivityAction.CREATE,
        module=MODULE,
        description=f"Purchased {payload.quantity_bags} bag(s) of {feed_type.name}",
        entity_id=purchase.id,
    )
    notification_service.push(
        db,
        type_=NotificationType.FEED_UPDATED,
        severity=NotificationSeverity.SUCCESS,
        title="Feed stock updated",
        message=f"{payload.quantity_bags} bag(s) of {feed_type.name} were added to stock.",
        module=MODULE,
        entity_id=purchase.id,
    )
    check_low_stock(db, feed_type)
    from app.services import budget_service

    budget_service.check_budget_alerts(db)
    db.commit()
    db.refresh(purchase)
    return purchase_out(purchase)


def update_purchase(
    db: Session, purchase_id: int, payload: FeedPurchaseUpdate, actor: Optional[User]
) -> FeedPurchaseOut:
    purchase = get_purchase(db, purchase_id)
    data = payload.model_dump(exclude_unset=True)

    new_bags = data.get("quantity_bags", purchase.quantity_bags)
    new_weight = data.get("bag_weight_kg", purchase.bag_weight_kg)
    # Reducing a purchase must not push the running stock below zero.
    stock_without = agg.feed_stock_kg(db, purchase.feed_type_id, exclude_purchase_id=purchase.id)
    if stock_without + (new_bags * new_weight) < 0:
        raise InsufficientStockError(
            "That change would leave the feed stock negative — some of this feed has "
            "already been recorded as consumed."
        )

    for field in ("purchase_date", "brand", "supplier", "lot_number", "notes"):
        if field in data and data[field] is not None:
            setattr(purchase, field, data[field])
    purchase.quantity_bags = new_bags
    purchase.bag_weight_kg = new_weight
    if "cost_per_bag" in data and data["cost_per_bag"] is not None:
        purchase.cost_per_bag = money(data["cost_per_bag"])
    purchase.total_cost = money(purchase.quantity_bags * purchase.cost_per_bag)
    purchase.updated_by_id = actor.id if actor else None

    _sync_purchase_expense(db, purchase, purchase.feed_type.name, actor)
    activity_service.record(
        db,
        user=actor,
        action=ActivityAction.UPDATE,
        module=MODULE,
        description=f"Updated feed purchase #{purchase.id}",
        entity_id=purchase.id,
    )
    check_low_stock(db, purchase.feed_type)
    db.commit()
    db.refresh(purchase)
    return purchase_out(purchase)


def delete_purchase(db: Session, purchase_id: int, actor: Optional[User]) -> None:
    purchase = get_purchase(db, purchase_id)
    stock_without = agg.feed_stock_kg(db, purchase.feed_type_id, exclude_purchase_id=purchase.id)
    if stock_without < 0:
        raise InsufficientStockError(
            "This purchase cannot be removed because the feed it brought in has already "
            "been recorded as consumed."
        )
    purchase.is_deleted = True
    purchase.deleted_at = datetime.utcnow()
    purchase.deleted_by_id = actor.id if actor else None
    expense_service.remove_system_expense(db, ExpenseSource.FEED_PURCHASE, purchase.id, actor)

    activity_service.record(
        db,
        user=actor,
        action=ActivityAction.DELETE,
        module=MODULE,
        description=f"Removed feed purchase #{purchase.id}",
        entity_id=purchase.id,
    )
    check_low_stock(db, purchase.feed_type)
    db.commit()


def _sync_purchase_expense(
    db: Session, purchase: FeedPurchase, feed_type_name: str, actor: Optional[User]
) -> None:
    expense_service.sync_system_expense(
        db,
        source_type=ExpenseSource.FEED_PURCHASE,
        source_id=purchase.id,
        category_name="Feed",
        description=f"{purchase.quantity_bags} bag(s) of {feed_type_name}"
        + (f" ({purchase.brand})" if purchase.brand else ""),
        amount=purchase.total_cost,
        expense_date=purchase.purchase_date,
        vendor=purchase.supplier,
        actor=actor,
    )


# --------------------------------------------------------------------------- consumption

def get_consumption(db: Session, consumption_id: int) -> FeedConsumption:
    record = db.get(FeedConsumption, consumption_id)
    if record is None or record.is_deleted:
        raise NotFoundError("Feed consumption record not found.")
    return record


def consumption_out(record: FeedConsumption) -> FeedConsumptionOut:
    return FeedConsumptionOut(
        id=record.id,
        feed_type_id=record.feed_type_id,
        feed_type_name=record.feed_type.name if record.feed_type else None,
        batch_id=record.batch_id,
        batch_code=None,
        consumption_date=record.consumption_date,
        quantity_bags=record.quantity_bags,
        quantity_kg=record.quantity_kg,
        notes=record.notes,
    )


def list_consumption(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 20,
    feed_type_id: Optional[int] = None,
    batch_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    sort: str = "consumption_date",
    order: str = "desc",
):
    from app.models.bird import BirdBatch

    stmt = select(FeedConsumption).where(FeedConsumption.is_deleted.is_(False))
    if feed_type_id:
        stmt = stmt.where(FeedConsumption.feed_type_id == feed_type_id)
    if batch_id:
        stmt = stmt.where(FeedConsumption.batch_id == batch_id)
    if start_date:
        stmt = stmt.where(FeedConsumption.consumption_date >= start_date)
    if end_date:
        stmt = stmt.where(FeedConsumption.consumption_date <= end_date)

    sortable = {
        "consumption_date": FeedConsumption.consumption_date,
        "quantity_kg": FeedConsumption.quantity_kg,
    }
    column = sortable.get(sort, FeedConsumption.consumption_date)
    stmt = stmt.order_by(column.desc() if order == "desc" else column.asc(), FeedConsumption.id.desc())

    rows, meta = paginate(db, stmt, page, page_size)
    batch_codes = dict(
        db.execute(select(BirdBatch.id, BirdBatch.batch_code)).all()
    )
    out = []
    for row in rows:
        item = consumption_out(row)
        item.batch_code = batch_codes.get(row.batch_id)
        out.append(item)
    return out, meta


def _resolve_quantities(
    feed_type: FeedType, bags: Optional[Decimal], kilograms: Optional[Decimal]
) -> tuple[Decimal, Decimal]:
    """Accept bags or kilograms and derive the other from the bag weight."""
    bag_weight = to_decimal(feed_type.default_bag_weight_kg) or Decimal("50")
    if kilograms is not None:
        kg = to_decimal(kilograms)
        bag_count = to_decimal(bags) if bags is not None else (kg / bag_weight)
    else:
        bag_count = to_decimal(bags)
        kg = bag_count * bag_weight
    return round(bag_count, 2), round(kg, 2)


def create_consumption(
    db: Session, payload: FeedConsumptionCreate, actor: Optional[User]
) -> FeedConsumptionOut:
    feed_type = get_feed_type(db, payload.feed_type_id)
    bags, kilograms = _resolve_quantities(feed_type, payload.quantity_bags, payload.quantity_kg)

    available = agg.feed_stock_kg(db, feed_type.id)
    if kilograms > available:
        raise InsufficientStockError(
            f"Only {available:.2f} kg of {feed_type.name} is in stock; "
            f"{kilograms:.2f} kg cannot be recorded as consumed."
        )
    if payload.batch_id:
        from app.services import bird_service

        bird_service.get_batch(db, payload.batch_id)

    record = FeedConsumption(
        feed_type_id=feed_type.id,
        batch_id=payload.batch_id,
        consumption_date=payload.consumption_date,
        quantity_bags=bags,
        quantity_kg=kilograms,
        notes=payload.notes,
        created_by_id=actor.id if actor else None,
    )
    db.add(record)
    db.flush()

    activity_service.record(
        db,
        user=actor,
        action=ActivityAction.CREATE,
        module=MODULE,
        description=f"Recorded {kilograms} kg of {feed_type.name} consumed",
        entity_id=record.id,
    )
    check_low_stock(db, feed_type)
    db.commit()
    db.refresh(record)
    return consumption_out(record)


def update_consumption(
    db: Session, consumption_id: int, payload: FeedConsumptionUpdate, actor: Optional[User]
) -> FeedConsumptionOut:
    record = get_consumption(db, consumption_id)
    feed_type = get_feed_type(db, record.feed_type_id)
    data = payload.model_dump(exclude_unset=True)

    if "quantity_bags" in data or "quantity_kg" in data:
        bags, kilograms = _resolve_quantities(
            feed_type, data.get("quantity_bags"), data.get("quantity_kg")
        )
        available = agg.feed_stock_kg(db, feed_type.id, exclude_consumption_id=record.id)
        if kilograms > available:
            raise InsufficientStockError(
                f"Only {available:.2f} kg of {feed_type.name} would be available for this record."
            )
        record.quantity_bags = bags
        record.quantity_kg = kilograms

    for field in ("batch_id", "consumption_date", "notes"):
        if field in data and data[field] is not None:
            setattr(record, field, data[field])
    record.updated_by_id = actor.id if actor else None

    activity_service.record(
        db,
        user=actor,
        action=ActivityAction.UPDATE,
        module=MODULE,
        description=f"Updated feed consumption #{record.id}",
        entity_id=record.id,
    )
    check_low_stock(db, feed_type)
    db.commit()
    db.refresh(record)
    return consumption_out(record)


def delete_consumption(db: Session, consumption_id: int, actor: Optional[User]) -> None:
    record = get_consumption(db, consumption_id)
    record.is_deleted = True
    record.deleted_at = datetime.utcnow()
    record.deleted_by_id = actor.id if actor else None
    activity_service.record(
        db,
        user=actor,
        action=ActivityAction.DELETE,
        module=MODULE,
        description=f"Removed feed consumption #{record.id}",
        entity_id=record.id,
    )
    check_low_stock(db, record.feed_type)
    db.commit()


# --------------------------------------------------------------------------- stock

def check_low_stock(db: Session, feed_type: FeedType) -> None:
    threshold = to_decimal(settings_service.get_settings(db).low_feed_threshold_bags)
    bag_weight = agg.average_bag_weight(db, feed_type)
    stock_kg = agg.feed_stock_kg(db, feed_type.id)
    stock_bags = stock_kg / bag_weight if bag_weight else ZERO
    key = f"feed-low:{feed_type.id}"

    if stock_bags < threshold:
        notification_service.push(
            db,
            type_=NotificationType.FEED_LOW,
            severity=NotificationSeverity.WARNING,
            title=f"{feed_type.name} is running low",
            message=(
                f"Only {stock_bags:.1f} bag(s) ({stock_kg:.1f} kg) of {feed_type.name} remain, "
                f"below the alert level of {threshold:.0f} bag(s)."
            ),
            module=MODULE,
            entity_id=feed_type.id,
            dedupe_key=key,
        )
    else:
        notification_service.clear_dedupe(db, key)


def stock_summary(db: Session) -> FeedStockSummary:
    by_type = list_feed_types(db)
    total_stock_kg = sum((item.stock_kg for item in by_type), ZERO)
    total_stock_bags = sum((item.stock_bags for item in by_type), ZERO)
    return FeedStockSummary(
        total_stock_kg=round(total_stock_kg, 2),
        total_stock_bags=round(total_stock_bags, 2),
        total_purchased_kg=round(sum((item.purchased_kg for item in by_type), ZERO), 2),
        total_consumed_kg=round(sum((item.consumed_kg for item in by_type), ZERO), 2),
        total_feed_cost=agg.feed_cost(db),
        low_stock_types=sum(1 for item in by_type if item.is_low_stock),
        by_type=by_type,
    )
