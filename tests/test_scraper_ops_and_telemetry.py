"""Tests for daily price sync workflow, fault isolation & freshness telemetry (#24)."""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import yaml
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from scripts.run_scrapers import (
    build_parser,
    build_telemetry_report,
    main,
    purge_synthetic_seed_products,
    run_pipeline,
)
from src.models.entities import PriceHistory, Product, StorePrice
from src.scrapers.base import BaseRetailerScraper, PlaceholderFixtureScraper
from src.scrapers.feed_loader import load_feed_items_from_dir
from src.scrapers.models import NormalizedPriceRecord, RawScrapedItem
from src.scrapers.publisher import CatalogPublisher, resolve_canonical_store

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "scrape_prices.yml"
FEEDS_FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "feeds"


class _EmptyRetailerScraper(BaseRetailerScraper):
    """Test double simulating a blocked/empty storefront returning 0 items."""

    def __init__(self, slug: str) -> None:
        self.retailer_slug = slug
        super().__init__(min_delay_seconds=0.0)

    async def scrape_catalog(self, query_terms: list[str]) -> list[RawScrapedItem]:
        return []


class _FailingRetailerScraper(BaseRetailerScraper):
    """Test double simulating a transient/upstream outage in one retailer."""

    def __init__(self, slug: str, message: str = "Upstream 503 outage") -> None:
        self.retailer_slug = slug
        self._message = message
        super().__init__(min_delay_seconds=0.0)

    async def scrape_catalog(self, query_terms: list[str]) -> list[RawScrapedItem]:
        raise RuntimeError(self._message)


# ---------------------------------------------------------------------------
# 1. GitHub Actions Scheduled Workflow Validation
# ---------------------------------------------------------------------------


def test_scrape_prices_workflow_is_valid_yaml_with_cron_and_dispatch():
    assert WORKFLOW_PATH.exists(), "Missing .github/workflows/scrape_prices.yml"
    parsed = yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))
    assert isinstance(parsed, dict)

    # PyYAML parses unquoted 'on' as boolean True under YAML 1.1 rules
    triggers = parsed.get("on") or parsed.get(True)
    assert isinstance(triggers, dict)
    assert "schedule" in triggers
    assert isinstance(triggers["schedule"], list) and len(triggers["schedule"]) >= 1
    cron_expr = triggers["schedule"][0]["cron"]
    assert len(cron_expr.split()) == 5
    assert "workflow_dispatch" in triggers

    jobs = parsed.get("jobs", {})
    assert "scrape-national-prices" in jobs
    steps = jobs["scrape-national-prices"]["steps"]
    run_blocks = "\n".join(str(step.get("run", "")) for step in steps)
    assert "scripts/run_scrapers.py" in run_blocks
    assert "--summary-json" in run_blocks


# ---------------------------------------------------------------------------
# 2. Per-Retailer Fault Isolation & Structured Warning Logs
# ---------------------------------------------------------------------------


def test_partial_retailer_failure_is_isolated_and_batch_continues(
    db_session: Session,
    caplog,
):
    mixed_registry = {
        "checkers": lambda: _FailingRetailerScraper(
            "checkers", "Simulated Checkers timeout"
        ),
        "shoprite": lambda: PlaceholderFixtureScraper("shoprite"),
        "spar": lambda: PlaceholderFixtureScraper("spar"),
    }

    with caplog.at_level(logging.WARNING, logger="smart_basket.scrapers"):
        summaries = asyncio.run(
            run_pipeline(
                ["checkers", "shoprite", "spar"],
                ["milk", "bread"],
                dry_run=True,
                session=db_session,
                scraper_registry=mixed_registry,
            )
        )

    assert len(summaries) == 3
    by_slug = {s.retailer_slug: s for s in summaries}

    # Failing retailer isolated with structured error & warning log
    assert by_slug["checkers"].status == "failed"
    assert by_slug["checkers"].error is not None
    assert "RuntimeError: Simulated Checkers timeout" in by_slug["checkers"].error
    assert by_slug["checkers"].records_processed == 0

    # Remaining healthy retailers still executed cleanly
    assert by_slug["shoprite"].status == "ok"
    assert by_slug["shoprite"].error is None
    assert by_slug["shoprite"].records_processed == 2

    assert by_slug["spar"].status == "ok"
    assert by_slug["spar"].error is None
    assert by_slug["spar"].records_processed == 2

    assert any(
        "Retailer scraper failed" in rec.message and "checkers" in rec.message
        for rec in caplog.records
    )

    report = build_telemetry_report(summaries)
    assert report["overall_status"] == "degraded"
    assert report["total_retailers"] == 3
    assert report["succeeded"] == 2
    assert report["failed"] == 1


