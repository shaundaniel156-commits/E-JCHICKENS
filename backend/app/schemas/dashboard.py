"""Dashboard and report payloads — every figure here is computed from the database."""
from datetime import date
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel

from app.schemas.common import Money, NonNegativeMoney, QuantityOut
from app.schemas.finance import CategoryBreakdown, TrendPoint
from app.schemas.system import ActivityLogOut, NotificationOut


class BirdSummary(BaseModel):
    total_batches: int
    active_batches: int
    initial_birds: int
    total_birds: int
    healthy_birds: int
    sick_birds: int
    dead_birds: int
    sold_birds: int
    other_losses: int
    available_birds: int
    mortality_rate: float


class FeedSummary(BaseModel):
    stock_bags: QuantityOut
    stock_kg: QuantityOut
    purchased_bags: QuantityOut
    purchased_kg: QuantityOut
    consumed_bags: QuantityOut
    consumed_kg: QuantityOut
    total_feed_cost: NonNegativeMoney
    low_stock: bool
    low_stock_threshold_bags: QuantityOut


class FinancialSummary(BaseModel):
    initial_budget: NonNegativeMoney
    total_expenses: NonNegativeMoney
    remaining_budget: Money
    budget_percentage_spent: float
    total_revenue: NonNegativeMoney
    cash_collected: NonNegativeMoney
    net_profit_or_loss: Money
    is_profit: bool
    profit: NonNegativeMoney
    loss: NonNegativeMoney
    net_cash_position: Money


class SeriesPoint(BaseModel):
    period: str
    value: float = 0.0
    secondary: float = 0.0


class DashboardCharts(BaseModel):
    bird_population: List[SeriesPoint]
    mortality: List[SeriesPoint]
    expenses_by_category: List[CategoryBreakdown]
    revenue_vs_expenses: List[TrendPoint]
    profit_trend: List[TrendPoint]
    feed_usage: List[SeriesPoint]


class DashboardSummary(BaseModel):
    generated_at: date
    farm_name: str
    currency: str
    birds: BirdSummary
    feed: FeedSummary
    finance: FinancialSummary
    charts: DashboardCharts
    recent_activity: List[ActivityLogOut]
    alerts: List[NotificationOut]
    has_data: bool


# --------------------------------------------------------------------------- reports
class ReportPeriod(BaseModel):
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class BirdReportRow(BaseModel):
    batch_id: int
    batch_code: str
    breed: str
    acquisition_date: date
    initial_quantity: int
    deaths: int
    sold: int
    other_losses: int
    current_quantity: int
    sick_count: int
    mortality_rate: float
    acquisition_cost: NonNegativeMoney


class BirdReport(BaseModel):
    period: ReportPeriod
    rows: List[BirdReportRow]
    totals: BirdReportRow


class FeedReportRow(BaseModel):
    feed_type_id: int
    feed_type: str
    purchased_bags: QuantityOut
    purchased_kg: QuantityOut
    consumed_bags: QuantityOut
    consumed_kg: QuantityOut
    stock_kg: QuantityOut
    stock_bags: QuantityOut
    total_cost: NonNegativeMoney


class FeedReport(BaseModel):
    period: ReportPeriod
    rows: List[FeedReportRow]
    total_purchased_kg: QuantityOut
    total_consumed_kg: QuantityOut
    total_stock_kg: QuantityOut
    total_cost: NonNegativeMoney


class ExpenseReport(BaseModel):
    period: ReportPeriod
    rows: List[CategoryBreakdown]
    total: NonNegativeMoney


class SalesReportRow(BaseModel):
    sale_id: int
    reference: str
    sale_date: date
    batch_code: str
    customer: Optional[str] = None
    quantity: int
    unit_price: NonNegativeMoney
    total_amount: NonNegativeMoney
    amount_paid: NonNegativeMoney
    payment_status: str


class SalesReport(BaseModel):
    period: ReportPeriod
    rows: List[SalesReportRow]
    total_birds_sold: int
    total_revenue: NonNegativeMoney
    total_collected: NonNegativeMoney
    customers: int


class ProfitLossReport(BaseModel):
    period: ReportPeriod
    total_revenue: NonNegativeMoney
    total_expenses: NonNegativeMoney
    expenses_by_category: List[CategoryBreakdown]
    net_profit_or_loss: Money
    is_profit: bool
    profit_margin_percent: float
    trend: List[TrendPoint]


class FarmPerformanceReport(BaseModel):
    period: ReportPeriod
    birds: BirdSummary
    feed: FeedSummary
    finance: FinancialSummary
    feed_cost_per_bird: NonNegativeMoney
    cost_per_bird_sold: NonNegativeMoney
    revenue_per_bird_sold: NonNegativeMoney
    average_sale_price: NonNegativeMoney
