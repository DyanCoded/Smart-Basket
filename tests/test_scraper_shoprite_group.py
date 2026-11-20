"""Offline fixture-based tests for Checkers & Shoprite catalog scrapers (#20)."""

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
from src.scrapers.retailers.shoprite_group import (
    DEFAULT_CORE_STAPLES,
    CheckersScraper,
    ShopriteScraper,
    parse_search_html,
    parse_search_json,
)

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "scrapers"


def _load_fixture_text(filename: str) -> str:
    return (FIXTURES_DIR / filename).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 1. Registry & Core Staples Configuration
# ---------------------------------------------------------------------------


def test_checkers_and_shoprite_registered_in_cli_registry():
    checkers = SCRAPER_REGISTRY["checkers"]()
    shoprite = SCRAPER_REGISTRY["shoprite"]()

    assert isinstance(checkers, CheckersScraper)
    assert checkers.retailer_slug == "checkers"
    assert checkers.base_url == "https://www.checkers.co.za"

    assert isinstance(shoprite, ShopriteScraper)
    assert shoprite.retailer_slug == "shoprite"
    assert shoprite.base_url == "https://www.shoprite.co.za"


def test_core_staples_cover_all_five_departments():
    expected_categories = {
        "dairy-eggs",
        "bakery",
        "pantry-staples",
        "fresh-produce",
        "household",
    }
    assert expected_categories.issubset(set(DEFAULT_CORE_STAPLES.keys()))
    scraper = CheckersScraper()
    assert len(scraper.default_queries) >= 15


# ---------------------------------------------------------------------------
# 2. Checkers HTML Fixture Parser & Normalizer Integration
# ---------------------------------------------------------------------------


def test_checkers_html_fixture_extracts_regular_and_promotional_prices():
    html_text = _load_fixture_text("checkers_search_staples.html")
    raw_items = parse_search_html(
        html_text,
        retailer_slug="checkers",
        base_url="https://www.checkers.co.za",
    )

    assert len(raw_items) == 5
    normalized = [normalize_scraped_item(item) for item in raw_items]
    by_name = {rec.name: rec for rec in normalized}

    # 1. Dairy & Eggs: Xtra Savings promo overrides shelf price R38.99 -> R31.99
    milk = by_name["Clover Full Cream Fresh Milk 2L"]
    assert milk.retailer_slug == "checkers"
    assert milk.brand == "Clover"
    assert milk.barcode == "6001299011011"
    assert milk.category_slug == "dairy-eggs"
    assert milk.unit_size == Decimal("2.00")
    assert milk.unit_type == "L"
    assert milk.price == Decimal("31.99")
    assert milk.is_promotional is True
    assert milk.source_url is not None
    assert milk.source_url.startswith("https://www.checkers.co.za/")

    # 2. Bakery: Standard regular price R17.99
    bread = by_name["Albany Superior Sliced White Bread 700g"]
    assert bread.brand == "Albany"
    assert bread.barcode == "6001299011059"
    assert bread.category_slug == "bakery"
    assert bread.unit_size == Decimal("700.00")
    assert bread.unit_type == "g"
    assert bread.price == Decimal("17.99")
    assert bread.is_promotional is False

    # 3. Pantry & Staples: Strikethrough before R44.99 -> now R39.99
    rice = by_name["Tastic Long Grain Parboiled Rice 2kg"]
    assert rice.brand == "Tastic"
    assert rice.barcode == "6001299011073"
    assert rice.category_slug == "pantry-staples"
    assert rice.unit_size == Decimal("2.00")
    assert rice.unit_type == "kg"
    assert rice.price == Decimal("39.99")
    assert rice.is_promotional is True

    # 4. Fresh Produce: Internal non-EAN SKU must NOT become barcode; unit from title
    apples = by_name["Freshmark Crisp Red Apples 1.5kg"]
    assert apples.brand == "Freshmark"
    assert apples.barcode is None
    assert apples.category_slug == "fresh-produce"
    assert apples.unit_size == Decimal("1.50")
    assert apples.unit_type == "kg"
    assert apples.price == Decimal("32.99")
    assert apples.is_promotional is False

    # 5. Household: Multi-buy deal ("2 FOR R139.98" -> R69.99 / unit)
    powder = by_name["Sunlight 2in1 Auto Washing Powder 2kg"]
    assert powder.brand == "Sunlight"
    assert powder.barcode == "6001087354127"
    assert powder.category_slug == "household"
    assert powder.unit_size == Decimal("2.00")
    assert powder.unit_type == "kg"
    assert powder.price == Decimal("69.99")
    assert powder.is_promotional is True
    assert powder.multi_buy_quantity == 2
    assert powder.multi_buy_total == Decimal("139.98")


