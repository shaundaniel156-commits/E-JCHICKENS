"""Health records. Open records determine the farm's sick-bird count."""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.models.bird import HealthRecord
from app.models.enums import (
    ActivityAction,
    ExpenseSource,
    HealthStatus,
    NotificationSeverity,
    NotificationType,
)
from app.models.user import User
from app.repositories import aggregates as agg
from app.schemas.bird import HealthCreate, HealthOut, HealthUpdate
from app.services import activity_service, bird_service, expense_service, notification_service
from app.utils.money import money
from app.utils.pagination import paginate

MODULE = "health"


def get_record(db: Session, record_id: int) -> HealthRecord:
    record = db.get(HealthRecord, record_id)
    if record is None or record.is_deleted:
        raise NotFoundError("Health record not found.")
    return record


def to_out(record: HealthRecord) -> HealthOut:
    return HealthOut(
        id=record.id,
        batch_id=record.batch_id,
        batch_code=record.batch.batch_code if record.batch else None,
        record_date=record.record_date,
        sick_count=record.sick_count,
        symptoms=record.symptoms,
        diagnosis=record.diagnosis,
        treatment=record.treatment,
        medicine=record.medicine,
        dosage=record.dosage,
        treatment_cost=record.treatment_cost,
        veterinarian=record.veterinarian,
        status=record.status,
        notes=record.notes,
    )


def list_records(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 20,
    batch_id: Optional[int] = None,
    status: Optional[HealthStatus] = None,
    search: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    sort: str = "record_date",
    order: str = "desc",
):
    stmt = select(HealthRecord).where(HealthRecord.is_deleted.is_(False))
    if batch_id:
        stmt = stmt.where(HealthRecord.batch_id == batch_id)
    if status:
        stmt = stmt.where(HealthRecord.status == status)
    if search:
        pattern = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                HealthRecord.diagnosis.ilike(pattern),
                HealthRecord.symptoms.ilike(pattern),
                HealthRecord.medicine.ilike(pattern),
                HealthRecord.veterinarian.ilike(pattern),
            )
        )
    if start_date:
        stmt = stmt.where(HealthRecord.record_date >= start_date)
    if end_date:
        stmt = stmt.where(HealthRecord.record_date <= end_date)

    sortable = {
        "record_date": HealthRecord.record_date,
        "sick_count": HealthRecord.sick_count,
        "treatment_cost": HealthRecord.treatment_cost,
        "created_at": HealthRecord.created_at,
    }
    column = sortable.get(sort, HealthRecord.record_date)
    stmt = stmt.order_by(column.desc() if order == "desc" else column.asc(), HealthRecord.id.desc())

    rows, meta = paginate(db, stmt, page, page_size)
    return [to_out(row) for row in rows], meta


def _assert_capacity(db: Session, batch, sick_count: int, exclude_record_id: Optional[int] = None) -> None:
    """Open sick records across a batch can never exceed the birds actually alive."""
    available = agg.batch_available(db, batch)
    already_sick = agg.batch_sick(db, batch.id, exclude_record_id=exclude_record_id)
    if sick_count + already_sick > available:
        remaining = max(available - already_sick, 0)
        raise ConflictError(
            f"Batch {batch.batch_code} holds {available} birds and {already_sick} are already "
            f"recorded as sick. At most {remaining} more can be reported."
        )


