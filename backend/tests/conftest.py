"""Test fixtures.

Tests run against a throw-away SQLite database by default so they need no server.
Set `TEST_DATABASE_URL` to a MySQL URL to run the same suite against MySQL.
"""
import os
import tempfile
from pathlib import Path

_TMP_DB = Path(tempfile.gettempdir()) / "ej_chickens_test.sqlite3"
os.environ.setdefault("TEST_DATABASE_URL", f"sqlite:///{_TMP_DB}")
os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]
os.environ["JWT_SECRET_KEY"] = "test-secret-key-not-for-production"
os.environ["DEBUG"] = "true"
os.environ["APP_ENV"] = "test"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db.session import SessionLocal, engine  # noqa: E402
from app.db.init_db import initialise  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base  # noqa: E402

ADMIN = {"identifier": "admin@ejchickens.com", "password": "Admin@12345"}


@pytest.fixture(scope="function")
def db():
    """A clean schema for every test, so no test depends on another."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    initialise(session)
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def client(db):
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def admin_token(client):
    response = client.post("/api/v1/auth/login", json=ADMIN)
    assert response.status_code == 200, response.text
    return response.json()["tokens"]["access_token"]


@pytest.fixture
def auth(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def api(client, auth):
    """A thin helper that carries the admin token on every call."""

    class Api:
        def get(self, path, **kwargs):
            return client.get(path, headers=auth, **kwargs)

        def post(self, path, json=None, **kwargs):
            return client.post(path, json=json, headers=auth, **kwargs)

        def put(self, path, json=None, **kwargs):
            return client.put(path, json=json, headers=auth, **kwargs)

        def delete(self, path, **kwargs):
            return client.delete(path, headers=auth, **kwargs)

    return Api()


@pytest.fixture
def make_user(api):
    def _make(username, role, password="Passw0rd!23"):
        response = api.post(
            "/api/v1/users",
            {
                "full_name": f"{role.title()} User",
                "username": username,
                "email": f"{username}@ejchickens.com",
                "role": role,
                "password": password,
            },
        )
        assert response.status_code == 201, response.text
        return response.json(), password

    return _make


@pytest.fixture
def token_for(client):
    def _token(identifier, password):
        response = client.post(
            "/api/v1/auth/login", json={"identifier": identifier, "password": password}
        )
        assert response.status_code == 200, response.text
        return {"Authorization": f"Bearer {response.json()['tokens']['access_token']}"}

    return _token
