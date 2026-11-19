"""Tests for Issue #18: Expo SDK 53 mobile app, SQLite queue & SmartBasket wiring.

Verifies acceptance criteria:
- Expo SDK 53 project migrated into mobile/ with services/, db/, and types/ layers.
- .github/workflows/ci.yml includes mobile lint and typecheck steps.
- Local SQLite (react-native-sqlite-storage) pending_sync queue wired to
  POST /api/v1/homes/{home_id}/pantry/sync.
- SmartBasket price comparison view wired to POST /api/v1/baskets/calculate
  using the household's auto-populated basket.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

import yaml
from fastapi.testclient import TestClient

from src.main import app

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MOBILE_DIR = PROJECT_ROOT / "mobile"


def test_mobile_expo_sdk53_directory_and_package_structure() -> None:
    """Verify Expo SDK 53 project and required services, db, types directories exist."""
    assert MOBILE_DIR.exists() and MOBILE_DIR.is_dir(), "mobile/ directory must exist"

    pkg_path = MOBILE_DIR / "package.json"
    assert pkg_path.exists(), "mobile/package.json must exist"
    pkg_data = json.loads(pkg_path.read_text(encoding="utf-8"))

    deps = pkg_data.get("dependencies", {})
    assert "expo" in deps and "53" in deps["expo"], "Expo SDK 53 must be declared"
    assert (
        "react-native-sqlite-storage" in deps
    ), "react-native-sqlite-storage must be declared in dependencies"

    scripts = pkg_data.get("scripts", {})
    assert "lint" in scripts, "mobile/package.json must define 'lint' script"
    assert "typecheck" in scripts, "mobile/package.json must define 'typecheck' script"

    # Required #18 directories and files
    assert (MOBILE_DIR / "types" / "api.ts").exists(), "mobile/types/api.ts must exist"
    assert (MOBILE_DIR / "db" / "sqlite.ts").exists(), "mobile/db/sqlite.ts must exist"
    assert (
        MOBILE_DIR / "services" / "api.ts"
    ).exists(), "mobile/services/api.ts must exist"
    assert (
        MOBILE_DIR / "services" / "sync.ts"
    ).exists(), "mobile/services/sync.ts must exist"
    assert (
        MOBILE_DIR / "services" / "websocket.ts"
    ).exists(), "mobile/services/websocket.ts must exist"


def test_mobile_sqlite_and_api_wiring_contracts() -> None:
    """Verify SQLite pending_sync schema and API service endpoints match backend."""
    sqlite_code = (MOBILE_DIR / "db" / "sqlite.ts").read_text(encoding="utf-8")
    assert "react-native-sqlite-storage" in sqlite_code
    assert "pending_sync" in sqlite_code
    assert "local_pantry_items" in sqlite_code

    api_code = (MOBILE_DIR / "services" / "api.ts").read_text(encoding="utf-8")
    assert "/pantry/sync" in api_code
    assert "/baskets/calculate" in api_code
    assert "/basket" in api_code

    sync_code = (MOBILE_DIR / "services" / "sync.ts").read_text(encoding="utf-8")
    assert "postPantryDeltaSync" in sync_code
    assert "calculateMultiStoreBasket" in sync_code
    assert "fetchHouseholdBasket" in sync_code

    pantry_tab = (MOBILE_DIR / "app" / "(tabs)" / "index.tsx").read_text(
        encoding="utf-8"
    )
    assert "syncOfflineQueueToServer" in pantry_tab
    assert "updatePantryItemStatusOfflineFirst" in pantry_tab

    basket_tab = (MOBILE_DIR / "app" / "(tabs)" / "explore.tsx").read_text(
        encoding="utf-8"
    )
    assert "syncAndCalculateSmartBasket" in basket_tab
    assert "cheapest_single_store" in basket_tab
    assert "optimal_split" in basket_tab
    assert "ranked_stores" in basket_tab


def test_ci_workflow_includes_mobile_lint_and_typecheck() -> None:
    """Verify .github/workflows/ci.yml runs mobile lint and typecheck steps."""
    ci_path = PROJECT_ROOT / ".github" / "workflows" / "ci.yml"
    assert ci_path.exists()
    ci_data = yaml.safe_load(ci_path.read_text(encoding="utf-8"))

    steps = ci_data["jobs"]["test-and-lint"]["steps"]
    mobile_steps = [s for s in steps if s.get("working-directory") == "mobile"]
    assert len(mobile_steps) >= 2, "CI must execute steps in mobile working-directory"

    commands = " ".join(str(s.get("run", "")) for s in mobile_steps)
    assert "npm run typecheck" in commands
    assert "npm run lint" in commands


def test_mobile_offline_to_online_sync_and_basket_calculate_flow() -> None:
    """Simulate mobile SQLite pending_sync payload syncing and calculating basket."""
    client = TestClient(app)
    uid = uuid.uuid4().hex[:8]
    email = f"mobile_{uid}@example.com"
    password = "MobileUser123!"

    reg = client.post(
        "/api/v1/auth/register",
        json={"username": f"mobile_user_{uid}", "email": email, "password": password},
    )
    assert reg.status_code == 201

    login = client.post(
        "/api/v1/auth/login",
        json={"username": email, "password": password},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    home = client.post(
        "/api/v1/homes",
        json={"name": f"Mobile Household {uid}"},
        headers=headers,
    )
    assert home.status_code == 201
    home_id = home.json()["id"]

    # Fetch catalog staple product IDs (milk & bread)
    milk_prod = client.get("/api/v1/products?q=milk&limit=1").json()["items"][0]
    bread_prod = client.get("/api/v1/products?q=bread&limit=1").json()["items"][0]
    p1_id = milk_prod["id"]
    p2_id = bread_prod["id"]

    # 1. Push mobile pending_sync queue to POST /api/v1/homes/{home_id}/pantry/sync
    m1_id = str(uuid.uuid4())
    m2_id = str(uuid.uuid4())
    sync_res = client.post(
        f"/api/v1/homes/{home_id}/pantry/sync",
        headers=headers,
        json={
            "last_synced_at": None,
            "mutations": [
                {
                    "id": m1_id,
                    "product_id": p1_id,
                    "custom_name": milk_prod["name"],
                    "quantity": "1.00",
                    "unit_type": "unit",
                    "low_stock_threshold": "2.00",
                    "status": "low",
                    "updated_at": "2026-11-19T12:00:00Z",
                    "is_deleted": False,
                    "note": "Status updated to low on mobile",
                },
                {
                    "id": m2_id,
                    "product_id": p2_id,
                    "custom_name": bread_prod["name"],
                    "quantity": "0.00",
                    "unit_type": "unit",
                    "low_stock_threshold": "1.00",
                    "status": "finished",
                    "updated_at": "2026-11-19T12:01:00Z",
                    "is_deleted": False,
                    "note": "Status updated to finished on mobile",
                },
            ],
        },
    )
    assert sync_res.status_code == 200
    sync_body = sync_res.json()
    assert sync_body["applied_mutations_count"] == 2

    # 2. Fetch auto-populated household basket (GET /api/v1/homes/{home_id}/basket)
    basket_res = client.get(f"/api/v1/homes/{home_id}/basket", headers=headers)
    assert basket_res.status_code == 200
    basket_items = basket_res.json()["items"]
    assert len(basket_items) == 2

    # 3. Calculate multi-store price comparison (POST /api/v1/baskets/calculate)
    calc_res = client.post(
        "/api/v1/baskets/calculate",
        json={
            "items": [
                {"product_id": bi["product_id"], "quantity": bi["quantity"]}
                for bi in basket_items
            ]
        },
    )
    assert calc_res.status_code == 200
    calc_data = calc_res.json()
    assert calc_data["total_items_requested"] == 2
    assert calc_data["cheapest_single_store"] is not None
    assert len(calc_data["ranked_stores"]) > 0
