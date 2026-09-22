"""Server-side validation: the frontend is never the only line of defence."""
from datetime import date, timedelta

from tests.factories import add_expense, add_mortality, add_sale, category_ids, create_batch, days_ago

TOMORROW = str(date.today() + timedelta(days=1))


def test_a_sale_cannot_exceed_the_birds_available(api):
    batch = create_batch(api, quantity=100)
    response = add_sale(api, batch["id"], 150, 20000)
    assert response.status_code == 409
    assert "100" in response.json()["error"]["message"]


def test_deaths_cannot_exceed_the_birds_available(api):
    batch = create_batch(api, quantity=100)
    add_sale(api, batch["id"], 60, 20000)
    assert add_mortality(api, batch["id"], 50).status_code == 409
    assert add_mortality(api, batch["id"], 40).status_code == 201


def test_sick_birds_cannot_exceed_the_flock(api):
    batch = create_batch(api, quantity=50)
    response = api.post(
        "/api/v1/health-records",
        {"batch_id": batch["id"], "record_date": days_ago(1), "sick_count": 80},
    )
    assert response.status_code == 409


def test_open_sick_records_cannot_double_count_birds(api):
    batch = create_batch(api, quantity=50)
    api.post(
        "/api/v1/health-records",
        {"batch_id": batch["id"], "record_date": days_ago(2), "sick_count": 40},
    )
    second = api.post(
        "/api/v1/health-records",
        {"batch_id": batch["id"], "record_date": days_ago(1), "sick_count": 20},
    )
    assert second.status_code == 409


def test_negative_and_zero_quantities_are_rejected(api):
    batch = create_batch(api, quantity=100)
    assert add_sale(api, batch["id"], -5, 20000).status_code == 422
    assert add_sale(api, batch["id"], 0, 20000).status_code == 422
    assert add_mortality(api, batch["id"], -1).status_code == 422


def test_negative_money_is_rejected(api):
    categories = category_ids(api)
    assert add_expense(api, categories["Feed"], -500).status_code == 422
    assert add_expense(api, categories["Feed"], 0).status_code == 422

    batch = create_batch(api, quantity=10)
    assert add_sale(api, batch["id"], 1, -100).status_code == 422


def test_future_dates_are_rejected(api):
    response = api.post(
        "/api/v1/birds",
        {
            "batch_code": "FUTURE-1",
            "breed": "Broiler",
            "initial_quantity": 10,
            "acquisition_date": TOMORROW,
        },
    )
    assert response.status_code == 422


def test_required_fields_are_enforced(api):
    assert api.post("/api/v1/birds", {"breed": "Broiler"}).status_code == 422
    assert api.post("/api/v1/expenses", {"description": "no amount"}).status_code == 422


def test_duplicate_batch_codes_are_refused(api):
    create_batch(api, code="DUP-1")
    response = api.post(
        "/api/v1/birds",
        {
            "batch_code": "dup-1",  # case-insensitive: codes are normalised to upper case
            "breed": "Broiler",
            "initial_quantity": 10,
            "acquisition_date": days_ago(1),
        },
    )
    assert response.status_code == 409


def test_duplicate_emails_and_usernames_are_refused(api, make_user):
    make_user("firstuser", "STAFF")
    response = api.post(
        "/api/v1/users",
        {
            "full_name": "Copycat",
            "username": "firstuser",
            "email": "different@ejchickens.com",
            "role": "STAFF",
            "password": "Passw0rd!23",
        },
    )
    assert response.status_code == 409


def test_invalid_email_addresses_are_refused(api):
    response = api.post(
        "/api/v1/users",
        {
            "full_name": "Bad Email",
            "username": "bademail",
            "email": "not-an-email",
            "role": "STAFF",
            "password": "Passw0rd!23",
        },
    )
    assert response.status_code == 422


def test_weak_passwords_are_refused(api):
    response = api.post(
        "/api/v1/users",
        {
            "full_name": "Weak Password",
            "username": "weakpass",
            "email": "weak@ejchickens.com",
            "role": "STAFF",
            "password": "password",
        },
    )
    assert response.status_code == 422


def test_a_batch_with_history_cannot_be_deleted(api):
    batch = create_batch(api, quantity=100)
    add_mortality(api, batch["id"], 5)
    assert api.delete(f"/api/v1/birds/{batch['id']}").status_code == 409


def test_a_missing_record_returns_404(api):
    assert api.get("/api/v1/birds/999999").status_code == 404
    assert api.get("/api/v1/sales/999999").status_code == 404
    assert api.get("/api/v1/expenses/999999").status_code == 404


def test_a_budget_cannot_end_before_it_starts(api):
    response = api.post(
        "/api/v1/budgets",
        {
            "name": "Backwards",
            "amount": "100000",
            "start_date": days_ago(1),
            "end_date": days_ago(10),
        },
    )
    assert response.status_code == 422


def test_records_cannot_predate_their_batch(api):
    batch = create_batch(api, quantity=100, acquired=10)
    assert add_mortality(api, batch["id"], 5, when=30).status_code == 409
    assert add_sale(api, batch["id"], 5, 20000, when=30).status_code == 409