def test_cli_summary_json_and_exit_codes_for_degraded_and_failed_runs(
    db_session: Session,
    tmp_path: Path,
):
    degraded_registry = {
        "shoprite": lambda: _FailingRetailerScraper("shoprite", "Connection reset"),
        "checkers": lambda: PlaceholderFixtureScraper("checkers"),
        "pick-n-pay": lambda: PlaceholderFixtureScraper("pick-n-pay"),
        "woolworths-food": lambda: PlaceholderFixtureScraper("woolworths-food"),
        "spar": lambda: PlaceholderFixtureScraper("spar"),
    }

    summary_file = tmp_path / "telemetry.json"
    exit_code = main(
        [
            "--retailer",
            "all",
            "--dry-run",
            "--summary-json",
            str(summary_file),
        ],
        session=db_session,
        scraper_registry=degraded_registry,
    )
    assert exit_code == 0
    assert summary_file.exists()

    payload = json.loads(summary_file.read_text(encoding="utf-8"))
    assert payload["overall_status"] == "degraded"
    assert payload["succeeded"] == 4
    assert payload["failed"] == 1

    # Strict mode returns exit code 1 on partial failure
    strict_code = main(
        ["--retailer", "all", "--dry-run", "--strict"],
        session=db_session,
        scraper_registry=degraded_registry,
    )
    assert strict_code == 1

    # Total failure always returns exit code 1
    total_fail_registry = {
        "spar": lambda: _FailingRetailerScraper("spar", "DNS error"),
    }
    fail_code = main(
        ["--retailer", "spar", "--dry-run"],
        session=db_session,
        scraper_registry=total_fail_registry,
    )
    assert fail_code == 1


# ---------------------------------------------------------------------------
# 3. Data Freshness Telemetry in GET /api/v1/stores & GET /health
# ---------------------------------------------------------------------------


def test_stores_endpoint_exposes_last_price_sync_and_updates_after_publish(
    client: TestClient,
    db_session: Session,
):
    res = client.get("/api/v1/stores")
    assert res.status_code == 200
    data = res.json()

    assert data["last_price_sync_at"] is not None
    assert len(data["items"]) == 5

    for store in data["items"]:
        assert store["last_price_sync_at"] is not None
        assert store["tracked_products_count"] == 18

    # Publish a newer scraped price for Checkers and verify timestamp advances
    future_ts = datetime.now(timezone.utc) + timedelta(hours=2)
    publisher = CatalogPublisher(db_session)
    publisher.publish_records(
        [
            NormalizedPriceRecord(
                retailer_slug="checkers",
                name="Clover Full Cream Fresh Milk 2L",
                brand="Clover",
                barcode="6001299011011",
                unit_size=Decimal("2.00"),
                unit_type="L",
                price=Decimal("30.99"),
                is_promotional=True,
                scraped_at=future_ts,
            )
        ],
        commit=False,
    )

    res_after = client.get("/api/v1/stores")
    assert res_after.status_code == 200
    data_after = res_after.json()
    checkers = next(
        s for s in data_after["items"] if s["retailer"]["slug"] == "checkers"
    )

    parsed_checkers_ts = datetime.fromisoformat(
        checkers["last_price_sync_at"].replace("Z", "+00:00")
    )
    assert parsed_checkers_ts.replace(tzinfo=None) >= (
        future_ts - timedelta(seconds=2)
    ).replace(tzinfo=None)


