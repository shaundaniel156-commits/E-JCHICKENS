"""Password hashing and JWT issuing/validation."""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import bcrypt
import jwt

from app.core.config import settings
from app.core.exceptions import AuthenticationError

ACCESS_TOKEN = "access"
REFRESH_TOKEN = "refresh"
RESET_TOKEN = "reset"

# bcrypt refuses inputs longer than 72 bytes; truncate deterministically instead of failing.
_BCRYPT_MAX_BYTES = 72


def _to_bcrypt_bytes(password: str) -> bytes:
    return password.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_to_bcrypt_bytes(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(_to_bcrypt_bytes(password), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def _create_token(subject: str, token_type: str, expires: timedelta, **claims: Any) -> str:
    now = datetime.now(timezone.utc)
    payload: Dict[str, Any] = {
        "sub": str(subject),
        "type": token_type,
        "iat": now,
        "exp": now + expires,
        "jti": secrets.token_urlsafe(16),
        **claims,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(user_id: int, role: str, **claims: Any) -> str:
    return _create_token(
        str(user_id),
        ACCESS_TOKEN,
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        role=role,
        **claims,
    )


def create_refresh_token(user_id: int) -> str:
    return _create_token(
        str(user_id), REFRESH_TOKEN, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )


def create_password_reset_token(user_id: int) -> str:
    return _create_token(
        str(user_id), RESET_TOKEN, timedelta(minutes=settings.PASSWORD_RESET_EXPIRE_MINUTES)
    )


def decode_token(token: str, expected_type: Optional[str] = None) -> Dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise AuthenticationError("Your session has expired. Please sign in again.") from exc
    except jwt.PyJWTError as exc:
        raise AuthenticationError("Invalid authentication token.") from exc

    if expected_type and payload.get("type") != expected_type:
        raise AuthenticationError("Invalid authentication token.")
    return payload


def generate_temporary_password(length: int = 12) -> str:
    """Used when an administrator resets another user's password."""
    alphabet = "abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(length)) + "!1"
