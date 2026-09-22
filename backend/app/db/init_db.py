"""Bootstrap: roles, reference data and the first administrator."""
from __future__ import annotations

import os

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging_config import get_logger
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.enums import RoleName
from app.models.user import Role, User
from app.services import expense_service, feed_service, settings_service

logger = get_logger(__name__)

ROLE_DESCRIPTIONS = {
    RoleName.ADMIN: "Full access to every module, users and settings",
    RoleName.MANAGER: "Runs the farm: birds, feed, health, sales and finance",
    RoleName.STAFF: "Records daily farm activity",
}


def ensure_roles(db: Session) -> None:
    existing = {role.name for role in db.execute(select(Role)).scalars().all()}
    for name, description in ROLE_DESCRIPTIONS.items():
        if name not in existing:
            db.add(Role(name=name, description=description))
    db.flush()


def ensure_admin(db: Session) -> User | None:
    """Create the first administrator from the environment, if none exists."""
    admin_role = db.execute(select(Role).where(Role.name == RoleName.ADMIN)).scalars().one()
    existing = db.execute(
        select(User).where(User.role_id == admin_role.id)
    ).scalars().first()
    if existing:
        return existing

    email = os.getenv("ADMIN_EMAIL", "admin@ejchickens.com")
    username = os.getenv("ADMIN_USERNAME", "admin")
    password = os.getenv("ADMIN_PASSWORD", "Admin@12345")
    full_name = os.getenv("ADMIN_NAME", "Farm Administrator")

    admin = User(
        full_name=full_name,
        username=username,
        email=email.lower(),
        password_hash=hash_password(password),
        role_id=admin_role.id,
        is_active=True,
    )
    db.add(admin)
    db.flush()
    logger.info("Created the initial administrator account: %s", email)
    return admin


def initialise(db: Session | None = None) -> None:
    """Idempotent: safe to run on every deployment."""
    owns_session = db is None
    db = db or SessionLocal()
    try:
        ensure_roles(db)
        ensure_admin(db)
        settings_service.get_settings(db)
        expense_service.ensure_default_categories(db)
        feed_service.ensure_default_feed_types(db)
        db.commit()
        logger.info("Reference data is in place.")
    finally:
        if owns_session:
            db.close()


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    initialise()
    print("Database initialised: roles, settings, categories, feed types and admin user.")
