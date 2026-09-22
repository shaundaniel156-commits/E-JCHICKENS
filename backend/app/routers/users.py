"""User administration endpoints (administrators only)."""
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import get_current_user, require_admin
from app.dependencies.filters import PageParams, pagination
from app.models.enums import RoleName
from app.models.user import User
from app.schemas.common import Message, Page
from app.schemas.user import (
    PasswordResetResult,
    ProfileUpdate,
    UserCreate,
    UserOut,
    UserUpdate,
)
from app.services import user_service

router = APIRouter(prefix="/users", tags=["Users"])


def _to_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        full_name=user.full_name,
        username=user.username,
        email=user.email,
        phone=user.phone,
        role=user.role_name,
        is_active=user.is_active,
        must_change_password=user.must_change_password,
        avatar_url=user.avatar_url,
        notes=user.notes,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
    )


@router.get("", response_model=Page[UserOut], summary="List users")
def list_users(
    page_params: PageParams = Depends(pagination),
    search: Optional[str] = Query(None),
    role: Optional[RoleName] = Query(None),
    is_active: Optional[bool] = Query(None),
    sort: str = Query("full_name"),
    order: str = Query("asc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    rows, meta = user_service.list_users(
        db,
        page=page_params.page,
        page_size=page_params.page_size,
        search=search,
        role=role,
        is_active=is_active,
        sort=sort,
        order=order,
    )
    return Page[UserOut](items=[_to_out(row) for row in rows], meta=meta)


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED, summary="Add a user")
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    return _to_out(user_service.create_user(db, payload, admin))


@router.get("/me", response_model=UserOut, summary="Your own profile")
def my_profile(user: User = Depends(get_current_user)):
    return _to_out(user)


@router.put("/me", response_model=UserOut, summary="Update your own profile")
def update_my_profile(
    payload: ProfileUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return _to_out(user_service.update_profile(db, user, payload))


@router.get("/{user_id}", response_model=UserOut, summary="Fetch one user")
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    return _to_out(user_service.get_user(db, user_id))


@router.put("/{user_id}", response_model=UserOut, summary="Update a user")
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    return _to_out(user_service.update_user(db, user_id, payload, admin))


@router.delete("/{user_id}", response_model=Message, summary="Deactivate a user")
def deactivate_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    user = user_service.deactivate_user(db, user_id, admin)
    return Message(message=f"{user.full_name} has been deactivated.")


@router.post("/{user_id}/activate", response_model=UserOut, summary="Re-activate a user")
def activate_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    return _to_out(user_service.activate_user(db, user_id, admin))


@router.post(
    "/{user_id}/reset-password",
    response_model=PasswordResetResult,
    summary="Issue a temporary password",
)
def reset_user_password(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    user, temporary = user_service.reset_password(db, user_id, admin)
    return PasswordResetResult(
        message=f"A temporary password has been issued for {user.full_name}. "
        "They will be asked to change it at next sign-in.",
        temporary_password=temporary,
    )
