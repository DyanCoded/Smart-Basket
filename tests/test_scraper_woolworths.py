"""Offline fixture-based tests for Woolworths Food catalog scraper (#22)."""

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
from src.scrapers.normalizer import match_product, normalize_scraped_item
from src.scrapers.publisher import resolve_canonical_store
from src.scrapers.retailers.woolworths import (
    WoolworthsScraper,
    parse_woolworths_html,
    parse_woolworths_json,
)

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "scrapers"


def _load_fixture_text(filename: str) -> str:
    return (FIXTURES_DIR / filename).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 1. Registry Verification
# ---------------------------------------------------------------------------


def test_woolworths_registered_in_cli_registry():
    scraper = SCRAPER_REGISTRY["woolworths-food"]()
    assert isinstance(scraper, WoolworthsScraper)
    assert scraper.retailer_slug == "woolworths-food"
    assert scraper.base_url == "https://www.woolworths.co.za"
    assert len(scraper.default_queries) >= 15


# ---------------------------------------------------------------------------
# 2. Endeca / ATG JSON Fixture Parsing, Spaced Units & Promo Tags
# ---------------------------------------------------------------------------


def test_woolworths_json_fixture_normalizes_spaced_units_and_promos():
    payload = json.loads(_load_fixture_text("woolworths_search_staples.json"))
    raw_items = parse_woolworths_json(payload)

    assert len(raw_items) == 6
    normalized = [normalize_scraped_item(item) for item in raw_items]
    by_name = {rec.name: rec for rec in normalized}

    # 1. Clover Milk 2 L + "Any 2 for R76.00" -> R38.00 / unit
    milk = by_name["Clover Full Cream Fresh Milk 2 L"]
    assert milk.retailer_slug == "woolworths-food"
    assert milk.brand == "Clover"
    assert milk.barcode == "6001299011011"
    assert milk.unit_size == Decimal("2.00")
    assert milk.unit_type == "L"
    assert milk.price == Decimal("38.00")
    assert milk.is_promotional is True
    assert milk.multi_buy_quantity == 2
    assert milk.multi_buy_total == Decimal("76.00")
    assert milk.source_url is not None
    assert milk.source_url.startswith("https://www.woolworths.co.za/")

    # 2. Albany Bread 700 g + 13-digit EAN-13 SKU fallback
    bread = by_name["Albany Superior Sliced White Bread 700 g"]
    assert bread.barcode == "6001299011059"
    assert bread.unit_size == Decimal("700.00")
    assert bread.unit_type == "g"
    assert bread.price == Decimal("19.99")
    assert bread.is_promotional is False

    # 3. Tastic Rice 2 kg + "WRewards: R44.99" + 9-digit internal SKU excluded
    rice = by_name["Tastic Long Grain Parboiled White Rice 2 kg"]
    assert rice.barcode is None
    assert rice.unit_size == Decimal("2.00")
    assert rice.unit_type == "kg"
    assert rice.price == Decimal("44.99")
    assert rice.is_promotional is True

    # 4. Nescafe 200 g + "WRewards Save 20%" keeps shelf price R109.99 & promo=True
    coffee = by_name["Nescafé Instant Coffee Classic Jar 200 g"]
    assert coffee.barcode is None
    assert coffee.unit_size == Decimal("200.00")
    assert coffee.unit_type == "g"
    assert coffee.price == Decimal("109.99")
    assert coffee.is_promotional is True

    # 5. Lurpak 500 g + listPrice / salePrice
    butter = by_name["Lurpak Salted Butter 500 g"]
    assert butter.barcode == "6001299011035"
    assert butter.unit_size == Decimal("500.00")
    assert butter.unit_type == "g"
    assert butter.price == Decimal("79.99")
    assert butter.is_promotional is True

    # 6. Private-label Woolworths brand auto-inference + 9-digit SKU excluded
    ww_milk = by_name["Woolworths Organic Free Range Milk 1 L"]
    assert ww_milk.brand == "Woolworths"
    assert ww_milk.barcode is None
    assert ww_milk.unit_size == Decimal("1.00")
    assert ww_milk.unit_type == "L"
    assert ww_milk.price == Decimal("28.99")


# ---------------------------------------------------------------------------
# 3. Shared Branded Staples Matching (Clover, Albany, Tastic, Nescafe, Lurpak)
# ---------------------------------------------------------------------------


def test_woolworths_matches_shared_branded_staples_to_canonical_products(
    db_session: Session,
):
    payload = json.loads(_load_fixture_text("woolworths_search_staples.json"))
    normalized = [normalize_scraped_item(i) for i in parse_woolworths_json(payload)]
    by_name = {rec.name: rec for rec in normalized}

    # Matches by EAN
    assert match_product(db_session, by_name["Clover Full Cream Fresh Milk 2 L"])
    assert match_product(
        db_session, by_name["Albany Superior Sliced White Bread 700 g"]
    )
    assert match_product(db_session, by_name["Lurpak Salted Butter 500 g"])

    # Matches by brand + name + unit without barcode (including diacritic folding)
    matched_rice = match_product(
        db_session, by_name["Tastic Long Grain Parboiled White Rice 2 kg"]
    )
    assert matched_rice is not None
    assert matched_rice.barcode == "6001299011080"

    matched_coffee = match_product(
        db_session, by_name["Nescafé Instant Coffee Classic Jar 200 g"]
    )
    assert matched_coffee is not None
    assert matched_coffee.barcode == "6001299011103"

    # Private-label Woolworths Organic Milk 1 L does NOT falsely match Clover 2L
    assert (
        match_product(db_session, by_name["Woolworths Organic Free Range Milk 1 L"])
        is None
    )


