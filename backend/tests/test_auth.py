"""Authentication, tokens and password workflows."""
from app.core.security import hash_password, verify_password


def test_password_hashing_is_not_reversible():
    hashed = hash_password("Sup3rSecret!")
    assert hashed != "Sup3rSecret!"
    assert hashed.startswith("$2")
    assert verify_password("Sup3rSecret!", hashed)
    assert not verify_password("wrong", hashed)


def test_login_returns_tokens_and_profile(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"identifier": "admin@ejchickens.com", "password": "Admin@12345"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["tokens"]["access_token"]
    assert body["tokens"]["refresh_token"]
    assert body["user"]["role"] == "ADMIN"
    assert "password" not in str(body).lower() or "password_hash" not in str(body)


def test_login_works_with_username_too(client):
    response = client.post(
        "/api/v1/auth/login", json={"identifier": "admin", "password": "Admin@12345"}
    )
    assert response.status_code == 200


def test_wrong_password_is_rejected(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"identifier": "admin@ejchickens.com", "password": "nope"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "authentication_error"


def test_unknown_account_gives_the_same_message_as_a_wrong_password(client):
    unknown = client.post(
        "/api/v1/auth/login", json={"identifier": "ghost@ejchickens.com", "password": "nope"}
    )
    wrong = client.post(
        "/api/v1/auth/login", json={"identifier": "admin@ejchickens.com", "password": "nope"}
    )
    assert unknown.status_code == wrong.status_code == 401
    assert unknown.json()["error"]["message"] == wrong.json()["error"]["message"]


def test_protected_route_requires_a_token(client):
    assert client.get("/api/v1/dashboard/summary").status_code == 401


def test_invalid_token_is_rejected(client):
    response = client.get(
        "/api/v1/dashboard/summary", headers={"Authorization": "Bearer not-a-token"}
    )
    assert response.status_code == 401


def test_refresh_token_issues_a_new_access_token(client):
    login = client.post(
        "/api/v1/auth/login",
        json={"identifier": "admin@ejchickens.com", "password": "Admin@12345"},
    ).json()
    response = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": login["tokens"]["refresh_token"]}
    )
    assert response.status_code == 200
    assert response.json()["access_token"]


def test_an_access_token_cannot_be_used_as_a_refresh_token(client):
    login = client.post(
        "/api/v1/auth/login",
        json={"identifier": "admin@ejchickens.com", "password": "Admin@12345"},
    ).json()
    response = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": login["tokens"]["access_token"]}
    )
    assert response.status_code == 401


def test_password_reset_round_trip(client):
    issued = client.post("/api/v1/auth/forgot-password", json={"email": "admin@ejchickens.com"})
    assert issued.status_code == 200
    token = issued.json()["reset_token"]
    assert token

    reset = client.post(
        "/api/v1/auth/reset-password", json={"token": token, "new_password": "Br@ndNew123"}
    )
    assert reset.status_code == 200
    assert (
        client.post(
            "/api/v1/auth/login",
            json={"identifier": "admin@ejchickens.com", "password": "Br@ndNew123"},
        ).status_code
        == 200
    )


def test_forgot_password_does_not_reveal_unknown_addresses(client):
    response = client.post("/api/v1/auth/forgot-password", json={"email": "ghost@ejchickens.com"})
    assert response.status_code == 200
    assert response.json()["reset_token"] is None


def test_change_password_requires_the_current_one(api):
    wrong = api.post(
        "/api/v1/auth/change-password",
        {"current_password": "not-it", "new_password": "An0therPass!"},
    )
    assert wrong.status_code == 422

    right = api.post(
        "/api/v1/auth/change-password",
        {"current_password": "Admin@12345", "new_password": "An0therPass!"},
    )
    assert right.status_code == 200
