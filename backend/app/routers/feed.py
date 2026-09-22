"""Feed endpoints: types, purchases, consumption and stock."""
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import require_admin, require_manager, require_staff
from app.dependencies.filters import PageParams, PeriodParams, pagination, period
from app.models.user import User
from app.schemas.common import Message, Page
from app.schemas.feed import (
    FeedConsumptionCreate,
    FeedConsumptionOut,
    FeedConsumptionUpdate,
    FeedPurchaseCreate,
    FeedPurchaseOut,
    FeedPurchaseUpdate,
    FeedStockSummary,
    FeedTypeCreate,
    FeedTypeOut,
    FeedTypeUpdate,
)
from app.services import feed_service

router = APIRouter(prefix="/feed", tags=["Feed"])


# --------------------------------------------------------------------------- stock
@router.get("/stock", response_model=FeedStockSummary, summary="Current feed stock")
def stock(db: Session = Depends(get_db), _user: User = Depends(require_staff)):
    return feed_service.stock_summary(db)


# --------------------------------------------------------------------------- types
@router.get("/types", response_model=List[FeedTypeOut], summary="List feed types with stock")
def list_types(db: Session = Depends(get_db), _user: User = Depends(require_staff)):
    return feed_service.list_feed_types(db)


@router.post(
    "/types", response_model=FeedTypeOut, status_code=status.HTTP_201_CREATED, summary="Add a feed type"
)
def create_type(
    payload: FeedTypeCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_manager),
):
    return feed_service.create_feed_type(db, payload, user)


@router.put("/types/{feed_type_id}", response_model=FeedTypeOut, summary="Update a feed type")
def update_type(
    feed_type_id: int,
    payload: FeedTypeUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_manager),
):
    return feed_service.update_feed_type(db, feed_type_id, payload, user)


@router.delete("/types/{feed_type_id}", response_model=Message, summary="Delete an unused feed type")
def delete_type(
    feed_type_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    feed_service.delete_feed_type(db, feed_type_id, user)
    return Message(message="The feed type has been removed.")


# --------------------------------------------------------------------------- purchases
@router.get("/purchases", response_model=Page[FeedPurchaseOut], summary="List feed purchases")
def list_purchases(
    page_params: PageParams = Depends(pagination),
    dates: PeriodParams = Depends(period),
    feed_type_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    sort: str = Query("purchase_date"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_staff),
):
    items, meta = feed_service.list_purchases(
        db,
        page=page_params.page,
        page_size=page_params.page_size,
        feed_type_id=feed_type_id,
        search=search,
        start_date=dates.start_date,
        end_date=dates.end_date,
        sort=sort,
        order=order,
    )
    return Page[FeedPurchaseOut](items=items, meta=meta)


@router.post(
    "/purchases",
    response_model=FeedPurchaseOut,
    status_code=status.HTTP_201_CREATED,
    summary="Record a feed purchase",
)
def create_purchase(
    payload: FeedPurchaseCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_manager),
):
    return feed_service.create_purchase(db, payload, user)


@router.put("/purchases/{purchase_id}", response_model=FeedPurchaseOut, summary="Update a purchase")
def update_purchase(
    purchase_id: int,
    payload: FeedPurchaseUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_manager),
):
    return feed_service.update_purchase(db, purchase_id, payload, user)


@router.delete("/purchases/{purchase_id}", response_model=Message, summary="Reverse a purchase")
def delete_purchase(
    purchase_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_manager),
):
    feed_service.delete_purchase(db, purchase_id, user)
    return Message(message="The feed purchase has been reversed.")


# --------------------------------------------------------------------------- consumption
@router.get("/consumption", response_model=Page[FeedConsumptionOut], summary="List feed consumption")
def list_consumption(
    page_params: PageParams = Depends(pagination),
    dates: PeriodParams = Depends(period),
    feed_type_id: Optional[int] = Query(None),
    batch_id: Optional[int] = Query(None),
    sort: str = Query("consumption_date"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_staff),
):
    items, meta = feed_service.list_consumption(
        db,
        page=page_params.page,
        page_size=page_params.page_size,
        feed_type_id=feed_type_id,
        batch_id=batch_id,
        start_date=dates.start_date,
        end_date=dates.end_date,
        sort=sort,
        order=order,
    )
    return Page[FeedConsumptionOut](items=items, meta=meta)


@router.post(
    "/consumption",
    response_model=FeedConsumptionOut,
    status_code=status.HTTP_201_CREATED,
    summary="Record feed consumption",
)
def create_consumption(
    payload: FeedConsumptionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_staff),
):
    return feed_service.create_consumption(db, payload, user)


@router.put(
    "/consumption/{consumption_id}",
    response_model=FeedConsumptionOut,
    summary="Update a consumption record",
)
def update_consumption(
    consumption_id: int,
    payload: FeedConsumptionUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_manager),
):
    return feed_service.update_consumption(db, consumption_id, payload, user)


@router.delete(
    "/consumption/{consumption_id}", response_model=Message, summary="Reverse a consumption record"
)
def delete_consumption(
    consumption_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_manager),
):
    feed_service.delete_consumption(db, consumption_id, user)
    return Message(message="The consumption record has been reversed.")
