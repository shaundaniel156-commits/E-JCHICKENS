"""Feed type, purchase and consumption payloads."""
from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.common import NonNegativeMoney, ORMModel, Quantity, QuantityOut


def _not_in_future(value: date) -> date:
    if value > date.today():
        raise ValueError("The date cannot be in the future.")
    return value


class FeedTypeCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    description: Optional[str] = Field(default=None, max_length=255)
    default_bag_weight_kg: Quantity = Decimal("50")


class FeedTypeUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=80)
    description: Optional[str] = Field(default=None, max_length=255)
    default_bag_weight_kg: Optional[Quantity] = None


class FeedTypeOut(ORMModel):
    id: int
    name: str
    description: Optional[str] = None
    default_bag_weight_kg: QuantityOut
    # Derived stock figures:
    stock_kg: QuantityOut = Decimal("0")
    stock_bags: QuantityOut = Decimal("0")
    purchased_kg: QuantityOut = Decimal("0")
    consumed_kg: QuantityOut = Decimal("0")
    is_low_stock: bool = False


class FeedPurchaseCreate(BaseModel):
    feed_type_id: int = Field(gt=0)
    purchase_date: date
    brand: Optional[str] = Field(default=None, max_length=120)
    quantity_bags: Quantity
    bag_weight_kg: Quantity = Decimal("50")
    cost_per_bag: NonNegativeMoney
    supplier: Optional[str] = Field(default=None, max_length=160)
    lot_number: Optional[str] = Field(default=None, max_length=60)
    notes: Optional[str] = None

    _check_date = field_validator("purchase_date")(_not_in_future)


class FeedPurchaseUpdate(BaseModel):
    purchase_date: Optional[date] = None
    brand: Optional[str] = Field(default=None, max_length=120)
    quantity_bags: Optional[Quantity] = None
    bag_weight_kg: Optional[Quantity] = None
    cost_per_bag: Optional[NonNegativeMoney] = None
    supplier: Optional[str] = Field(default=None, max_length=160)
    lot_number: Optional[str] = Field(default=None, max_length=60)
    notes: Optional[str] = None


class FeedPurchaseOut(ORMModel):
    id: int
    feed_type_id: int
    feed_type_name: Optional[str] = None
    purchase_date: date
    brand: Optional[str] = None
    quantity_bags: QuantityOut
    bag_weight_kg: QuantityOut
    quantity_kg: QuantityOut
    cost_per_bag: NonNegativeMoney
    total_cost: NonNegativeMoney
    supplier: Optional[str] = None
    lot_number: Optional[str] = None
    notes: Optional[str] = None


class FeedConsumptionCreate(BaseModel):
    feed_type_id: int = Field(gt=0)
    batch_id: Optional[int] = Field(default=None, gt=0)
    consumption_date: date
    quantity_bags: Optional[Quantity] = None
    quantity_kg: Optional[Quantity] = None
    notes: Optional[str] = None

    _check_date = field_validator("consumption_date")(_not_in_future)

    @model_validator(mode="after")
    def _need_one_quantity(self):
        if self.quantity_bags is None and self.quantity_kg is None:
            raise ValueError("Enter the quantity consumed in bags or in kilograms.")
        return self


class FeedConsumptionUpdate(BaseModel):
    batch_id: Optional[int] = Field(default=None, gt=0)
    consumption_date: Optional[date] = None
    quantity_bags: Optional[Quantity] = None
    quantity_kg: Optional[Quantity] = None
    notes: Optional[str] = None


class FeedConsumptionOut(ORMModel):
    id: int
    feed_type_id: int
    feed_type_name: Optional[str] = None
    batch_id: Optional[int] = None
    batch_code: Optional[str] = None
    consumption_date: date
    quantity_bags: QuantityOut
    quantity_kg: QuantityOut
    notes: Optional[str] = None


class FeedStockSummary(BaseModel):
    total_stock_kg: QuantityOut
    total_stock_bags: QuantityOut
    total_purchased_kg: QuantityOut
    total_consumed_kg: QuantityOut
    total_feed_cost: NonNegativeMoney
    low_stock_types: int
    by_type: list[FeedTypeOut]
