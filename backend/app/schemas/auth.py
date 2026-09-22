"""Authentication payloads."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import ORMModel


class LoginRequest(BaseModel):
    identifier: str = Field(min_length=3, max_length=160, description="Email address or username")
    password: str = Field(min_length=1, max_length=128)
    remember_me: bool = False


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str


class CurrentUser(ORMModel):
    id: int
    full_name: str
    username: str
    email: EmailStr
    phone: Optional[str] = None
    role: str
    is_active: bool
    must_change_password: bool
    avatar_url: Optional[str] = None
    last_login_at: Optional[datetime] = None


class LoginResponse(BaseModel):
    tokens: TokenPair
    user: CurrentUser


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    message: str
    # Development convenience: no mail server is configured, so the token is returned
    # directly when DEBUG is on. It is omitted in production.
    reset_token: Optional[str] = None


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)
