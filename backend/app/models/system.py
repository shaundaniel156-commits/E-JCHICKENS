"""Farm settings, notifications and the activity/audit log."""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin
from app.models.enums import ActivityAction, NotificationSeverity, NotificationType


class FarmSetting(Base, TimestampMixin):
    """Single-row configuration table (id is always 1)."""

    __tablename__ = "farm_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    farm_name: Mapped[str] = mapped_column(String(160), default="E&J's CHICKENS", nullable=False)
    owner_name: Mapped[Optional[str]] = mapped_column(String(160))
    location: Mapped[Optional[str]] = mapped_column(String(200))
    phone: Mapped[Optional[str]] = mapped_column(String(30))
    email: Mapped[Optional[str]] = mapped_column(String(160))
    logo_url: Mapped[Optional[str]] = mapped_column(String(255))
    currency: Mapped[str] = mapped_column(String(10), default="UGX", nullable=False)
    date_format: Mapped[str] = mapped_column(String(20), default="DD/MM/YYYY", nullable=False)
    low_feed_threshold_bags: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=Decimal("5"), nullable=False
    )
    high_mortality_rate_percent: Mapped[Decimal] = mapped_column(
        Numeric(6, 2), default=Decimal("5"), nullable=False
    )
    budget_warning_percent: Mapped[Decimal] = mapped_column(
        Numeric(6, 2), default=Decimal("80"), nullable=False
    )
    notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Notification(Base, TimestampMixin):
    __tablename__ = "notifications"
    __table_args__ = (Index("ix_notification_read_created", "is_read", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType, native_enum=False, length=30), nullable=False, index=True
    )
    severity: Mapped[NotificationSeverity] = mapped_column(
        Enum(NotificationSeverity, native_enum=False, length=20),
        default=NotificationSeverity.INFO,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    module: Mapped[Optional[str]] = mapped_column(String(40))
    entity_id: Mapped[Optional[int]] = mapped_column(Integer)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    # NULL = broadcast to every user.
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    # Guards against re-raising the same alert every time a figure is recalculated.
    dedupe_key: Mapped[Optional[str]] = mapped_column(String(120), index=True)


class ActivityLog(Base):
    __tablename__ = "activity_logs"
    __table_args__ = (Index("ix_activity_module_created", "module", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    user_display: Mapped[Optional[str]] = mapped_column(String(120))
    action: Mapped[ActivityAction] = mapped_column(
        Enum(ActivityAction, native_enum=False, length=20), nullable=False, index=True
    )
    module: Mapped[str] = mapped_column(String(40), nullable=False)
    description: Mapped[str] = mapped_column(String(400), nullable=False)
    entity_id: Mapped[Optional[int]] = mapped_column(Integer)
    ip_address: Mapped[Optional[str]] = mapped_column(String(60))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False, index=True
    )

    user: Mapped[Optional["User"]] = relationship(lazy="joined")  # noqa: F821
