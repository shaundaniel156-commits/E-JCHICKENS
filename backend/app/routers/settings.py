"""Farm settings endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import require_admin, require_staff
from app.models.user import User
from app.schemas.system import FarmSettingsOut, FarmSettingsUpdate
from app.services import settings_service

router = APIRouter(prefix="/settings", tags=["Settings"])


@router.get("", response_model=FarmSettingsOut, summary="Read the farm settings")
def read_settings(db: Session = Depends(get_db), _user: User = Depends(require_staff)):
    settings = settings_service.get_settings(db)
    db.commit()
    return settings


@router.put("", response_model=FarmSettingsOut, summary="Update the farm settings")
def update_settings(
    payload: FarmSettingsUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    return settings_service.update_settings(db, payload, admin)
