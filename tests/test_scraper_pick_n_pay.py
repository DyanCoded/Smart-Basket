"""Offline fixture-based tests for Pick n Pay catalog scraper (#21)."""

from __future__ import annotations

import asyncio
import json
from decimal import Decimal
from pathlib import Path

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from scripts.run_scrapers import SCRAPER_REGISTRY, run_pipeline
from src.models.entities import PriceHistory, Product, StorePrice
from src.scrapers.normalizer import normalize_scraped_item
from src.scrapers.publisher import resolve_canonical_store
from src.scrapers.retailers.pick_n_pay import (
    PickNPayScraper,
    parse_pnp_html,
    parse_pnp_json,
)

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "scrapers"


def _load_fixture_text(filename: str) -> str:
    return (FIXTURES_DIR / filename).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 1. Registry Verification
# ---------------------------------------------------------------------------


def test_pick_n_pay_registered_in_cli_registry():
    scraper = SCRAPER_REGISTRY["pick-n-pay"]()
    assert isinstance(scraper, PickNPayScraper)
    assert scraper.retailer_slug == "pick-n-pay"
    assert scraper.base_url == "https://www.pnp.co.za"
    assert len(scraper.default_queries) >= 15


# ---------------------------------------------------------------------------
# 2. Pick n Pay OCC v2 JSON Fixture Parsing & Smart Shopper Promos
# ---------------------------------------------------------------------------


def test_pnp_json_fixture_extracts_shelf_and_smart_shopper_prices():
    payload = json.loads(_load_fixture_text("pnp_search_staples.json"))
    raw_items = parse_pnp_json(payload)

    assert len(raw_items) == 5
    normalized = [normalize_scraped_item(item) for item in raw_items]
    by_name = {rec.name: rec for rec in normalized}

    # 1. Smart Shopper "Save R6.00 - Pay R32.99" extracts R32.99 (NOT R6.00)
    milk = by_name["Clover Full Cream Fresh Milk 2L"]
    assert milk.retailer_slug == "pick-n-pay"
    assert milk.brand == "Clover"
    assert milk.barcode == "6001299011011"
    assert milk.category_slug == "dairy-eggs"
    assert milk.unit_size == Decimal("2.00")
    assert milk.unit_type == "L"
    assert milk.price == Decimal("32.99")
    assert milk.is_promotional is True
    assert milk.source_url is not None
    assert milk.source_url.startswith("https://www.pnp.co.za/")

    # 2. Multi-buy promo ("Buy 2 for R109.98" -> R54.99 / unit) + barcodes list
    eggs = by_name["Farmer Brown Large Eggs 18 Pack"]
    assert eggs.brand == "Farmer Brown"
    assert eggs.barcode == "6001299011028"
    assert eggs.unit_size == Decimal("18.00")
    assert eggs.unit_type == "unit"
    assert eggs.price == Decimal("54.99")
    assert eggs.is_promotional is True
    assert eggs.multi_buy_quantity == 2
    assert eggs.multi_buy_total == Decimal("109.98")

    # 3. Discount-only copy ("Smart Shopper Save R2.00") must NOT overwrite R16.99
    bread = by_name["Albany Superior Sliced White Bread 700g"]
    assert bread.brand == "Albany"
    assert bread.barcode == "6001299011059"
    assert bread.category_slug == "bakery"
    assert bread.unit_size == Decimal("700.00")
    assert bread.unit_type == "g"
    assert bread.price == Decimal("16.99")
    assert bread.is_promotional is False

    # 4. wasPrice / price sale + internal non-EAN PnP SKU ignored + unit from title
    apples = by_name["PnP Fresh Crisp Red Apples 1.5kg"]
    assert apples.brand == "Pick n Pay"
    assert apples.barcode is None
    assert apples.category_slug == "fresh-produce"
    assert apples.unit_size == Decimal("1.50")
    assert apples.unit_type == "kg"
    assert apples.price == Decimal("31.99")
    assert apples.is_promotional is True

    # 5. Structured smartShopperPrice object + 2000g -> 2.00 kg
    powder = by_name["Sunlight 2in1 Auto Washing Powder 2000g"]
    assert powder.brand == "Sunlight"
    assert powder.barcode == "6001087354127"
    assert powder.category_slug == "household"
    assert powder.unit_size == Decimal("2.00")
    assert powder.unit_type == "kg"
    assert powder.price == Decimal("67.99")
    assert powder.is_promotional is True


