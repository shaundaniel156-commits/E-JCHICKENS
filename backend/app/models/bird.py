"""Bird batches, mortality and health records."""
from datetime import date
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import (
    CheckConstraint,
    Date,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import AuthorshipMixin, Base, SoftDeleteMixin, TimestampMixin
from app.models.enums import BatchStatus, HealthStatus


class BirdBatch(Base, TimestampMixin, AuthorshipMixin, SoftDeleteMixin):
    __tablename__ = "bird_batches"
    __table_args__ = (
        CheckConstraint("initial_quantity > 0", name="ck_batch_initial_positive"),
        CheckConstraint("adjustment_quantity >= 0", name="ck_batch_adjustment_non_negative"),
        CheckConstraint("cost_per_bird >= 0", name="ck_batch_cost_non_negative"),
        Index("ix_batch_status_date", "status", "acquisition_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    batch_code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False, index=True)
    breed: Mapped[str] = mapped_column(String(80), nullable=False)
    initial_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    acquisition_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    source: Mapped[Optional[str]] = mapped_column(String(160))
    age_days_at_acquisition: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cost_per_bird: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=Decimal("0"), nullable=False)
    # Non-mortality shrinkage (theft, escape, corrected miscount) recorded explicitly.
    adjustment_quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[BatchStatus] = mapped_column(
        Enum(BatchStatus, native_enum=False, length=20),
        default=BatchStatus.ACTIVE,
        nullable=False,
        index=True,
    )
    notes: Mapped[Optional[str]] = mapped_column(Text)

    mortality_records: Mapped[List["MortalityRecord"]] = relationship(
        back_populates="batch", cascade="all, delete-orphan"
    )
    health_records: Mapped[List["HealthRecord"]] = relationship(
        back_populates="batch", cascade="all, delete-orphan"
    )

    @property
    def total_acquisition_cost(self) -> Decimal:
        return (self.cost_per_bird or Decimal("0")) * self.initial_quantity


class MortalityRecord(Base, TimestampMixin, AuthorshipMixin, SoftDeleteMixin):
    __tablename__ = "mortality_records"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_mortality_quantity_positive"),
        Index("ix_mortality_batch_date", "batch_id", "record_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    batch_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("bird_batches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    record_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    cause: Mapped[Optional[str]] = mapped_column(String(160))
    notes: Mapped[Optional[str]] = mapped_column(Text)

    batch: Mapped[BirdBatch] = relationship(back_populates="mortality_records")


class HealthRecord(Base, TimestampMixin, AuthorshipMixin, SoftDeleteMixin):
    __tablename__ = "health_records"
    __table_args__ = (
        CheckConstraint("sick_count > 0", name="ck_health_sick_positive"),
        CheckConstraint("treatment_cost >= 0", name="ck_health_cost_non_negative"),
        Index("ix_health_batch_status", "batch_id", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    batch_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("bird_batches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    record_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    sick_count: Mapped[int] = mapped_column(Integer, nullable=False)
    symptoms: Mapped[Optional[str]] = mapped_column(Text)
    diagnosis: Mapped[Optional[str]] = mapped_column(String(200))
    treatment: Mapped[Optional[str]] = mapped_column(Text)
    medicine: Mapped[Optional[str]] = mapped_column(String(160))
    dosage: Mapped[Optional[str]] = mapped_column(String(120))
    treatment_cost: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=Decimal("0"), nullable=False)
    veterinarian: Mapped[Optional[str]] = mapped_column(String(120))
    status: Mapped[HealthStatus] = mapped_column(
        Enum(HealthStatus, native_enum=False, length=20),
        default=HealthStatus.SICK,
        nullable=False,
        index=True,
    )
    notes: Mapped[Optional[str]] = mapped_column(Text)

    batch: Mapped[BirdBatch] = relationship(back_populates="health_records")

    OPEN_STATUSES = (HealthStatus.SICK, HealthStatus.UNDER_TREATMENT, HealthStatus.CRITICAL)

    @property
    def is_open(self) -> bool:
        return self.status in self.OPEN_STATUSES
