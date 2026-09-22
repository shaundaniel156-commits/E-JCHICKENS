"""Bird batches: creation, derived populations and validated adjustments.

Creating a batch also creates the matching acquisition expense, so the flock and
the books are entered once and stay in step.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Dict, List, Optional

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.exceptions import (
    ConflictError,
    DuplicateError,
    NotFoundError,
    PermissionDeniedError,
)
from app.models.bird import BirdBatch
from app.models.enums import (
    ActivityAction,
    BatchStatus,
    ExpenseSource,
    NotificationSeverity,
    NotificationType,
    RoleName,
)
from app.models.user import User
from app.repositories import aggregates as agg
from app.schemas.bird import BatchAdjustment, BirdBatchCreate, BirdBatchOut, BirdBatchUpdate
from app.services import activity_service, expense_service, notification_service
from app.utils.money import money
from app.utils.pagination import paginate

MODULE = "birds"


def get_batch(db: Session, batch_id: int) -> BirdBatch:
    batch = db.get(BirdBatch, batch_id)
    if batch is None or batch.is_deleted:
        raise NotFoundError("Bird batch not found.")
    return batch


def to_out(db: Session, batch: BirdBatch, *, cache: Optional[Dict[str, Dict[int, int]]] = None) -> BirdBatchOut:
    """Attach the derived population figures to a batch row."""
    if cache is not None:
        deaths = cache["deaths"].get(batch.id, 0)
        sold = cache["sold"].get(batch.id, 0)
        sick = cache["sick"].get(batch.id, 0)
    else:
        deaths = agg.batch_deaths(db, batch.id)
        sold = agg.batch_sold(db, batch.id)
        sick = agg.batch_sick(db, batch.id)

    adjustment = batch.adjustment_quantity or 0
    current = batch.initial_quantity - deaths - sold - adjustment
    current = max(current, 0)
    sick_capped = min(sick, current)

    return BirdBatchOut(
        id=batch.id,
        batch_code=batch.batch_code,
        breed=batch.breed,
        initial_quantity=batch.initial_quantity,
        acquisition_date=batch.acquisition_date,
        source=batch.source,
        age_days_at_acquisition=batch.age_days_at_acquisition,
        cost_per_bird=batch.cost_per_bird,
        total_acquisition_cost=batch.total_acquisition_cost,
        adjustment_quantity=adjustment,
        status=batch.status,
        notes=batch.notes,
        total_deaths=deaths,
        total_sold=sold,
        current_quantity=current,
        sick_count=sick_capped,
        healthy_quantity=max(current - sick_capped, 0),
        mortality_rate=agg.mortality_rate(batch.initial_quantity, adjustment, deaths),
        age_days=(date.today() - batch.acquisition_date).days + batch.age_days_at_acquisition,
    )


def list_batches(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 20,
    search: Optional[str] = None,
    status: Optional[BatchStatus] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    sort: str = "acquisition_date",
    order: str = "desc",
):
    stmt = select(BirdBatch).where(BirdBatch.is_deleted.is_(False))
    if search:
        pattern = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                BirdBatch.batch_code.ilike(pattern),
                BirdBatch.breed.ilike(pattern),
                BirdBatch.source.ilike(pattern),
            )
        )
    if status:
        stmt = stmt.where(BirdBatch.status == status)
    if start_date:
        stmt = stmt.where(BirdBatch.acquisition_date >= start_date)
    if end_date:
        stmt = stmt.where(BirdBatch.acquisition_date <= end_date)

    sortable = {
        "batch_code": BirdBatch.batch_code,
        "breed": BirdBatch.breed,
        "acquisition_date": BirdBatch.acquisition_date,
        "initial_quantity": BirdBatch.initial_quantity,
        "created_at": BirdBatch.created_at,
    }
    column = sortable.get(sort, BirdBatch.acquisition_date)
    stmt = stmt.order_by(column.desc() if order == "desc" else column.asc(), BirdBatch.id.desc())

    rows, meta = paginate(db, stmt, page, page_size)
    cache = _cache_for(db, [row.id for row in rows])
    return [to_out(db, row, cache=cache) for row in rows], meta


def _cache_for(db: Session, batch_ids: List[int]) -> Dict[str, Dict[int, int]]:
    if not batch_ids:
        return {"deaths": {}, "sold": {}, "sick": {}}
    return {
        "deaths": agg.deaths_by_batch(db, batch_ids),
        "sold": agg.sold_by_batch(db, batch_ids),
        "sick": agg.sick_by_batch(db, batch_ids),
    }


def all_batches_out(db: Session, active_only: bool = False) -> List[BirdBatchOut]:
    stmt = select(BirdBatch).where(BirdBatch.is_deleted.is_(False))
    if active_only:
        stmt = stmt.where(BirdBatch.status == BatchStatus.ACTIVE)
    rows = list(db.execute(stmt.order_by(BirdBatch.acquisition_date.desc())).scalars().all())
    cache = _cache_for(db, [row.id for row in rows])
    return [to_out(db, row, cache=cache) for row in rows]


def create_batch(db: Session, payload: BirdBatchCreate, actor: Optional[User]) -> BirdBatchOut:
    existing = db.execute(
        select(BirdBatch).where(BirdBatch.batch_code == payload.batch_code)
    ).scalars().first()
    if existing:
        raise DuplicateError(f"Batch code {payload.batch_code} is already in use.")

    batch = BirdBatch(
        batch_code=payload.batch_code,
        breed=payload.breed.strip(),
        initial_quantity=payload.initial_quantity,
        acquisition_date=payload.acquisition_date,
        source=payload.source,
        age_days_at_acquisition=payload.age_days_at_acquisition,
        cost_per_bird=money(payload.cost_per_bird),
        notes=payload.notes,
        status=BatchStatus.ACTIVE,
        created_by_id=actor.id if actor else None,
    )
    db.add(batch)
    db.flush()

    # One entry, two modules: the acquisition cost becomes an expense automatically.
    total_cost = money(batch.cost_per_bird * batch.initial_quantity)
    if total_cost > 0:
        expense_service.sync_system_expense(
            db,
            source_type=ExpenseSource.BIRD_BATCH,
            source_id=batch.id,
            category_name="Birds",
            description=f"Purchase of {batch.initial_quantity} {batch.breed} birds ({batch.batch_code})",
            amount=total_cost,
            expense_date=batch.acquisition_date,
            vendor=batch.source,
            actor=actor,
        )

    activity_service.record(
        db,
        user=actor,
        action=ActivityAction.CREATE,
        module=MODULE,
        description=f"Added batch {batch.batch_code}: {batch.initial_quantity} {batch.breed}",
        entity_id=batch.id,
    )
    notification_service.push(
        db,
        type_=NotificationType.BIRDS_ADDED,
        severity=NotificationSeverity.SUCCESS,
        title="New bird batch added",
        message=f"{batch.initial_quantity} {batch.breed} birds were added as batch {batch.batch_code}.",
        module=MODULE,
        entity_id=batch.id,
    )
    db.commit()
    db.refresh(batch)
    return to_out(db, batch)


# Staff keep batch details up to date, but the figures that drive the books —
# quantity, cost and lifecycle status — stay with managers and administrators.
STAFF_EDITABLE_FIELDS = {"breed", "source", "age_days_at_acquisition", "notes"}


def update_batch(
    db: Session, batch_id: int, payload: BirdBatchUpdate, actor: Optional[User]
) -> BirdBatchOut:
    batch = get_batch(db, batch_id)
    data = payload.model_dump(exclude_unset=True)

    if actor and actor.role.name == RoleName.STAFF:
        restricted = sorted(set(data) - STAFF_EDITABLE_FIELDS)
        if restricted:
            raise PermissionDeniedError(
                "Staff can update a batch's breed, source, age and notes. "
                f"Changing {', '.join(restricted)} needs a manager.",
            )

    if "initial_quantity" in data and data["initial_quantity"] is not None:
        consumed = (
            agg.batch_deaths(db, batch.id)
            + agg.batch_sold(db, batch.id)
            + (batch.adjustment_quantity or 0)
        )
        if data["initial_quantity"] < consumed:
            raise ConflictError(
                f"This batch already has {consumed} birds accounted for "
                f"(deaths, sales and losses). The initial quantity cannot be lower."
            )
        batch.initial_quantity = data["initial_quantity"]

    for field in ("breed", "acquisition_date", "source", "age_days_at_acquisition", "notes", "status"):
        if field in data and data[field] is not None:
            setattr(batch, field, data[field])
    if "cost_per_bird" in data and data["cost_per_bird"] is not None:
        batch.cost_per_bird = money(data["cost_per_bird"])

    batch.updated_by_id = actor.id if actor else None

    total_cost = money(batch.cost_per_bird * batch.initial_quantity)
    expense_service.sync_system_expense(
        db,
        source_type=ExpenseSource.BIRD_BATCH,
        source_id=batch.id,
        category_name="Birds",
        description=f"Purchase of {batch.initial_quantity} {batch.breed} birds ({batch.batch_code})",
        amount=total_cost,
        expense_date=batch.acquisition_date,
        vendor=batch.source,
        actor=actor,
    )

    activity_service.record(
        db,
        user=actor,
        action=ActivityAction.UPDATE,
        module=MODULE,
        description=f"Updated batch {batch.batch_code}",
        entity_id=batch.id,
    )
    db.commit()
    db.refresh(batch)
    return to_out(db, batch)


def adjust_batch(
    db: Session, batch_id: int, payload: BatchAdjustment, actor: Optional[User]
) -> BirdBatchOut:
    """Record non-mortality shrinkage (theft, escape, corrected miscount)."""
    batch = get_batch(db, batch_id)
    available = agg.batch_available(db, batch)
    if payload.quantity > available:
        raise ConflictError(
            f"Batch {batch.batch_code} only has {available} birds left; "
            f"{payload.quantity} cannot be removed."
        )
    batch.adjustment_quantity = (batch.adjustment_quantity or 0) + payload.quantity
    batch.updated_by_id = actor.id if actor else None
    _refresh_status(db, batch)

    activity_service.record(
        db,
        user=actor,
        action=ActivityAction.UPDATE,
        module=MODULE,
        description=(
            f"Recorded a loss of {payload.quantity} birds in {batch.batch_code}: {payload.reason}"
        ),
        entity_id=batch.id,
    )
    db.commit()
    db.refresh(batch)
    return to_out(db, batch)


def delete_batch(db: Session, batch_id: int, actor: Optional[User]) -> None:
    """Soft delete; refused while the batch still carries transactions."""
    batch = get_batch(db, batch_id)
    deaths = agg.batch_deaths(db, batch.id)
    sold = agg.batch_sold(db, batch.id)
    if deaths or sold:
        raise ConflictError(
            "This batch has mortality or sales records attached. "
            "Close the batch instead of deleting it so the history is kept."
        )

    batch.is_deleted = True
    batch.deleted_at = datetime.utcnow()
    batch.deleted_by_id = actor.id if actor else None
    expense_service.remove_system_expense(db, ExpenseSource.BIRD_BATCH, batch.id, actor)

    activity_service.record(
        db,
        user=actor,
        action=ActivityAction.DELETE,
        module=MODULE,
        description=f"Deleted batch {batch.batch_code}",
        entity_id=batch.id,
    )
    db.commit()


def _refresh_status(db: Session, batch: BirdBatch) -> None:
    """Keep the batch status honest as birds leave."""
    if batch.status == BatchStatus.CLOSED:
        return
    remaining = agg.batch_available(db, batch)
    batch.status = BatchStatus.SOLD_OUT if remaining <= 0 else BatchStatus.ACTIVE


def refresh_status(db: Session, batch: BirdBatch) -> None:
    _refresh_status(db, batch)


def available_birds(db: Session, batch: BirdBatch, **exclusions) -> int:
    return agg.batch_available(db, batch, **exclusions)


def farm_totals(db: Session) -> dict:
    """Whole-farm bird figures used by the dashboard and reports."""
    batches = list(
        db.execute(select(BirdBatch).where(BirdBatch.is_deleted.is_(False))).scalars().all()
    )
    cache = _cache_for(db, [b.id for b in batches])

    initial = sum(b.initial_quantity for b in batches)
    deaths = sum(cache["deaths"].get(b.id, 0) for b in batches)
    sold = sum(cache["sold"].get(b.id, 0) for b in batches)
    losses = sum(b.adjustment_quantity or 0 for b in batches)
    current = max(initial - deaths - sold - losses, 0)
    sick = min(sum(cache["sick"].get(b.id, 0) for b in batches), current)

    return {
        "total_batches": len(batches),
        "active_batches": sum(1 for b in batches if b.status == BatchStatus.ACTIVE),
        "initial_birds": initial,
        "total_birds": current,
        "dead_birds": deaths,
        "sold_birds": sold,
        "other_losses": losses,
        "sick_birds": sick,
        "healthy_birds": max(current - sick, 0),
        "available_birds": max(current - sick, 0),
        "mortality_rate": agg.mortality_rate(initial, losses, deaths),
    }
