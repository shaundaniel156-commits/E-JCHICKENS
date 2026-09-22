"""Role-based access control."""
import pytest

from tests.factories import create_batch, days_ago


@pytest.fixture
def staff(make_user, token_for):
    user, password = make_user("teststaff", "STAFF")
    return token_for(user["email"], password)


@pytest.fixture
def manager(make_user, token_for):
    user, password = make_user("testmanager", "MANAGER")
    return token_for(user["email"], password)


@pytest.mark.parametrize(
    "method,path",
    [
        ("get", "/api/v1/users"),
        ("get", "/api/v1/activity"),
        ("get", "/api/v1/expenses"),
        ("get", "/api/v1/finance/summary"),
        ("get", "/api/v1/reports/profit-loss"),
    ],
)
def test_staff_cannot_reach_management_endpoints(client, staff, method, path):
    assert getattr(client, method)(path, headers=staff).status_code == 403


@pytest.mark.parametrize(
    "method,path",
    [
        ("get", "/api/v1/dashboard/summary"),
        ("get", "/api/v1/birds"),
        ("get", "/api/v1/feed/stock"),
        ("get", "/api/v1/health-records"),
        ("get", "/api/v1/mortality"),
        ("get", "/api/v1/notifications"),
    ],
)
def test_staff_can_reach_day_to_day_endpoints(client, staff, method, path):
    assert getattr(client, method)(path, headers=staff).status_code == 200


def test_staff_can_record_mortality_and_health(client, staff, api):
    batch = create_batch(api)
    mortality = client.post(
        "/api/v1/mortality",
        json={"batch_id": batch["id"], "record_date": days_ago(2), "quantity": 3},
        headers=staff,
    )
    assert mortality.status_code == 201

    health = client.post(
        "/api/v1/health-records",
        json={"batch_id": batch["id"], "record_date": days_ago(1), "sick_count": 4},
        headers=staff,
    )
    assert health.status_code == 201


def test_staff_cannot_create_batches_or_budgets(client, staff):
    batch = client.post(
        "/api/v1/birds",
        json={
            "batch_code": "NOPE-1",
            "breed": "Broiler",
            "initial_quantity": 10,
            "acquisition_date": days_ago(1),
        },
        headers=staff,
    )
    assert batch.status_code == 403

    budget = client.post(
        "/api/v1/budgets",
        json={
            "name": "Nope",
            "amount": "100",
            "start_date": days_ago(1),
            "end_date": days_ago(0),
        },
        headers=staff,
    )
    assert budget.status_code == 403


def test_manager_runs_the_farm_but_not_user_administration(client, manager):
    assert client.get("/api/v1/expenses", headers=manager).status_code == 200
    assert client.get("/api/v1/finance/summary", headers=manager).status_code == 200
    assert client.get("/api/v1/users", headers=manager).status_code == 403
    assert client.get("/api/v1/activity", headers=manager).status_code == 403


def test_administrator_reaches_everything(api):
    for path in ("/api/v1/users", "/api/v1/activity", "/api/v1/settings", "/api/v1/budgets"):
        assert api.get(path).status_code == 200


def test_a_deactivated_user_can_no_longer_sign_in(api, client, make_user):
    user, password = make_user("leaver", "STAFF")
    assert api.delete(f"/api/v1/users/{user['id']}").status_code == 200
    response = client.post(
        "/api/v1/auth/login", json={"identifier": user["email"], "password": password}
    )
    assert response.status_code == 401


def test_the_last_administrator_cannot_be_removed(api, client):
    me = client.post(
        "/api/v1/auth/login",
        json={"identifier": "admin@ejchickens.com", "password": "Admin@12345"},
    ).json()["user"]
    assert api.delete(f"/api/v1/users/{me['id']}").status_code == 409


def test_staff_can_update_batch_details_but_not_its_figures(client, staff, api):
    """The brief lets staff keep bird information up to date; the money stays
    with managers."""
    batch = create_batch(api, code="STAFF-EDIT-1", quantity=100)

    allowed = client.put(
        f"/api/v1/birds/{batch['id']}",
        json={"breed": "Kuroiler", "notes": "Moved to house 2"},
        headers=staff,
    )
    assert allowed.status_code == 200
    assert allowed.json()["breed"] == "Kuroiler"

    for payload in ({"initial_quantity": 900}, {"cost_per_bird": "99"}, {"status": "CLOSED"}):
        refused = client.put(f"/api/v1/birds/{batch['id']}", json=payload, headers=staff)
        assert refused.status_code == 403, payload

    # The figures are untouched.
    assert api.get(f"/api/v1/birds/{batch['id']}").json()["initial_quantity"] == 100
