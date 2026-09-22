"""Sales and customer endpoints."""
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import require_manager, require_staff
from app.dependencies.filters import PageParams, PeriodParams, pagination, period
from app.models.enums import PaymentStatus
from app.models.user import User
from app.schemas.common import Message, Page
from app.schemas.finance import (
    CustomerCreate,
    CustomerOut,
    CustomerUpdate,
    SaleCreate,
    SaleOut,
    SaleUpdate,
)
from app.services import sale_service

router = APIRouter(tags=["Sales"])


# --------------------------------------------------------------------------- customers
@router.get("/customers", response_model=Page[CustomerOut], summary="List customers")
def list_customers(
    page_params: PageParams = Depends(pagination),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _user: User = Depends(require_staff),
):
    items, meta = sale_service.list_customers(
        db, page=page_params.page, page_size=page_params.page_size, search=search
    )
    return Page[CustomerOut](items=items, meta=meta)


@router.post(
    "/customers",
    response_model=CustomerOut,
    status_code=status.HTTP_201_CREATED,
    summary="Add a customer",
)
def create_customer(
    payload: CustomerCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_staff),
):
    return sale_service.create_customer(db, payload, user)


@router.put("/customers/{customer_id}", response_model=CustomerOut, summary="Update a customer")
def update_customer(
    customer_id: int,
    payload: CustomerUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_manager),
):
    return sale_service.update_customer(db, customer_id, payload, user)


@router.delete("/customers/{customer_id}", response_model=Message, summary="Delete a customer")
def delete_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_manager),
):
    sale_service.delete_customer(db, customer_id, user)
    return Message(message="The customer has been removed.")


# --------------------------------------------------------------------------- sales
@router.get("/sales", response_model=Page[SaleOut], summary="List sales")
def list_sales(
    page_params: PageParams = Depends(pagination),
    dates: PeriodParams = Depends(period),
    batch_id: Optional[int] = Query(None),
    customer_id: Optional[int] = Query(None),
    payment_status: Optional[PaymentStatus] = Query(None),
    search: Optional[str] = Query(None),
    sort: str = Query("sale_date"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_staff),
):
    items, meta = sale_service.list_sales(
        db,
        page=page_params.page,
        page_size=page_params.page_size,
        batch_id=batch_id,
        customer_id=customer_id,
        payment_status=payment_status,
        search=search,
        start_date=dates.start_date,
        end_date=dates.end_date,
        sort=sort,
        order=order,
    )
    return Page[SaleOut](items=items, meta=meta)


@router.post(
    "/sales", response_model=SaleOut, status_code=status.HTTP_201_CREATED, summary="Record a sale"
)
def create_sale(
    payload: SaleCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_manager),
):
    return sale_service.create_sale(db, payload, user)


@router.get("/sales/{sale_id}", response_model=SaleOut, summary="Fetch one sale")
def get_sale(
    sale_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_staff),
):
    return sale_service.to_out(sale_service.get_sale(db, sale_id))


@router.put("/sales/{sale_id}", response_model=SaleOut, summary="Update a sale")
def update_sale(
    sale_id: int,
    payload: SaleUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_manager),
):
    return sale_service.update_sale(db, sale_id, payload, user)


@router.delete("/sales/{sale_id}", response_model=Message, summary="Reverse a sale")
def delete_sale(
    sale_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_manager),
):
    sale_service.delete_sale(db, sale_id, user)
    return Message(message="The sale has been reversed and the birds returned to the batch.")
