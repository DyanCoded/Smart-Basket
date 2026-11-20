"""Offline fixture tests for SPAR catalog scraper & 5-chain --retailer all (#23)."""

from __future__ import annotations

import asyncio
import json
from decimal import Decimal
from pathlib import Path

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from scripts.run_scrapers import CANONICAL_RETAILERS, SCRAPER_REGISTRY, run_pipeline
from src.models.entities import PriceHistory, Product, StorePrice
from src.scrapers.base import PlaceholderFixtureScraper
from src.scrapers.normalizer import normalize_scraped_item
from src.scrapers.publisher import resolve_canonical_store
from src.scrapers.retailers.pick_n_pay import PickNPayScraper
from src.scrapers.retailers.shoprite_group import CheckersScraper, ShopriteScraper
from src.scrapers.retailers.spar import (
    SparScraper,
    parse_spar_html,
    parse_spar_json,
)
from src.scrapers.retailers.woolworths import WoolworthsScraper

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "scrapers"


def _load_fixture_text(filename: str) -> str:
    return (FIXTURES_DIR / filename).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 1. Registry & Full 5-Chain Coverage Verification
# ---------------------------------------------------------------------------


def test_spar_and_all_five_national_chains_registered_with_live_adapters():
    assert set(SCRAPER_REGISTRY.keys()) == set(CANONICAL_RETAILERS)

    expected_types = {
        "shoprite": ShopriteScraper,
        "checkers": CheckersScraper,
        "pick-n-pay": PickNPayScraper,
        "woolworths-food": WoolworthsScraper,
        "spar": SparScraper,
    }
    for slug, expected_cls in expected_types.items():
        instance = SCRAPER_REGISTRY[slug]()
        assert isinstance(instance, expected_cls)
        assert not isinstance(instance, PlaceholderFixtureScraper)
        assert instance.retailer_slug == slug

    spar = SCRAPER_REGISTRY["spar"]()
    assert spar.base_url == "https://www.spar.co.za"
    assert len(spar.default_queries) >= 15


# ---------------------------------------------------------------------------
# 2. SPAR JSON Fixture Parsing (Rewards Specials, Multi-Buy & Multipacks)
# ---------------------------------------------------------------------------


def test_spar_json_fixture_extracts_national_pricing_and_specials():
    payload = json.loads(_load_fixture_text("spar_search_staples.json"))
    raw_items = parse_spar_json(payload)

    assert len(raw_items) == 5
    normalized = [normalize_scraped_item(item) for item in raw_items]
    by_name = {rec.name: rec for rec in normalized}

    # 1. SPAR Rewards special overrides regular price R40.49 -> R34.99
    milk = by_name["Clover Full Cream Fresh Milk 2L"]
    assert milk.retailer_slug == "spar"
    assert milk.brand == "Clover"
    assert milk.barcode == "6001299011011"
    assert milk.unit_size == Decimal("2.00")
    assert milk.unit_type == "L"
    assert milk.price == Decimal("34.99")
    assert milk.is_promotional is True
    assert milk.source_url is not None
    assert milk.source_url.startswith("https://www.spar.co.za/")

    # 2. Standard numeric shelf price R18.49
    bread = by_name["Albany Superior Sliced White Bread 700g"]
    assert bread.barcode == "6001299011059"
    assert bread.unit_size == Decimal("700.00")
    assert bread.unit_type == "g"
    assert bread.price == Decimal("18.49")
    assert bread.is_promotional is False

    # 3. Multi-buy promo ("Any 2 for R114.98" -> R57.49 / unit) + "18's" -> 18 unit
    eggs = by_name["Farmer Brown Large Eggs 18's"]
    assert eggs.barcode == "6001299011028"
    assert eggs.unit_size == Decimal("18.00")
    assert eggs.unit_type == "unit"
    assert eggs.price == Decimal("57.49")
    assert eggs.is_promotional is True
    assert eggs.multi_buy_quantity == 2
    assert eggs.multi_buy_total == Decimal("114.98")

    # 4. Discount-only promo ("SPAR Rewards Save R5.00") preserves R46.99 & promo=True
    rice = by_name["Tastic Long Grain Parboiled White Rice 2kg"]
    assert rice.barcode is None
    assert rice.unit_size == Decimal("2.00")
    assert rice.unit_type == "kg"
    assert rice.price == Decimal("46.99")
    assert rice.is_promotional is True

    # 5. Private-label SPAR multipack ("6 x 1L" -> 6.00 L) + internal SKU excluded
    uht = by_name["SPAR Full Cream UHT Milk 6 x 1L"]
    assert uht.brand == "SPAR"
    assert uht.barcode is None
    assert uht.unit_size == Decimal("6.00")
    assert uht.unit_type == "L"
    assert uht.price == Decimal("99.99")
    assert uht.is_promotional is True


# ---------------------------------------------------------------------------
# 3. SPAR HTML Specials Fixture Parsing
# ---------------------------------------------------------------------------


