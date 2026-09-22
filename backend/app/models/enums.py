"""Enumerations shared by models and schemas."""
from enum import Enum


class StrEnum(str, Enum):
    def __str__(self) -> str:  # pragma: no cover - convenience only
        return self.value


class RoleName(StrEnum):
    ADMIN = "ADMIN"
    MANAGER = "MANAGER"
    STAFF = "STAFF"


class BatchStatus(StrEnum):
    ACTIVE = "ACTIVE"
    SOLD_OUT = "SOLD_OUT"
    CLOSED = "CLOSED"


class HealthStatus(StrEnum):
    SICK = "SICK"
    UNDER_TREATMENT = "UNDER_TREATMENT"
    RECOVERED = "RECOVERED"
    CRITICAL = "CRITICAL"


class PaymentStatus(StrEnum):
    PAID = "PAID"
    PARTIAL = "PARTIAL"
    UNPAID = "UNPAID"
    CANCELLED = "CANCELLED"


class PaymentMethod(StrEnum):
    CASH = "CASH"
    MOBILE_MONEY = "MOBILE_MONEY"
    BANK_TRANSFER = "BANK_TRANSFER"
    CHEQUE = "CHEQUE"
    CREDIT = "CREDIT"
    OTHER = "OTHER"


class NotificationType(StrEnum):
    FEED_LOW = "FEED_LOW"
    FEED_UPDATED = "FEED_UPDATED"
    MORTALITY_HIGH = "MORTALITY_HIGH"
    MORTALITY_RECORDED = "MORTALITY_RECORDED"
    BUDGET_WARNING = "BUDGET_WARNING"
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"
    HEALTH_ALERT = "HEALTH_ALERT"
    SALE_COMPLETED = "SALE_COMPLETED"
    BIRDS_ADDED = "BIRDS_ADDED"
    SYSTEM = "SYSTEM"


class NotificationSeverity(StrEnum):
    INFO = "INFO"
    SUCCESS = "SUCCESS"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class ActivityAction(StrEnum):
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    RESTORE = "RESTORE"


class ExpenseSource(StrEnum):
    MANUAL = "MANUAL"
    BIRD_BATCH = "BIRD_BATCH"
    FEED_PURCHASE = "FEED_PURCHASE"
    HEALTH_RECORD = "HEALTH_RECORD"
