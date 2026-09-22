"""Expenses, customers, sales and budgets."""
from datetime import date
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import AuthorshipMixin, Base, SoftDeleteMixin, TimestampMixin
from app.models.enums import ExpenseSource, PaymentMethod, PaymentStatus


class ExpenseCategory(Base, TimestampMixin):
    __tablename__ = "expense_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(String(255))
    # System categories are the targets of auto-generated expenses and cannot be removed.
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    expenses: Mapped[List["Expense"]] = relationship(back_populates="category")


class Expense(Base, TimestampMixin, AuthorshipMixin, SoftDeleteMixin):
    __tablename__ = "expenses"
    __table_args__ = (
        CheckConstraint("amount >= 0", name="ck_expense_amount_non_negative"),
        Index("ix_expense_date_category", "expense_date", "category_id"),
        Index("ix_expense_source", "source_type", "source_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    expense_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    category_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("expense_categories.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False)
    vendor: Mapped[Optional[str]] = mapped_column(String(160))
    payment_method: Mapped[PaymentMethod] = mapped_column(
        Enum(PaymentMethod, native_enum=False, length=20),
        default=PaymentMethod.CASH,
        nullable=False,
    )
    reference_number: Mapped[Optional[str]] = mapped_column(String(80))
    receipt_url: Mapped[Optional[str]] = mapped_column(String(255))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    # Auto-generated expenses are owned by their source record and are read-only here.
    source_type: Mapped[ExpenseSource] = mapped_column(
        Enum(ExpenseSource, native_enum=False, length=20),
        default=ExpenseSource.MANUAL,
        nullable=False,
    )
    source_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    category: Mapped[ExpenseCategory] = relationship(back_populates="expenses", lazy="joined")

    @property
    def is_system_generated(self) -> bool:
        return self.source_type != ExpenseSource.MANUAL


class Customer(Base, TimestampMixin):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160), unique=True, nullable=False, index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(30))
    email: Mapped[Optional[str]] = mapped_column(String(160))
    address: Mapped[Optional[str]] = mapped_column(String(255))
    notes: Mapped[Optional[str]] = mapped_column(Text)

    sales: Mapped[List["Sale"]] = relationship(back_populates="customer")


class Sale(Base, TimestampMixin, AuthorshipMixin, SoftDeleteMixin):
    __tablename__ = "sales"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_sale_quantity_positive"),
        CheckConstraint("unit_price >= 0", name="ck_sale_price_non_negative"),
        CheckConstraint("amount_paid >= 0", name="ck_sale_paid_non_negative"),
        Index("ix_sale_batch_date", "batch_id", "sale_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    reference: Mapped[str] = mapped_column(String(40), unique=True, nullable=False, index=True)
    sale_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    batch_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("bird_batches.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    customer_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False)
    amount_paid: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=Decimal("0"), nullable=False)
    payment_status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, native_enum=False, length=20),
        default=PaymentStatus.PAID,
        nullable=False,
        index=True,
    )
    payment_method: Mapped[PaymentMethod] = mapped_column(
        Enum(PaymentMethod, native_enum=False, length=20),
        default=PaymentMethod.CASH,
        nullable=False,
    )
    notes: Mapped[Optional[str]] = mapped_column(Text)

    customer: Mapped[Optional[Customer]] = relationship(back_populates="sales", lazy="joined")
    batch: Mapped["BirdBatch"] = relationship(lazy="joined")  # noqa: F821

    @property
    def balance_due(self) -> Decimal:
        return self.total_amount - self.amount_paid


class Budget(Base, TimestampMixin, AuthorshipMixin, SoftDeleteMixin):
    __tablename__ = "budgets"
    __table_args__ = (
        CheckConstraint("amount >= 0", name="ck_budget_amount_non_negative"),
        Index("ix_budget_period", "start_date", "end_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    notes: Mapped[Optional[str]] = mapped_column(Text)