def test_spar_html_fixture_parses_multibuy_and_was_now_specials():
    html_text = _load_fixture_text("spar_search_staples.html")
    raw_items = parse_spar_html(html_text)

    assert len(raw_items) == 2
    normalized = [normalize_scraped_item(item) for item in raw_items]

    # "2 FOR R70" -> R35.00 per unit
    assert normalized[0].barcode == "6001299011011"
    assert normalized[0].unit_size == Decimal("2.00")
    assert normalized[0].unit_type == "L"
    assert normalized[0].price == Decimal("35.00")
    assert normalized[0].is_promotional is True
    assert normalized[0].multi_buy_quantity == 2

    # price-was R19.49 -> price-now R17.49
    assert normalized[1].barcode == "6001299011059"
    assert normalized[1].unit_size == Decimal("700.00")
    assert normalized[1].unit_type == "g"
    assert normalized[1].price == Decimal("17.49")
    assert normalized[1].is_promotional is True


# ---------------------------------------------------------------------------
# 4. End-to-End 5-Chain (--retailer all) Offline Pipeline Integration
# ---------------------------------------------------------------------------


def test_all_five_national_chains_offline_pipeline_end_to_end(db_session: Session):
    fixture_responses = {
        "checkers": (
            _load_fixture_text("checkers_search_staples.html"),
            "text/html; charset=utf-8",
        ),
        "shoprite": (
            _load_fixture_text("shoprite_search_staples.json"),
            "application/json",
        ),
        "pick-n-pay": (
            _load_fixture_text("pnp_search_staples.json"),
            "application/json",
        ),
        "woolworths-food": (
            _load_fixture_text("woolworths_search_staples.json"),
            "application/json",
        ),
        "spar": (
            _load_fixture_text("spar_search_staples.json"),
            "application/json",
        ),
    }

    def _make_transport(slug: str) -> httpx.MockTransport:
        body, content_type = fixture_responses[slug]
        return httpx.MockTransport(
            lambda req: httpx.Response(
                200, text=body, headers={"Content-Type": content_type}
            )
        )

    offline_all_five = {
        "shoprite": lambda: ShopriteScraper(
            min_delay_seconds=0.0, transport=_make_transport("shoprite")
        ),
        "checkers": lambda: CheckersScraper(
            min_delay_seconds=0.0, transport=_make_transport("checkers")
        ),
        "pick-n-pay": lambda: PickNPayScraper(
            min_delay_seconds=0.0, transport=_make_transport("pick-n-pay")
        ),
        "woolworths-food": lambda: WoolworthsScraper(
            min_delay_seconds=0.0, transport=_make_transport("woolworths-food")
        ),
        "spar": lambda: SparScraper(
            min_delay_seconds=0.0, transport=_make_transport("spar")
        ),
    }

    initial_history = db_session.scalar(select(func.count(PriceHistory.id)))

    summaries = asyncio.run(
        run_pipeline(
            list(CANONICAL_RETAILERS),
            ["milk", "bread"],
            dry_run=False,
            session=db_session,
            scraper_registry=offline_all_five,
        )
    )

    assert len(summaries) == 5
    by_slug = {s.retailer_slug: s for s in summaries}
    assert set(by_slug.keys()) == set(CANONICAL_RETAILERS)
    for summary in summaries:
        assert summary.records_processed >= 5
        assert summary.skipped == 0

    # Verify Clover Full Cream Fresh Milk 2L has updated prices across all 5 chains
    milk = db_session.execute(
        select(Product).where(Product.barcode == "6001299011011")
    ).scalar_one()

    expected_milk_prices = {
        "checkers": Decimal("31.99"),
        "shoprite": Decimal("33.99"),
        "pick-n-pay": Decimal("32.99"),
        "woolworths-food": Decimal("38.00"),
        "spar": Decimal("34.99"),
    }
    for slug, expected_price in expected_milk_prices.items():
        store = resolve_canonical_store(db_session, slug)
        assert store is not None
        sp = db_session.execute(
            select(StorePrice).where(
                StorePrice.store_id == store.id,
                StorePrice.product_id == milk.id,
            )
        ).scalar_one()
        assert Decimal(sp.price) == expected_price

    # SPAR matched Tastic Rice 2kg without barcode and created only 1 SPAR UHT item
    assert by_slug["spar"].products_matched == 4
    assert by_slug["spar"].products_created == 1
    assert db_session.scalar(select(func.count(PriceHistory.id))) > initial_history


# ---------------------------------------------------------------------------
# 5. Respectful Anti-Bot / Access Control Handling
# ---------------------------------------------------------------------------


def test_spar_scraper_halts_gracefully_on_403_or_cloudflare_challenge():
    def blocked_403(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, text="Forbidden")

    def cf_challenge(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            text="<html><title>Attention Required! | Cloudflare</title></html>",
            headers={"Content-Type": "text/html"},
        )

    async def _run():
        async with SparScraper(
            min_delay_seconds=0.0,
            transport=httpx.MockTransport(blocked_403),
        ) as s1:
            items_403 = await s1.scrape_catalog(["milk"])

        async with SparScraper(
            min_delay_seconds=0.0,
            transport=httpx.MockTransport(cf_challenge),
        ) as s2:
            items_cf = await s2.scrape_catalog(["milk"])

        return items_403, items_cf

    items_403, items_cf = asyncio.run(_run())
    assert items_403 == []
    assert items_cf == []
