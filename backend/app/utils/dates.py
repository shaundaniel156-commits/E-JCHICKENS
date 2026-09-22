"""Date-range helpers shared by the dashboard, finance and reports modules."""
from __future__ import annotations

from calendar import monthrange
from datetime import date, timedelta
from typing import Optional, Tuple

PRESETS = (
    "today",
    "yesterday",
    "this_week",
    "last_week",
    "this_month",
    "last_month",
    "this_year",
    "all_time",
)


def resolve_preset(preset: str, today: Optional[date] = None) -> Tuple[Optional[date], Optional[date]]:
    """Translate a named period into a concrete (start, end) pair."""
    today = today or date.today()
    preset = (preset or "").lower()

    if preset == "today":
        return today, today
    if preset == "yesterday":
        day = today - timedelta(days=1)
        return day, day
    if preset == "this_week":
        start = today - timedelta(days=today.weekday())
        return start, today
    if preset == "last_week":
        this_week_start = today - timedelta(days=today.weekday())
        start = this_week_start - timedelta(days=7)
        return start, this_week_start - timedelta(days=1)
    if preset == "this_month":
        return today.replace(day=1), today
    if preset == "last_month":
        first_of_month = today.replace(day=1)
        end = first_of_month - timedelta(days=1)
        return end.replace(day=1), end
    if preset == "this_year":
        return today.replace(month=1, day=1), today
    return None, None  # all_time / unknown


def month_start(value: date) -> date:
    return value.replace(day=1)


def month_end(value: date) -> date:
    return value.replace(day=monthrange(value.year, value.month)[1])


def add_months(value: date, months: int) -> date:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, monthrange(year, month)[1])
    return date(year, month, day)


def month_series(start: date, end: date, max_points: int = 24) -> list[date]:
    """First day of each month in the range, oldest first."""
    points: list[date] = []
    cursor = month_start(start)
    last = month_start(end)
    while cursor <= last and len(points) < max_points:
        points.append(cursor)
        cursor = add_months(cursor, 1)
    return points


def day_series(start: date, end: date, max_points: int = 90) -> list[date]:
    days = (end - start).days
    if days < 0:
        return []
    if days + 1 > max_points:
        start = end - timedelta(days=max_points - 1)
    return [start + timedelta(days=offset) for offset in range((end - start).days + 1)]


def week_start(value: date) -> date:
    return value - timedelta(days=value.weekday())


def label_month(value: date) -> str:
    return value.strftime("%b %Y")


def label_day(value: date) -> str:
    return value.strftime("%d %b")
