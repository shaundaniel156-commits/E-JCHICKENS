"""User administration."""
from __future__ import annotations

from typing import Optional

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, DuplicateError, NotFoundError
from app.core.security import generate_temporary_password, hash_password
from app.models.enums import ActivityAction, RoleName
from app.models.user import Role, User
from app.schemas.user import ProfileUpdate, UserCreate, UserUpdate
from app.services import activity_service
from app.utils.pagination import paginate


def get_role(db: Session, name: RoleName) -> Role:
    role = db.execute(select(Role).where(Role.name == name)).scalars().first()
    if role is None:
        raise NotFoundError(f"Role {name} is not configured.")
    return role


def get_user(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise NotFoundError("User not found.")
    return user


def find_by_identifier(db: Session, identifier: str) -> Optional[User]:
    value = identifier.strip().lower()
    return db.execute(
        select(User).where(
            or_(func.lower(User.email) == value, func.lower(User.username) == value)
        )
    ).scalars().first()


def _assert_unique(db: Session, email: str, username: str, exclude_id: Optional[int] = None) -> None:
    stmt = select(User).where(
        or_(
            func.lower(User.email) == email.lower(),
            func.lower(User.username) == username.lower(),
        )
    )
    if exclude_id:
        stmt = stmt.where(User.id != exclude_id)
    existing = db.execute(stmt).scalars().first()
    if existing:
        field = "email address" if existing.email.lower() == email.lower() else "username"
        raise DuplicateError(f"That {field} is already registered.")


def list_users(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 20,
    search: Optional[str] = None,
    role: Optional[RoleName] = None,
    is_active: Optional[bool] = None,
    sort: str = "full_name",
    order: str = "asc",
):
    stmt = select(User).join(Role)
    if search:
        pattern = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                User.full_name.ilike(pattern),
                User.email.ilike(pattern),
                User.username.ilike(pattern),
            )
        )
    if role:
        stmt = stmt.where(Role.name == role)
    if is_active is not None:
        stmt = stmt.where(User.is_active.is_(is_active))

    sortable = {
        "full_name": User.full_name,
        "email": User.email,
        "username": User.username,
        "created_at": User.created_at,
        "last_login_at": User.last_login_at,
    }
    column = sortable.get(sort, User.full_name)
    stmt = stmt.order_by(column.desc() if order == "desc" else column.asc())
    return paginate(db, stmt, page, page_size)


def create_user(db: Session, payload: UserCreate, actor: Optional[User] = None) -> User:
    _assert_unique(db, payload.email, payload.username)
    role = get_role(db, payload.role)
    user = User(
        full_name=payload.full_name.strip(),
        username=payload.username.strip(),
        email=payload.email.strip().lower(),
        phone=payload.phone,
        password_hash=hash_password(payload.password),
        role_id=role.id,
        is_active=payload.is_active,
        notes=payload.notes,
    )
    db.add(user)
    db.flush()
    activity_service.record(
        db,
        user=actor,
        action=ActivityAction.CREATE,
        module="users",
        description=f"Created user {user.full_name} ({payload.role.value})",
        entity_id=user.id,
    )
    db.commit()
    db.refresh(user)
    return user


def update_user(db: Session, user_id: int, payload: UserUpdate, actor: Optional[User] = None) -> User:
    user = get_user(db, user_id)
    data = payload.model_dump(exclude_unset=True)

    new_email = data.get("email", user.email)
    if "email" in data:
        _assert_unique(db, new_email, user.username, exclude_id=user.id)
        user.email = new_email.strip().lower()

    if "role" in data and data["role"] is not None:
        if user.role.name == RoleName.ADMIN and data["role"] != RoleName.ADMIN:
            _assert_another_admin_exists(db, user.id)
        user.role_id = get_role(db, data["role"]).id

    if "is_active" in data and data["is_active"] is False and user.role.name == RoleName.ADMIN:
        _assert_another_admin_exists(db, user.id)

    for field in ("full_name", "phone", "is_active", "notes"):
        if field in data:
            setattr(user, field, data[field])

    activity_service.record(
        db,
        user=actor,
        action=ActivityAction.UPDATE,
        module="users",
        description=f"Updated user {user.full_name}",
        entity_id=user.id,
    )
    db.commit()
    db.refresh(user)
    return user


def _assert_another_admin_exists(db: Session, excluding_user_id: int) -> None:
    remaining = db.execute(
        select(func.count(User.id))
        .join(Role)
        .where(Role.name == RoleName.ADMIN, User.is_active.is_(True), User.id != excluding_user_id)
    ).scalar_one()
    if remaining == 0:
        raise ConflictError("The farm must keep at least one active administrator.")


def deactivate_user(db: Session, user_id: int, actor: Optional[User] = None) -> User:
    user = get_user(db, user_id)
    if actor and actor.id == user.id:
        raise ConflictError("You cannot deactivate your own account.")
    if user.role.name == RoleName.ADMIN:
        _assert_another_admin_exists(db, user.id)
    user.is_active = False
    activity_service.record(
        db,
        user=actor,
        action=ActivityAction.DELETE,
        module="users",
        description=f"Deactivated user {user.full_name}",
        entity_id=user.id,
    )
    db.commit()
    db.refresh(user)
    return user


def activate_user(db: Session, user_id: int, actor: Optional[User] = None) -> User:
    user = get_user(db, user_id)
    user.is_active = True
    activity_service.record(
        db,
        user=actor,
        action=ActivityAction.RESTORE,
        module="users",
        description=f"Re-activated user {user.full_name}",
        entity_id=user.id,
    )
    db.commit()
    db.refresh(user)
    return user


def reset_password(db: Session, user_id: int, actor: Optional[User] = None) -> tuple[User, str]:
    """Administrator reset: issues a temporary password the user must change."""
    user = get_user(db, user_id)
    temporary = generate_temporary_password()
    user.password_hash = hash_password(temporary)
    user.must_change_password = True
    activity_service.record(
        db,
        user=actor,
        action=ActivityAction.UPDATE,
        module="users",
        description=f"Reset the password for {user.full_name}",
        entity_id=user.id,
    )
    db.commit()
    db.refresh(user)
    return user, temporary


def update_profile(db: Session, user: User, payload: ProfileUpdate) -> User:
    data = payload.model_dump(exclude_unset=True)
    if "email" in data and data["email"]:
        _assert_unique(db, data["email"], user.username, exclude_id=user.id)
        user.email = data["email"].strip().lower()
    for field in ("full_name", "phone", "avatar_url"):
        if field in data:
            setattr(user, field, data[field])
    activity_service.record(
        db,
        user=user,
        action=ActivityAction.UPDATE,
        module="profile",
        description="Updated own profile",
        entity_id=user.id,
    )
    db.commit()
    db.refresh(user)
    return user
