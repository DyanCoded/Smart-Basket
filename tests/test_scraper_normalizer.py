"""Unit and integration tests for Phase 3 scraper framework, normalizer & publisher."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import httpx
import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from scripts.run_scrapers import CANONICAL_RETAILERS, run_pipeline
from src.models.entities import PriceHistory, Product, StorePrice
from src.scrapers.base import BaseRetailerScraper
from src.scrapers.models import NormalizedPriceRecord, RawScrapedItem
from src.scrapers.normalizer import (
    clean_barcode,
    match_product,
    normalize_scraped_item,
    normalize_unit,
    parse_zar_price,
)
from src.scrapers.publisher import CatalogPublisher, resolve_canonical_store

# ---------------------------------------------------------------------------
# 1. South African Rand (ZAR) Currency Parser
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw_price", "expected_price"),
    [
        ("R 34.99", Decimal("34.99")),
        ("R39.99 / ea", Decimal("39.99")),
        ("ZAR 18.50", Decimal("18.50")),
        ("R1,299.50", Decimal("1299.50")),
        ("R 1 299.50", Decimal("1299.50")),
        ("R34,99", Decimal("34.99")),
        ("R35", Decimal("35.00")),
        ("99c", Decimal("0.99")),
        ("59 c", Decimal("0.59")),
    ],
)
def test_parse_zar_price_standard_formats(raw_price: str, expected_price: Decimal):
    parsed = parse_zar_price(raw_price)
    assert parsed.unit_price == expected_price
    assert parsed.is_promotional is False
    assert parsed.multi_buy_quantity is None
    assert parsed.multi_buy_total is None


@pytest.mark.parametrize(
    ("raw_price", "expected_unit", "expected_qty", "expected_total"),
    [
        ("2 FOR R60", Decimal("30.00"), 2, Decimal("60.00")),
        ("3 for R 100.00", Decimal("33.33"), 3, Decimal("100.00")),
        ("Buy 2 @ R45", Decimal("22.50"), 2, Decimal("45.00")),
        ("2 FOR R109.98", Decimal("54.99"), 2, Decimal("109.98")),
        ("4 for R 1,000.00", Decimal("250.00"), 4, Decimal("1000.00")),
    ],
)
def test_parse_zar_price_multi_buy_promos(
    raw_price: str,
    expected_unit: Decimal,
    expected_qty: int,
    expected_total: Decimal,
):
    parsed = parse_zar_price(raw_price)
    assert parsed.unit_price == expected_unit
    assert parsed.is_promotional is True
    assert parsed.multi_buy_quantity == expected_qty
    assert parsed.multi_buy_total == expected_total


@pytest.mark.parametrize(
    "invalid_price",
    [
        "",
        "   ",
        "R 0.00",
        "0c",
        "-R 15.00",
        "R -12.50",
        "FREE",
        "0 FOR R50",
    ],
)
def test_parse_zar_price_rejects_invalid_values(invalid_price: str):
    with pytest.raises(ValueError):
        parse_zar_price(invalid_price)


# ---------------------------------------------------------------------------
# 2. Unit Standardizer (g / kg / ml / L / unit)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw_unit", "expected_size", "expected_type"),
    [
        ("2 Litre", Decimal("2.00"), "L"),
        ("2000ml", Decimal("2.00"), "L"),
        ("2L", Decimal("2.00"), "L"),
        ("1000 ml", Decimal("1.00"), "L"),
        ("750ml", Decimal("750.00"), "ml"),
        ("0.5L", Decimal("500.00"), "ml"),
        ("2000g", Decimal("2.00"), "kg"),
        ("2.5 kg", Decimal("2.50"), "kg"),
        ("2500 grams", Decimal("2.50"), "kg"),
        ("700g", Decimal("700.00"), "g"),
        ("400gr", Decimal("400.00"), "g"),
        ("0.5kg", Decimal("500.00"), "g"),
        ("6 x 1L", Decimal("6.00"), "L"),
        ("6 x 330ml", Decimal("1.98"), "L"),
        ("12x250g", Decimal("3.00"), "kg"),
        ("18pk", Decimal("18.00"), "unit"),
        ("18 pack", Decimal("18.00"), "unit"),
        ("18's", Decimal("18.00"), "unit"),
        ("2 units", Decimal("2.00"), "unit"),
        ("each", Decimal("1.00"), "unit"),
        ("", Decimal("1.00"), "unit"),
        (None, Decimal("1.00"), "unit"),
    ],
)
def test_normalize_unit_conversions(
    raw_unit: str | None,
    expected_size: Decimal,
    expected_type: str,
):
    size, unit_type = normalize_unit(raw_unit)
    assert size == expected_size
    assert unit_type == expected_type


def test_clean_barcode():
    assert clean_barcode("600-1299-011011") == "6001299011011"
    assert clean_barcode("60012990") == "60012990"
    assert clean_barcode("12345") is None
    assert clean_barcode(None) is None


def test_normalize_scraped_item_promo_and_name_unit_fallback():
    raw = RawScrapedItem(
        retailer_slug="Pick-n-Pay",
        raw_name="  Clover   Full Cream Fresh Milk 2 Litre  ",
        raw_price="R 38.99",
        raw_promo_price="2 FOR R60",
        brand="  Clover ",
        barcode="600-1299-011011",
        raw_unit="each",
    )
    record = normalize_scraped_item(raw)
    assert record.retailer_slug == "pick-n-pay"
    assert record.name == "Clover Full Cream Fresh Milk 2 Litre"
    assert record.brand == "Clover"
    assert record.barcode == "6001299011011"
    assert record.unit_size == Decimal("2.00")
    assert record.unit_type == "L"
    assert record.price == Decimal("30.00")
    assert record.is_promotional is True
    assert record.multi_buy_quantity == 2
    assert record.multi_buy_total == Decimal("60.00")


# ---------------------------------------------------------------------------
# 3. BaseRetailerScraper Lifecycle, Headers & Retry Backoff
# ---------------------------------------------------------------------------


class _DummyHttpScraper(BaseRetailerScraper):
    retailer_slug = "checkers"
    base_url = "https://example.invalid"

    async def scrape_catalog(self, query_terms: list[str]) -> list[RawScrapedItem]:
        response = await self._fetch_with_retry("GET", "/catalog")
        payload = response.json()
        return [
            RawScrapedItem(
                retailer_slug=self.retailer_slug,
                raw_name=item["name"],
                raw_price=item["price"],
            )
            for item in payload["items"]
        ]


class _MissingSlugScraper(BaseRetailerScraper):
    async def scrape_catalog(self, query_terms: list[str]) -> list[RawScrapedItem]:
        return []


def test_base_scraper_requires_retailer_slug():
    with pytest.raises(ValueError, match="retailer_slug"):
        _MissingSlugScraper()


def test_base_scraper_retries_transient_errors_and_closes_client():
    attempts = 0
    captured_headers: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        captured_headers.update(dict(request.headers))
        if attempts == 1:
            return httpx.Response(429, json={"error": "rate limited"})
        if attempts == 2:
            return httpx.Response(503, json={"error": "temporarily unavailable"})
        return httpx.Response(
            200,
            json={"items": [{"name": "Clover Milk 2L", "price": "R 34.99"}]},
        )

    async def _run():
        transport = httpx.MockTransport(handler)
        scraper = _DummyHttpScraper(
            min_delay_seconds=0.0,
            max_retries=3,
            backoff_base_seconds=0.0,
            transport=transport,
        )
        async with scraper:
            items = await scraper.scrape_catalog(["milk"])
            assert scraper._client is not None
            assert not scraper._client.is_closed
        assert scraper._client is None
        return items

    items = asyncio.run(_run())
    assert attempts == 3
    assert len(items) == 1
    assert items[0].raw_price == "R 34.99"
    assert "SmartBasketBot" in captured_headers.get("user-agent", "")
    assert "en-ZA" in captured_headers.get("accept-language", "")


def test_base_scraper_does_not_retry_client_404():
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(404, json={"error": "not found"})

    async def _run():
        scraper = _DummyHttpScraper(
            min_delay_seconds=0.0,
            max_retries=3,
            backoff_base_seconds=0.0,
            transport=httpx.MockTransport(handler),
        )
        async with scraper:
            await scraper.scrape_catalog(["milk"])

    with pytest.raises(httpx.HTTPStatusError):
        asyncio.run(_run())
    assert attempts == 1


# ---------------------------------------------------------------------------
# 4. Product Matcher (EAN First -> Normalized Brand + Name + Unit Fallback)
# ---------------------------------------------------------------------------


def test_match_product_by_barcode_first(db_session: Session):
    record = NormalizedPriceRecord(
        retailer_slug="checkers",
        name="Different Storefront Label For Milk",
        brand="Unknown",
        barcode="6001299011011",
        unit_size=Decimal("2.00"),
        unit_type="L",
        price=Decimal("32.99"),
    )
    matched = match_product(db_session, record)
    assert matched is not None
    assert matched.barcode == "6001299011011"
    assert matched.brand == "Clover"


def test_match_product_fallback_brand_name_unit(db_session: Session):
    # Matches Clover Full Cream Fresh Milk 2L without barcode and with brand in title
    record = NormalizedPriceRecord(
        retailer_slug="shoprite",
        name="Clover Full Cream Fresh Milk 2 Litre",
        brand="Clover",
        barcode=None,
        unit_size=Decimal("2.00"),
        unit_type="L",
        price=Decimal("33.99"),
    )
    matched = match_product(db_session, record)
    assert matched is not None
    assert matched.barcode == "6001299011011"


def test_match_product_fallback_without_explicit_brand(db_session: Session):
    record = NormalizedPriceRecord(
        retailer_slug="spar",
        name="Albany Superior Sliced White Bread 700g",
        brand=None,
        barcode=None,
        unit_size=Decimal("700.00"),
        unit_type="g",
        price=Decimal("18.49"),
    )
    matched = match_product(db_session, record)
    assert matched is not None
    assert matched.brand == "Albany"


def test_match_product_distinguishes_unit_size(db_session: Session):
    record = NormalizedPriceRecord(
        retailer_slug="checkers",
        name="Clover Full Cream Fresh Milk 1L",
        brand="Clover",
        barcode=None,
        unit_size=Decimal("1.00"),
        unit_type="L",
        price=Decimal("21.99"),
    )
    assert match_product(db_session, record) is None


# ---------------------------------------------------------------------------
# 5. Catalog Publisher (Canonical Chain Upsert & PriceHistory Snapshots)
# ---------------------------------------------------------------------------


def test_publisher_upserts_canonical_chain_price_and_appends_history(
    db_session: Session,
):
    store = resolve_canonical_store(db_session, "checkers")
    assert store is not None
    assert store.name == "Checkers"
    assert store.branch_code is None

    initial_product_count = db_session.scalar(select(func.count(Product.id)))
    initial_history_count = db_session.scalar(select(func.count(PriceHistory.id)))

    t1 = datetime.now(timezone.utc)
    record_changed = NormalizedPriceRecord(
        retailer_slug="checkers",
        name="Clover Full Cream Fresh Milk 2 Litre",
        brand="Clover",
        barcode="6001299011011",
        unit_size=Decimal("2.00"),
        unit_type="L",
        price=Decimal("29.99"),
        is_promotional=True,
        scraped_at=t1,
    )

    publisher = CatalogPublisher(db_session)
    summary1 = publisher.publish_records([record_changed], commit=False)

    assert summary1.records_processed == 1
    assert summary1.products_matched == 1
    assert summary1.products_created == 0
    assert summary1.prices_updated == 1
    assert summary1.history_appended == 1
    assert db_session.scalar(select(func.count(Product.id))) == initial_product_count
    assert (
        db_session.scalar(select(func.count(PriceHistory.id)))
        == initial_history_count + 1
    )

    # Verify StorePrice reflects exact Decimal and is_in_stock=True
    product = match_product(db_session, record_changed)
    assert product is not None
    sp = db_session.execute(
        select(StorePrice).where(
            StorePrice.store_id == store.id,
            StorePrice.product_id == product.id,
        )
    ).scalar_one()
    assert Decimal(sp.price) == Decimal("29.99")
    assert sp.is_promotional is True
    assert sp.is_in_stock is True

    # Re-publish identical price -> unchanged, no extra history row
    record_same = record_changed.model_copy(
        update={"scraped_at": t1 + timedelta(hours=1)}
    )
    summary2 = publisher.publish_records([record_same], commit=False)
    assert summary2.prices_unchanged == 1
    assert summary2.prices_updated == 0
    assert summary2.history_appended == 0
    assert (
        db_session.scalar(select(func.count(PriceHistory.id)))
        == initial_history_count + 1
    )

    # Scheduled run with force_history_snapshot=True appends history even if unchanged
    record_scheduled = record_changed.model_copy(
        update={"scraped_at": t1 + timedelta(days=1)}
    )
    summary3 = publisher.publish_records(
        [record_scheduled], force_history_snapshot=True, commit=False
    )
    assert summary3.prices_unchanged == 1
    assert summary3.history_appended == 1
    assert (
        db_session.scalar(select(func.count(PriceHistory.id)))
        == initial_history_count + 2
    )


def test_publisher_creates_new_product_once_across_multiple_chains(
    db_session: Session,
):
    initial_products = db_session.scalar(select(func.count(Product.id)))
    initial_prices = db_session.scalar(select(func.count(StorePrice.id)))
    initial_history = db_session.scalar(select(func.count(PriceHistory.id)))

    records = [
        NormalizedPriceRecord(
            retailer_slug="shoprite",
            name="Koo Baked Beans in Tomato Sauce 410g",
            brand="Koo",
            barcode="6009522300142",
            category_slug="pantry-staples",
            unit_size=Decimal("410.00"),
            unit_type="g",
            price=Decimal("16.99"),
        ),
        NormalizedPriceRecord(
            retailer_slug="pick-n-pay",
            name="Koo Baked Beans in Tomato Sauce 410g",
            brand="Koo",
            barcode="6009522300142",
            category_slug="pantry-staples",
            unit_size=Decimal("410.00"),
            unit_type="g",
            price=Decimal("18.49"),
        ),
    ]

    publisher = CatalogPublisher(db_session)
    summary = publisher.publish_records(records, retailer_slug="all", commit=False)

    assert summary.records_processed == 2
    assert summary.products_created == 1
    assert summary.products_matched == 1
    assert summary.prices_inserted == 2
    assert summary.history_appended == 2
    assert db_session.scalar(select(func.count(Product.id))) == initial_products + 1
    assert db_session.scalar(select(func.count(StorePrice.id))) == initial_prices + 2
    assert db_session.scalar(select(func.count(PriceHistory.id))) == initial_history + 2


def test_publisher_dry_run_makes_zero_database_writes(db_session: Session):
    initial_products = db_session.scalar(select(func.count(Product.id)))
    initial_prices = db_session.scalar(select(func.count(StorePrice.id)))
    initial_history = db_session.scalar(select(func.count(PriceHistory.id)))

    records = [
        NormalizedPriceRecord(
            retailer_slug="shoprite",
            name="Brand New Uncatalogued Pasta 500g",
            brand="Fatti's & Moni's",
            barcode="6001234567890",
            unit_size=Decimal("500.00"),
            unit_type="g",
            price=Decimal("24.99"),
        ),
        NormalizedPriceRecord(
            retailer_slug="unknown-chain",
            name="Skipped Item 1L",
            unit_size=Decimal("1.00"),
            unit_type="L",
            price=Decimal("19.99"),
        ),
    ]

    publisher = CatalogPublisher(db_session)
    summary = publisher.publish_records(records, dry_run=True)

    assert summary.dry_run is True
    assert summary.products_created == 1
    assert summary.prices_inserted == 1
    assert summary.history_appended == 1
    assert summary.skipped == 1
    assert db_session.scalar(select(func.count(Product.id))) == initial_products
    assert db_session.scalar(select(func.count(StorePrice.id))) == initial_prices
    assert db_session.scalar(select(func.count(PriceHistory.id))) == initial_history


def test_cli_pipeline_dry_run_all_five_chains(db_session: Session):
    initial_products = db_session.scalar(select(func.count(Product.id)))
    initial_history = db_session.scalar(select(func.count(PriceHistory.id)))

    summaries = asyncio.run(
        run_pipeline(
            list(CANONICAL_RETAILERS),
            ["milk", "bread", "eggs"],
            dry_run=True,
            session=db_session,
        )
    )

    assert len(summaries) == 5
    assert {s.retailer_slug for s in summaries} == set(CANONICAL_RETAILERS)
    for summary in summaries:
        assert summary.dry_run is True
        assert summary.records_processed == 3
        assert summary.products_matched == 3
        assert summary.products_created == 0
        assert summary.skipped == 0

    assert db_session.scalar(select(func.count(Product.id))) == initial_products
    assert db_session.scalar(select(func.count(PriceHistory.id))) == initial_history
