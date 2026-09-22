"""Bird batch endpoints."""
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import require_admin, require_manager, require_staff
from app.dependencies.filters import PageParams, PeriodParams, pagination, period
from app.models.enums import BatchStatus
from app.models.user import User
from app.schemas.bird import BatchAdjustment, BirdBatchCreate, BirdBatchOut, BirdBatchUpdate
from app.schemas.common import Message, Page
from app.services import bird_service

router = APIRouter(prefix="/birds", tags=["Birds"])


@router.get("", response_model=Page[BirdBatchOut], summary="List bird batches")
def list_batches(
    page_params: PageParams = Depends(pagination),
    dates: PeriodParams = Depends(period),
    search: Optional[str] = Query(None, description="Batch code, breed or source"),
    status_filter: Optional[BatchStatus] = Query(None, alias="status"),
    sort: str = Query("acquisition_date"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_staff),
):
    items, meta = bird_service.list_batches(
        db,
        page=page_params.page,
        page_size=page_params.page_size,
        search=search,
        status=status_filter,
        start_date=dates.start_date,
        end_date=dates.end_date,
        sort=sort,
        order=order,
    )
    return Page[BirdBatchOut](items=items, meta=meta)


@router.get("/options", response_model=List[BirdBatchOut], summary="All batches, for dropdowns")
def batch_options(
    active_only: bool = Query(False),
    db: Session = Depends(get_db),
    _user: User = Depends(require_staff),
):
    return bird_service.all_batches_out(db, active_only=active_only)


@router.get("/{batch_id}", response_model=BirdBatchOut, summary="Fetch one batch")
def get_batch(
    batch_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_staff),
):
    return bird_service.to_out(db, bird_service.get_batch(db, batch_id))


@router.post(
    "", response_model=BirdBatchOut, status_code=status.HTTP_201_CREATED, summary="Add a batch"
)
def create_batch(
    payload: BirdBatchCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_manager),
):
    return bird_service.create_batch(db, payload, user)


@router.put(
    "/{batch_id}",
    response_model=BirdBatchOut,
    summary="Update a batch (staff may change breed, source, age and notes only)",
)
def update_batch(
    batch_id: int,
    payload: BirdBatchUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_staff),
):
    return bird_service.update_batch(db, batch_id, payload, user)


@router.post(
    "/{batch_id}/adjust",
    response_model=BirdBatchOut,
    summary="Record a non-mortality loss (theft, escape, miscount)",
)
def adjust_batch(
    batch_id: int,
    payload: BatchAdjustment,
    db: Session = Depends(get_db),
    user: User = Depends(require_manager),
):
    return bird_service.adjust_batch(db, batch_id, payload, user)


@router.delete("/{batch_id}", response_model=Message, summary="Delete an empty batch")
def delete_batch(
    batch_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    bird_service.delete_batch(db, batch_id, user)
    return Message(message="The batch has been removed.")
