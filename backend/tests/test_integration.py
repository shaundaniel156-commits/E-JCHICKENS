"""Data entered once must flow through every other module."""
from tests.factories import (
    add_budget,
    add_expense,
    add_mortality,
    add_sale,
    category_ids,
    create_batch,
    days_ago,
    feed_type_ids,
)


def test_a_batch_purchase_reaches_the_dashboard_and_the_books(api):
    create_batch(api, quantity=500, cost_per_bird="700")

    dashboard = api.get("/api/v1/dashboard/summary").json()
    assert dashboard["birds"]["total_birds"] == 500
    assert dashboard["finance"]["total_expenses"] == "350000.00"

    expenses = api.get("/api/v1/expenses").json()["items"]
    assert any(e["category_name"] == "Birds" and e["amount"] == "350000.00" for e in expenses)


def test_a_sale_moves_birds_revenue_profit_notifications_and_the_log(api):
    batch = create_batch(api, quantity=200)
    before = api.get("/api/v1/dashboard/summary").json()

    sale = add_sale(api, batch["id"], 50, 24000).json()
    after = api.get("/api/v1/dashboard/summary").json()

    assert after["birds"]["total_birds"] == before["birds"]["total_birds"] - 50
    assert after["birds"]["sold_birds"] == 50
    assert after["finance"]["total_revenue"] == "1200000.00"
    assert after["finance"]["net_profit_or_loss"] == "1200000.00"

    notifications = api.get("/api/v1/notifications").json()["items"]
    assert any(n["type"] == "SALE_COMPLETED" for n in notifications)

    activity = api.get("/api/v1/activity").json()["items"]
    assert any(str(sale["quantity"]) in entry["description"] for entry in activity)

    report = api.get("/api/v1/reports/sales").json()
    assert report["total_revenue"] == after["finance"]["total_revenue"]


def test_a_treatment_cost_becomes_a_medicine_expense(api):
    batch = create_batch(api, quantity=100)
    api.post(
        "/api/v1/health-records",
        {
            "batch_id": batch["id"],
            "record_date": days_ago(2),
            "sick_count": 10,
            "medicine": "Doxycycline",
            "treatment_cost": "40000",
        },
    )
    expenses = api.get("/api/v1/expenses").json()["items"]
    medicine = [e for e in expenses if e["category_name"] == "Medicine"]
    assert len(medicine) == 1
    assert medicine[0]["amount"] == "40000.00"
    assert api.get("/api/v1/dashboard/summary").json()["finance"]["total_expenses"] == "40000.00"


def test_removing_a_health_record_removes_its_expense(api):
    batch = create_batch(api, quantity=100)
    record = api.post(
        "/api/v1/health-records",
        {
            "batch_id": batch["id"],
            "record_date": days_ago(2),
            "sick_count": 10,
            "treatment_cost": "40000",
        },
    ).json()
    api.delete(f"/api/v1/health-records/{record['id']}")
    assert api.get("/api/v1/dashboard/summary").json()["finance"]["total_expenses"] == "0.00"


def test_every_report_agrees_with_the_dashboard(api):
    add_budget(api, "1000000")
    batch = create_batch(api, quantity=500, cost_per_bird="700")
    feed = feed_type_ids(api)
    api.post(
        "/api/v1/feed/purchases",
        {
            "feed_type_id": feed["Broiler Starter"],
            "purchase_date": days_ago(20),
            "quantity_bags": "10",
            "bag_weight_kg": "50",
            "cost_per_bag": "35000",
        },
    )
    api.post(
        "/api/v1/feed/consumption",
        {
            "feed_type_id": feed["Broiler Starter"],
            "consumption_date": days_ago(5),
            "quantity_bags": "2",
        },
    )
    add_mortality(api, batch["id"], 5)
    add_sale(api, batch["id"], 50, 24000)
    add_expense(api, category_ids(api)["Labour"], 60000, "Labour")

    dashboard = api.get("/api/v1/dashboard/summary").json()
    birds = api.get("/api/v1/reports/birds").json()
    feed_report = api.get("/api/v1/reports/feed").json()
    expenses = api.get("/api/v1/reports/expenses").json()
    sales = api.get("/api/v1/reports/sales").json()
    profit_loss = api.get("/api/v1/reports/profit-loss").json()
    performance = api.get("/api/v1/reports/performance").json()
    finance = api.get("/api/v1/finance/summary").json()

    assert birds["totals"]["current_quantity"] == dashboard["birds"]["total_birds"]
    assert birds["totals"]["deaths"] == dashboard["birds"]["dead_birds"]
    assert feed_report["total_stock_kg"] == dashboard["feed"]["stock_kg"]
    assert expenses["total"] == dashboard["finance"]["total_expenses"]
    assert sales["total_revenue"] == dashboard["finance"]["total_revenue"]
    assert profit_loss["net_profit_or_loss"] == dashboard["finance"]["net_profit_or_loss"]
    assert performance["finance"]["net_profit_or_loss"] == dashboard["finance"]["net_profit_or_loss"]
    assert finance["net_profit_or_loss"] == dashboard["finance"]["net_profit_or_loss"]
    assert finance["budget_remaining"] == dashboard["finance"]["remaining_budget"]


