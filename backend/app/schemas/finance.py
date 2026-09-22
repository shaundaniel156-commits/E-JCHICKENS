"""Expense, sale, customer, budget and finance-summary payloads."""
from datetime import date
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from app.models.enums import ExpenseSource, PaymentMethod, PaymentStatus
from app.schemas.common import Money, NonNegativeMoney, ORMModel, PositiveMoney


def _not_in_future(value: date) -> date:
    if value > date.today():
        raise ValueError("The date cannot be in the future.")
    return value


# --------------------------------------------------------------------------- expenses
class ExpenseCategoryCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    description: Optional[str] = Field(default=None, max_length=255)


class ExpenseCategoryOut(ORMModel):
    id: int
    name: str
    description: Optional[str] = None
    is_system: bool


class ExpenseCreate(BaseModel):
    expense_date: date
    category_id: int = Field(gt=0)
    description: str = Field(min_length=2, max_length=255)
    amount: PositiveMoney
    vendor: Optional[str] = Field(default=None, max_length=160)
    payment_method: PaymentMethod = PaymentMethod.CASH
    reference_number: Optional[str] = Field(default=None, max_length=80)
    receipt_url: Optional[str] = Field(default=None, max_length=255)
    notes: Optional[str] = None

    _check_date = field_validator("expense_date")(_not_in_future)


class ExpenseUpdate(BaseModel):
    expense_date: Optional[date] = None
    category_id: Optional[int] = Field(default=None, gt=0)
    description: Optional[str] = Field(default=None, min_length=2, max_length=255)
    amount: Optional[PositiveMoney] = None
    vendor: Optional[str] = Field(default=None, max_length=160)
    payment_method: Optional[PaymentMethod] = None
    reference_number: Optional[str] = Field(default=None, max_length=80)
    receipt_url: Optional[str] = Field(default=None, max_length=255)
    notes: Optional[str] = None


class ExpenseOut(ORMModel):
    id: int
    expense_date: date
    category_id: int
    category_name: Optional[str] = None
    description: str
    amount: NonNegativeMoney
    vendor: Optional[str] = None
    payment_method: PaymentMethod
    reference_number: Optional[str] = None
    receipt_url: Optional[str] = None
    notes: Optional[str] = None
    source_type: ExpenseSource
    source_id: Optional[int] = None
    is_system_generated: bool = False


class CategoryBreakdown(BaseModel):
    category_id: Optional[int] = None
    category: str
    amount: NonNegativeMoney
    percentage: float
    count: int = 0


# --------------------------------------------------------------------------- customers
class CustomerCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    phone: Optional[str] = Field(default=None, max_length=30)
    email: Optional[EmailStr] = None
    address: Optional[str] = Field(default=None, max_length=255)
    notes: Optional[str] = None


class CustomerUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=160)
    phone: Optional[str] = Field(default=None, max_length=30)
    email: Optional[EmailStr] = None
    address: Optional[str] = Field(default=None, max_length=255)
    notes: Optional[str] = None


class CustomerOut(ORMModel):
    id: int
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None
    total_purchases: NonNegativeMoney = Decimal("0")
    birds_bought: int = 0


# --------------------------------------------------------------------------- sales
class SaleCreate(BaseModel):
    sale_date: date
    batch_id: int = Field(gt=0)
    customer_id: Optional[int] = Field(default=None, gt=0)
    customer_name: Optional[str] = Field(
        default=None, max_length=160, description="Creates the customer when no id is given"
    )
    quantity: int = Field(gt=0, le=1_000_000)
    unit_price: NonNegativeMoney
    amount_paid: Optional[NonNegativeMoney] = None
    payment_status: PaymentStatus = PaymentStatus.PAID
    payment_method: PaymentMethod = PaymentMethod.CASH
    notes: Optional[str] = None

    _check_date = field_validator("sale_date")(_not_in_future)

    @model_validator(mode="after")
    def _check_payment(self):
        if self.payment_status == PaymentStatus.CANCELLED:
            raise ValueError("A new sale cannot be created as cancelled.")
        total = self.unit_price * self.quantity
        if self.amount_paid is not None and self.amount_paid > total:
            raise ValueError("Amount paid cannot be greater than the sale total.")
        return self


class SaleUpdate(BaseModel):
    sale_date: Optional[date] = None
    customer_id: Optional[int] = Field(default=None, gt=0)
    quantity: Optional[int] = Field(default=None, gt=0, le=1_000_000)
    unit_price: Optional[NonNegativeMoney] = None
    amount_paid: Optional[NonNegativeMoney] = None
    payment_status: Optional[PaymentStatus] = None
    payment_method: Optional[PaymentMethod] = None
    notes: Optional[str] = None


class SaleOut(ORMModel):
    id: int
    reference: str
    sale_date: date
    batch_id: int
    batch_code: Optional[str] = None
    customer_id: Optional[int] = None
    customer_name: Optional[str] = None
    quantity: int
    unit_price: NonNegativeMoney
    total_amount: NonNegativeMoney
    amount_paid: NonNegativeMoney
    balance_due: NonNegativeMoney
    payment_status: PaymentStatus
    payment_method: PaymentMethod
    notes: Optional[str] = None


# --------------------------------------------------------------------------- budgets
class BudgetCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    amount: PositiveMoney
    start_date: date
    end_date: date
    is_active: bool = True
    notes: Optional[str] = None

    @model_validator(mode="after")
    def _check_period(self):
        if self.end_date < self.start_date:
            raise ValueError("The budget end date must fall on or after the start date.")
        return self


class BudgetUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    amount: Optional[PositiveMoney] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None


class BudgetOut(ORMModel):
    id: int
    name: str
    amount: NonNegativeMoney
    start_date: date
    end_date: date
    is_active: bool
    notes: Optional[str] = None
    # Derived:
    spent: NonNegativeMoney = Decimal("0")
    remaining: Money = Decimal("0")
    percentage_spent: float = 0.0
    percentage_remaining: float = 0.0
    is_exceeded: bool = False


# --------------------------------------------------------------------------- summaries
class TrendPoint(BaseModel):
    period: str
    revenue: NonNegativeMoney = Decimal("0")
    expenses: NonNegativeMoney = Decimal("0")
    profit: Money = Decimal("0")


class FinanceSummary(BaseModel):
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    budget_total: NonNegativeMoney
    budget_spent: NonNegativeMoney
    budget_remaining: Money
    budget_percentage_spent: float
    total_revenue: NonNegativeMoney
    cash_collected: NonNegativeMoney
    outstanding_receivables: NonNegativeMoney
    total_expenses: NonNegativeMoney
    net_profit_or_loss: Money
    is_profit: bool
    net_cash_position: Money
    profit_margin_percent: float
    expenses_by_category: List[CategoryBreakdown]
    trend: List[TrendPoint]
    active_budget: Optional[BudgetOut] = None
