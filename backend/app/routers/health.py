"""Health record endpoints."""
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import require_manager, require_staff
from app.dependencies.filters import PageParams, PeriodParams, pagination, period
from app.models.enums import HealthStatus
from app.models.user import User
from app.schemas.bird import HealthCreate, HealthOut, HealthUpdate
from app.schemas.common import Message, Page
from app.services import health_service

router = APIRouter(prefix="/health-records", tags=["Health"])


@router.get("", response_model=Page[HealthOut], summary="List health records")
def list_records(
    page_params: PageParams = Depends(pagination),
    dates: PeriodParams = Depends(period),
    batch_id: Optional[int] = Query(None),
    status_filter: Optional[HealthStatus] = Query(None, alias="status"),
    search: Optional[str] = Query(None),
    sort: str = Query("record_date"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_staff),
):
    items, meta = health_service.list_records(
        db,
        page=page_params.page,
        page_size=page_params.page_size,
        batch_id=batch_id,
        status=status_filter,
        search=search,
        start_date=dates.start_date,
        end_date=dates.end_date,
        sort=sort,
        order=order,
    )
    return Page[HealthOut](items=items, meta=meta)


@router.get("/summary", summary="Sick birds grouped by status")
def status_summary(
    db: Session = Depends(get_db),
    _user: User = Depends(require_staff),
):
    return health_service.status_counts(db)


@router.post(
    "", response_model=HealthOut, status_code=status.HTTP_201_CREATED, summary="Record sick birds"
)
def create_record(
    payload: HealthCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_staff),
):
    return health_service.create_record(db, payload, user)


@router.put("/{record_id}", response_model=HealthOut, summary="Update a health record")
def update_record(
    record_id: int,
    payload: HealthUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_staff),
):
    return health_service.update_record(db, record_id, payload, user)


@router.delete("/{record_id}", response_model=Message, summary="Remove a health record")
def delete_record(
    record_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_manager),
):
    health_service.delete_record(db, record_id, user)
    return Message(message="The health record has been removed.")
