"""Integration tests for store branches and supermarket chains API endpoints."""

from fastapi.testclient import TestClient


def test_list_stores_default(client: TestClient):
    """Test GET /api/v1/stores with default pagination."""
    response = client.get("/api/v1/stores")
    assert response.status_code == 200

    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] == 8
    assert data["limit"] == 50
    assert data["offset"] == 0
    assert len(data["items"]) == 8

    # Verify store branch structure
    first_store = data["items"][0]
    assert "id" in first_store
    assert "name" in first_store
    assert "branch_code" in first_store
    assert "address" in first_store
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
    assert data_1["total"] == 8

    res_page_2 = client.get("/api/v1/stores?limit=3&offset=3")
    assert res_page_2.status_code == 200
    data_2 = res_page_2.json()
    assert len(data_2["items"]) == 3
    assert data_2["total"] == 8

    ids_1 = {s["id"] for s in data_1["items"]}
    ids_2 = {s["id"] for s in data_2["items"]}
    assert ids_1.isdisjoint(ids_2)


def test_list_stores_filter_by_retailer(client: TestClient, raw_catalog_fixtures):
    """Test filtering stores by parent retailer UUID."""
    checkers = next(
        r for r in raw_catalog_fixtures["retailers"] if r["slug"] == "checkers"
    )
    checkers_id = str(checkers["id"])

    response = client.get(f"/api/v1/stores?retailer_id={checkers_id}")
    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 2
    for store in data["items"]:
        assert store["retailer_id"] == checkers_id
        assert store["retailer"]["slug"] == "checkers"
        assert "Checkers" in store["name"]


def test_list_stores_filter_by_active(client: TestClient):
    """Test filtering stores by is_active status."""
    response = client.get("/api/v1/stores?is_active=true")
    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 8
    assert all(s["is_active"] is True for s in data["items"])


def test_list_stores_search_by_query(client: TestClient):
    """Test search query matching store name, branch code, or address."""
    # Search by branch name keyword
    res_sandton = client.get("/api/v1/stores?q=sandton")
    assert res_sandton.status_code == 200
    data_sandton = res_sandton.json()
    assert data_sandton["total"] >= 2
    assert all("Sandton" in s["name"] for s in data_sandton["items"])

    # Search by branch code
    res_code = client.get("/api/v1/stores?q=CHK-CPT-002")
    assert res_code.status_code == 200
    data_code = res_code.json()
    assert data_code["total"] == 1
    assert data_code["items"][0]["branch_code"] == "CHK-CPT-002"

    # Search by city address
    res_cpt = client.get("/api/v1/stores?q=Cape Town")
    assert res_cpt.status_code == 200
    data_cpt = res_cpt.json()
    assert data_cpt["total"] >= 3
    assert all("Cape Town" in s["address"] for s in data_cpt["items"])


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
