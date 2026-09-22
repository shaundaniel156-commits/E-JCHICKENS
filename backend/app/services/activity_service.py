"""Audit trail. Every service calls `record` inside its own transaction."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models.enums import ActivityAction
from app.models.system import ActivityLog
from app.models.user import User
from app.utils.pagination import paginate


def record(
    db: Session,
    *,
    user: Optional[User],
    action: ActivityAction,
    module: str,
    description: str,
    entity_id: Optional[int] = None,
    ip_address: Optional[str] = None,
) -> ActivityLog:
    """Add a log entry to the current transaction (the caller commits)."""
    entry = ActivityLog(
        user_id=user.id if user else None,
        user_display=user.full_name if user else "System",
        action=action,
        module=module,
        description=description[:400],
        entity_id=entity_id,
        ip_address=ip_address,
        created_at=datetime.utcnow(),
    )
    db.add(entry)
    return entry


def _base_query(
    module: Optional[str] = None,
    action: Optional[ActivityAction] = None,
    user_id: Optional[int] = None,
    search: Optional[str] = None,
) -> Select:
    stmt = select(ActivityLog)
    if module:
        stmt = stmt.where(ActivityLog.module == module)
    if action:
        stmt = stmt.where(ActivityLog.action == action)
    if user_id:
        stmt = stmt.where(ActivityLog.user_id == user_id)
    if search:
        pattern = f"%{search.strip()}%"
        stmt = stmt.where(
            ActivityLog.description.ilike(pattern) | ActivityLog.user_display.ilike(pattern)
        )
    return stmt.order_by(ActivityLog.created_at.desc(), ActivityLog.id.desc())


def list_logs(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 25,
    module: Optional[str] = None,
    action: Optional[ActivityAction] = None,
    user_id: Optional[int] = None,
    search: Optional[str] = None,
):
    return paginate(db, _base_query(module, action, user_id, search), page, page_size)


def recent(db: Session, limit: int = 10) -> list[ActivityLog]:
    return list(db.execute(_base_query().limit(limit)).scalars().all())
