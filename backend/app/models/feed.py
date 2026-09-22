"""Feed types, purchases and consumption."""
from datetime import date
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import AuthorshipMixin, Base, SoftDeleteMixin, TimestampMixin


class FeedType(Base, TimestampMixin):
    __tablename__ = "feed_types"
    __table_args__ = (
        CheckConstraint("default_bag_weight_kg > 0", name="ck_feedtype_bag_weight_positive"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(String(255))
    default_bag_weight_kg: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=Decimal("50"), nullable=False
    )

    purchases: Mapped[List["FeedPurchase"]] = relationship(back_populates="feed_type")
    consumption: Mapped[List["FeedConsumption"]] = relationship(back_populates="feed_type")


class FeedPurchase(Base, TimestampMixin, AuthorshipMixin, SoftDeleteMixin):
    __tablename__ = "feed_purchases"
    __table_args__ = (
        CheckConstraint("quantity_bags > 0", name="ck_purchase_bags_positive"),
        CheckConstraint("bag_weight_kg > 0", name="ck_purchase_weight_positive"),
        CheckConstraint("cost_per_bag >= 0", name="ck_purchase_cost_non_negative"),
        Index("ix_feed_purchase_type_date", "feed_type_id", "purchase_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    feed_type_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("feed_types.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    purchase_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    brand: Mapped[Optional[str]] = mapped_column(String(120))
    quantity_bags: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    bag_weight_kg: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    cost_per_bag: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False)
    total_cost: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False)
    supplier: Mapped[Optional[str]] = mapped_column(String(160))
    lot_number: Mapped[Optional[str]] = mapped_column(String(60))
    notes: Mapped[Optional[str]] = mapped_column(Text)

    feed_type: Mapped[FeedType] = relationship(back_populates="purchases", lazy="joined")

    @property
    def quantity_kg(self) -> Decimal:
        return self.quantity_bags * self.bag_weight_kg


class FeedConsumption(Base, TimestampMixin, AuthorshipMixin, SoftDeleteMixin):
    __tablename__ = "feed_consumption"
    __table_args__ = (
        CheckConstraint("quantity_kg > 0", name="ck_consumption_kg_positive"),
        Index("ix_feed_consumption_type_date", "feed_type_id", "consumption_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    feed_type_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("feed_types.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    batch_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("bird_batches.id", ondelete="SET NULL"), nullable=True, index=True
    )
    consumption_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    quantity_bags: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"), nullable=False)
    quantity_kg: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    feed_type: Mapped[FeedType] = relationship(back_populates="consumption", lazy="joined")