# ---------------------------------------------------------------------------
# 3. Shoprite JSON & HTML Fixture Parsers
# ---------------------------------------------------------------------------


def test_shoprite_json_fixture_extracts_all_staples_and_promos():
    payload = json.loads(_load_fixture_text("shoprite_search_staples.json"))
    raw_items = parse_search_json(
        payload,
        retailer_slug="shoprite",
        base_url="https://www.shoprite.co.za",
    )

    assert len(raw_items) == 5
    normalized = [normalize_scraped_item(item) for item in raw_items]
    by_name = {rec.name: rec for rec in normalized}

    milk = by_name["Clover Full Cream Fresh Milk 2 Litre"]
    assert milk.retailer_slug == "shoprite"
    assert milk.barcode == "6001299011011"
    assert milk.unit_size == Decimal("2.00")
    assert milk.unit_type == "L"
    assert milk.price == Decimal("33.99")
    assert milk.is_promotional is False

    eggs = by_name["Farmer Brown Large Eggs 18 Pack"]
    assert eggs.barcode == "6001299011028"
    assert eggs.unit_size == Decimal("18.00")
    assert eggs.unit_type == "unit"
    assert eggs.price == Decimal("54.99")
    assert eggs.is_promotional is True
    assert eggs.multi_buy_quantity == 2
    assert eggs.multi_buy_total == Decimal("109.98")

    bread = by_name["Albany Superior Sliced White Bread 700g"]
    assert bread.price == Decimal("15.99")
    assert bread.is_promotional is False

    potatoes = by_name["Ritebrand Washed Potatoes 2kg"]
    assert potatoes.barcode is None
    assert potatoes.category_slug == "fresh-produce"
    assert potatoes.price == Decimal("24.99")
    assert potatoes.is_promotional is True

    dishwash = by_name["Sunlight Regular Dishwashing Liquid 750ml"]
    assert dishwash.barcode == "6001087361200"
    assert dishwash.category_slug == "household"
    assert dishwash.unit_size == Decimal("750.00")
    assert dishwash.unit_type == "ml"
    assert dishwash.price == Decimal("34.99")
    assert dishwash.is_promotional is False


def test_shoprite_html_fixture_handles_superscript_cents_without_dot():
    html_text = _load_fixture_text("shoprite_search_staples.html")
    raw_items = parse_search_html(
        html_text,
        retailer_slug="shoprite",
        base_url="https://www.shoprite.co.za",
    )

    assert len(raw_items) == 2
    normalized = [normalize_scraped_item(item) for item in raw_items]

    assert normalized[0].price == Decimal("15.99")
    assert normalized[0].is_promotional is False

    assert normalized[1].price == Decimal("37.99")
    assert normalized[1].is_promotional is True


# ---------------------------------------------------------------------------
# 4. End-to-End Offline Pipeline Integration (MockTransport -> Publisher)
# ---------------------------------------------------------------------------


