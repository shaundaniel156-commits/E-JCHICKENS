"""Bird population arithmetic — the headline example from the brief."""
from tests.factories import add_mortality, add_sale, create_batch, days_ago


def test_the_brief_example_500_minus_20_deaths_minus_50_sales_is_430(api):
    """Initial 500, deaths 20, sales 50 → current birds must be 430."""
    batch = create_batch(api, quantity=500)
    assert add_mortality(api, batch["id"], 20).status_code == 201
    assert add_sale(api, batch["id"], 50, 20000).status_code == 201

    detail = api.get(f"/api/v1/birds/{batch['id']}").json()
    assert detail["initial_quantity"] == 500
    assert detail["total_deaths"] == 20
    assert detail["total_sold"] == 50
    assert detail["current_quantity"] == 430

    dashboard = api.get("/api/v1/dashboard/summary").json()["birds"]
    assert dashboard["total_birds"] == 430
    assert dashboard["dead_birds"] == 20
    assert dashboard["sold_birds"] == 50


def test_totals_add_up_across_several_batches(api):
    first = create_batch(api, code="B-1", quantity=500)
    second = create_batch(api, code="B-2", quantity=300)
    add_mortality(api, first["id"], 10)
    add_mortality(api, second["id"], 5)
    add_sale(api, first["id"], 100, 20000)

    birds = api.get("/api/v1/dashboard/summary").json()["birds"]
    assert birds["initial_birds"] == 800
    assert birds["dead_birds"] == 15
    assert birds["sold_birds"] == 100
    assert birds["total_birds"] == 800 - 15 - 100


def test_mortality_rate_uses_the_exposed_population(api):
    batch = create_batch(api, quantity=400)
    add_mortality(api, batch["id"], 20)
    assert api.get(f"/api/v1/birds/{batch['id']}").json()["mortality_rate"] == 5.0


def test_other_losses_reduce_the_flock_without_inflating_mortality(api):
    batch = create_batch(api, quantity=100)
    response = api.post(
        f"/api/v1/birds/{batch['id']}/adjust", {"quantity": 10, "reason": "Stolen overnight"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["current_quantity"] == 90
    assert body["adjustment_quantity"] == 10
    assert body["mortality_rate"] == 0.0


def test_healthy_count_excludes_open_sick_records(api):
    batch = create_batch(api, quantity=200)
    api.post(
        "/api/v1/health-records",
        {"batch_id": batch["id"], "record_date": days_ago(1), "sick_count": 30},
    )
    detail = api.get(f"/api/v1/birds/{batch['id']}").json()
    assert detail["sick_count"] == 30
    assert detail["healthy_quantity"] == 170


def test_recovered_birds_stop_counting_as_sick(api):
    batch = create_batch(api, quantity=200)
    record = api.post(
        "/api/v1/health-records",
        {"batch_id": batch["id"], "record_date": days_ago(2), "sick_count": 30},
    ).json()
    assert api.get("/api/v1/dashboard/summary").json()["birds"]["sick_birds"] == 30

    api.put(f"/api/v1/health-records/{record['id']}", {"status": "RECOVERED"})
    assert api.get("/api/v1/dashboard/summary").json()["birds"]["sick_birds"] == 0


def test_a_batch_becomes_sold_out_when_it_empties(api):
    batch = create_batch(api, quantity=50)
    add_sale(api, batch["id"], 50, 20000)
    detail = api.get(f"/api/v1/birds/{batch['id']}").json()
    assert detail["current_quantity"] == 0
    assert detail["status"] == "SOLD_OUT"


def test_reversing_a_sale_returns_the_birds(api):
    batch = create_batch(api, quantity=100)
    sale = add_sale(api, batch["id"], 40, 20000).json()
    assert api.get(f"/api/v1/birds/{batch['id']}").json()["current_quantity"] == 60

    assert api.delete(f"/api/v1/sales/{sale['id']}").status_code == 200
    assert api.get(f"/api/v1/birds/{batch['id']}").json()["current_quantity"] == 100


def test_reversing_a_mortality_record_returns_the_birds(api):
    batch = create_batch(api, quantity=100)
    record = add_mortality(api, batch["id"], 25).json()
    assert api.get(f"/api/v1/birds/{batch['id']}").json()["current_quantity"] == 75

    api.delete(f"/api/v1/mortality/{record['id']}")
    assert api.get(f"/api/v1/birds/{batch['id']}").json()["current_quantity"] == 100


def test_acquisition_cost_is_quantity_times_unit_cost(api):
    batch = create_batch(api, quantity=500, cost_per_bird="700")
    assert batch["total_acquisition_cost"] == "350000.00"
