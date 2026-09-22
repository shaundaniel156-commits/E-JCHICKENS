"""Notification endpoints."""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.filters import PageParams, pagination
from app.models.enums import NotificationType
from app.models.user import User
from app.schemas.common import Message, Page
from app.schemas.system import NotificationCount, NotificationOut
from app.services import notification_service

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=Page[NotificationOut], summary="List notifications")
def list_notifications(
    page_params: PageParams = Depends(pagination),
    unread_only: bool = Query(False),
    type_filter: Optional[NotificationType] = Query(None, alias="type"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rows, meta = notification_service.list_notifications(
        db,
        user_id=user.id,
        page=page_params.page,
        page_size=page_params.page_size,
        unread_only=unread_only,
        type_=type_filter,
    )
    return Page[NotificationOut](
        items=[NotificationOut.model_validate(row) for row in rows], meta=meta
    )


@router.get("/count", response_model=NotificationCount, summary="Unread badge count")
def count(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    total, unread = notification_service.counts(db, user.id)
    return NotificationCount(total=total, unread=unread)


@router.post("/{notification_id}/read", response_model=NotificationOut, summary="Mark as read")
def mark_read(
    notification_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return NotificationOut.model_validate(
        notification_service.mark_read(db, notification_id, user.id)
    )


@router.post("/read-all", response_model=Message, summary="Mark everything as read")
def mark_all_read(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    count = notification_service.mark_all_read(db, user.id)
    return Message(message=f"{count} notification(s) marked as read.")


@router.delete("/{notification_id}", response_model=Message, summary="Dismiss a notification")
def delete(
    notification_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    notification_service.delete(db, notification_id, user.id)
    return Message(message="Notification dismissed.")