def test_shoprite_group_end_to_end_offline_pipeline_and_deduplication(
    db_session: Session,
):
    checkers_html = _load_fixture_text("checkers_search_staples.html")
    shoprite_json = _load_fixture_text("shoprite_search_staples.json")
    captured_queries: list[str] = []

    def checkers_handler(request: httpx.Request) -> httpx.Response:
        captured_queries.append(str(request.url))
        return httpx.Response(
            200,
            text=checkers_html,
            headers={"Content-Type": "text/html; charset=utf-8"},
        )

    def shoprite_handler(request: httpx.Request) -> httpx.Response:
        captured_queries.append(str(request.url))
        return httpx.Response(
            200,
            text=shoprite_json,
            headers={"Content-Type": "application/json"},
        )

    offline_registry = {
        "checkers": lambda: CheckersScraper(
            min_delay_seconds=0.0,
            transport=httpx.MockTransport(checkers_handler),
        ),
        "shoprite": lambda: ShopriteScraper(
            min_delay_seconds=0.0,
            transport=httpx.MockTransport(shoprite_handler),
        ),
    }

    initial_history = db_session.scalar(select(func.count(PriceHistory.id)))

    # Passing two overlapping queries verifies deduplication (5 unique items per chain)
    summaries = asyncio.run(
        run_pipeline(
            ["checkers", "shoprite"],
            ["milk", "bread"],
            dry_run=False,
            session=db_session,
            scraper_registry=offline_registry,
        )
    )

    assert len(summaries) == 2
    by_slug = {s.retailer_slug: s for s in summaries}

    assert by_slug["checkers"].records_processed == 5
    assert by_slug["checkers"].skipped == 0
    assert by_slug["shoprite"].records_processed == 5
    assert by_slug["shoprite"].skipped == 0

    # Verify Checkers Milk 2L canonical chain price reflects Xtra Savings R31.99
    checkers_store = resolve_canonical_store(db_session, "checkers")
    milk_product = db_session.execute(
        select(Product).where(Product.barcode == "6001299011011")
    ).scalar_one()
    checkers_milk_price = db_session.execute(
        select(StorePrice).where(
            StorePrice.store_id == checkers_store.id,
            StorePrice.product_id == milk_product.id,
        )
    ).scalar_one()
    assert Decimal(checkers_milk_price.price) == Decimal("31.99")
    assert checkers_milk_price.is_promotional is True

    # Verify Shoprite Eggs 18pk reflects multi-buy promo unit price R54.99
    shoprite_store = resolve_canonical_store(db_session, "shoprite")
    eggs_product = db_session.execute(
        select(Product).where(Product.barcode == "6001299011028")
    ).scalar_one()
    shoprite_eggs_price = db_session.execute(
        select(StorePrice).where(
            StorePrice.store_id == shoprite_store.id,
            StorePrice.product_id == eggs_product.id,
        )
    ).scalar_one()
    assert Decimal(shoprite_eggs_price.price) == Decimal("54.99")
    assert shoprite_eggs_price.is_promotional is True

    # Verify new history snapshots were appended
    assert db_session.scalar(select(func.count(PriceHistory.id))) > initial_history
    assert any("q=milk%3Arelevance" in url for url in captured_queries)


# ---------------------------------------------------------------------------
# 5. Respectful Anti-Bot / Access Control Handling
# ---------------------------------------------------------------------------


def test_scraper_halts_gracefully_on_403_or_cloudflare_challenge():
    def blocked_403(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, text="Forbidden")

    def cloudflare_html(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            text="<html><title>Attention Required! | Cloudflare</title></html>",
            headers={"Content-Type": "text/html"},
        )

    async def _run():
        async with CheckersScraper(
            min_delay_seconds=0.0,
            transport=httpx.MockTransport(blocked_403),
        ) as s1:
            items_403 = await s1.scrape_catalog(["milk"])

        async with ShopriteScraper(
            min_delay_seconds=0.0,
            transport=httpx.MockTransport(cloudflare_html),
        ) as s2:
            items_cf = await s2.scrape_catalog(["milk"])

        return items_403, items_cf

    items_403, items_cf = asyncio.run(_run())
    assert items_403 == []
    assert items_cf == []
