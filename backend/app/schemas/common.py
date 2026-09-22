"""Shared schema building blocks: money, pagination and generic responses."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Annotated, Generic, List, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer, model_validator

T = TypeVar("T")

_CENTS = Decimal("0.01")


def _serialize_money(value: Decimal) -> str:
    """Money crosses the wire as an exact decimal string — never a float."""
    return format(Decimal(value or 0).quantize(_CENTS), "f")


Money = Annotated[
    Decimal,
    Field(max_digits=16, decimal_places=2),
    PlainSerializer(_serialize_money, return_type=str, when_used="json"),
]

PositiveMoney = Annotated[
    Decimal,
    Field(gt=0, max_digits=16, decimal_places=2),
    PlainSerializer(_serialize_money, return_type=str, when_used="json"),
]

NonNegativeMoney = Annotated[
    Decimal,
    Field(ge=0, max_digits=16, decimal_places=2),
    PlainSerializer(_serialize_money, return_type=str, when_used="json"),
]

Quantity = Annotated[
    Decimal,
    Field(gt=0, max_digits=12, decimal_places=2),
    PlainSerializer(lambda v: format(Decimal(v or 0), "f"), return_type=str, when_used="json"),
]

QuantityOut = Annotated[
    Decimal,
    PlainSerializer(lambda v: format(Decimal(v or 0), "f"), return_type=str, when_used="json"),
]


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Message(BaseModel):
    message: str


class PageMeta(BaseModel):
    total: int
    page: int
    page_size: int
    pages: int


class Page(BaseModel, Generic[T]):
    items: List[T]
    meta: PageMeta


class DateRange(BaseModel):
    start_date: Optional[date] = None
    end_date: Optional[date] = None

    @model_validator(mode="after")
    def _check_order(self):
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError("start_date cannot be after end_date")
        return self
