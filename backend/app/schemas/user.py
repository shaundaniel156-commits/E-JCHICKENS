"""User management payloads."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.enums import RoleName
from app.schemas.common import ORMModel

_USERNAME_PATTERN = r"^[A-Za-z0-9._-]+$"


class UserBase(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    phone: Optional[str] = Field(default=None, max_length=30)
    role: RoleName = RoleName.STAFF
    is_active: bool = True
    notes: Optional[str] = None


class UserCreate(UserBase):
    username: str = Field(min_length=3, max_length=60, pattern=_USERNAME_PATTERN)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def _strength(cls, value: str) -> str:
        if value.isdigit() or value.isalpha():
            raise ValueError("Password must mix letters with numbers or symbols.")
        return value


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(default=None, max_length=30)
    role: Optional[RoleName] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None


class ProfileUpdate(BaseModel):
    full_name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(default=None, max_length=30)
    avatar_url: Optional[str] = Field(default=None, max_length=255)


class UserOut(ORMModel):
    id: int
    full_name: str
    username: str
    email: EmailStr
    phone: Optional[str] = None
    role: str
    is_active: bool
    must_change_password: bool
    avatar_url: Optional[str] = None
    notes: Optional[str] = None
    last_login_at: Optional[datetime] = None
    created_at: datetime


class PasswordResetResult(BaseModel):
    message: str
    temporary_password: str
