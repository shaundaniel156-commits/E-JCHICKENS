"""Small builders that keep the tests readable."""
from datetime import date, timedelta

TODAY = date.today()


def days_ago(n: int) -> str:
    return str(TODAY - timedelta(days=n))


def create_batch(api, code="BATCH-001", quantity=500, cost_per_bird="0", acquired=40):
    response = api.post(
        "/api/v1/birds",
        {
            "batch_code": code,
            "breed": "Broiler",
            "initial_quantity": quantity,
            "acquisition_date": days_ago(acquired),
            "source": "Test Hatchery",
            "cost_per_bird": cost_per_bird,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def category_ids(api):
    response = api.get("/api/v1/expenses/categories")
    assert response.status_code == 200
    return {row["name"]: row["id"] for row in response.json()}


def feed_type_ids(api):
    response = api.get("/api/v1/feed/types")
    assert response.status_code == 200
    return {row["name"]: row["id"] for row in response.json()}


def add_expense(api, category_id, amount, description="Test expense", when=10):
    return api.post(
        "/api/v1/expenses",
        {
            "expense_date": days_ago(when),
            "category_id": category_id,
            "description": description,
            "amount": str(amount),
        },
    )


def add_sale(api, batch_id, quantity, unit_price, when=3, **extra):
    payload = {
        "sale_date": days_ago(when),
        "batch_id": batch_id,
        "quantity": quantity,
        "unit_price": str(unit_price),
        "payment_status": "PAID",
    }
    payload.update(extra)
    return api.post("/api/v1/sales", payload)


def add_mortality(api, batch_id, quantity, when=5, cause="Disease"):
    return api.post(
        "/api/v1/mortality",
        {
            "batch_id": batch_id,
            "record_date": days_ago(when),
            "quantity": quantity,
            "cause": cause,
        },
    )


def add_budget(api, amount="1000000", name="Test budget"):
    return api.post(
        "/api/v1/budgets",
        {
            "name": name,
            "amount": str(amount),
            "start_date": days_ago(90),
            "end_date": str(TODAY + timedelta(days=90)),
            "is_active": True,
        },
    )
