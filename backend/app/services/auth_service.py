"""Login, token refresh and password workflows."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AuthenticationError, NotFoundError, ValidationError
from app.core.security import (
    ACCESS_TOKEN,
    REFRESH_TOKEN,
    RESET_TOKEN,
    create_access_token,
    create_password_reset_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.enums import ActivityAction
from app.models.user import User
from app.schemas.auth import TokenPair
from app.services import activity_service, user_service

_INVALID_CREDENTIALS = "Incorrect email/username or password."


def authenticate(
    db: Session, identifier: str, password: str, ip_address: Optional[str] = None
) -> User:
    user = user_service.find_by_identifier(db, identifier)
    # The same message is returned whether the account is missing or the password is
    # wrong, so the login form cannot be used to enumerate users.
    if user is None or not verify_password(password, user.password_hash):
        raise AuthenticationError(_INVALID_CREDENTIALS)
    if not user.is_active:
        raise AuthenticationError("This account has been deactivated. Contact an administrator.")

    user.last_login_at = datetime.utcnow()
    activity_service.record(
        db,
        user=user,
        action=ActivityAction.LOGIN,
        module="auth",
        description=f"{user.full_name} signed in",
        entity_id=user.id,
        ip_address=ip_address,
    )
    db.commit()
    db.refresh(user)
    return user


def issue_tokens(user: User, remember_me: bool = False) -> TokenPair:
    minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES * (8 if remember_me else 1)
    access = create_access_token(user.id, user.role_name, username=user.username)
    return TokenPair(
        access_token=access,
        refresh_token=create_refresh_token(user.id),
        expires_in=minutes * 60,
    )


def refresh_tokens(db: Session, refresh_token: str) -> tuple[User, TokenPair]:
    payload = decode_token(refresh_token, expected_type=REFRESH_TOKEN)
    user = db.get(User, int(payload["sub"]))
    if user is None or not user.is_active:
        raise AuthenticationError("This session is no longer valid. Please sign in again.")
    return user, issue_tokens(user)


def logout(db: Session, user: User, ip_address: Optional[str] = None) -> None:
    activity_service.record(
        db,
        user=user,
        action=ActivityAction.LOGOUT,
        module="auth",
        description=f"{user.full_name} signed out",
        entity_id=user.id,
        ip_address=ip_address,
    )
    db.commit()


def change_password(db: Session, user: User, current_password: str, new_password: str) -> None:
    if not verify_password(current_password, user.password_hash):
        raise ValidationError("Your current password is not correct.")
    if current_password == new_password:
        raise ValidationError("The new password must be different from the current one.")
    user.password_hash = hash_password(new_password)
    user.must_change_password = False
    activity_service.record(
        db,
        user=user,
        action=ActivityAction.UPDATE,
        module="auth",
        description=f"{user.full_name} changed their password",
        entity_id=user.id,
    )
    db.commit()


def request_password_reset(db: Session, email: str) -> Optional[str]:
    """Returns a reset token, or None when the address is unknown.

    The router always answers with the same message so the endpoint cannot be used
    to discover which addresses exist.
    """
    user = user_service.find_by_identifier(db, email)
    if user is None or not user.is_active:
        return None
    return create_password_reset_token(user.id)


def reset_password_with_token(db: Session, token: str, new_password: str) -> User:
    payload = decode_token(token, expected_type=RESET_TOKEN)
    user = db.get(User, int(payload["sub"]))
    if user is None or not user.is_active:
        raise NotFoundError("This reset link is no longer valid.")
    user.password_hash = hash_password(new_password)
    user.must_change_password = False
    activity_service.record(
        db,
        user=user,
        action=ActivityAction.UPDATE,
        module="auth",
        description=f"{user.full_name} reset their password",
        entity_id=user.id,
    )
    db.commit()
    db.refresh(user)
    return user


def user_from_access_token(db: Session, token: str) -> User:
    payload = decode_token(token, expected_type=ACCESS_TOKEN)
    user = db.get(User, int(payload["sub"]))
    if user is None:
        raise AuthenticationError("Your account could not be found.")
    if not user.is_active:
        raise AuthenticationError("This account has been deactivated.")
    return user
