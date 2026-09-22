"""Budget, revenue, expense and profit arithmetic."""
from tests.factories import add_budget, add_expense, add_sale, category_ids, create_batch


def test_budget_example_1000000_minus_800000_leaves_200000(api):
    """Budget 1,000,000 − expenses 800,000 → remaining 200,000."""
    add_budget(api, "1000000")
    categories = category_ids(api)
    assert add_expense(api, categories["Feed"], 500000, "Feed").status_code == 201
    assert add_expense(api, categories["Labour"], 300000, "Labour").status_code == 201

    budget = api.get("/api/v1/budgets/active").json()
    assert budget["amount"] == "1000000.00"
    assert budget["spent"] == "800000.00"
    assert budget["remaining"] == "200000.00"
    assert budget["percentage_spent"] == 80.0
    assert budget["is_exceeded"] is False


def test_profit_example_revenue_1200000_minus_expenses_800000_is_400000(api):
    """Revenue 1,200,000 − expenses 800,000 → profit 400,000."""
    batch = create_batch(api, quantity=100)
    categories = category_ids(api)
    add_expense(api, categories["Feed"], 800000, "Feed for the season")
    assert add_sale(api, batch["id"], 50, 24000).status_code == 201  # 1,200,000

    finance = api.get("/api/v1/finance/summary").json()
    assert finance["total_revenue"] == "1200000.00"
    assert finance["total_expenses"] == "800000.00"
    assert finance["net_profit_or_loss"] == "400000.00"
    assert finance["is_profit"] is True


def test_a_loss_is_reported_as_a_loss(api):
    batch = create_batch(api, quantity=100)
    categories = category_ids(api)
    add_expense(api, categories["Feed"], 900000, "Expensive feed")
    add_sale(api, batch["id"], 10, 20000)  # 200,000

    finance = api.get("/api/v1/finance/summary").json()
    assert finance["net_profit_or_loss"] == "-700000.00"
    assert finance["is_profit"] is False

    dashboard = api.get("/api/v1/dashboard/summary").json()["finance"]
    assert dashboard["loss"] == "700000.00"
    assert dashboard["profit"] == "0.00"


def test_remaining_budget_is_never_reported_as_profit(api):
    """The brief's central warning: a budget balance is not a profit."""
    add_budget(api, "1000000")
    categories = category_ids(api)
    add_expense(api, categories["Feed"], 800000, "Feed")
    batch = create_batch(api, quantity=100)
    add_sale(api, batch["id"], 50, 24000)

    finance = api.get("/api/v1/finance/summary").json()
    assert finance["budget_remaining"] == "200000.00"
    assert finance["net_profit_or_loss"] == "400000.00"
    assert finance["budget_remaining"] != finance["net_profit_or_loss"]


def test_sale_total_is_quantity_times_unit_price(api):
    batch = create_batch(api, quantity=100)
    sale = add_sale(api, batch["id"], 37, 18500).json()
    assert sale["total_amount"] == "684500.00"  # 37 × 18,500


def test_partial_payment_splits_revenue_from_cash_collected(api):
    batch = create_batch(api, quantity=100)
    sale = add_sale(
        api, batch["id"], 10, 20000, payment_status="PARTIAL", amount_paid="120000"
    ).json()
    assert sale["total_amount"] == "200000.00"
    assert sale["amount_paid"] == "120000.00"
    assert sale["balance_due"] == "80000.00"
    assert sale["payment_status"] == "PARTIAL"

    finance = api.get("/api/v1/finance/summary").json()
    assert finance["total_revenue"] == "200000.00"
    assert finance["cash_collected"] == "120000.00"
    assert finance["outstanding_receivables"] == "80000.00"


def test_paying_more_than_the_total_is_rejected(api):
    batch = create_batch(api, quantity=100)
    response = add_sale(
        api, batch["id"], 10, 20000, payment_status="PARTIAL", amount_paid="500000"
    )
    assert response.status_code == 422


def test_budget_warning_and_exceeded_notifications_fire(api):
    add_budget(api, "100000")
    categories = category_ids(api)
    add_expense(api, categories["Feed"], 85000, "Near the limit")
    types = [n["type"] for n in api.get("/api/v1/notifications").json()["items"]]
    assert "BUDGET_WARNING" in types

    add_expense(api, categories["Labour"], 50000, "Over the limit")
    body = api.get("/api/v1/notifications").json()["items"]
    assert "BUDGET_EXCEEDED" in [n["type"] for n in body]
    assert api.get("/api/v1/budgets/active").json()["is_exceeded"] is True


def test_expense_breakdown_percentages_sum_to_one_hundred(api):
    categories = category_ids(api)
    add_expense(api, categories["Feed"], 600000, "Feed")
    add_expense(api, categories["Labour"], 400000, "Labour")

    rows = api.get("/api/v1/expenses/breakdown").json()
    assert sum(row["percentage"] for row in rows) == 100.0
    assert {row["category"] for row in rows} == {"Feed", "Labour"}


def test_reversing_an_expense_restores_the_budget(api):
    add_budget(api, "1000000")
    categories = category_ids(api)
    expense = add_expense(api, categories["Feed"], 400000, "Feed").json()
    assert api.get("/api/v1/budgets/active").json()["remaining"] == "600000.00"

    api.delete(f"/api/v1/expenses/{expense['id']}")
    assert api.get("/api/v1/budgets/active").json()["remaining"] == "1000000.00"
