"""The Alembic migration must run on every database we claim to support.

This exists because the first migration was generated against MySQL and baked
`now()` into its column defaults — valid MySQL, a syntax error on SQLite. The
rest of the suite builds its schema with `create_all`, so nothing caught it and
`alembic upgrade head` simply failed for anyone not on MySQL.
"""
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from app.models import Base

BACKEND_ROOT = Path(__file__).resolve().parents[1]
VERSIONS_DIR = BACKEND_ROOT / "alembic" / "versions"


def _alembic_config(database_url: str) -> Config:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def test_migrations_run_on_sqlite(tmp_path):
    """`alembic upgrade head` must succeed on a database with no server."""
    database_url = f"sqlite:///{tmp_path / 'migrate.db'}"
    command.upgrade(_alembic_config(database_url), "head")

    tables = set(inspect(create_engine(database_url)).get_table_names())
    expected = set(Base.metadata.tables) | {"alembic_version"}
    assert expected <= tables, f"missing tables: {sorted(expected - tables)}"


def test_migrations_build_the_same_schema_as_the_models(tmp_path):
    """The migration and the ORM models must not drift apart."""
    migrated_url = f"sqlite:///{tmp_path / 'migrated.db'}"
    command.upgrade(_alembic_config(migrated_url), "head")
    migrated = inspect(create_engine(migrated_url))

    declared_url = f"sqlite:///{tmp_path / 'declared.db'}"
    declared_engine = create_engine(declared_url)
    Base.metadata.create_all(declared_engine)
    declared = inspect(declared_engine)

    for table in sorted(Base.metadata.tables):
        migrated_columns = {c["name"] for c in migrated.get_columns(table)}
        declared_columns = {c["name"] for c in declared.get_columns(table)}
        assert migrated_columns == declared_columns, (
            f"{table}: migration and models disagree — "
            f"only in migration {sorted(migrated_columns - declared_columns)}, "
            f"only in models {sorted(declared_columns - migrated_columns)}"
        )


def test_no_vendor_specific_defaults_in_migrations():
    """`now()` is MySQL-only; CURRENT_TIMESTAMP is portable."""
    offenders = [
        path.name
        for path in VERSIONS_DIR.glob("*.py")
        if "now()" in path.read_text()
    ]
    assert not offenders, (
        f"MySQL-only now() found in {offenders}. Use CURRENT_TIMESTAMP so the "
        f"migration runs on SQLite and PostgreSQL too."
    )
