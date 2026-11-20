"""Tests for smart basket calculation and multi-store optimization engine."""

import time
import uuid
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.api.v1.schemas import BasketItemRequest
from src.services.basket_service import calculate_basket


def test_basket_calculation_full_match(client: TestClient, raw_catalog_fixtures):
    """Test basket calculation when all requested items are stocked by stores."""
    prods = raw_catalog_fixtures["products"]
    milk = next(p for p in prods if "Milk" in p["name"])
    bread = next(p for p in prods if "White Bread" in p["name"])
    butter = next(p for p in prods if "Butter" in p["name"])

    payload = {
        "items": [
            {"product_id": str(milk["id"]), "quantity": "2.00"},
            {"product_id": str(bread["id"]), "quantity": "1.00"},
            {"product_id": str(butter["id"]), "quantity": "1.00"},
        ]
    }

    response = client.post("/api/v1/baskets/calculate", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["total_items_requested"] == 3
    assert len(data["ranked_stores"]) == 5

    # Ensure all 5 national chains are returned cleanly without duplicate branches
    expected_chains = {
        "Checkers",
        "Pick n Pay",
        "SPAR",
        "Shoprite",
        "Woolworths Food",
    }
    assert {s["retailer_name"] for s in data["ranked_stores"]} == expected_chains
    for store in data["ranked_stores"]:
        assert store["store_name"] == store["retailer_name"]
        assert store["branch_code"] is None
        assert store["is_complete_match"] is True
        assert len(store["missing_items"]) == 0

    # Ensure ranked chains are sorted ascending by total price
    prices = [Decimal(str(s["total_price"])) for s in data["ranked_stores"]]
    assert prices == sorted(prices)

    # Verify cheapest single chain matches first ranked chain
    cheapest = data["cheapest_single_store"]
    assert cheapest is not None
    assert cheapest["is_complete_match"] is True
    assert Decimal(str(cheapest["total_price"])) == prices[0]
    assert len(cheapest["items"]) == 3
    assert len(cheapest["missing_items"]) == 0


def test_basket_calculation_ignores_stock_flag_and_covers_all_5_chains(
    client: TestClient, db_session: Session, raw_catalog_fixtures
):
    """Verify basket engine evaluates chain-level prices without stock filtering."""
    from sqlalchemy import select

    from src.models.entities import StorePrice

    prods = raw_catalog_fixtures["products"]
    milk = next(p for p in prods if "Milk" in p["name"])
    teabags = next(p for p in prods if "Teabags" in p["name"])

    # Mark one chain's StorePrice.is_in_stock=False to verify no stock filtering occurs
    milk_price = db_session.scalars(
        select(StorePrice).where(StorePrice.product_id == milk["id"])
    ).first()
    assert milk_price is not None
    milk_price.is_in_stock = False
    db_session.commit()

    payload = {
        "items": [
            {"product_id": str(milk["id"]), "quantity": "1.00"},
            {"product_id": str(teabags["id"]), "quantity": "1.00"},
        ]
    }

    response = client.post("/api/v1/baskets/calculate", json=payload)
    assert response.status_code == 200
    data = response.json()

    # All 5 national chains must return complete pricing without stock filtering
    assert len(data["ranked_stores"]) == 5
    for chain in data["ranked_stores"]:
        assert chain["is_complete_match"] is True
        assert len(chain["missing_items"]) == 0
        assert chain["items_available_count"] == 2
        assert chain["store_name"] == chain["retailer_name"]
        assert chain["branch_code"] is None


def test_basket_calculation_smart_split_optimization(
    client: TestClient, raw_catalog_fixtures
):
    """Verify Smart Mode identifies savings by splitting basket across 2 stores."""
    prods = raw_catalog_fixtures["products"]
    # Select products where different stores have price advantages
    milk = next(p for p in prods if "Milk" in p["name"])
    rice = next(p for p in prods if "Rice" in p["name"])
    oil = next(p for p in prods if "Oil" in p["name"])

    payload = {
        "items": [
            {"product_id": str(milk["id"]), "quantity": "2.00"},
            {"product_id": str(rice["id"]), "quantity": "1.00"},
            {"product_id": str(oil["id"]), "quantity": "2.00"},
        ]
    }

    response = client.post("/api/v1/baskets/calculate", json=payload)
    assert response.status_code == 200
    data = response.json()

    split = data["optimal_split"]
    assert split is not None
    assert len(split["stores"]) in [1, 2]
    assert split["is_complete_match"] is True

    # Total price of split must equal sum of store allocations
    split_subtotals = [Decimal(str(st["subtotal"])) for st in split["stores"]]
    assert sum(split_subtotals) == Decimal(str(split["total_price"]))

    # If cheaper than single store, savings must be positive
    cheapest_single = Decimal(str(data["cheapest_single_store"]["total_price"]))
    split_total = Decimal(str(split["total_price"]))
    if split["cheaper_than_single_store"]:
        assert split_total < cheapest_single
        expected_savings = cheapest_single - split_total
        assert Decimal(str(split["savings_amount"])) == expected_savings
        assert Decimal(str(split["savings_percentage"])) > Decimal("0.00")


def test_basket_calculation_three_staple_replenishment_split_savings(
    client: TestClient, raw_catalog_fixtures
):
    """Verify 3-item staple basket (Milk, Bread, Eggs) yields positive split savings."""
    prods = raw_catalog_fixtures["products"]
    milk = next(p for p in prods if "Milk" in p["name"])
    bread = next(p for p in prods if "White Bread" in p["name"])
    eggs = next(p for p in prods if "Eggs" in p["name"])

    payload = {
        "items": [
            {"product_id": str(milk["id"]), "quantity": "2.00"},
            {"product_id": str(bread["id"]), "quantity": "1.00"},
            {"product_id": str(eggs["id"]), "quantity": "1.00"},
        ]
    }

    response = client.post("/api/v1/baskets/calculate", json=payload)
    assert response.status_code == 200
    data = response.json()

    cheapest_single = data["cheapest_single_store"]
    split = data["optimal_split"]

    assert cheapest_single is not None
    assert split is not None
    assert split["cheaper_than_single_store"] is True
    assert len(split["stores"]) == 2
    assert Decimal(str(split["savings_amount"])) > Decimal("0.00")
    assert Decimal(str(split["total_price"])) < Decimal(
        str(cheapest_single["total_price"])
    )
    assert Decimal(str(split["savings_amount"])) == (
        Decimal(str(cheapest_single["total_price"]))
        - Decimal(str(split["total_price"]))
    )
    # All participating chains must use canonical retailer names
    for alloc in split["stores"]:
        assert alloc["store_name"] == alloc["retailer_name"]


def test_basket_calculation_quantity_multiplication(
    client: TestClient, raw_catalog_fixtures
):
    """Test unit normalization and price multiplication by quantity."""
    prods = raw_catalog_fixtures["products"]
    milk = next(p for p in prods if "Milk" in p["name"])

    payload = {
        "items": [
            {"product_id": str(milk["id"]), "quantity": "3.50"},
        ]
    }

    response = client.post("/api/v1/baskets/calculate", json=payload)
    assert response.status_code == 200
    data = response.json()

    for store in data["ranked_stores"]:
        if store["items"]:
            item = store["items"][0]
            unit_price = Decimal(str(item["unit_price"]))
            quantity = Decimal(str(item["quantity"]))
            expected_subtotal = (unit_price * quantity).quantize(Decimal("0.01"))
            assert Decimal(str(item["subtotal"])) == expected_subtotal
            assert Decimal(str(store["total_price"])) == expected_subtotal


def test_basket_calculation_duplicate_product_ids(
    client: TestClient, raw_catalog_fixtures
):
    """Verify duplicate product lines are consolidated into aggregated quantities."""
    prods = raw_catalog_fixtures["products"]
    milk = next(p for p in prods if "Milk" in p["name"])

    payload = {
        "items": [
            {"product_id": str(milk["id"]), "quantity": "1.00"},
            {"product_id": str(milk["id"]), "quantity": "2.50"},
        ]
    }

    response = client.post("/api/v1/baskets/calculate", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["total_items_requested"] == 1
    for store in data["ranked_stores"]:
        if store["items"]:
            assert Decimal(str(store["items"][0]["quantity"])) == Decimal("3.50")


def test_basket_calculation_zero_or_negative_quantity(client: TestClient):
    """Verify input validation rejects zero or negative item quantities."""
    random_id = str(uuid.uuid4())

    res_zero = client.post(
        "/api/v1/baskets/calculate",
        json={"items": [{"product_id": random_id, "quantity": "0.00"}]},
    )
    assert res_zero.status_code == 422

    res_neg = client.post(
        "/api/v1/baskets/calculate",
        json={"items": [{"product_id": random_id, "quantity": "-2.00"}]},
    )
    assert res_neg.status_code == 422


def test_basket_calculation_empty_basket(client: TestClient):
    """Verify validation error when basket contains zero items."""
    response = client.post("/api/v1/baskets/calculate", json={"items": []})
    assert response.status_code == 422


def test_basket_calculation_non_existent_product(
    client: TestClient, raw_catalog_fixtures
):
    """Verify 404 response when a requested product does not exist in catalog."""
    prods = raw_catalog_fixtures["products"]
    real_id = str(prods[0]["id"])
    fake_id = str(uuid.uuid4())

    payload = {
        "items": [
            {"product_id": real_id, "quantity": "1.00"},
            {"product_id": fake_id, "quantity": "1.00"},
        ]
    }

    response = client.post("/api/v1/baskets/calculate", json=payload)
    assert response.status_code == 404
    assert f"Product with id '{fake_id}' not found" in response.json()["detail"]


def test_basket_calculation_performance_benchmark(
    db_session: Session, raw_catalog_fixtures
):
    """Benchmark query and optimization performance for baskets with 20+ items."""
    prods = raw_catalog_fixtures["products"]
    # Build a basket with 24 items (repeating products with varying quantities)
    basket_items = []
    for i in range(24):
        p = prods[i % len(prods)]
        basket_items.append(
            BasketItemRequest(
                product_id=p["id"],
                quantity=Decimal(str((i % 3) + 1)),
            )
        )

    # Warm-up run
    calculate_basket(session=db_session, items=basket_items)

    # Timed run
    start_time = time.perf_counter()
    result = calculate_basket(session=db_session, items=basket_items)
    duration_ms = (time.perf_counter() - start_time) * 1000

    assert result is not None
    assert len(result.ranked_stores) > 0
    # Engine execution must comfortably finish in under 100ms
    assert duration_ms < 100.0, f"Engine took {duration_ms:.2f}ms (> 100ms target)"
