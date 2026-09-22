"""Bird batch, mortality and health payloads."""
from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.models.enums import BatchStatus, HealthStatus
from app.schemas.common import NonNegativeMoney, ORMModel


def _not_in_future(value: date) -> date:
    if value > date.today():
        raise ValueError("The date cannot be in the future.")
    return value


class BirdBatchBase(BaseModel):
    breed: str = Field(min_length=2, max_length=80)
    acquisition_date: date
    source: Optional[str] = Field(default=None, max_length=160)
    age_days_at_acquisition: int = Field(default=0, ge=0, le=2000)
    cost_per_bird: NonNegativeMoney = Decimal("0")
    notes: Optional[str] = None

    _check_date = field_validator("acquisition_date")(_not_in_future)


class BirdBatchCreate(BirdBatchBase):
    batch_code: str = Field(min_length=2, max_length=40)
    initial_quantity: int = Field(gt=0, le=1_000_000)

    @field_validator("batch_code")
    @classmethod
    def _normalise_code(cls, value: str) -> str:
        return value.strip().upper()


class BirdBatchUpdate(BaseModel):
    breed: Optional[str] = Field(default=None, min_length=2, max_length=80)
    acquisition_date: Optional[date] = None
    source: Optional[str] = Field(default=None, max_length=160)
    age_days_at_acquisition: Optional[int] = Field(default=None, ge=0, le=2000)
    cost_per_bird: Optional[NonNegativeMoney] = None
    initial_quantity: Optional[int] = Field(default=None, gt=0, le=1_000_000)
    status: Optional[BatchStatus] = None
    notes: Optional[str] = None

    _check_date = field_validator("acquisition_date")(
        lambda v: _not_in_future(v) if v else v
    )


class BatchAdjustment(BaseModel):
    """Non-mortality shrinkage: theft, escape or a corrected miscount."""

    quantity: int = Field(gt=0, description="Birds to remove from the batch")
    reason: str = Field(min_length=3, max_length=200)


class BirdBatchOut(ORMModel):
    id: int
    batch_code: str
    breed: str
    initial_quantity: int
    acquisition_date: date
    source: Optional[str] = None
    age_days_at_acquisition: int
    cost_per_bird: NonNegativeMoney
    total_acquisition_cost: NonNegativeMoney
    adjustment_quantity: int
    status: BatchStatus
    notes: Optional[str] = None
    # Derived, never stored:
    total_deaths: int = 0
    total_sold: int = 0
    current_quantity: int = 0
    sick_count: int = 0
    healthy_quantity: int = 0
    mortality_rate: float = 0.0
    age_days: int = 0


class MortalityBase(BaseModel):
    batch_id: int = Field(gt=0)
    record_date: date
    quantity: int = Field(gt=0, le=1_000_000)
    cause: Optional[str] = Field(default=None, max_length=160)
    notes: Optional[str] = None

    _check_date = field_validator("record_date")(_not_in_future)


class MortalityCreate(MortalityBase):
    pass


class MortalityUpdate(BaseModel):
    record_date: Optional[date] = None
    quantity: Optional[int] = Field(default=None, gt=0, le=1_000_000)
    cause: Optional[str] = Field(default=None, max_length=160)
    notes: Optional[str] = None


class MortalityOut(ORMModel):
    id: int
    batch_id: int
    batch_code: Optional[str] = None
    record_date: date
    quantity: int
    cause: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[date] = None


class HealthBase(BaseModel):
    batch_id: int = Field(gt=0)
    record_date: date
    sick_count: int = Field(gt=0, le=1_000_000)
    symptoms: Optional[str] = None
    diagnosis: Optional[str] = Field(default=None, max_length=200)
    treatment: Optional[str] = None
    medicine: Optional[str] = Field(default=None, max_length=160)
    dosage: Optional[str] = Field(default=None, max_length=120)
    treatment_cost: NonNegativeMoney = Decimal("0")
    veterinarian: Optional[str] = Field(default=None, max_length=120)
    status: HealthStatus = HealthStatus.SICK
    notes: Optional[str] = None

    _check_date = field_validator("record_date")(_not_in_future)


class HealthCreate(HealthBase):
    pass


class HealthUpdate(BaseModel):
    record_date: Optional[date] = None
    sick_count: Optional[int] = Field(default=None, gt=0, le=1_000_000)
    symptoms: Optional[str] = None
    diagnosis: Optional[str] = Field(default=None, max_length=200)
    treatment: Optional[str] = None
    medicine: Optional[str] = Field(default=None, max_length=160)
    dosage: Optional[str] = Field(default=None, max_length=120)
    treatment_cost: Optional[NonNegativeMoney] = None
    veterinarian: Optional[str] = Field(default=None, max_length=120)
    status: Optional[HealthStatus] = None
    notes: Optional[str] = None


class HealthOut(ORMModel):
    id: int
    batch_id: int
    batch_code: Optional[str] = None
    record_date: date
    sick_count: int
    symptoms: Optional[str] = None
    diagnosis: Optional[str] = None
    treatment: Optional[str] = None
    medicine: Optional[str] = None
    dosage: Optional[str] = None
    treatment_cost: NonNegativeMoney
    veterinarian: Optional[str] = None
    status: HealthStatus
    notes: Optional[str] = None
