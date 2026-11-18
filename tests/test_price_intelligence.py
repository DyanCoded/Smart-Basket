"""Integration tests for price history tracking and trend intelligence endpoints."""

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.entities import Product, Store, StorePrice


def test_get_price_history_chronological(client: TestClient, raw_catalog_fixtures):
    """Verify price history points are returned in ascending chronological order."""
    prods = raw_catalog_fixtures["products"]
    milk = next(p for p in prods if "Milk" in p["name"])
    product_id = str(milk["id"])

    response = client.get(f"/api/v1/products/{product_id}/history")
    assert response.status_code == 200

    data = response.json()
    assert data["product_id"] == product_id
    assert data["total_points"] >= 3
    assert len(data["history"]) == data["total_points"]

    # Verify chronological ascending order
    timestamps = [datetime.fromisoformat(pt["recorded_at"]) for pt in data["history"]]
    assert timestamps == sorted(timestamps)

    first_pt = data["history"][0]
    assert "store_id" in first_pt
    assert "store_name" in first_pt
    assert "retailer_name" in first_pt
    assert "price" in first_pt
    assert "is_promotional" in first_pt
    assert Decimal(str(first_pt["price"])) > Decimal("0.00")


def test_get_price_history_filter_by_store(client: TestClient, raw_catalog_fixtures):
    """Test filtering price timeseries by specific store location."""
    prods = raw_catalog_fixtures["products"]
    stores = raw_catalog_fixtures["stores"]
    milk = next(p for p in prods if "Milk" in p["name"])
    chk_sandton = next(s for s in stores if "Checkers Sandton" in s["name"])

    product_id = str(milk["id"])
    store_id = str(chk_sandton["id"])

    response = client.get(f"/api/v1/products/{product_id}/history?store_id={store_id}")
    assert response.status_code == 200

    data = response.json()
    assert data["store_id"] == store_id
    assert data["total_points"] >= 3
    assert all(pt["store_id"] == store_id for pt in data["history"])


def test_get_price_history_filter_by_date_range(
    client: TestClient, raw_catalog_fixtures
):
    """Test filtering price timeseries within a date range."""
    prods = raw_catalog_fixtures["products"]
    milk = next(p for p in prods if "Milk" in p["name"])
    product_id = str(milk["id"])

    now = datetime.now(timezone.utc)
    start_dt = now - timedelta(days=40)
    end_dt = now - timedelta(days=1)

    response = client.get(
        f"/api/v1/products/{product_id}/history",
        params={
            "start_date": start_dt.isoformat(),
            "end_date": end_dt.isoformat(),
        },
    )
    assert response.status_code == 200
    data = response.json()

    # The 60-day-old record should be excluded; 30d and 5d should be included
    for pt in data["history"]:
        pt_time = datetime.fromisoformat(pt["recorded_at"])
        if pt_time.tzinfo is None:
            pt_time = pt_time.replace(tzinfo=timezone.utc)
        assert pt_time >= start_dt
        assert pt_time <= end_dt


def test_get_price_history_invalid_date_range(client: TestClient, raw_catalog_fixtures):
    """Verify 400 Bad Request when start_date is after end_date."""
    prods = raw_catalog_fixtures["products"]
    product_id = str(prods[0]["id"])

    now = datetime.now(timezone.utc)
    start_dt = now
    end_dt = now - timedelta(days=10)

    response = client.get(
        f"/api/v1/products/{product_id}/history",
        params={
            "start_date": start_dt.isoformat(),
            "end_date": end_dt.isoformat(),
        },
    )
    assert response.status_code == 400
    assert "start_date must be before or equal to end_date" in response.json()["detail"]


def test_get_price_history_not_found(client: TestClient, raw_catalog_fixtures):
    """Verify 404 for non-existent product or store IDs."""
    prods = raw_catalog_fixtures["products"]
    real_product_id = str(prods[0]["id"])
    fake_id = str(uuid.uuid4())

    # Product not found
    res_prod = client.get(f"/api/v1/products/{fake_id}/history")
    assert res_prod.status_code == 404
    assert f"Product with id '{fake_id}' not found" in res_prod.json()["detail"]

    # Store not found
    res_store = client.get(
        f"/api/v1/products/{real_product_id}/history",
        params={"store_id": fake_id},
    )
    assert res_store.status_code == 404
    assert f"Store with id '{fake_id}' not found" in res_store.json()["detail"]


