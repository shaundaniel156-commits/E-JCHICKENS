"""Activity log endpoints (administrators only)."""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import require_admin
from app.dependencies.filters import PageParams, pagination
from app.models.enums import ActivityAction
from app.models.user import User
from app.schemas.common import Page
from app.schemas.system import ActivityLogOut
from app.services import activity_service

router = APIRouter(prefix="/activity", tags=["Activity log"])


@router.get("", response_model=Page[ActivityLogOut], summary="Browse the audit trail")
def list_activity(
    page_params: PageParams = Depends(pagination),
    module: Optional[str] = Query(None),
    action: Optional[ActivityAction] = Query(None),
    user_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    rows, meta = activity_service.list_logs(
        db,
        page=page_params.page,
        page_size=page_params.page_size,
        module=module,
        action=action,
        user_id=user_id,
        search=search,
    )
    return Page[ActivityLogOut](
        items=[ActivityLogOut.model_validate(row) for row in rows], meta=meta
    )
