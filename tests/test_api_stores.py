"""Integration tests for store branches and supermarket chains API endpoints."""

from fastapi.testclient import TestClient


def test_list_stores_default(client: TestClient):
    """Test GET /api/v1/stores with default pagination."""
    response = client.get("/api/v1/stores")
    assert response.status_code == 200

    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] == 5
    assert data["limit"] == 50
    assert data["offset"] == 0
    assert len(data["items"]) == 5

    # Verify canonical national chain structure (no branch locations)
    expected_chains = {
        "Checkers",
        "Pick n Pay",
        "SPAR",
        "Shoprite",
        "Woolworths Food",
    }
    returned_names = {s["name"] for s in data["items"]}
    assert returned_names == expected_chains

    first_store = data["items"][0]
    assert "id" in first_store
    assert first_store["name"] == first_store["retailer"]["name"]
    assert first_store["branch_code"] is None
    assert first_store["address"] is None
    assert "is_active" in first_store
    assert "retailer_id" in first_store
    assert "retailer" in first_store
    assert "name" in first_store["retailer"]
    assert "slug" in first_store["retailer"]


def test_list_stores_pagination(client: TestClient):
    """Test pagination parameters on /api/v1/stores."""
    res_page_1 = client.get("/api/v1/stores?limit=3&offset=0")
    assert res_page_1.status_code == 200
    data_1 = res_page_1.json()
    assert len(data_1["items"]) == 3
    assert data_1["total"] == 5

    res_page_2 = client.get("/api/v1/stores?limit=3&offset=3")
    assert res_page_2.status_code == 200
    data_2 = res_page_2.json()
    assert len(data_2["items"]) == 2
    assert data_2["total"] == 5

    ids_1 = {s["id"] for s in data_1["items"]}
    ids_2 = {s["id"] for s in data_2["items"]}
    assert ids_1.isdisjoint(ids_2)


def test_list_stores_filter_by_retailer(client: TestClient, raw_catalog_fixtures):
    """Test filtering stores by parent retailer UUID returns 1 canonical chain."""
    checkers = next(
        r for r in raw_catalog_fixtures["retailers"] if r["slug"] == "checkers"
    )
    checkers_id = str(checkers["id"])

    response = client.get(f"/api/v1/stores?retailer_id={checkers_id}")
    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 1
    store = data["items"][0]
    assert store["retailer_id"] == checkers_id
    assert store["retailer"]["slug"] == "checkers"
    assert store["name"] == "Checkers"
    assert store["branch_code"] is None


def test_list_stores_filter_by_active(client: TestClient):
    """Test filtering stores by is_active status."""
    response = client.get("/api/v1/stores?is_active=true")
    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 5
    assert all(s["is_active"] is True for s in data["items"])


def test_list_stores_search_by_query(client: TestClient):
    """Test search query matching canonical national retailer chain name or slug."""
    res_checkers = client.get("/api/v1/stores?q=checkers")
    assert res_checkers.status_code == 200
    data_checkers = res_checkers.json()
    assert data_checkers["total"] == 1
    assert data_checkers["items"][0]["name"] == "Checkers"

    res_ww = client.get("/api/v1/stores?q=woolworths-food")
    assert res_ww.status_code == 200
    data_ww = res_ww.json()
    assert data_ww["total"] == 1
    assert data_ww["items"][0]["name"] == "Woolworths Food"

    res_shoprite = client.get("/api/v1/stores?q=Shoprite")
    assert res_shoprite.status_code == 200
    data_shoprite = res_shoprite.json()
    assert data_shoprite["total"] == 1
    assert data_shoprite["items"][0]["name"] == "Shoprite"


def test_list_stores_invalid_pagination(client: TestClient):
    """Verify input validation rejects invalid store query pagination."""
    res_zero = client.get("/api/v1/stores?limit=0")
    assert res_zero.status_code == 422

    res_neg = client.get("/api/v1/stores?offset=-5")
    assert res_neg.status_code == 422


def test_list_stores_invalid_retailer_uuid(client: TestClient):
    """Verify 422 when invalid retailer UUID format is supplied."""
    response = client.get("/api/v1/stores?retailer_id=not-a-valid-uuid")
    assert response.status_code == 422
    assert "detail" in response.json()