def test_get_price_intelligence_metrics(client: TestClient, raw_catalog_fixtures):
    """Verify computation of high, low, average prices and trend metrics."""
    prods = raw_catalog_fixtures["products"]
    milk = next(p for p in prods if "Milk" in p["name"])
    product_id = str(milk["id"])

    response = client.get(f"/api/v1/products/{product_id}/intelligence")
    assert response.status_code == 200

    data = response.json()
    assert data["product_id"] == product_id
    assert data["product_name"] == "Full Cream Fresh Milk 2L"

    lowest = Decimal(str(data["all_time_lowest_price"]))
    highest = Decimal(str(data["all_time_highest_price"]))
    curr_lowest = Decimal(str(data["current_lowest_price"]))
    curr_avg = Decimal(str(data["current_average_price"]))
    hist_avg = Decimal(str(data["historical_average_price"]))

    # Mathematical consistency invariants
    assert lowest <= highest
    assert curr_lowest <= curr_avg
    assert lowest <= curr_lowest
    assert highest >= curr_avg
    assert hist_avg > Decimal("0.00")
    assert data["trend_direction"] in ["INCREASING", "DECREASING", "STABLE"]
    assert data["sample_size_days"] >= 30


def test_get_price_intelligence_deal_veracity(client: TestClient, raw_catalog_fixtures):
    """Verify promotional deal indicator and authenticity scoring."""
    prods = raw_catalog_fixtures["products"]
    # Checkers milk has an active promotion (R34.99 vs R39.99 regular)
    milk = next(p for p in prods if "Milk" in p["name"])
    product_id = str(milk["id"])

    response = client.get(f"/api/v1/products/{product_id}/intelligence")
    assert response.status_code == 200

    data = response.json()
    assert data["is_on_promotion"] is True
    assert data["current_promotional_price"] is not None
    assert Decimal(str(data["current_promotional_price"])) > Decimal("0.00")
    assert data["veracity_rating"] in ["GENUINE_SAVINGS", "ARTIFICIAL_DISCOUNT"]
    assert Decimal(str(data["discount_veracity_score"])) >= Decimal("0.00")
    assert Decimal(str(data["discount_veracity_score"])) <= Decimal("100.00")


def test_get_price_intelligence_edge_case_single_price_product(
    client: TestClient, db_session: Session
):
    """Verify edge case for newly listed product with single price and no history."""
    new_product = Product(
        id=uuid.uuid4(),
        name="Artisanal Sourdough Loaf 600g",
        brand="Artisan Bake",
        barcode="6001299099999",
        unit_size=Decimal("600.00"),
        unit_type="g",
    )
    db_session.add(new_product)

    store = db_session.scalars(select(Store)).first()
    # Add single store price without any price_history records
    store_price = StorePrice(
        id=uuid.uuid4(),
        store_id=store.id,
        product_id=new_product.id,
        price=Decimal("45.00"),
        is_promotional=False,
        is_in_stock=True,
    )
    db_session.add(store_price)
    db_session.commit()

    response = client.get(f"/api/v1/products/{new_product.id}/intelligence")
    assert response.status_code == 200

    data = response.json()
    assert Decimal(str(data["all_time_lowest_price"])) == Decimal("45.00")
    assert Decimal(str(data["all_time_highest_price"])) == Decimal("45.00")
    assert Decimal(str(data["current_lowest_price"])) == Decimal("45.00")
    assert Decimal(str(data["current_average_price"])) == Decimal("45.00")
    assert Decimal(str(data["price_change_percentage"])) == Decimal("0.00")
    assert data["trend_direction"] == "STABLE"
    assert data["is_on_promotion"] is False
    assert data["veracity_rating"] == "NO_PROMOTION"


def test_get_price_intelligence_product_not_found(client: TestClient):
    """Verify 404 when querying intelligence for non-existent product."""
    fake_id = str(uuid.uuid4())
    response = client.get(f"/api/v1/products/{fake_id}/intelligence")
    assert response.status_code == 404
    assert f"Product with id '{fake_id}' not found" in response.json()["detail"]
