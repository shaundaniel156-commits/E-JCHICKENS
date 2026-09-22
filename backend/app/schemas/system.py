"""Settings, notification and activity-log payloads."""
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from app.models.enums import ActivityAction, NotificationSeverity, NotificationType
from app.schemas.common import ORMModel, QuantityOut


class FarmSettingsUpdate(BaseModel):
    farm_name: Optional[str] = Field(default=None, min_length=2, max_length=160)
    owner_name: Optional[str] = Field(default=None, max_length=160)
    location: Optional[str] = Field(default=None, max_length=200)
    phone: Optional[str] = Field(default=None, max_length=30)
    email: Optional[EmailStr] = None
    logo_url: Optional[str] = Field(default=None, max_length=255)
    currency: Optional[str] = Field(default=None, min_length=2, max_length=10)
    date_format: Optional[str] = Field(default=None, max_length=20)
    low_feed_threshold_bags: Optional[Decimal] = Field(default=None, ge=0, le=100000)
    high_mortality_rate_percent: Optional[Decimal] = Field(default=None, ge=0, le=100)
    budget_warning_percent: Optional[Decimal] = Field(default=None, ge=0, le=100)
    notifications_enabled: Optional[bool] = None


class FarmSettingsOut(ORMModel):
    id: int
    farm_name: str
    owner_name: Optional[str] = None
    location: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    logo_url: Optional[str] = None
    currency: str
    date_format: str
    low_feed_threshold_bags: QuantityOut
    high_mortality_rate_percent: QuantityOut
    budget_warning_percent: QuantityOut
    notifications_enabled: bool


class NotificationOut(ORMModel):
    id: int
    type: NotificationType
    severity: NotificationSeverity
    title: str
    message: str
    module: Optional[str] = None
    entity_id: Optional[int] = None
    is_read: bool
    read_at: Optional[datetime] = None
    created_at: datetime


class NotificationCount(BaseModel):
    total: int
    unread: int


class ActivityLogOut(ORMModel):
    id: int
    user_id: Optional[int] = None
    user_display: Optional[str] = None
    action: ActivityAction
    module: str
    description: str
    entity_id: Optional[int] = None
    ip_address: Optional[str] = None
    created_at: datetime
