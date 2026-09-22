"""Feed stock arithmetic and guards."""
from tests.factories import create_batch, days_ago, feed_type_ids


def buy(api, feed_type_id, bags="10", cost="35000", weight="50", when=20):
    return api.post(
        "/api/v1/feed/purchases",
        {
            "feed_type_id": feed_type_id,
            "purchase_date": days_ago(when),
            "quantity_bags": bags,
            "bag_weight_kg": weight,
            "cost_per_bag": cost,
            "supplier": "Test Feeds",
        },
    )


def consume(api, feed_type_id, bags=None, kilograms=None, when=5, batch_id=None):
    payload = {"feed_type_id": feed_type_id, "consumption_date": days_ago(when)}
    if bags is not None:
        payload["quantity_bags"] = str(bags)
    if kilograms is not None:
        payload["quantity_kg"] = str(kilograms)
    if batch_id:
        payload["batch_id"] = batch_id
    return api.post("/api/v1/feed/consumption", payload)


def test_stock_is_purchases_minus_consumption(api):
    feed = feed_type_ids(api)
    assert buy(api, feed["Broiler Starter"], bags="10").status_code == 201
    assert consume(api, feed["Broiler Starter"], bags=2).status_code == 201

    stock = api.get("/api/v1/feed/stock").json()
    assert stock["total_purchased_kg"] == "500.00"
    assert stock["total_consumed_kg"] == "100.00"
    assert stock["total_stock_kg"] == "400.00"
    assert stock["total_stock_bags"] == "8.00"


def test_consumption_can_be_entered_in_kilograms(api):
    feed = feed_type_ids(api)
    buy(api, feed["Broiler Starter"], bags="4")  # 200 kg
    assert consume(api, feed["Broiler Starter"], kilograms=75).status_code == 201
    assert api.get("/api/v1/feed/stock").json()["total_stock_kg"] == "125.00"


def test_feed_stock_cannot_go_negative(api):
    feed = feed_type_ids(api)
    buy(api, feed["Broiler Starter"], bags="2")  # 100 kg
    response = consume(api, feed["Broiler Starter"], bags=5)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "insufficient_stock"
    assert api.get("/api/v1/feed/stock").json()["total_stock_kg"] == "100.00"


def test_a_purchase_cannot_be_removed_once_its_feed_was_eaten(api):
    feed = feed_type_ids(api)
    purchase = buy(api, feed["Broiler Starter"], bags="2").json()
    consume(api, feed["Broiler Starter"], bags=2)
    assert api.delete(f"/api/v1/feed/purchases/{purchase['id']}").status_code == 409


def test_a_feed_purchase_creates_its_own_expense(api):
    feed = feed_type_ids(api)
    buy(api, feed["Broiler Starter"], bags="10", cost="35000")

    expenses = api.get("/api/v1/expenses").json()["items"]
    feed_expenses = [e for e in expenses if e["category_name"] == "Feed"]
    assert len(feed_expenses) == 1
    assert feed_expenses[0]["amount"] == "350000.00"
    assert feed_expenses[0]["is_system_generated"] is True


def test_an_auto_generated_expense_cannot_be_edited_directly(api):
    feed = feed_type_ids(api)
    buy(api, feed["Broiler Starter"], bags="10")
    expense = [
        e for e in api.get("/api/v1/expenses").json()["items"] if e["is_system_generated"]
    ][0]

    assert api.put(f"/api/v1/expenses/{expense['id']}", {"amount": "1"}).status_code == 409
    assert api.delete(f"/api/v1/expenses/{expense['id']}").status_code == 409


def test_editing_a_purchase_updates_its_expense(api):
    feed = feed_type_ids(api)
    purchase = buy(api, feed["Broiler Starter"], bags="10", cost="35000").json()
    api.put(f"/api/v1/feed/purchases/{purchase['id']}", {"cost_per_bag": "40000"})

    expense = [
        e for e in api.get("/api/v1/expenses").json()["items"] if e["is_system_generated"]
    ][0]
    assert expense["amount"] == "400000.00"


def test_low_stock_raises_a_notification(api):
    feed = feed_type_ids(api)
    buy(api, feed["Broiler Starter"], bags="10")
    consume(api, feed["Broiler Starter"], bags=8)  # 2 bags left, threshold is 5

    types = [n["type"] for n in api.get("/api/v1/notifications").json()["items"]]
    assert "FEED_LOW" in types
    assert api.get("/api/v1/dashboard/summary").json()["feed"]["low_stock"] is True


def test_consumption_can_be_attributed_to_a_batch(api):
    feed = feed_type_ids(api)
    batch = create_batch(api)
    buy(api, feed["Broiler Starter"], bags="10")
    consume(api, feed["Broiler Starter"], bags=3, batch_id=batch["id"])

    rows = api.get("/api/v1/feed/consumption").json()["items"]
    assert rows[0]["batch_id"] == batch["id"]
    assert rows[0]["batch_code"] == batch["batch_code"]
