"""Expense and expense-category endpoints."""
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import require_admin, require_manager, require_staff
from app.dependencies.filters import PageParams, PeriodParams, pagination, period
from app.models.user import User
from app.schemas.common import Message, Page
from app.schemas.finance import (
    CategoryBreakdown,
    ExpenseCategoryCreate,
    ExpenseCategoryOut,
    ExpenseCreate,
    ExpenseOut,
    ExpenseUpdate,
)
from app.services import expense_service

router = APIRouter(prefix="/expenses", tags=["Expenses"])


@router.get("/categories", response_model=List[ExpenseCategoryOut], summary="List categories")
def list_categories(db: Session = Depends(get_db), _user: User = Depends(require_staff)):
    return expense_service.list_categories(db)


@router.post(
    "/categories",
    response_model=ExpenseCategoryOut,
    status_code=status.HTTP_201_CREATED,
    summary="Add a category",
)
def create_category(
    payload: ExpenseCategoryCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_manager),
):
    return expense_service.create_category(db, payload, user)


@router.delete("/categories/{category_id}", response_model=Message, summary="Delete a category")
def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    expense_service.delete_category(db, category_id, user)
    return Message(message="The category has been removed.")


@router.get("/breakdown", response_model=List[CategoryBreakdown], summary="Expenses by category")
def breakdown(
    dates: PeriodParams = Depends(period),
    db: Session = Depends(get_db),
    _user: User = Depends(require_manager),
):
    return expense_service.category_breakdown(db, dates.start_date, dates.end_date)


@router.get("", response_model=Page[ExpenseOut], summary="List expenses")
def list_expenses(
    page_params: PageParams = Depends(pagination),
    dates: PeriodParams = Depends(period),
    category_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    sort: str = Query("expense_date"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_manager),
):
    items, meta = expense_service.list_expenses(
        db,
        page=page_params.page,
        page_size=page_params.page_size,
        search=search,
        category_id=category_id,
        start_date=dates.start_date,
        end_date=dates.end_date,
        sort=sort,
        order=order,
    )
    return Page[ExpenseOut](items=items, meta=meta)


@router.post(
    "", response_model=ExpenseOut, status_code=status.HTTP_201_CREATED, summary="Record an expense"
)
def create_expense(
    payload: ExpenseCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_manager),
):
    return expense_service.create_expense(db, payload, user)


@router.get("/{expense_id}", response_model=ExpenseOut, summary="Fetch one expense")
def get_expense(
    expense_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_manager),
):
    return expense_service.to_out(expense_service.get_expense(db, expense_id))


@router.put("/{expense_id}", response_model=ExpenseOut, summary="Update an expense")
def update_expense(
    expense_id: int,
    payload: ExpenseUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_manager),
):
    return expense_service.update_expense(db, expense_id, payload, user)


@router.delete("/{expense_id}", response_model=Message, summary="Reverse an expense")
def delete_expense(
    expense_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_manager),
):
    expense_service.delete_expense(db, expense_id, user)
    return Message(message="The expense has been reversed.")
