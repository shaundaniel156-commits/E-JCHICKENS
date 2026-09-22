"""Mortality recording, validated against the live batch population."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import List, Optional

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.models.bird import BirdBatch, MortalityRecord
from app.models.enums import ActivityAction, NotificationSeverity, NotificationType
from app.models.user import User
from app.repositories import aggregates as agg
from app.schemas.bird import MortalityCreate, MortalityOut, MortalityUpdate
from app.schemas.dashboard import SeriesPoint
from app.services import activity_service, bird_service, notification_service, settings_service
from app.utils.dates import day_series, label_day, label_month, month_series, week_start
from app.utils.pagination import paginate

MODULE = "mortality"


def get_record(db: Session, record_id: int) -> MortalityRecord:
    record = db.get(MortalityRecord, record_id)
    if record is None or record.is_deleted:
        raise NotFoundError("Mortality record not found.")
    return record


def to_out(record: MortalityRecord) -> MortalityOut:
    return MortalityOut(
        id=record.id,
        batch_id=record.batch_id,
        batch_code=record.batch.batch_code if record.batch else None,
        record_date=record.record_date,
        quantity=record.quantity,
        cause=record.cause,
        notes=record.notes,
    )


def list_records(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 20,
    batch_id: Optional[int] = None,
    search: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    sort: str = "record_date",
    order: str = "desc",
):
    stmt = select(MortalityRecord).where(MortalityRecord.is_deleted.is_(False))
    if batch_id:
        stmt = stmt.where(MortalityRecord.batch_id == batch_id)
    if search:
        pattern = f"%{search.strip()}%"
        stmt = stmt.where(or_(MortalityRecord.cause.ilike(pattern), MortalityRecord.notes.ilike(pattern)))
    if start_date:
        stmt = stmt.where(MortalityRecord.record_date >= start_date)
    if end_date:
        stmt = stmt.where(MortalityRecord.record_date <= end_date)

    sortable = {
        "record_date": MortalityRecord.record_date,
        "quantity": MortalityRecord.quantity,
        "created_at": MortalityRecord.created_at,
    }
    column = sortable.get(sort, MortalityRecord.record_date)
    stmt = stmt.order_by(column.desc() if order == "desc" else column.asc(), MortalityRecord.id.desc())

    rows, meta = paginate(db, stmt, page, page_size)
    return [to_out(row) for row in rows], meta


def create_record(db: Session, payload: MortalityCreate, actor: Optional[User]) -> MortalityOut:
    batch = bird_service.get_batch(db, payload.batch_id)
    available = agg.batch_available(db, batch)
    if payload.quantity > available:
        raise ConflictError(
            f"Batch {batch.batch_code} currently holds {available} birds. "
            f"You cannot record {payload.quantity} deaths."
        )
    if payload.record_date < batch.acquisition_date:
        raise ConflictError(
            f"Batch {batch.batch_code} was only acquired on "
            f"{batch.acquisition_date:%d/%m/%Y}."
        )

    record = MortalityRecord(
        batch_id=batch.id,
        record_date=payload.record_date,
        quantity=payload.quantity,
        cause=payload.cause,
        notes=payload.notes,
        created_by_id=actor.id if actor else None,
    )
    db.add(record)
    db.flush()

    bird_service.refresh_status(db, batch)
    activity_service.record(
        db,
        user=actor,
        action=ActivityAction.CREATE,
        module=MODULE,
        description=(
            f"Recorded {payload.quantity} death(s) in {batch.batch_code}"
            + (f" — {payload.cause}" if payload.cause else "")
        ),
        entity_id=record.id,
    )
    _raise_alerts(db, batch)
    db.commit()
    db.refresh(record)
    return to_out(record)


def update_record(
    db: Session, record_id: int, payload: MortalityUpdate, actor: Optional[User]
) -> MortalityOut:
    record = get_record(db, record_id)
    batch = bird_service.get_batch(db, record.batch_id)
    data = payload.model_dump(exclude_unset=True)

    if "quantity" in data and data["quantity"] is not None:
        available = agg.batch_available(db, batch, exclude_mortality_id=record.id)
        if data["quantity"] > available:
            raise ConflictError(
                f"Batch {batch.batch_code} can account for at most {available} deaths "
                f"on this record."
            )
        record.quantity = data["quantity"]

    for field in ("record_date", "cause", "notes"):
        if field in data and data[field] is not None:
            setattr(record, field, data[field])
    record.updated_by_id = actor.id if actor else None

    bird_service.refresh_status(db, batch)
    activity_service.record(
        db,
        user=actor,
        action=ActivityAction.UPDATE,
        module=MODULE,
        description=f"Updated mortality record #{record.id} for {batch.batch_code}",
        entity_id=record.id,
    )
    _raise_alerts(db, batch)
    db.commit()
    db.refresh(record)
    return to_out(record)


def delete_record(db: Session, record_id: int, actor: Optional[User]) -> None:
    """Soft delete — the birds return to the available count automatically."""
    record = get_record(db, record_id)
    batch = bird_service.get_batch(db, record.batch_id)
    record.is_deleted = True
    record.deleted_at = datetime.utcnow()
    record.deleted_by_id = actor.id if actor else None

    bird_service.refresh_status(db, batch)
    activity_service.record(
        db,
        user=actor,
        action=ActivityAction.DELETE,
        module=MODULE,
        description=f"Reversed mortality record #{record.id} ({record.quantity} birds, {batch.batch_code})",
        entity_id=record.id,
    )
    db.commit()


def _raise_alerts(db: Session, batch: BirdBatch) -> None:
    """Warn when a batch's mortality rate crosses the configured threshold."""
    threshold = float(settings_service.get_settings(db).high_mortality_rate_percent or 5)
    deaths = agg.batch_deaths(db, batch.id)
    rate = agg.mortality_rate(batch.initial_quantity, batch.adjustment_quantity or 0, deaths)
    key = f"mortality-high:{batch.id}"

    if rate >= threshold and deaths > 0:
        notification_service.push(
            db,
            type_=NotificationType.MORTALITY_HIGH,
            severity=NotificationSeverity.CRITICAL,
            title=f"High mortality in {batch.batch_code}",
            message=(
                f"{deaths} of {batch.initial_quantity} birds have died — a mortality rate of "
                f"{rate:.2f}%, above the {threshold:.0f}% alert level."
            ),
            module=MODULE,
            entity_id=batch.id,
            dedupe_key=key,
        )
    else:
        notification_service.clear_dedupe(db, key)


