"""Farm settings live in a single row; the getter creates it on first use."""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import settings as app_settings
from app.models.enums import ActivityAction
from app.models.system import FarmSetting
from app.models.user import User
from app.schemas.system import FarmSettingsUpdate
from app.services import activity_service


def get_settings(db: Session) -> FarmSetting:
    record = db.get(FarmSetting, 1)
    if record is None:
        record = FarmSetting(
            id=1,
            farm_name=app_settings.APP_NAME,
            currency=app_settings.DEFAULT_CURRENCY,
            low_feed_threshold_bags=app_settings.LOW_FEED_THRESHOLD_BAGS,
            high_mortality_rate_percent=app_settings.HIGH_MORTALITY_RATE_PERCENT,
            budget_warning_percent=app_settings.BUDGET_WARNING_PERCENT,
        )
        db.add(record)
        db.flush()
    return record


def currency(db: Session) -> str:
    """The farm's configured currency code, for any user-facing text."""
    return get_settings(db).currency or app_settings.DEFAULT_CURRENCY


def money_text(db: Session, amount) -> str:
    """Format an amount the way the farm sees it, e.g. "UGX 800,000"."""
    from app.utils.money import format_ugx

    return format_ugx(amount, currency(db))


def update_settings(
    db: Session, payload: FarmSettingsUpdate, actor: Optional[User] = None
) -> FarmSetting:
    record = get_settings(db)
    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(record, field, value)

    if changes:
        activity_service.record(
            db,
            user=actor,
            action=ActivityAction.UPDATE,
            module="settings",
            description=f"Updated farm settings ({', '.join(sorted(changes))})",
            entity_id=record.id,
        )
    db.commit()
    db.refresh(record)
    return record
