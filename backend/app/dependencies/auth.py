"""Authentication and role dependencies used by the routers."""
from typing import Optional

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.exceptions import AuthenticationError, PermissionDeniedError
from app.db.session import get_db
from app.models.enums import RoleName
from app.models.user import User
from app.services import auth_service

_bearer = HTTPBearer(auto_error=False, description="JWT access token")


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or not credentials.credentials:
        raise AuthenticationError("Please sign in to continue.")
    return auth_service.user_from_access_token(db, credentials.credentials)


def require_roles(*roles: RoleName):
    """Dependency factory: allows only the listed roles through."""

    allowed = set(roles)

    def _guard(user: User = Depends(get_current_user)) -> User:
        if user.role.name not in allowed:
            raise PermissionDeniedError(
                "You do not have permission to perform this action."
            )
        return user

    return _guard


require_admin = require_roles(RoleName.ADMIN)
require_manager = require_roles(RoleName.ADMIN, RoleName.MANAGER)
require_staff = require_roles(RoleName.ADMIN, RoleName.MANAGER, RoleName.STAFF)


def client_ip(request: Request) -> Optional[str]:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None
