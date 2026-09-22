"""Expenses, expense categories and the auto-generated entries owned by other modules."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, DuplicateError, NotFoundError
from app.models.enums import ActivityAction, ExpenseSource, PaymentMethod
from app.models.finance import Expense, ExpenseCategory
from app.models.user import User
from app.repositories import aggregates as agg
from app.schemas.finance import (
    CategoryBreakdown,
    ExpenseCategoryCreate,
    ExpenseCreate,
    ExpenseOut,
    ExpenseUpdate,
)
from app.utils.money import ZERO, money, percentage
from app.utils.pagination import paginate

MODULE = "expenses"

# Categories the system relies on for its automatic entries.
DEFAULT_CATEGORIES = [
    ("Birds", "Day-old chicks and point-of-lay birds", True),
    ("Feed", "Starter, grower and finisher feed", True),
    ("Medicine", "Drugs, vitamins and treatment", True),
    ("Vaccines", "Vaccination programmes", False),
    ("Drinkers", "Drinkers and waterers", False),
    ("Feed Troughs", "Feeders and troughs", False),
    ("Lighting", "Bulbs and brooding lamps", False),
    ("Electricity", "Power bills", False),
    ("Labour", "Wages and casual labour", False),
    ("Transport", "Deliveries and travel", False),
    ("Equipment", "Tools and farm equipment", False),
    ("Repairs", "Housing and equipment repairs", False),
    ("Water", "Water bills and bowsers", False),
    ("Packaging", "Crates, bags and packaging", False),
    ("Marketing", "Advertising and promotion", False),
    ("Other", "Anything not covered above", False),
]


def ensure_default_categories(db: Session) -> None:
    existing = {
        name.lower()
        for (name,) in db.execute(select(ExpenseCategory.name)).all()
    }
    for name, description, is_system in DEFAULT_CATEGORIES:
        if name.lower() not in existing:
            db.add(ExpenseCategory(name=name, description=description, is_system=is_system))
    db.flush()


def get_category(db: Session, category_id: int) -> ExpenseCategory:
    category = db.get(ExpenseCategory, category_id)
    if category is None:
        raise NotFoundError("Expense category not found.")
    return category


def get_or_create_category(db: Session, name: str, is_system: bool = False) -> ExpenseCategory:
    category = db.execute(
        select(ExpenseCategory).where(ExpenseCategory.name == name)
    ).scalars().first()
    if category is None:
        category = ExpenseCategory(name=name, is_system=is_system)
        db.add(category)
        db.flush()
    return category


def list_categories(db: Session) -> List[ExpenseCategory]:
    return list(db.execute(select(ExpenseCategory).order_by(ExpenseCategory.name)).scalars().all())


def create_category(
    db: Session, payload: ExpenseCategoryCreate, actor: Optional[User]
) -> ExpenseCategory:
    name = payload.name.strip()
    if db.execute(select(ExpenseCategory).where(ExpenseCategory.name == name)).scalars().first():
        raise DuplicateError(f"An expense category called “{name}” already exists.")
    category = ExpenseCategory(name=name, description=payload.description)
    db.add(category)
    db.flush()
    from app.services import activity_service

    activity_service.record(
        db,
        user=actor,
        action=ActivityAction.CREATE,
        module=MODULE,
        description=f"Created expense category {name}",
        entity_id=category.id,
    )
    db.commit()
    db.refresh(category)
    return category


def delete_category(db: Session, category_id: int, actor: Optional[User]) -> None:
    category = get_category(db, category_id)
    if category.is_system:
        raise ConflictError("System categories are used by automatic entries and cannot be removed.")
    in_use = db.execute(
        select(Expense.id).where(Expense.category_id == category.id, Expense.is_deleted.is_(False)).limit(1)
    ).scalars().first()
    if in_use:
        raise ConflictError("This category still has expenses recorded against it.")
    db.delete(category)
    from app.services import activity_service

    activity_service.record(
        db,
        user=actor,
        action=ActivityAction.DELETE,
        module=MODULE,
        description=f"Deleted expense category {category.name}",
        entity_id=category_id,
    )
    db.commit()


# --------------------------------------------------------------------------- expenses

def get_expense(db: Session, expense_id: int) -> Expense:
    expense = db.get(Expense, expense_id)
    if expense is None or expense.is_deleted:
        raise NotFoundError("Expense not found.")
    return expense


def to_out(expense: Expense) -> ExpenseOut:
    return ExpenseOut(
        id=expense.id,
        expense_date=expense.expense_date,
        category_id=expense.category_id,
        category_name=expense.category.name if expense.category else None,
        description=expense.description,
        amount=expense.amount,
        vendor=expense.vendor,
        payment_method=expense.payment_method,
        reference_number=expense.reference_number,
        receipt_url=expense.receipt_url,
        notes=expense.notes,
        source_type=expense.source_type,
        source_id=expense.source_id,
        is_system_generated=expense.is_system_generated,
    )


def list_expenses(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 20,
    search: Optional[str] = None,
    category_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    sort: str = "expense_date",
    order: str = "desc",
):
    stmt = select(Expense).where(Expense.is_deleted.is_(False))
    if search:
        pattern = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                Expense.description.ilike(pattern),
                Expense.vendor.ilike(pattern),
                Expense.reference_number.ilike(pattern),
            )
        )
    if category_id:
        stmt = stmt.where(Expense.category_id == category_id)
    if start_date:
        stmt = stmt.where(Expense.expense_date >= start_date)
    if end_date:
        stmt = stmt.where(Expense.expense_date <= end_date)

    sortable = {
        "expense_date": Expense.expense_date,
        "amount": Expense.amount,
        "description": Expense.description,
        "created_at": Expense.created_at,
    }
    column = sortable.get(sort, Expense.expense_date)
    stmt = stmt.order_by(column.desc() if order == "desc" else column.asc(), Expense.id.desc())

    rows, meta = paginate(db, stmt, page, page_size)
    return [to_out(row) for row in rows], meta


def create_expense(db: Session, payload: ExpenseCreate, actor: Optional[User]) -> ExpenseOut:
    get_category(db, payload.category_id)
    expense = Expense(
        expense_date=payload.expense_date,
        category_id=payload.category_id,
        description=payload.description.strip(),
        amount=money(payload.amount),
        vendor=payload.vendor,
        payment_method=payload.payment_method,
        reference_number=payload.reference_number,
        receipt_url=payload.receipt_url,
        notes=payload.notes,
        source_type=ExpenseSource.MANUAL,
        created_by_id=actor.id if actor else None,
    )
    db.add(expense)
    db.flush()

    from app.services import activity_service, budget_service, settings_service

    activity_service.record(
        db,
        user=actor,
        action=ActivityAction.CREATE,
        module=MODULE,
        description=(
            f"Recorded expense: {expense.description} "
            f"({settings_service.money_text(db, expense.amount)})"
        ),
        entity_id=expense.id,
    )
    budget_service.check_budget_alerts(db)
    db.commit()
    db.refresh(expense)
    return to_out(expense)


def update_expense(
    db: Session, expense_id: int, payload: ExpenseUpdate, actor: Optional[User]
) -> ExpenseOut:
    expense = get_expense(db, expense_id)
    if expense.is_system_generated:
        raise ConflictError(
            "This expense was generated automatically. Edit the record it came from instead."
        )

    data = payload.model_dump(exclude_unset=True)
    if "category_id" in data and data["category_id"]:
        get_category(db, data["category_id"])
    if "amount" in data and data["amount"] is not None:
        data["amount"] = money(data["amount"])
    for field, value in data.items():
        if value is not None:
            setattr(expense, field, value)
    expense.updated_by_id = actor.id if actor else None

    from app.services import activity_service, budget_service

    activity_service.record(
        db,
        user=actor,
        action=ActivityAction.UPDATE,
        module=MODULE,
        description=f"Updated expense: {expense.description}",
        entity_id=expense.id,
    )
    budget_service.check_budget_alerts(db)
    db.commit()
    db.refresh(expense)
    return to_out(expense)


def delete_expense(db: Session, expense_id: int, actor: Optional[User]) -> None:
    expense = get_expense(db, expense_id)
    if expense.is_system_generated:
        raise ConflictError(
            "This expense was generated automatically. Remove the record it came from instead."
        )
    expense.is_deleted = True
    expense.deleted_at = datetime.utcnow()
    expense.deleted_by_id = actor.id if actor else None

    from app.services import activity_service

    activity_service.record(
        db,
        user=actor,
        action=ActivityAction.DELETE,
        module=MODULE,
        description=f"Deleted expense: {expense.description}",
        entity_id=expense.id,
    )
    db.commit()


# --------------------------------------------------------- system-generated expenses

def sync_system_expense(
    db: Session,
    *,
    source_type: ExpenseSource,
    source_id: int,
    category_name: str,
    description: str,
    amount: Decimal,
    expense_date: date,
    vendor: Optional[str] = None,
    actor: Optional[User] = None,
) -> Optional[Expense]:
    """Create, update or retire the expense that mirrors another module's record.

    Called by the birds, feed and health services so a cost is never typed twice
    and the two modules can never drift apart.
    """
    amount = money(amount)
    existing = db.execute(
        select(Expense).where(
            Expense.source_type == source_type,
            Expense.source_id == source_id,
            Expense.is_deleted.is_(False),
        )
    ).scalars().first()

    if amount <= 0:
        if existing:
            existing.is_deleted = True
            existing.deleted_at = datetime.utcnow()
        return None

    category = get_or_create_category(db, category_name, is_system=True)
    if existing:
        existing.category_id = category.id
        existing.description = description
        existing.amount = amount
        existing.expense_date = expense_date
        existing.vendor = vendor
        existing.updated_by_id = actor.id if actor else None
        return existing

    expense = Expense(
        expense_date=expense_date,
        category_id=category.id,
        description=description,
        amount=amount,
        vendor=vendor,
        payment_method=PaymentMethod.CASH,
        source_type=source_type,
        source_id=source_id,
        created_by_id=actor.id if actor else None,
    )
    db.add(expense)
    db.flush()
    return expense


def remove_system_expense(
    db: Session, source_type: ExpenseSource, source_id: int, actor: Optional[User] = None
) -> None:
    rows = db.execute(
        select(Expense).where(
            Expense.source_type == source_type,
            Expense.source_id == source_id,
            Expense.is_deleted.is_(False),
        )
    ).scalars().all()
    for row in rows:
        row.is_deleted = True
        row.deleted_at = datetime.utcnow()
        row.deleted_by_id = actor.id if actor else None


# --------------------------------------------------------------------------- summaries

def category_breakdown(
    db: Session, start: Optional[date] = None, end: Optional[date] = None
) -> List[CategoryBreakdown]:
    rows = agg.expenses_by_category(db, start, end)
    total = sum((row[2] for row in rows), ZERO)
    return [
        CategoryBreakdown(
            category_id=row[0],
            category=row[1],
            amount=row[2],
            percentage=percentage(row[2], total),
            count=row[3],
        )
        for row in rows
    ]