def test_health_endpoint_exposes_catalog_freshness_telemetry(client: TestClient):
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()

    assert data["status"] == "ok"
    assert data["app"] == "Smart Basket API"
    assert "catalog_freshness" in data
    freshness = data["catalog_freshness"]
    assert freshness["status"] == "ok"
    assert freshness["last_price_sync_at"] is not None
    assert freshness["active_chains"] == 5
    assert freshness["tracked_prices"] == 90


# ---------------------------------------------------------------------------
# 4. Zero-Item Partial Status Reporting (No Silent OK on Blocked/Empty Runs)
# ---------------------------------------------------------------------------


def test_zero_item_run_reports_partial_status_and_degraded_telemetry(
    db_session: Session,
    caplog,
    capsys,
):
    registry = {
        "checkers": lambda: _EmptyRetailerScraper("checkers"),
        "shoprite": lambda: PlaceholderFixtureScraper("shoprite"),
    }

    with caplog.at_level(logging.WARNING, logger="smart_basket.scrapers"):
        summaries = asyncio.run(
            run_pipeline(
                ["checkers", "shoprite"],
                ["milk"],
                dry_run=True,
                session=db_session,
                scraper_registry=registry,
            )
        )

    by_slug = {s.retailer_slug: s for s in summaries}
    assert by_slug["checkers"].status == "partial"
    assert by_slug["checkers"].records_processed == 0
    assert by_slug["checkers"].error is not None
    assert "0 items" in by_slug["checkers"].error
    assert by_slug["shoprite"].status == "ok"

    report = build_telemetry_report(summaries)
    assert report["overall_status"] == "degraded"
    assert report["succeeded"] == 1
    assert report["partial"] == 1
    assert report["failed"] == 0

    assert any(
        "returned 0 items" in rec.message and "checkers" in rec.message
        for rec in caplog.records
    )

    # CLI output displays STATUS=PARTIAL (0 items) and fails under --strict
    exit_code = main(
        ["--retailer", "checkers", "--dry-run"],
        session=db_session,
        scraper_registry=registry,
    )
    assert exit_code == 0
    stdout = capsys.readouterr().out
    assert "STATUS=PARTIAL (0 items)" in stdout

    strict_exit = main(
        ["--retailer", "checkers", "--dry-run", "--strict"],
        session=db_session,
        scraper_registry=registry,
    )
    assert strict_exit == 1


# ---------------------------------------------------------------------------
# 5. --source-dir JSON/CSV Feed Ingestion & End-to-End Basket Recalculation
# ---------------------------------------------------------------------------


def test_feed_loader_parses_json_and_csv_snapshots_across_all_five_chains():
    grouped = load_feed_items_from_dir(FEEDS_FIXTURE_DIR)
    assert set(grouped.keys()) == {
        "checkers",
        "shoprite",
        "pick-n-pay",
        "woolworths-food",
        "spar",
    }
    assert len(grouped["checkers"]) == 2
    assert len(grouped["shoprite"]) == 2
    assert len(grouped["pick-n-pay"]) == 1
    assert len(grouped["woolworths-food"]) == 2
    assert len(grouped["spar"]) == 2