# ---------------------------------------------------------------------------
# 4. Storefront HTML Fixture Parsing
# ---------------------------------------------------------------------------


def test_woolworths_html_fixture_parses_multibuy_and_was_now_prices():
    html_text = _load_fixture_text("woolworths_search_staples.html")
    raw_items = parse_woolworths_html(html_text)

    assert len(raw_items) == 2
    normalized = [normalize_scraped_item(item) for item in raw_items]

    # "Buy 2 for R75" -> R37.50 per unit
    assert normalized[0].unit_size == Decimal("2.00")
    assert normalized[0].unit_type == "L"
    assert normalized[0].price == Decimal("37.50")
    assert normalized[0].is_promotional is True
    assert normalized[0].multi_buy_quantity == 2

    # was R89.99 / now R79.99
    assert normalized[1].unit_size == Decimal("500.00")
    assert normalized[1].unit_type == "g"
    assert normalized[1].price == Decimal("79.99")
    assert normalized[1].is_promotional is True


# ---------------------------------------------------------------------------
# 5. End-to-End Offline Pipeline Integration (MockTransport -> Publisher)
# ---------------------------------------------------------------------------


def test_woolworths_end_to_end_offline_pipeline_publishes_canonical_prices(
    db_session: Session,
):
    ww_json = _load_fixture_text("woolworths_search_staples.json")
    captured_urls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_urls.append(str(request.url))
        return httpx.Response(
            200,
            text=ww_json,
            headers={"Content-Type": "application/json"},
        )

    offline_registry = {
        "woolworths-food": lambda: WoolworthsScraper(
            min_delay_seconds=0.0,
            transport=httpx.MockTransport(handler),
        )
    }

    initial_products = db_session.scalar(select(func.count(Product.id)))
    initial_history = db_session.scalar(select(func.count(PriceHistory.id)))

    summaries = asyncio.run(
        run_pipeline(
            ["woolworths-food"],
            ["milk", "coffee"],
            dry_run=False,
            session=db_session,
            scraper_registry=offline_registry,
        )
    )

    assert len(summaries) == 1
    summary = summaries[0]
    assert summary.retailer_slug == "woolworths-food"
    assert summary.records_processed == 6
    assert summary.products_matched == 5
    assert summary.products_created == 1
    assert summary.skipped == 0

    # Only the 1 private-label Woolworths item created a new product row
    assert db_session.scalar(select(func.count(Product.id))) == initial_products + 1
    assert db_session.scalar(select(func.count(PriceHistory.id))) > initial_history

    ww_store = resolve_canonical_store(db_session, "woolworths-food")
    assert ww_store is not None
    assert ww_store.name == "Woolworths Food"

    # Clover Milk 2L reflects multi-buy unit price R38.00
    milk_product = db_session.execute(
        select(Product).where(Product.barcode == "6001299011011")
    ).scalar_one()
    ww_milk_price = db_session.execute(
        select(StorePrice).where(
            StorePrice.store_id == ww_store.id,
            StorePrice.product_id == milk_product.id,
        )
    ).scalar_one()
    assert Decimal(ww_milk_price.price) == Decimal("38.00")
    assert ww_milk_price.is_promotional is True

    # Tastic Rice 2kg matched without barcode and updated to WRewards R44.99
    rice_product = db_session.execute(
        select(Product).where(Product.barcode == "6001299011080")
    ).scalar_one()
    ww_rice_price = db_session.execute(
        select(StorePrice).where(
            StorePrice.store_id == ww_store.id,
            StorePrice.product_id == rice_product.id,
        )
    ).scalar_one()
    assert Decimal(ww_rice_price.price) == Decimal("44.99")
    assert ww_rice_price.is_promotional is True
    assert any("format=json" in url for url in captured_urls)


# ---------------------------------------------------------------------------
# 6. Respectful Anti-Bot / Access Control Handling
# ---------------------------------------------------------------------------


def test_woolworths_scraper_halts_gracefully_on_403_or_akamai_block():
    def blocked_403(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, text="Forbidden")

    def akamai_block(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            text=(
                "<html><title>Access Denied</title>"
                "<body>Akamai Reference</body></html>"
            ),
            headers={"Content-Type": "text/html"},
        )

    async def _run():
        async with WoolworthsScraper(
            min_delay_seconds=0.0,
            transport=httpx.MockTransport(blocked_403),
        ) as s1:
            items_403 = await s1.scrape_catalog(["milk"])

        async with WoolworthsScraper(
            min_delay_seconds=0.0,
            transport=httpx.MockTransport(akamai_block),
        ) as s2:
            items_waf = await s2.scrape_catalog(["milk"])

        return items_403, items_waf

    items_403, items_waf = asyncio.run(_run())
    assert items_403 == []
    assert items_waf == []
