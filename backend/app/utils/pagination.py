"""Uniform pagination for list endpoints."""
from math import ceil
from typing import Sequence, TypeVar

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.schemas.common import PageMeta

T = TypeVar("T")

MAX_PAGE_SIZE = 200


def paginate(db: Session, statement: Select, page: int, page_size: int):
    """Return (rows, PageMeta) for a SELECT, running one COUNT and one page query."""
    page = max(1, page)
    page_size = max(1, min(page_size, MAX_PAGE_SIZE))

    count_stmt = select(func.count()).select_from(statement.order_by(None).subquery())
    total = db.execute(count_stmt).scalar_one()

    rows = db.execute(statement.offset((page - 1) * page_size).limit(page_size)).scalars().all()
    meta = PageMeta(
        total=total,
        page=page,
        page_size=page_size,
        pages=ceil(total / page_size) if total else 0,
    )
    return rows, meta


def page_meta(total: int, page: int, page_size: int) -> PageMeta:
    return PageMeta(
        total=total,
        page=page,
        page_size=page_size,
        pages=ceil(total / page_size) if total else 0,
    )


def slice_rows(rows: Sequence[T], page: int, page_size: int) -> Sequence[T]:
    start = (page - 1) * page_size
    return rows[start : start + page_size]
