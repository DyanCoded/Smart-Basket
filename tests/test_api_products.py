"""Integration tests for product catalog search and pricing API endpoints."""

import uuid
from decimal import Decimal

from fastapi.testclient import TestClient


def test_list_products_default(client: TestClient):
    """Test GET /api/v1/products with default pagination."""
    response = client.get("/api/v1/products")
    assert response.status_code == 200

    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] == 18
    assert data["limit"] == 20
    assert data["offset"] == 0
    assert len(data["items"]) == 18

    # Verify item structure
    first_item = data["items"][0]
    assert "id" in first_item
    assert "name" in first_item
    assert "brand" in first_item
    assert "barcode" in first_item
    assert "unit_size" in first_item
    assert "unit_type" in first_item
    assert "category" in first_item


def test_list_products_pagination(client: TestClient):
    """Test pagination limit and offset parameters."""
    res_page_1 = client.get("/api/v1/products?limit=5&offset=0")
    assert res_page_1.status_code == 200
    data_1 = res_page_1.json()
    assert len(data_1["items"]) == 5
    assert data_1["total"] == 18

    res_page_2 = client.get("/api/v1/products?limit=5&offset=5")
    assert res_page_2.status_code == 200
    data_2 = res_page_2.json()
    assert len(data_2["items"]) == 5
    assert data_2["total"] == 18

    # Ensure page 1 and page 2 don't overlap
    ids_1 = {p["id"] for p in data_1["items"]}
    ids_2 = {p["id"] for p in data_2["items"]}
    assert ids_1.isdisjoint(ids_2)


def test_list_products_search_case_insensitive(client: TestClient):
    """Test case-insensitive product search functionality."""
    queries = ["milk", "MILK", "MiLk", "mIlK"]
    for q in queries:
        response = client.get(f"/api/v1/products?q={q}")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert any("Milk" in p["name"] for p in data["items"])


def test_list_products_search_partial_match(client: TestClient):
    """Test partial-match search across name and brand."""
    # Search by partial name
    res_oil = client.get("/api/v1/products?q=oil")
    assert res_oil.status_code == 200
    data_oil = res_oil.json()
    assert any("Sunflower Cooking Oil" in p["name"] for p in data_oil["items"])

    # Search by partial brand
    res_brand = client.get("/api/v1/products?q=Lurpak")
    assert res_brand.status_code == 200
    data_brand = res_brand.json()
    assert any(p["brand"] == "Lurpak" for p in data_brand["items"])

    # Search by partial barcode
    res_barcode = client.get("/api/v1/products?q=6001299011011")
    assert res_barcode.status_code == 200
    data_barcode = res_barcode.json()
    assert len(data_barcode["items"]) == 1
    assert data_barcode["items"][0]["barcode"] == "6001299011011"


def test_list_products_filter_by_brand(client: TestClient):
    """Test filtering catalog by specific brand name."""
    response = client.get("/api/v1/products?brand=Albany")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["brand"] == "Albany"
    assert "White Bread" in data["items"][0]["name"]