# --------------------------------------------------------------------------- analytics

def summary(db: Session, start: Optional[date] = None, end: Optional[date] = None) -> dict:
    totals = db.execute(
        select(
            func.coalesce(func.sum(MortalityRecord.quantity), 0),
            func.count(MortalityRecord.id),
        ).where(
            MortalityRecord.is_deleted.is_(False),
            *( [MortalityRecord.record_date >= start] if start else [] ),
            *( [MortalityRecord.record_date <= end] if end else [] ),
        )
    ).one()
    return {"total_deaths": int(totals[0]), "record_count": int(totals[1])}


def series(db: Session, grouping: str = "day", days: int = 30) -> List[SeriesPoint]:
    """Deaths grouped by day, week or month for the mortality chart."""
    today = date.today()
    rows = db.execute(
        select(MortalityRecord.record_date, MortalityRecord.quantity).where(
            MortalityRecord.is_deleted.is_(False)
        )
    ).all()

    if grouping == "month":
        earliest = min((row[0] for row in rows), default=today)
        buckets = {label_month(point): 0 for point in month_series(earliest, today, 12)}
        for record_date, quantity in rows:
            key = label_month(record_date)
            if key in buckets:
                buckets[key] += int(quantity)
    elif grouping == "week":
        start = week_start(today - timedelta(weeks=11))
        buckets = {}
        cursor = start
        while cursor <= today:
            buckets[f"w/c {cursor:%d %b}"] = 0
            cursor += timedelta(days=7)
        for record_date, quantity in rows:
            key = f"w/c {week_start(record_date):%d %b}"
            if key in buckets:
                buckets[key] += int(quantity)
    else:
        start = today - timedelta(days=max(days, 1) - 1)
        buckets = {label_day(point): 0 for point in day_series(start, today, days)}
        for record_date, quantity in rows:
            key = label_day(record_date)
            if key in buckets and start <= record_date <= today:
                buckets[key] += int(quantity)

    return [SeriesPoint(period=key, value=float(value)) for key, value in buckets.items()]