# ---------------------------------------------------------------------------
# 3. Pick n Pay Storefront HTML Fixture Parsing
# ---------------------------------------------------------------------------


def test_pnp_html_fixture_extracts_superscript_and_smart_shopper():
    html_text = _load_fixture_text("pnp_search_staples.html")
    raw_items = parse_pnp_html(html_text)

    assert len(raw_items) == 2
    normalized = [normalize_scraped_item(item) for item in raw_items]

    milk = normalized[0]
    assert milk.barcode == "6001299011011"
    assert milk.unit_size == Decimal("2.00")
    assert milk.unit_type == "L"
    assert milk.price == Decimal("32.99")
    assert milk.is_promotional is True

    bread = normalized[1]
    assert bread.barcode == "6001299011059"
    assert bread.unit_size == Decimal("700.00")
    assert bread.unit_type == "g"
    assert bread.price == Decimal("16.99")
    assert bread.is_promotional is False


# ---------------------------------------------------------------------------
# 4. End-to-End Offline Pipeline Integration (MockTransport -> Publisher)
# ---------------------------------------------------------------------------


def test_pnp_end_to_end_offline_pipeline_publishes_canonical_chain_prices(
    db_session: Session,
):
    pnp_json = _load_fixture_text("pnp_search_staples.json")
    captured_urls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_urls.append(str(request.url))
        return httpx.Response(
            200,
            text=pnp_json,
            headers={"Content-Type": "application/json"},
        )

    offline_registry = {
        "pick-n-pay": lambda: PickNPayScraper(
            min_delay_seconds=0.0,
            transport=httpx.MockTransport(handler),
        )
    }

    initial_history = db_session.scalar(select(func.count(PriceHistory.id)))

    # Two overlapping queries confirm deduplication to 5 unique Pick n Pay records
    summaries = asyncio.run(
        run_pipeline(
            ["pick-n-pay"],
            ["milk", "eggs"],
            dry_run=False,
            session=db_session,
            scraper_registry=offline_registry,
        )
    )

    assert len(summaries) == 1
    summary = summaries[0]
    assert summary.retailer_slug == "pick-n-pay"
    assert summary.records_processed == 5
    assert summary.skipped == 0

    pnp_store = resolve_canonical_store(db_session, "pick-n-pay")
    assert pnp_store is not None
    assert pnp_store.name == "Pick n Pay"

    # Clover Milk 2L updated to Smart Shopper promo R32.99
    milk_product = db_session.execute(
        select(Product).where(Product.barcode == "6001299011011")
    ).scalar_one()
    pnp_milk_price = db_session.execute(
        select(StorePrice).where(
            StorePrice.store_id == pnp_store.id,
            StorePrice.product_id == milk_product.id,
        )
    ).scalar_one()
    assert Decimal(pnp_milk_price.price) == Decimal("32.99")
    assert pnp_milk_price.is_promotional is True

    # History snapshots appended and query params sent properly
    assert db_session.scalar(select(func.count(PriceHistory.id))) > initial_history
    assert any("query=milk" in url and "fields=FULL" in url for url in captured_urls)


# ---------------------------------------------------------------------------
# 5. Respectful Anti-Bot / Access Control Handling
# ---------------------------------------------------------------------------


def test_pnp_scraper_halts_gracefully_on_403_or_incapsula_challenge():
    def blocked_403(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, text="Forbidden")

    def incapsula_html(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            text=(
                "<html><body>Request unsuccessful. "
                "Incapsula incident ID</body></html>"
            ),
            headers={"Content-Type": "text/html"},
        )

    async def _run():
        async with PickNPayScraper(
            min_delay_seconds=0.0,
            transport=httpx.MockTransport(blocked_403),
        ) as s1:
            items_403 = await s1.scrape_catalog(["milk"])

        async with PickNPayScraper(
            min_delay_seconds=0.0,
            transport=httpx.MockTransport(incapsula_html),
        ) as s2:
            items_waf = await s2.scrape_catalog(["milk"])

        return items_403, items_waf

    items_403, items_waf = asyncio.run(_run())
    assert items_403 == []
    assert items_waf == []
