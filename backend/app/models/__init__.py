"""Import every model so SQLAlchemy's metadata (and Alembic) sees the full schema."""
from app.db.base_class import Base
from app.models.bird import BirdBatch, HealthRecord, MortalityRecord
from app.models.enums import (
    ActivityAction,
    BatchStatus,
    ExpenseSource,
    HealthStatus,
    NotificationSeverity,
    NotificationType,
    PaymentMethod,
    PaymentStatus,
    RoleName,
)
from app.models.feed import FeedConsumption, FeedPurchase, FeedType
from app.models.finance import Budget, Customer, Expense, ExpenseCategory, Sale
from app.models.system import ActivityLog, FarmSetting, Notification
from app.models.user import Role, User

__all__ = [
    "Base",
    "Role",
    "User",
    "BirdBatch",
    "MortalityRecord",
    "HealthRecord",
    "FeedType",
    "FeedPurchase",
    "FeedConsumption",
    "ExpenseCategory",
    "Expense",
    "Customer",
    "Sale",
    "Budget",
    "FarmSetting",
    "Notification",
    "ActivityLog",
    "RoleName",
    "BatchStatus",
    "HealthStatus",
    "PaymentStatus",
    "PaymentMethod",
    "NotificationType",
    "NotificationSeverity",
    "ActivityAction",
    "ExpenseSource",
]
