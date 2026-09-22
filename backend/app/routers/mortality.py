"""Mortality endpoints."""
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import require_manager, require_staff
from app.dependencies.filters import PageParams, PeriodParams, pagination, period
from app.models.user import User
from app.schemas.bird import MortalityCreate, MortalityOut, MortalityUpdate
from app.schemas.common import Message, Page
from app.schemas.dashboard import SeriesPoint
from app.services import mortality_service

router = APIRouter(prefix="/mortality", tags=["Mortality"])


@router.get("", response_model=Page[MortalityOut], summary="List mortality records")
def list_records(
    page_params: PageParams = Depends(pagination),
    dates: PeriodParams = Depends(period),
    batch_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    sort: str = Query("record_date"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_staff),
):
    items, meta = mortality_service.list_records(
        db,
        page=page_params.page,
        page_size=page_params.page_size,
        batch_id=batch_id,
        search=search,
        start_date=dates.start_date,
        end_date=dates.end_date,
        sort=sort,
        order=order,
    )
    return Page[MortalityOut](items=items, meta=meta)


@router.get("/series", response_model=List[SeriesPoint], summary="Deaths by day, week or month")
def series(
    grouping: str = Query("day", pattern="^(day|week|month)$"),
    days: int = Query(30, ge=7, le=90),
    db: Session = Depends(get_db),
    _user: User = Depends(require_staff),
):
    return mortality_service.series(db, grouping=grouping, days=days)


@router.post(
    "", response_model=MortalityOut, status_code=status.HTTP_201_CREATED, summary="Record deaths"
)
def create_record(
    payload: MortalityCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_staff),
):
    return mortality_service.create_record(db, payload, user)


@router.put("/{record_id}", response_model=MortalityOut, summary="Update a mortality record")
def update_record(
    record_id: int,
    payload: MortalityUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_manager),
):
    return mortality_service.update_record(db, record_id, payload, user)


@router.delete("/{record_id}", response_model=Message, summary="Reverse a mortality record")
def delete_record(
    record_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_manager),
):
    mortality_service.delete_record(db, record_id, user)
    return Message(message="The mortality record has been reversed.")