def test_an_empty_farm_reports_zeros_rather_than_breaking(api):
    dashboard = api.get("/api/v1/dashboard/summary").json()
    assert dashboard["has_data"] is False
    assert dashboard["birds"]["total_birds"] == 0
    assert dashboard["finance"]["total_revenue"] == "0.00"
    assert dashboard["finance"]["net_profit_or_loss"] == "0.00"
    assert dashboard["charts"]["bird_population"] == []

    for path in (
        "/api/v1/reports/birds",
        "/api/v1/reports/feed",
        "/api/v1/reports/expenses",
        "/api/v1/reports/sales",
        "/api/v1/reports/profit-loss",
        "/api/v1/reports/performance",
    ):
        assert api.get(path).status_code == 200


def test_reports_export_as_csv_and_pdf(api):
    batch = create_batch(api, quantity=100)
    add_sale(api, batch["id"], 10, 20000)

    csv_response = api.get("/api/v1/reports/sales/export?format=csv")
    assert csv_response.status_code == 200
    assert csv_response.headers["content-type"].startswith("text/csv")
    assert b"Reference" in csv_response.content

    pdf_response = api.get("/api/v1/reports/birds/export?format=pdf")
    assert pdf_response.status_code == 200
    assert pdf_response.content[:4] == b"%PDF"


def test_date_filters_narrow_the_figures(api):
    batch = create_batch(api, quantity=200, acquired=60)
    add_sale(api, batch["id"], 10, 20000, when=50)  # old sale:   200,000
    add_sale(api, batch["id"], 5, 20000, when=1)    # recent sale: 100,000

    all_time = api.get("/api/v1/finance/summary").json()
    assert all_time["total_revenue"] == "300000.00"

    recent = api.get(
        f"/api/v1/finance/summary?start_date={days_ago(7)}&end_date={days_ago(0)}"
    ).json()
    assert recent["total_revenue"] == "100000.00"

    older = api.get(
        f"/api/v1/finance/summary?start_date={days_ago(60)}&end_date={days_ago(30)}"
    ).json()
    assert older["total_revenue"] == "200000.00"


def test_period_presets_resolve_to_real_ranges(api):
    """`preset` is translated server-side, so the client never computes dates."""
    batch = create_batch(api, quantity=200, acquired=60)
    add_sale(api, batch["id"], 5, 20000, when=0)  # today

    today = api.get("/api/v1/finance/summary?preset=today").json()
    assert today["total_revenue"] == "100000.00"
    assert today["start_date"] == today["end_date"] == days_ago(0)

    year = api.get("/api/v1/finance/summary?preset=this_year").json()
    assert year["total_revenue"] == "100000.00"


def test_search_sort_and_pagination_work_together(api):
    for index in range(1, 8):
        create_batch(api, code=f"PAGE-{index:03d}", quantity=10 * index)

    page_one = api.get("/api/v1/birds?page=1&page_size=3&sort=batch_code&order=asc").json()
    assert len(page_one["items"]) == 3
    assert page_one["meta"]["total"] == 7
    assert page_one["meta"]["pages"] == 3
    assert page_one["items"][0]["batch_code"] == "PAGE-001"

    page_three = api.get("/api/v1/birds?page=3&page_size=3&sort=batch_code&order=asc").json()
    assert page_three["items"][0]["batch_code"] == "PAGE-007"

    searched = api.get("/api/v1/birds?search=PAGE-004").json()
    assert searched["meta"]["total"] == 1


def test_the_activity_log_captures_the_signed_in_user(api):
    create_batch(api, code="AUDIT-1")
    entries = api.get("/api/v1/activity").json()["items"]
    created = [e for e in entries if e["module"] == "birds" and e["action"] == "CREATE"]
    assert created
    assert created[0]["user_display"] == "Farm Administrator"


def test_notifications_can_be_read_and_dismissed(api):
    create_batch(api)
    count = api.get("/api/v1/notifications/count").json()
    assert count["unread"] >= 1

    first = api.get("/api/v1/notifications").json()["items"][0]
    assert api.post(f"/api/v1/notifications/{first['id']}/read").json()["is_read"] is True
    assert api.post("/api/v1/notifications/read-all").status_code == 200
    assert api.get("/api/v1/notifications/count").json()["unread"] == 0
