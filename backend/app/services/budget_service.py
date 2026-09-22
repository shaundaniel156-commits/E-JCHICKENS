"""Budgets. Remaining budget is a spending allowance — deliberately not profit."""
from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.enums import ActivityAction, NotificationSeverity, NotificationType
from app.models.finance import Budget
from app.models.user import User
from app.repositories import aggregates as agg
from app.schemas.finance import BudgetCreate, BudgetOut, BudgetUpdate
from app.services import activity_service, notification_service, settings_service
from app.utils.money import ZERO, money, percentage

MODULE = "budgets"


def get_budget(db: Session, budget_id: int) -> Budget:
    budget = db.get(Budget, budget_id)
    if budget is None or budget.is_deleted:
        raise NotFoundError("Budget not found.")
    return budget


def to_out(db: Session, budget: Budget) -> BudgetOut:
    spent = agg.total_expenses(db, budget.start_date, budget.end_date)
    remaining = money(budget.amount - spent)
    return BudgetOut(
        id=budget.id,
        name=budget.name,
        amount=budget.amount,
        start_date=budget.start_date,
        end_date=budget.end_date,
        is_active=budget.is_active,
        notes=budget.notes,
        spent=spent,
        remaining=remaining,
        percentage_spent=percentage(spent, budget.amount),
        percentage_remaining=max(0.0, round(100 - percentage(spent, budget.amount), 2)),
        is_exceeded=remaining < 0,
    )


def list_budgets(db: Session) -> List[BudgetOut]:
    rows = list(
        db.execute(
            select(Budget).where(Budget.is_deleted.is_(False)).order_by(Budget.start_date.desc())
        ).scalars().all()
    )
    return [to_out(db, row) for row in rows]


def active_budget(db: Session, on_date: Optional[date] = None) -> Optional[Budget]:
    """The budget that covers the given day; falls back to the newest active one."""
    on_date = on_date or date.today()
    covering = db.execute(
        select(Budget)
        .where(
            Budget.is_deleted.is_(False),
            Budget.is_active.is_(True),
            Budget.start_date <= on_date,
            Budget.end_date >= on_date,
        )
        .order_by(Budget.start_date.desc())
    ).scalars().first()
    if covering:
        return covering
    return db.execute(
        select(Budget)
        .where(Budget.is_deleted.is_(False), Budget.is_active.is_(True))
        .order_by(Budget.start_date.desc())
    ).scalars().first()


def active_budget_out(db: Session) -> Optional[BudgetOut]:
    budget = active_budget(db)
    return to_out(db, budget) if budget else None


def create_budget(db: Session, payload: BudgetCreate, actor: Optional[User]) -> BudgetOut:
    budget = Budget(
        name=payload.name.strip(),
        amount=money(payload.amount),
        start_date=payload.start_date,
        end_date=payload.end_date,
        is_active=payload.is_active,
        notes=payload.notes,
        created_by_id=actor.id if actor else None,
    )
    db.add(budget)
    db.flush()
    activity_service.record(
        db,
        user=actor,
        action=ActivityAction.CREATE,
        module=MODULE,
        description=f"Created budget {budget.name} of {settings_service.money_text(db, budget.amount)}",
        entity_id=budget.id,
    )
    check_budget_alerts(db)
    db.commit()
    db.refresh(budget)
    return to_out(db, budget)


def update_budget(
    db: Session, budget_id: int, payload: BudgetUpdate, actor: Optional[User]
) -> BudgetOut:
    budget = get_budget(db, budget_id)
    data = payload.model_dump(exclude_unset=True)
    if "amount" in data and data["amount"] is not None:
        data["amount"] = money(data["amount"])
    for field, value in data.items():
        if value is not None:
            setattr(budget, field, value)
    if budget.end_date < budget.start_date:
        from app.core.exceptions import ValidationError

        raise ValidationError("The budget end date must fall on or after the start date.")
    budget.updated_by_id = actor.id if actor else None

    activity_service.record(
        db,
        user=actor,
        action=ActivityAction.UPDATE,
        module=MODULE,
        description=f"Updated budget {budget.name}",
        entity_id=budget.id,
    )
    check_budget_alerts(db)
    db.commit()
    db.refresh(budget)
    return to_out(db, budget)


def delete_budget(db: Session, budget_id: int, actor: Optional[User]) -> None:
    budget = get_budget(db, budget_id)
    budget.is_deleted = True
    budget.deleted_at = datetime.utcnow()
    budget.deleted_by_id = actor.id if actor else None
    activity_service.record(
        db,
        user=actor,
        action=ActivityAction.DELETE,
        module=MODULE,
        description=f"Deleted budget {budget.name}",
        entity_id=budget.id,
    )
    db.commit()


def check_budget_alerts(db: Session) -> None:
    """Warn as the active budget approaches, then passes, its limit."""
    budget = active_budget(db)
    if budget is None:
        return

    spent = agg.total_expenses(db, budget.start_date, budget.end_date)
    used = percentage(spent, budget.amount)
    warning_at = float(settings_service.get_settings(db).budget_warning_percent or 80)
    remaining = money(budget.amount - spent)

    exceeded_key = f"budget-exceeded:{budget.id}"
    warning_key = f"budget-warning:{budget.id}"

    if remaining < 0:
        notification_service.clear_dedupe(db, warning_key)
        notification_service.push(
            db,
            type_=NotificationType.BUDGET_EXCEEDED,
            severity=NotificationSeverity.CRITICAL,
            title="Budget exceeded",
            message=(
                f"“{budget.name}” is over by {settings_service.money_text(db, abs(remaining))}. "
                f"{settings_service.money_text(db, spent)} has been spent against a budget of "
                f"{settings_service.money_text(db, budget.amount)}."
            ),
            module=MODULE,
            entity_id=budget.id,
            dedupe_key=exceeded_key,
        )
    elif used >= warning_at:
        notification_service.clear_dedupe(db, exceeded_key)
        notification_service.push(
            db,
            type_=NotificationType.BUDGET_WARNING,
            severity=NotificationSeverity.WARNING,
            title="Budget nearly exhausted",
            message=(
                f"{used:.1f}% of “{budget.name}” has been spent. "
                f"{settings_service.money_text(db, remaining)} remains of "
                f"{settings_service.money_text(db, budget.amount)}."
            ),
            module=MODULE,
            entity_id=budget.id,
            dedupe_key=warning_key,
        )
    else:
        notification_service.clear_dedupe(db, warning_key)
        notification_service.clear_dedupe(db, exceeded_key)
