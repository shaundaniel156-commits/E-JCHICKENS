"""Reusable query-parameter dependencies: pagination and date ranges."""
from dataclasses import dataclass
from datetime import date
from typing import Optional

from fastapi import Query

from app.core.exceptions import ValidationError
from app.utils.dates import resolve_preset
from app.utils.pagination import MAX_PAGE_SIZE


@dataclass
class PageParams:
    page: int
    page_size: int


def pagination(
    page: int = Query(1, ge=1, description="1-based page number"),
    page_size: int = Query(20, ge=1, le=MAX_PAGE_SIZE, description="Rows per page"),
) -> PageParams:
    return PageParams(page=page, page_size=page_size)


@dataclass
class PeriodParams:
    start_date: Optional[date]
    end_date: Optional[date]
    preset: Optional[str]


def period(
    preset: Optional[str] = Query(
        None,
        description="today | yesterday | this_week | last_week | this_month | last_month | this_year | all_time",
    ),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
) -> PeriodParams:
    if preset and preset != "custom":
        start, end = resolve_preset(preset)
        return PeriodParams(start_date=start, end_date=end, preset=preset)
    if start_date and end_date and start_date > end_date:
        raise ValidationError("The start date cannot be after the end date.")
    return PeriodParams(start_date=start_date, end_date=end_date, preset=preset or "custom")