def create_record(db: Session, payload: HealthCreate, actor: Optional[User]) -> HealthOut:
    batch = bird_service.get_batch(db, payload.batch_id)
    if payload.status in HealthRecord.OPEN_STATUSES:
        _assert_capacity(db, batch, payload.sick_count)

    record = HealthRecord(
        batch_id=batch.id,
        record_date=payload.record_date,
        sick_count=payload.sick_count,
        symptoms=payload.symptoms,
        diagnosis=payload.diagnosis,
        treatment=payload.treatment,
        medicine=payload.medicine,
        dosage=payload.dosage,
        treatment_cost=money(payload.treatment_cost),
        veterinarian=payload.veterinarian,
        status=payload.status,
        notes=payload.notes,
        created_by_id=actor.id if actor else None,
    )
    db.add(record)
    db.flush()

    _sync_expense(db, record, batch.batch_code, actor)
    activity_service.record(
        db,
        user=actor,
        action=ActivityAction.CREATE,
        module=MODULE,
        description=(
            f"Recorded {record.sick_count} sick bird(s) in {batch.batch_code}"
            + (f" — {record.diagnosis}" if record.diagnosis else "")
        ),
        entity_id=record.id,
    )
    notification_service.push(
        db,
        type_=NotificationType.HEALTH_ALERT,
        severity=(
            NotificationSeverity.CRITICAL
            if record.status == HealthStatus.CRITICAL
            else NotificationSeverity.WARNING
        ),
        title=f"Birds need attention in {batch.batch_code}",
        message=(
            f"{record.sick_count} bird(s) reported as {record.status.value.replace('_', ' ').lower()}"
            + (f" ({record.diagnosis})" if record.diagnosis else "")
            + "."
        ),
        module=MODULE,
        entity_id=record.id,
    )
    db.commit()
    db.refresh(record)
    return to_out(record)


def update_record(
    db: Session, record_id: int, payload: HealthUpdate, actor: Optional[User]
) -> HealthOut:
    record = get_record(db, record_id)
    batch = bird_service.get_batch(db, record.batch_id)
    data = payload.model_dump(exclude_unset=True)

    new_status = data.get("status", record.status)
    new_count = data.get("sick_count", record.sick_count)
    if new_status in HealthRecord.OPEN_STATUSES:
        _assert_capacity(db, batch, new_count, exclude_record_id=record.id)

    for field in (
        "record_date",
        "sick_count",
        "symptoms",
        "diagnosis",
        "treatment",
        "medicine",
        "dosage",
        "veterinarian",
        "status",
        "notes",
    ):
        if field in data and data[field] is not None:
            setattr(record, field, data[field])
    if "treatment_cost" in data and data["treatment_cost"] is not None:
        record.treatment_cost = money(data["treatment_cost"])
    record.updated_by_id = actor.id if actor else None

    _sync_expense(db, record, batch.batch_code, actor)
    activity_service.record(
        db,
        user=actor,
        action=ActivityAction.UPDATE,
        module=MODULE,
        description=f"Updated health record #{record.id} ({batch.batch_code}) → {record.status.value}",
        entity_id=record.id,
    )
    db.commit()
    db.refresh(record)
    return to_out(record)


def delete_record(db: Session, record_id: int, actor: Optional[User]) -> None:
    record = get_record(db, record_id)
    record.is_deleted = True
    record.deleted_at = datetime.utcnow()
    record.deleted_by_id = actor.id if actor else None
    expense_service.remove_system_expense(db, ExpenseSource.HEALTH_RECORD, record.id, actor)

    activity_service.record(
        db,
        user=actor,
        action=ActivityAction.DELETE,
        module=MODULE,
        description=f"Removed health record #{record.id}",
        entity_id=record.id,
    )
    db.commit()


def _sync_expense(db: Session, record: HealthRecord, batch_code: str, actor: Optional[User]) -> None:
    """Treatment cost flows straight into the Medicine expense category."""
    expense_service.sync_system_expense(
        db,
        source_type=ExpenseSource.HEALTH_RECORD,
        source_id=record.id,
        category_name="Medicine",
        description=(
            f"Treatment for {record.sick_count} bird(s) in {batch_code}"
            + (f" — {record.medicine}" if record.medicine else "")
        ),
        amount=record.treatment_cost,
        expense_date=record.record_date,
        vendor=record.veterinarian,
        actor=actor,
    )


def status_counts(db: Session) -> dict:
    from sqlalchemy import func

    rows = db.execute(
        select(HealthRecord.status, func.coalesce(func.sum(HealthRecord.sick_count), 0))
        .where(HealthRecord.is_deleted.is_(False))
        .group_by(HealthRecord.status)
    ).all()
    counts = {status.value: 0 for status in HealthStatus}
    for status, total in rows:
        counts[status.value] = int(total)
    return counts
