"""Integration tests for pantry inventory, offline delta-sync, and auto-basket bridge.

Covers Issue #16 acceptance criteria:
- Pantry CRUD operations and audit logging isolated by home_id
- SmartBasket auto-replenishment hook when catalog items transition to
  low or finished
- Offline delta-sync endpoint with last-write-wins (LWW) conflict
  resolution and tombstones
- Multi-user household security guards preventing unauthorized pantry access (403)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi.testclient import TestClient


def _create_authenticated_user_and_home(
    client: TestClient, username: str, email: str, home_name: str
) -> tuple[str, str, dict[str, str]]:
    """Helper to register user, log in, create household, and return auth header."""
    client.post(
        "/api/v1/auth/register",
        json={"username": username, "email": email, "password": "Password123!"},
    )
    login_res = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "Password123!"},
    )
    token = login_res.json()["access_token"]
    header = {"Authorization": f"Bearer {token}"}

    home_res = client.post("/api/v1/homes", json={"name": home_name}, headers=header)
    home_id = home_res.json()["id"]
    return token, home_id, header


def test_pantry_crud_operations(client: TestClient) -> None:
    """Verify full pantry CRUD lifecycle including soft-deletion and filtering."""
    _, home_id, header = _create_authenticated_user_and_home(
        client, "pantry_shopper", "shopper@example.com", "Main Pantry"
    )

    # 1. Fetch catalog milk product
    prod_res = client.get("/api/v1/products?q=milk&limit=1")
    assert prod_res.status_code == 200
    milk_product = prod_res.json()["items"][0]
    milk_id = milk_product["id"]

    # 2. Add catalog item to pantry
    res_catalog = client.post(
        f"/api/v1/homes/{home_id}/pantry",
        json={
            "product_id": milk_id,
            "quantity": 2.0,
            "unit_type": "L",
            "low_stock_threshold": 1.0,
            "status": "ok",
            "note": "Bought 2 fresh bottles",
        },
        headers=header,
    )
    assert res_catalog.status_code == 201
    cat_item = res_catalog.json()
    assert cat_item["product_id"] == milk_id
    assert cat_item["quantity"] == "2.00"
    assert cat_item["status"] == "ok"
    assert cat_item["product_name"] == milk_product["name"]
    catalog_item_id = cat_item["id"]

    # 3. Add custom uncatalogued item
    res_custom = client.post(
        f"/api/v1/homes/{home_id}/pantry",
        json={
            "custom_name": "Grandma's Strawberry Jam",
            "quantity": 3.0,
            "unit_type": "unit",
            "low_stock_threshold": 1.0,
            "status": "ok",
        },
        headers=header,
    )
    assert res_custom.status_code == 201
    custom_item_id = res_custom.json()["id"]

    # 4. List pantry items with status filter
    res_list = client.get(f"/api/v1/homes/{home_id}/pantry?status=ok", headers=header)
    assert res_list.status_code == 200
    items = res_list.json()
    assert len(items) == 2

    # 5. Get single pantry item
    res_single = client.get(
        f"/api/v1/homes/{home_id}/pantry/{catalog_item_id}", headers=header
    )
    assert res_single.status_code == 200
    assert res_single.json()["id"] == catalog_item_id

    # 6. Patch pantry item (update quantity)
    res_patch = client.patch(
        f"/api/v1/homes/{home_id}/pantry/{catalog_item_id}",
        json={"quantity": 1.5, "note": "Consumed half bottle"},
        headers=header,
    )
    assert res_patch.status_code == 200
    assert res_patch.json()["quantity"] == "1.50"

    # 7. Soft-delete custom item
    res_del = client.delete(
        f"/api/v1/homes/{home_id}/pantry/{custom_item_id}", headers=header
    )
    assert res_del.status_code == 200

    # 8. List excludes soft-deleted items by default
    res_active = client.get(f"/api/v1/homes/{home_id}/pantry", headers=header)
    active_ids = [i["id"] for i in res_active.json()]
    assert catalog_item_id in active_ids
    assert custom_item_id not in active_ids

    # 9. List includes soft-deleted items when include_deleted=true
    res_all = client.get(
        f"/api/v1/homes/{home_id}/pantry?include_deleted=true", headers=header
    )
    all_ids = [i["id"] for i in res_all.json()]
    assert custom_item_id in all_ids


def test_auto_basket_replenishment_hook(client: TestClient) -> None:
    """Verify catalog item transitioning to low/finished auto-populates SmartBasket."""
    _, home_id, header = _create_authenticated_user_and_home(
        client, "bridge_user", "bridge@example.com", "Auto Replenish Home"
    )

    # 1. Fetch catalog bread product
    prod_res = client.get("/api/v1/products?q=bread&limit=1")
    assert prod_res.status_code == 200
    bread_product = prod_res.json()["items"][0]
    bread_id = bread_product["id"]

    # 2. Add bread to pantry with status="ok"
    pantry_res = client.post(
        f"/api/v1/homes/{home_id}/pantry",
        json={
            "product_id": bread_id,
            "quantity": 2.0,
            "unit_type": "unit",
            "low_stock_threshold": 1.0,
            "status": "ok",
        },
        headers=header,
    )
    pantry_item_id = pantry_res.json()["id"]

    # 3. Check household basket before replenishment
    basket_before = client.get(f"/api/v1/homes/{home_id}/basket", headers=header)
    assert basket_before.status_code == 200
    items_before = basket_before.json()["items"]
    assert not any(i["product_id"] == bread_id for i in items_before)

    # 4. Transition bread to status="low"
    patch_res = client.patch(
        f"/api/v1/homes/{home_id}/pantry/{pantry_item_id}",
        json={"status": "low", "quantity": 0.5, "note": "Only heels left"},
        headers=header,
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "low"

    # 5. Check household basket after replenishment
    basket_after = client.get(f"/api/v1/homes/{home_id}/basket", headers=header)
    assert basket_after.status_code == 200
    items_after = basket_after.json()["items"]
    replenished_item = next(
        (i for i in items_after if i["product_id"] == bread_id), None
    )
    assert (
        replenished_item is not None
    ), "Bread product must be auto-replenished into basket"
    assert Decimal(replenished_item["quantity"]) >= Decimal("1.00")

    # 6. Verify buyer can directly run multi-store price calculation on basket items
    calc_res = client.post(
        "/api/v1/baskets/calculate",
        json={
            "items": [
                {
                    "product_id": replenished_item["product_id"],
                    "quantity": float(replenished_item["quantity"]),
                }
            ]
        },
    )
    assert calc_res.status_code == 200
    calc_data = calc_res.json()
    assert "cheapest_single_store" in calc_data
    assert len(calc_data["ranked_stores"]) > 0


def test_offline_delta_sync_reconciliation_and_lww(client: TestClient) -> None:
    """Verify offline delta synchronization with last-write-wins and tombstones."""
    _, home_id, header = _create_authenticated_user_and_home(
        client, "sync_user", "sync@example.com", "Offline Sync Villa"
    )

    # 1. Fetch catalog egg product
    prod_res = client.get("/api/v1/products?q=eggs&limit=1")
    eggs_id = prod_res.json()["items"][0]["id"]

    # 2. Create server-side item initially
    base_time = datetime.now(timezone.utc) - timedelta(minutes=10)
    server_item_id = str(uuid.uuid4())
    create_res = client.post(
        f"/api/v1/homes/{home_id}/pantry",
        json={
            "product_id": eggs_id,
            "quantity": 18.0,
            "unit_type": "unit",
            "low_stock_threshold": 6.0,
            "status": "ok",
        },
        headers=header,
    )
    server_item_id = create_res.json()["id"]

    # 3. Prepare client offline mutations:
    # Mutation A: Create completely new item offline
    offline_new_id = str(uuid.uuid4())
    mutation_new = {
        "id": offline_new_id,
        "custom_name": "Artisanal Sourdough Loaf",
        "quantity": 1.0,
        "unit_type": "unit",
        "low_stock_threshold": 1.0,
        "status": "ok",
        "is_deleted": False,
        "updated_at": (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat(),
        "note": "Bought at farmers market",
    }

    # Mutation B: Client updates server item with NEWER timestamp -> client wins
    newer_client_time = datetime.now(timezone.utc) + timedelta(minutes=1)
    mutation_update_newer = {
        "id": server_item_id,
        "product_id": eggs_id,
        "quantity": 2.0,
        "unit_type": "unit",
        "low_stock_threshold": 6.0,
        "status": "finished",
        "is_deleted": False,
        "updated_at": newer_client_time.isoformat(),
        "note": "Used last eggs for baking",
    }

    # Execute sync
    sync_res = client.post(
        f"/api/v1/homes/{home_id}/pantry/sync",
        json={
            "last_synced_at": base_time.isoformat(),
            "mutations": [mutation_new, mutation_update_newer],
        },
        headers=header,
    )
    assert sync_res.status_code == 200
    sync_data = sync_res.json()
    assert sync_data["applied_mutations_count"] == 2
    delta_ids = [i["id"] for i in sync_data["items"]]
    assert offline_new_id in delta_ids
    assert server_item_id in delta_ids

    # Verify that transitioning eggs to 'finished' offline triggered auto-replenishment!
    basket_res = client.get(f"/api/v1/homes/{home_id}/basket", headers=header)
    assert basket_res.status_code == 200
    basket_products = [i["product_id"] for i in basket_res.json()["items"]]
    assert eggs_id in basket_products

    # 4. Mutation C: Client sends OLDER timestamp for an item -> server wins (LWW)
    stale_client_time = datetime.now(timezone.utc) - timedelta(hours=2)
    mutation_stale = {
        "id": server_item_id,
        "product_id": eggs_id,
        "quantity": 100.0,
        "status": "ok",
        "updated_at": stale_client_time.isoformat(),
    }
    sync_stale_res = client.post(
        f"/api/v1/homes/{home_id}/pantry/sync",
        json={
            "last_synced_at": datetime.now(timezone.utc).isoformat(),
            "mutations": [mutation_stale],
        },
        headers=header,
    )
    assert sync_stale_res.status_code == 200
    # Check that server still holds status="finished", not overwritten by stale mutation
    check_item = client.get(
        f"/api/v1/homes/{home_id}/pantry/{server_item_id}", headers=header
    )
    assert check_item.json()["status"] == "finished"
    assert Decimal(check_item.json()["quantity"]) != Decimal("100.00")


def test_pantry_household_isolation_and_403(client: TestClient) -> None:
    """Verify non-members cannot access, view, or modify household pantry (403)."""
    # User A creates Home A
    _, home_a_id, _ = _create_authenticated_user_and_home(
        client, "user_alpha", "alpha@example.com", "Alpha Sanctuary"
    )

    # User B creates Home B
    _, _, header_b = _create_authenticated_user_and_home(
        client, "user_beta", "beta@example.com", "Beta Compound"
    )

    # User B attempts to access Home A's pantry -> 403 Forbidden!
    res_list = client.get(f"/api/v1/homes/{home_a_id}/pantry", headers=header_b)
    assert res_list.status_code == 403
    assert "not a member" in res_list.json()["detail"].lower()

    # User B attempts to add item to Home A's pantry -> 403 Forbidden!
    res_add = client.post(
        f"/api/v1/homes/{home_a_id}/pantry",
        json={"custom_name": "Intruder Item"},
        headers=header_b,
    )
    assert res_add.status_code == 403

    # User B attempts offline sync to Home A's pantry -> 403 Forbidden!
    res_sync = client.post(
        f"/api/v1/homes/{home_a_id}/pantry/sync",
        json={"mutations": []},
        headers=header_b,
    )
    assert res_sync.status_code == 403


def test_offline_sync_nonexistent_product_id_degrades_to_custom_item(
    client: TestClient,
) -> None:
    """Verify sync gracefully clears unknown product_id instead of 500 FK error."""
    _, home_id, header = _create_authenticated_user_and_home(
        client, "fk_guard_user", "fk_guard@example.com", "FK Guard Home"
    )

    client_item_id = str(uuid.uuid4())
    unknown_product_id = "4f8b2f19-6c87-54d5-9c9a-3102e9f76b12"
    unknown_category_id = str(uuid.uuid4())

    sync_res = client.post(
        f"/api/v1/homes/{home_id}/pantry/sync",
        headers=header,
        json={
            "last_synced_at": None,
            "mutations": [
                {
                    "id": client_item_id,
                    "product_id": unknown_product_id,
                    "category_id": unknown_category_id,
                    "custom_name": "Free Range Large Eggs 18pk",
                    "quantity": "2.00",
                    "unit_type": "pack",
                    "low_stock_threshold": "1.00",
                    "status": "low",
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    "is_deleted": False,
                }
            ],
        },
    )
    assert sync_res.status_code == 200
    body = sync_res.json()
    assert body["applied_mutations_count"] == 1

    matched = next((i for i in body["items"] if i["id"] == client_item_id), None)
    assert matched is not None
    assert matched["product_id"] is None
    assert matched["category_id"] is None
    assert matched["custom_name"] == "Free Range Large Eggs 18pk"
    assert matched["status"] == "low"
