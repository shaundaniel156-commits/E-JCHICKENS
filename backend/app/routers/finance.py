"""Finance summary and budget endpoints."""
from typing import List

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import require_admin, require_manager
from app.dependencies.filters import PeriodParams, period
from app.models.user import User
from app.schemas.common import Message
from app.schemas.finance import BudgetCreate, BudgetOut, BudgetUpdate, FinanceSummary
from app.services import budget_service, finance_service

router = APIRouter(tags=["Finance"])


@router.get("/finance/summary", response_model=FinanceSummary, summary="Finance dashboard figures")
def summary(
    dates: PeriodParams = Depends(period),
    db: Session = Depends(get_db),
    _user: User = Depends(require_manager),
):
    return finance_service.finance_summary(db, dates.start_date, dates.end_date)


@router.get("/budgets", response_model=List[BudgetOut], summary="List budgets")
def list_budgets(db: Session = Depends(get_db), _user: User = Depends(require_manager)):
    return budget_service.list_budgets(db)


@router.get("/budgets/active", response_model=BudgetOut | None, summary="The budget in force today")
def active_budget(db: Session = Depends(get_db), _user: User = Depends(require_manager)):
    return budget_service.active_budget_out(db)


@router.post(
    "/budgets", response_model=BudgetOut, status_code=status.HTTP_201_CREATED, summary="Create a budget"
)
def create_budget(
    payload: BudgetCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    return budget_service.create_budget(db, payload, user)


@router.put("/budgets/{budget_id}", response_model=BudgetOut, summary="Update a budget")
def update_budget(
    budget_id: int,
    payload: BudgetUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    return budget_service.update_budget(db, budget_id, payload, user)


@router.delete("/budgets/{budget_id}", response_model=Message, summary="Delete a budget")
def delete_budget(
    budget_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    budget_service.delete_budget(db, budget_id, user)
    return Message(message="The budget has been removed.")
