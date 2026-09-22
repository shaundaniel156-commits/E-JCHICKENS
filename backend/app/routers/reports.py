"""Reports, with CSV and PDF export."""
from typing import Optional

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.db.session import get_db
from app.dependencies.auth import require_manager
from app.dependencies.filters import PeriodParams, period
from app.models.user import User
from app.schemas.dashboard import (
    BirdReport,
    ExpenseReport,
    FarmPerformanceReport,
    FeedReport,
    ProfitLossReport,
    SalesReport,
)
from app.services import report_service, settings_service
from app.utils.export import to_csv, to_pdf
from app.utils.money import format_ugx

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/birds", response_model=BirdReport, summary="Bird report")
def birds(
    dates: PeriodParams = Depends(period),
    batch_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    _user: User = Depends(require_manager),
):
    return report_service.bird_report(db, dates.start_date, dates.end_date, batch_id)


@router.get("/feed", response_model=FeedReport, summary="Feed report")
def feed(
    dates: PeriodParams = Depends(period),
    db: Session = Depends(get_db),
    _user: User = Depends(require_manager),
):
    return report_service.feed_report(db, dates.start_date, dates.end_date)


@router.get("/expenses", response_model=ExpenseReport, summary="Expense report")
def expenses(
    dates: PeriodParams = Depends(period),
    db: Session = Depends(get_db),
    _user: User = Depends(require_manager),
):
    return report_service.expense_report(db, dates.start_date, dates.end_date)


@router.get("/sales", response_model=SalesReport, summary="Sales report")
def sales(
    dates: PeriodParams = Depends(period),
    batch_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    _user: User = Depends(require_manager),
):
    return report_service.sales_report(db, dates.start_date, dates.end_date, batch_id)


@router.get("/profit-loss", response_model=ProfitLossReport, summary="Profit & loss report")
def profit_loss(
    dates: PeriodParams = Depends(period),
    db: Session = Depends(get_db),
    _user: User = Depends(require_manager),
):
    return report_service.profit_loss_report(db, dates.start_date, dates.end_date)


@router.get("/performance", response_model=FarmPerformanceReport, summary="Farm performance report")
def performance(
    dates: PeriodParams = Depends(period),
    db: Session = Depends(get_db),
    _user: User = Depends(require_manager),
):
    return report_service.farm_performance_report(db, dates.start_date, dates.end_date)


# --------------------------------------------------------------------------- export

_REPORTS = ("birds", "feed", "expenses", "sales", "profit-loss")


@router.get(
    "/{report}/export",
    summary="Download a report as CSV or PDF",
    response_class=Response,
)
def export(
    report: str,
    export_format: str = Query("csv", alias="format", pattern="^(csv|pdf)$"),
    dates: PeriodParams = Depends(period),
    batch_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    _user: User = Depends(require_manager),
):
    if report not in _REPORTS:
        raise ValidationError(f"Unknown report. Choose one of: {', '.join(_REPORTS)}.")

    farm = settings_service.get_settings(db)
    currency = farm.currency
    start, end = dates.start_date, dates.end_date
    subtitle = _period_label(start, end)
    headers, rows, title, summary_lines = _build(db, report, start, end, batch_id, currency)

    if export_format == "csv":
        content = to_csv(headers, rows)
        media_type = "text/csv"
        extension = "csv"
    else:
        content = to_pdf(
            title,
            headers,
            rows,
            farm_name=farm.farm_name,
            subtitle=subtitle,
            summary_lines=summary_lines,
        )
        media_type = "application/pdf"
        extension = "pdf"

    filename = f"ej-chickens-{report}-report.{extension}"
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _period_label(start, end) -> str:
    if start and end:
        return f"Period: {start:%d/%m/%Y} – {end:%d/%m/%Y}"
    if start:
        return f"From {start:%d/%m/%Y}"
    if end:
        return f"Up to {end:%d/%m/%Y}"
    return "All recorded data"


