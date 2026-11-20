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
from sqlalchemy.orm import Session

from scripts.run_scrapers import build_telemetry_report, main, run_pipeline
from src.scrapers.base import BaseRetailerScraper, PlaceholderFixtureScraper
from src.scrapers.models import NormalizedPriceRecord, RawScrapedItem
from src.scrapers.publisher import CatalogPublisher

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "scrape_prices.yml"


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
