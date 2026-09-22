"""Finance roll-ups.

The four figures the brief insists on keeping apart:

    budget_remaining   = budget amount − expenses inside the budget period
    total_revenue      = value of every recognised sale
    total_expenses     = every expense recorded
    net_profit_or_loss = total_revenue − total_expenses
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.enums import PaymentStatus
from app.models.finance import Expense, Sale
from app.repositories import aggregates as agg
from app.schemas.dashboard import FinancialSummary
from app.schemas.finance import FinanceSummary, TrendPoint
from app.services import budget_service, expense_service
from app.utils.dates import add_months, label_month, month_start
from app.utils.money import ZERO, money, percentage, to_decimal


def _month_key(db: Session, column):
    """A portable 'YYYY-MM' grouping expression (MySQL and SQLite)."""
    if db.bind.dialect.name == "mysql":
        return func.date_format(column, "%Y-%m")
    return func.strftime("%Y-%m", column)


def financial_summary(
    db: Session, start: Optional[date] = None, end: Optional[date] = None
) -> FinancialSummary:
    """The figures shown on the dashboard's financial cards."""
    revenue = agg.total_revenue(db, start, end)
    collected = agg.cash_collected(db, start, end)
    expenses = agg.total_expenses(db, start, end)
    net = money(revenue - expenses)

    budget = budget_service.active_budget(db)
    if budget:
        budget_amount = to_decimal(budget.amount)
        budget_spent = agg.total_expenses(db, budget.start_date, budget.end_date)
    else:
        budget_amount, budget_spent = ZERO, ZERO

    return FinancialSummary(
        initial_budget=budget_amount,
        total_expenses=expenses,
        remaining_budget=money(budget_amount - budget_spent),
        budget_percentage_spent=percentage(budget_spent, budget_amount),
        total_revenue=revenue,
        cash_collected=collected,
        net_profit_or_loss=net,
        is_profit=net >= 0,
        profit=net if net > 0 else ZERO,
        loss=abs(net) if net < 0 else ZERO,
        net_cash_position=money(collected - expenses),
    )


def monthly_trend(
    db: Session, start: Optional[date] = None, end: Optional[date] = None, months: int = 12
) -> List[TrendPoint]:
    """Revenue, expenses and profit per calendar month."""
    end = end or date.today()
    if start is None:
        earliest_sale = db.execute(
            select(func.min(Sale.sale_date)).where(Sale.is_deleted.is_(False))
        ).scalar()
        earliest_expense = db.execute(
            select(func.min(Expense.expense_date)).where(Expense.is_deleted.is_(False))
        ).scalar()
        candidates = [value for value in (earliest_sale, earliest_expense) if value]
        start = min(candidates) if candidates else add_months(end, -(months - 1))
    start = max(month_start(start), add_months(month_start(end), -(months - 1)))

    sale_month = _month_key(db, Sale.sale_date)
    expense_month = _month_key(db, Expense.expense_date)

    revenue_rows = dict(
        db.execute(
            select(sale_month, func.coalesce(func.sum(Sale.total_amount), 0))
            .where(
                Sale.is_deleted.is_(False),
                Sale.payment_status != PaymentStatus.CANCELLED,
                Sale.sale_date >= start,
                Sale.sale_date <= end,
            )
            .group_by(sale_month)
        ).all()
    )
    expense_rows = dict(
        db.execute(
            select(expense_month, func.coalesce(func.sum(Expense.amount), 0))
            .where(
                Expense.is_deleted.is_(False),
                Expense.expense_date >= start,
                Expense.expense_date <= end,
            )
            .group_by(expense_month)
        ).all()
    )

    points: List[TrendPoint] = []
    cursor = month_start(start)
    last = month_start(end)
    while cursor <= last:
        key = cursor.strftime("%Y-%m")
        revenue = to_decimal(revenue_rows.get(key, 0))
        expenses = to_decimal(expense_rows.get(key, 0))
        points.append(
            TrendPoint(
                period=label_month(cursor),
                revenue=revenue,
                expenses=expenses,
                profit=money(revenue - expenses),
            )
        )
        cursor = add_months(cursor, 1)
    return points


def finance_summary(
    db: Session, start: Optional[date] = None, end: Optional[date] = None
) -> FinanceSummary:
    """The full Finance page payload."""
    revenue = agg.total_revenue(db, start, end)
    collected = agg.cash_collected(db, start, end)
    expenses = agg.total_expenses(db, start, end)
    net = money(revenue - expenses)
    active = budget_service.active_budget_out(db)

    return FinanceSummary(
        start_date=start,
        end_date=end,
        budget_total=active.amount if active else ZERO,
        budget_spent=active.spent if active else ZERO,
        budget_remaining=active.remaining if active else ZERO,
        budget_percentage_spent=active.percentage_spent if active else 0.0,
        total_revenue=revenue,
        cash_collected=collected,
        outstanding_receivables=money(revenue - collected),
        total_expenses=expenses,
        net_profit_or_loss=net,
        is_profit=net >= 0,
        net_cash_position=money(collected - expenses),
        profit_margin_percent=percentage(net, revenue),
        expenses_by_category=expense_service.category_breakdown(db, start, end),
        trend=monthly_trend(db, start, end),
        active_budget=active,
    )