def test_list_products_filter_by_category(client: TestClient, raw_catalog_fixtures):
    """Test filtering catalog by category UUID."""
    dairy_category = next(
        c for c in raw_catalog_fixtures["categories"] if c["slug"] == "dairy-eggs"
    )
    dairy_id = str(dairy_category["id"])

    response = client.get(f"/api/v1/products?category_id={dairy_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 4
    for prod in data["items"]:
        assert prod["category_id"] == dairy_id
        assert prod["category"]["name"] == "Dairy & Eggs"


def test_list_products_invalid_pagination(client: TestClient):
    """Verify input validation rejects invalid limit and offset values."""
    # Limit too low (< 1)
    res_low = client.get("/api/v1/products?limit=0")
    assert res_low.status_code == 422
    assert "detail" in res_low.json()

    # Limit too high (> 100)
    res_high = client.get("/api/v1/products?limit=101")
    assert res_high.status_code == 422
    assert "detail" in res_high.json()

    # Negative offset (< 0)
    res_neg = client.get("/api/v1/products?offset=-1")
    assert res_neg.status_code == 422
    assert "detail" in res_neg.json()


def test_get_product_by_id_success(client: TestClient, raw_catalog_fixtures):
    """Verify retrieving detailed product metadata by UUID."""
    milk = next(p for p in raw_catalog_fixtures["products"] if "Milk" in p["name"])
    product_id = str(milk["id"])

    response = client.get(f"/api/v1/products/{product_id}")
    assert response.status_code == 200

    data = response.json()
    assert data["id"] == product_id
    assert data["name"] == "Full Cream Fresh Milk 2L"
    assert data["brand"] == "Clover"
    assert data["barcode"] == "6001299011011"
    assert Decimal(str(data["unit_size"])) == Decimal("2.00")
    assert data["unit_type"] == "L"
    assert data["category"]["name"] == "Dairy & Eggs"


def test_get_product_by_id_not_found(client: TestClient):
    """Verify 404 response for non-existent product ID."""
    random_id = str(uuid.uuid4())
    response = client.get(f"/api/v1/products/{random_id}")
    assert response.status_code == 404

    data = response.json()
    assert "detail" in data
    assert f"Product with id '{random_id}' not found" in data["detail"]


def test_get_product_by_id_invalid_uuid(client: TestClient):
    """Verify 422 response for malformed UUID."""
    response = client.get("/api/v1/products/invalid-uuid-string")
    assert response.status_code == 422
    assert "detail" in response.json()


def test_get_product_prices_success(client: TestClient, raw_catalog_fixtures):
    """Verify listing store-level active prices for a product."""
    milk = next(p for p in raw_catalog_fixtures["products"] if "Milk" in p["name"])
    product_id = str(milk["id"])

    response = client.get(f"/api/v1/products/{product_id}/prices")
    assert response.status_code == 200

    data = response.json()
    assert data["product_id"] == product_id
    assert data["product_name"] == "Full Cream Fresh Milk 2L"
    assert data["total_stores"] == 5
    assert len(data["prices"]) == 5

    # Verify prices are sorted ascending across the 5 national chains
    prices = [Decimal(str(item["price"])) for item in data["prices"]]
    assert prices == sorted(prices)

    # Check chain fields (no branch names or codes)
    first_price = data["prices"][0]
    assert "store_id" in first_price
    assert first_price["store_name"] == first_price["retailer_name"]
    assert first_price["branch_code"] is None
    assert "price" in first_price
    assert "is_promotional" in first_price
    assert "is_in_stock" in first_price
    assert "updated_at" in first_price

    # Check promotional item exists in price list
    promo_prices = [p for p in data["prices"] if p["is_promotional"] is True]
    assert len(promo_prices) > 0


def test_get_product_prices_not_found(client: TestClient):
    """Verify 404 when querying prices for a non-existent product."""
    random_id = str(uuid.uuid4())
    response = client.get(f"/api/v1/products/{random_id}/prices")
    assert response.status_code == 404

    data = response.json()
    assert "detail" in data
    assert f"Product with id '{random_id}' not found" in data["detail"]


def test_list_products_prioritizes_multi_chain_prices_and_brand_name_search(
    client: TestClient,
    db_session,
):
    """Products with more active chain store_prices rank first in GET /products."""
    from sqlalchemy import select

    from src.models.entities import Product, Store, StorePrice

    stores = list(
        db_session.scalars(select(Store).where(Store.is_active.is_(True))).all()
    )
    assert len(stores) >= 3

    p_zero = Product(
        id=uuid.uuid4(),
        name="Alpha Artisan Milk 1L",
        brand="ZeroChain",
        barcode="6009999000001",
        unit_size=Decimal("1.00"),
        unit_type="L",
    )
    p_one = Product(
        id=uuid.uuid4(),
        name="Beta Farm Milk 1L",
        brand="OneChain",
        barcode="6009999000002",
        unit_size=Decimal("1.00"),
        unit_type="L",
    )
    p_three = Product(
        id=uuid.uuid4(),
        name="Zeta Comparable Milk 2L",
        brand="ThreeChain",
        barcode="6009999000003",
        unit_size=Decimal("2.00"),
        unit_type="L",
    )
    db_session.add_all([p_zero, p_one, p_three])
    db_session.flush()

    db_session.add(
        StorePrice(
            store_id=stores[0].id,
            product_id=p_one.id,
            price=Decimal("24.99"),
            is_promotional=False,
            is_in_stock=True,
        )
    )
    for idx in range(3):
        db_session.add(
            StorePrice(
                store_id=stores[idx].id,
                product_id=p_three.id,
                price=Decimal("34.99") + Decimal(idx),
                is_promotional=False,
                is_in_stock=True,
            )
        )
    db_session.flush()

    # Query specifically matching our 3 test products ("Chain" in brand)
    res = client.get("/api/v1/products?q=Chain&limit=15")
    assert res.status_code == 200
    items = res.json()["items"]
    returned_ids = [item["id"] for item in items]

    # Even though 'Zeta' sorts last alphabetically, 3 active chains ranks first!
    assert returned_ids == [str(p_three.id), str(p_one.id), str(p_zero.id)]

    # Multi-word search combining brand + product name matches cleanly
    multi_res = client.get("/api/v1/products?q=ThreeChain%20Milk&limit=15")
    assert multi_res.status_code == 200
    multi_items = multi_res.json()["items"]
    assert len(multi_items) == 1
    assert multi_items[0]["id"] == str(p_three.id)