def test_source_dir_cli_ingestion_updates_db_and_recalculates_basket(
    client: TestClient,
    db_session: Session,
    tmp_path: Path,
):
    initial_history = db_session.scalar(select(func.count(PriceHistory.id)))
    summary_file = tmp_path / "feed_summary.json"

    exit_code = main(
        [
            "--retailer",
            "all",
            "--source-dir",
            str(FEEDS_FIXTURE_DIR),
            "--summary-json",
            str(summary_file),
        ],
        session=db_session,
    )
    assert exit_code == 0

    telemetry = json.loads(summary_file.read_text(encoding="utf-8"))
    assert telemetry["overall_status"] == "ok"
    assert telemetry["succeeded"] == 5
    assert telemetry["partial"] == 0
    assert telemetry["failed"] == 0

    # Verify normalized prices updated in store_prices & appended to price_history
    milk = db_session.execute(
        select(Product).where(Product.barcode == "6001299011011")
    ).scalar_one()
    bread = db_session.execute(
        select(Product).where(Product.barcode == "6001299011059")
    ).scalar_one()
    eggs = db_session.execute(
        select(Product).where(Product.barcode == "6001299011028")
    ).scalar_one()

    checkers_store = resolve_canonical_store(db_session, "checkers")
    pnp_store = resolve_canonical_store(db_session, "pick-n-pay")
    assert checkers_store is not None and pnp_store is not None

    checkers_milk = db_session.execute(
        select(StorePrice).where(
            StorePrice.store_id == checkers_store.id,
            StorePrice.product_id == milk.id,
        )
    ).scalar_one()
    assert Decimal(checkers_milk.price) == Decimal("29.99")
    assert checkers_milk.is_promotional is True

    # Pick n Pay "2 FOR R104.98" normalized to R52.49 per unit
    pnp_eggs = db_session.execute(
        select(StorePrice).where(
            StorePrice.store_id == pnp_store.id,
            StorePrice.product_id == eggs.id,
        )
    ).scalar_one()
    assert Decimal(pnp_eggs.price) == Decimal("52.49")
    assert pnp_eggs.is_promotional is True

    assert db_session.scalar(select(func.count(PriceHistory.id))) > initial_history

    # Verify POST /api/v1/baskets/calculate reflects the newly ingested prices
    calc_res = client.post(
        "/api/v1/baskets/calculate",
        json={
            "items": [
                {"product_id": str(milk.id), "quantity": 1},
                {"product_id": str(bread.id), "quantity": 1},
                {"product_id": str(eggs.id), "quantity": 1},
            ]
        },
    )
    assert calc_res.status_code == 200
    body = calc_res.json()

    # Smart Mode picks Checkers Milk (29.99) + Shoprite Bread (14.99) + PnP Eggs (52.49)
    split = body["optimal_split"]
    assert split is not None
    assert Decimal(str(split["total_price"])) == Decimal("97.47")
    assert Decimal(str(split["savings_amount"])) > Decimal("0.00")


# ---------------------------------------------------------------------------
# 6. Synthetic Seed Product Purge (--purge-seed)
# ---------------------------------------------------------------------------


def test_purge_synthetic_seed_products_preserves_live_catalog_and_stores(
    db_session: Session,
):
    import uuid

    # Add a genuine live-scraped product alongside the 18 synthetic seed products
    checkers_store = resolve_canonical_store(db_session, "checkers")
    assert checkers_store is not None
    live_product = Product(
        id=uuid.uuid4(),
        name="Clover Fresh Full Cream Milk 2L",
        brand="Clover",
        barcode="6001299015274",
        unit_size=Decimal("2.00"),
        unit_type="L",
    )
    db_session.add(live_product)
    db_session.flush()
    db_session.add(
        StorePrice(
            store_id=checkers_store.id,
            product_id=live_product.id,
            price=Decimal("36.99"),
            is_promotional=False,
            is_in_stock=True,
        )
    )
    db_session.flush()

    # Dry-run reports all 18 synthetic seed products without deleting anything
    dry_stats = purge_synthetic_seed_products(db_session, dry_run=True, commit=False)
    assert dry_stats["products_purged"] == 18
    assert dry_stats["store_prices_purged"] == 90
    assert db_session.scalar(select(func.count(Product.id))) == 19

    # Real purge removes only the 18 synthetic 6001299011xxx seed products
    stats = purge_synthetic_seed_products(db_session, dry_run=False, commit=False)
    assert stats["products_purged"] == 18
    assert stats["store_prices_purged"] == 90

    remaining = list(db_session.scalars(select(Product)).all())
    assert len(remaining) == 1
    assert remaining[0].id == live_product.id
    assert remaining[0].barcode == "6001299015274"
    assert db_session.scalar(select(func.count(StorePrice.id))) == 1

    # CLI flag parses cleanly
    args = build_parser().parse_args(["--purge-seed", "--retailer", "all", "--dry-run"])
    assert args.purge_seed is True