def _build(db: Session, report: str, start, end, batch_id, currency):
    if report == "birds":
        data = report_service.bird_report(db, start, end, batch_id)
        headers = [
            "Batch", "Breed", "Acquired", "Initial", "Deaths", "Sold",
            "Other losses", "Current", "Sick", "Mortality %", "Acquisition cost",
        ]
        rows = [
            [
                row.batch_code, row.breed, f"{row.acquisition_date:%d/%m/%Y}",
                row.initial_quantity, row.deaths, row.sold, row.other_losses,
                row.current_quantity, row.sick_count, f"{row.mortality_rate:.2f}",
                format_ugx(row.acquisition_cost, currency),
            ]
            for row in data.rows
        ]
        summary = [
            f"<b>Current flock:</b> {data.totals.current_quantity} birds "
            f"(from {data.totals.initial_quantity} acquired)",
            f"<b>Deaths:</b> {data.totals.deaths} &nbsp;|&nbsp; "
            f"<b>Sold:</b> {data.totals.sold} &nbsp;|&nbsp; "
            f"<b>Mortality rate:</b> {data.totals.mortality_rate:.2f}%",
        ]
        return headers, rows, "Bird Report", summary

    if report == "feed":
        data = report_service.feed_report(db, start, end)
        headers = [
            "Feed type", "Purchased (bags)", "Purchased (kg)", "Consumed (bags)",
            "Consumed (kg)", "Stock (bags)", "Stock (kg)", "Cost",
        ]
        rows = [
            [
                row.feed_type, row.purchased_bags, row.purchased_kg, row.consumed_bags,
                row.consumed_kg, row.stock_bags, row.stock_kg,
                format_ugx(row.total_cost, currency),
            ]
            for row in data.rows
        ]
        summary = [
            f"<b>Purchased:</b> {data.total_purchased_kg} kg &nbsp;|&nbsp; "
            f"<b>Consumed:</b> {data.total_consumed_kg} kg &nbsp;|&nbsp; "
            f"<b>In stock:</b> {data.total_stock_kg} kg",
            f"<b>Feed expenditure:</b> {format_ugx(data.total_cost, currency)}",
        ]
        return headers, rows, "Feed Report", summary

    if report == "expenses":
        data = report_service.expense_report(db, start, end)
        headers = ["Category", "Entries", "Amount", "Share of total"]
        rows = [
            [row.category, row.count, format_ugx(row.amount, currency), f"{row.percentage:.1f}%"]
            for row in data.rows
        ]
        summary = [f"<b>Total expenses:</b> {format_ugx(data.total, currency)}"]
        return headers, rows, "Expense Report", summary

    if report == "sales":
        data = report_service.sales_report(db, start, end, batch_id)
        headers = [
            "Reference", "Date", "Batch", "Customer", "Birds", "Unit price", "Total", "Paid", "Status",
        ]
        rows = [
            [
                row.reference, f"{row.sale_date:%d/%m/%Y}", row.batch_code, row.customer or "—",
                row.quantity, format_ugx(row.unit_price, currency),
                format_ugx(row.total_amount, currency), format_ugx(row.amount_paid, currency),
                row.payment_status.title(),
            ]
            for row in data.rows
        ]
        summary = [
            f"<b>Birds sold:</b> {data.total_birds_sold} &nbsp;|&nbsp; "
            f"<b>Customers:</b> {data.customers}",
            f"<b>Revenue:</b> {format_ugx(data.total_revenue, currency)} &nbsp;|&nbsp; "
            f"<b>Collected:</b> {format_ugx(data.total_collected, currency)}",
        ]
        return headers, rows, "Sales Report", summary

    data = report_service.profit_loss_report(db, start, end)
    headers = ["Item", "Amount"]
    rows = [["Total revenue", format_ugx(data.total_revenue, currency)]]
    rows += [
        [f"Expenses — {row.category}", format_ugx(row.amount, currency)]
        for row in data.expenses_by_category
    ]
    rows.append(["Total expenses", format_ugx(data.total_expenses, currency)])
    rows.append(
        [
            "Net profit" if data.is_profit else "Net loss",
            format_ugx(abs(data.net_profit_or_loss), currency),
        ]
    )
    summary = [
        f"<b>{'Net profit' if data.is_profit else 'Net loss'}:</b> "
        f"{format_ugx(abs(data.net_profit_or_loss), currency)} "
        f"(margin {data.profit_margin_percent:.1f}%)"
    ]
    return headers, rows, "Profit & Loss Report", summary
