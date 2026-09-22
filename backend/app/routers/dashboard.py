"""Dashboard endpoint."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import require_staff
from app.models.user import User
from app.schemas.dashboard import DashboardSummary
from app.services import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get(
    "/summary",
    response_model=DashboardSummary,
    summary="Everything the dashboard shows, computed from the database",
)
def summary(db: Session = Depends(get_db), user: User = Depends(require_staff)):
    return dashboard_service.summary(db, user)
