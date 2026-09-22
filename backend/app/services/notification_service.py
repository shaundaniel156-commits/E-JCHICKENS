"""Notifications are raised automatically by the modules that change farm state."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.enums import NotificationSeverity, NotificationType
from app.models.system import Notification
from app.utils.pagination import paginate


def push(
    db: Session,
    *,
    type_: NotificationType,
    title: str,
    message: str,
    severity: NotificationSeverity = NotificationSeverity.INFO,
    module: Optional[str] = None,
    entity_id: Optional[int] = None,
    user_id: Optional[int] = None,
    dedupe_key: Optional[str] = None,
) -> Optional[Notification]:
    """Add a notification unless an identical unread one already exists.

    `dedupe_key` stops recurring conditions (low feed, exceeded budget) from
    producing a new alert on every single save.
    """
    from app.services import settings_service

    if not settings_service.get_settings(db).notifications_enabled:
        return None

    if dedupe_key:
        existing = db.execute(
            select(Notification).where(
                Notification.dedupe_key == dedupe_key, Notification.is_read.is_(False)
            )
        ).scalars().first()
        if existing:
            existing.message = message
            existing.created_at = datetime.utcnow()
            return existing

    notification = Notification(
        type=type_,
        severity=severity,
        title=title[:160],
        message=message,
        module=module,
        entity_id=entity_id,
        user_id=user_id,
        dedupe_key=dedupe_key,
    )
    db.add(notification)
    return notification


def clear_dedupe(db: Session, dedupe_key: str) -> None:
    """Resolve an open condition so the alert can fire again if it comes back."""
    rows = db.execute(
        select(Notification).where(
            Notification.dedupe_key == dedupe_key, Notification.is_read.is_(False)
        )
    ).scalars().all()
    for row in rows:
        row.is_read = True
        row.read_at = datetime.utcnow()


def _visible_for(user_id: int):
    return (Notification.user_id.is_(None)) | (Notification.user_id == user_id)


def list_notifications(
    db: Session,
    *,
    user_id: int,
    page: int = 1,
    page_size: int = 20,
    unread_only: bool = False,
    type_: Optional[NotificationType] = None,
):
    stmt = select(Notification).where(_visible_for(user_id))
    if unread_only:
        stmt = stmt.where(Notification.is_read.is_(False))
    if type_:
        stmt = stmt.where(Notification.type == type_)
    stmt = stmt.order_by(Notification.created_at.desc(), Notification.id.desc())
    return paginate(db, stmt, page, page_size)


def counts(db: Session, user_id: int) -> tuple[int, int]:
    total = db.execute(
        select(func.count(Notification.id)).where(_visible_for(user_id))
    ).scalar_one()
    unread = db.execute(
        select(func.count(Notification.id)).where(
            _visible_for(user_id), Notification.is_read.is_(False)
        )
    ).scalar_one()
    return int(total), int(unread)


def alerts(db: Session, user_id: int, limit: int = 5) -> list[Notification]:
    """Unread warnings and criticals for the dashboard alert panel."""
    stmt = (
        select(Notification)
        .where(
            _visible_for(user_id),
            Notification.is_read.is_(False),
            Notification.severity.in_(
                [NotificationSeverity.WARNING, NotificationSeverity.CRITICAL]
            ),
        )
        .order_by(Notification.created_at.desc())
        .limit(limit)
    )
    return list(db.execute(stmt).scalars().all())


def mark_read(db: Session, notification_id: int, user_id: int) -> Notification:
    notification = db.get(Notification, notification_id)
    if not notification or (notification.user_id not in (None, user_id)):
        raise NotFoundError("Notification not found.")
    notification.is_read = True
    notification.read_at = datetime.utcnow()
    db.commit()
    db.refresh(notification)
    return notification


def mark_all_read(db: Session, user_id: int) -> int:
    rows = db.execute(
        select(Notification).where(_visible_for(user_id), Notification.is_read.is_(False))
    ).scalars().all()
    now = datetime.utcnow()
    for row in rows:
        row.is_read = True
        row.read_at = now
    db.commit()
    return len(rows)


def delete(db: Session, notification_id: int, user_id: int) -> None:
    notification = db.get(Notification, notification_id)
    if not notification or (notification.user_id not in (None, user_id)):
        raise NotFoundError("Notification not found.")
    db.delete(notification)
    db.commit()
