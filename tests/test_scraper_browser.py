"""Unit tests for Issue #30: Playwright headless-browser adapter & dual-engine scrapers.

All tests run 100% offline without launching a real Chromium browser.
"""

from __future__ import annotations

import json
import logging
import sys
import types
from pathlib import Path
from typing import Any, Optional, Sequence

import httpx
import pytest

from scripts.run_scrapers import build_live_registry, build_parser
from src.scrapers.browser import (
    DEFAULT_LOCALE,
    DEFAULT_SA_DESKTOP_USER_AGENT,
    DEFAULT_SA_MOBILE_USER_AGENT,
    DEFAULT_TIMEZONE,
    PlaywrightFetcher,
    PlaywrightPageResult,
    PlaywrightUnavailableError,
    is_hard_block_response,
)
from src.scrapers.normalizer import normalize_scraped_item
from src.scrapers.retailers import (
    CheckersScraper,
    PickNPayScraper,
    ShopriteScraper,
    SparScraper,
    WoolworthsScraper,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "scrapers"


class _FakePlaywrightFetcher(PlaywrightFetcher):
    """In-memory PlaywrightFetcher test double returning preconfigured page results."""

    def __init__(
        self,
        result: Optional[PlaywrightPageResult] = None,
        *,
        error: Optional[Exception] = None,
    ) -> None:
        super().__init__(headless=True)
        self._result = result
        self._error = error
        self.calls: list[dict[str, Any]] = []
        self.closed = False

    async def start(self) -> None:
        return None

    async def close(self) -> None:
        self.closed = True

    async def fetch_page(
        self,
        url: str,
        *,
        wait_selector: Optional[str] = None,
        json_url_patterns: Optional[Sequence[str]] = None,
    ) -> PlaywrightPageResult:
        self.calls.append(
            {
                "url": url,
                "wait_selector": wait_selector,
                "json_url_patterns": list(json_url_patterns or ()),
            }
        )
        if self._error is not None:
            raise self._error
        assert self._result is not None
        return self._result


# ---------------------------------------------------------------------------
# 1. PlaywrightFetcher configuration & hard-block detection
# ---------------------------------------------------------------------------


def test_playwright_fetcher_defaults_south_african_desktop() -> None:
    fetcher = PlaywrightFetcher()
    assert fetcher.headless is True
    assert fetcher.mobile is False
    assert fetcher.locale == DEFAULT_LOCALE == "en-ZA"
    assert fetcher.timezone_id == DEFAULT_TIMEZONE == "Africa/Johannesburg"
    assert fetcher.user_agent == DEFAULT_SA_DESKTOP_USER_AGENT
    assert fetcher.viewport == {"width": 1366, "height": 900}


def test_playwright_fetcher_mobile_and_headed_configuration() -> None:
    fetcher = PlaywrightFetcher(
        headless=False,
        mobile=True,
        navigation_timeout_ms=100,
        network_idle_timeout_ms=50,
    )
    assert fetcher.headless is False
    assert fetcher.mobile is True
    assert fetcher.user_agent == DEFAULT_SA_MOBILE_USER_AGENT
    assert fetcher.viewport == {"width": 390, "height": 844}
    assert fetcher.navigation_timeout_ms == 1000
    assert fetcher.network_idle_timeout_ms == 500


@pytest.mark.parametrize(
    ("status_code", "html", "expected_blocked"),
    [
        (403, "<html><body>Forbidden</body></html>", True),
        (451, "<html><body>Unavailable</body></html>", True),
        (200, "<html><title>Attention Required! | Cloudflare</title></html>", True),
        (200, '<div class="cf-turnstile">Verify you are human</div>', True),
        (200, '<div class="g-recaptcha" data-sitekey="abc"></div>', True),
        (200, '<script src="/_Incapsula_Resource?SWJIYLWA=1"></script>', True),
        (
            200,
            "<html><body><div class='product'>Clover Milk 2L R34.99</div></body>",
            False,
        ),
    ],
)
def test_is_hard_block_response(
    status_code: int, html: str, expected_blocked: bool
) -> None:
    blocked, reason = is_hard_block_response(status_code, html)
    assert blocked is expected_blocked
    if expected_blocked:
        assert reason is not None
    else:
        assert reason is None


# ---------------------------------------------------------------------------
# 2. Missing Playwright / missing Chromium fallback handling
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_playwright_fetcher_raises_helpful_error_when_package_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(sys.modules, "playwright", None)
    monkeypatch.setitem(sys.modules, "playwright.async_api", None)

    fetcher = PlaywrightFetcher()
    with pytest.raises(PlaywrightUnavailableError) as exc_info:
        await fetcher.start()

    assert "playwright install chromium" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_playwright_fetcher_raises_helpful_error_when_chromium_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _FakeChromium:
        async def launch(self, headless: bool = True) -> Any:
            raise RuntimeError("Executable doesn't exist at /ms-playwright/chromium")

    class _FakePlaywright:
        chromium = _FakeChromium()

        async def stop(self) -> None:
            return None

    class _FakeCM:
        async def start(self) -> _FakePlaywright:
            return _FakePlaywright()

    fake_pkg = types.ModuleType("playwright")
    fake_async_api = types.ModuleType("playwright.async_api")
    fake_async_api.async_playwright = lambda: _FakeCM()  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "playwright", fake_pkg)
    monkeypatch.setitem(sys.modules, "playwright.async_api", fake_async_api)

    fetcher = PlaywrightFetcher()
    with pytest.raises(PlaywrightUnavailableError) as exc_info:
        await fetcher.start()

    assert "playwright install chromium" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_playwright_fetcher_fetch_page_intercepts_json_and_reads_dom() -> None:
    class _FakeResponse:
        def __init__(
            self,
            url: str,
            status: int,
            content_type: str,
            payload: Any = None,
        ) -> None:
            self.url = url
            self.status = status
            self.headers = {"content-type": content_type}
            self._payload = payload

        async def json(self) -> Any:
            return self._payload

    class _FakePage:
        def __init__(self) -> None:
            self.url = "https://www.pnp.co.za/search/milk"
            self.closed = False
            self._listeners: dict[str, Any] = {}

        def on(self, event: str, handler: Any) -> None:
            self._listeners[event] = handler

        async def goto(self, url: str, **kwargs: Any) -> _FakeResponse:
            self.url = url
            handler = self._listeners.get("response")
            if handler is not None:
                # Matching JSON response -> captured
                await handler(
                    _FakeResponse(
                        "https://www.pnp.co.za/pnphybris/v2/pnp-spa/products/search?q=milk",
                        200,
                        "application/json; charset=utf-8",
                        {"products": [{"name": "Clover Milk 2L"}]},
                    )
                )
                # Non-matching URL -> ignored
                await handler(
                    _FakeResponse(
                        "https://www.pnp.co.za/analytics/config",
                        200,
                        "application/json",
                        {"ignored": True},
                    )
                )
                # Non-JSON -> ignored
                await handler(
                    _FakeResponse(
                        "https://www.pnp.co.za/products/search",
                        200,
                        "text/html",
                        None,
                    )
                )
            return _FakeResponse(url, 200, "text/html")

        async def wait_for_selector(self, selector: str, timeout: int = 5000) -> None:
            return None

        async def wait_for_load_state(self, state: str, timeout: int = 5000) -> None:
            return None

        async def content(self) -> str:
            return "<html><body><div>Clover Milk 2L</div></body></html>"

        async def close(self) -> None:
            self.closed = True

    fake_page = _FakePage()

    class _FakeContext:
        async def new_page(self) -> _FakePage:
            return fake_page

        async def close(self) -> None:
            return None

    fetcher = PlaywrightFetcher()
    fetcher._context = _FakeContext()

    result = await fetcher.fetch_page(
        "https://www.pnp.co.za/search/milk",
        wait_selector="div",
        json_url_patterns=("/products/search",),
    )

    assert result.blocked is False
    assert result.status_code == 200
    assert "Clover Milk 2L" in result.html
    assert len(result.intercepted_json) == 1
    assert result.intercepted_json[0][1] == {"products": [{"name": "Clover Milk 2L"}]}
    assert fake_page.closed is True


# ---------------------------------------------------------------------------
# 3. Dual-engine defaults & live storefront URLs across all 5 retailers
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("scraper_cls", "expected_url"),
    [
        (PickNPayScraper, "https://www.pnp.co.za/search/full%20cream%20milk"),
        (
            WoolworthsScraper,
            "https://www.woolworths.co.za/browse?searchterm=full+cream+milk",
        ),
        (SparScraper, "https://www.spar.co.za/?q=full+cream+milk"),
        (
            CheckersScraper,
            "https://www.checkers.co.za/search?Search=full+cream+milk",
        ),
        (
            ShopriteScraper,
            "https://www.shoprite.co.za/search?Search=full+cream+milk",
        ),
    ],
)
def test_retailer_defaults_to_playwright_and_builds_live_urls(
    scraper_cls: type[Any], expected_url: str
) -> None:
    live_scraper = scraper_cls()
    assert live_scraper.engine == "playwright"
    assert live_scraper.build_storefront_search_url("full cream milk") == expected_url

    mock_transport = httpx.MockTransport(lambda req: httpx.Response(200, text=""))
    offline_scraper = scraper_cls(transport=mock_transport)
    assert offline_scraper.engine == "http"

    explicit_http = scraper_cls(engine="http")
    assert explicit_http.engine == "http"


# ---------------------------------------------------------------------------
# 4. Playwright engine end-to-end extraction (JSON interception & DOM HTML)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pick_n_pay_playwright_uses_intercepted_json() -> None:
    payload = json.loads(
        (FIXTURES_DIR / "pnp_search_staples.json").read_text(encoding="utf-8")
    )
    fetcher = _FakePlaywrightFetcher(
        PlaywrightPageResult(
            url="https://www.pnp.co.za/search/milk",
            status_code=200,
            html="<html><body></body></html>",
            intercepted_json=[
                (
                    "https://www.pnp.co.za/pnphybris/v2/pnp-spa/products/search?q=milk",
                    payload,
                )
            ],
        )
    )
    async with PickNPayScraper(
        engine="playwright",
        min_delay_seconds=0.0,
        browser_fetcher=fetcher,
    ) as scraper:
        items = await scraper.scrape_catalog(["milk"])

    assert len(items) == 5
    assert fetcher.calls[0]["url"] == "https://www.pnp.co.za/search/milk"
    normalized = [normalize_scraped_item(i) for i in items]
    assert all(rec.retailer_slug == "pick-n-pay" for rec in normalized)


@pytest.mark.asyncio
async def test_checkers_and_shoprite_playwright_parse_rendered_dom() -> None:
    checkers_html = (FIXTURES_DIR / "checkers_search_staples.html").read_text(
        encoding="utf-8"
    )
    fetcher = _FakePlaywrightFetcher(
        PlaywrightPageResult(
            url="https://www.checkers.co.za/search/all?q=milk",
            status_code=200,
            html=checkers_html,
            intercepted_json=[],
        )
    )
    async with CheckersScraper(
        engine="playwright",
        min_delay_seconds=0.0,
        browser_fetcher=fetcher,
    ) as scraper:
        items = await scraper.scrape_catalog(["milk"])

    assert len(items) >= 3
    assert fetcher.calls[0]["url"] == "https://www.checkers.co.za/search?Search=milk"

    shoprite_html = (FIXTURES_DIR / "shoprite_search_staples.html").read_text(
        encoding="utf-8"
    )
    sr_fetcher = _FakePlaywrightFetcher(
        PlaywrightPageResult(
            url="https://www.shoprite.co.za/search?Search=bread",
            status_code=200,
            html=shoprite_html,
            intercepted_json=[],
        )
    )
    async with ShopriteScraper(
        engine="playwright",
        min_delay_seconds=0.0,
        browser_fetcher=sr_fetcher,
    ) as scraper:
        sr_items = await scraper.scrape_catalog(["bread"])

    assert len(sr_items) >= 2
    assert (
        sr_fetcher.calls[0]["url"] == "https://www.shoprite.co.za/search?Search=bread"
    )


@pytest.mark.asyncio
async def test_sixty60_and_woolworths_cnstrc_live_json_formats() -> None:
    """Verify live Sixty60 get-products-filter and Woolworths Constructor.io schemas."""
    sixty60_payload = {
        "totalCount": 2,
        "products": [
            {
                "id": "5d3af672f434cf84207388ca",
                "name": "Clover Full Cream Milk 2L",
                "displayName": "Clover Full Cream Milk 2L",
                "unitOfMeasure": "EA",
                "priceFactor": 100,
                "priceWithoutDecimal": 3499,
                "oldPrice": 3999,
                "price": 39.99,
                "discountedPrice": 34.99,
                "isOnPromotion": True,
                "brand": "Clover",
                "barcodes": ["6001299015274"],
                "displayCategories": ["Milk, Dairy & Eggs", "Milk"],
            },
            {
                "id": "5d3af63cf434cf8420737e3e",
                "name": "Checkers Housebrand Full Cream Milk 6 x 1L",
                "displayName": "Checkers Housebrand Full Cream Milk 6 x 1L",
                "unitOfMeasure": "PK1",
                "priceFactor": 100,
                "priceWithoutDecimal": 9799,
                "oldPrice": 9799,
                "isOnPromotion": False,
                "brand": "Checkers Housebrand",
                "barcodes": ["6001001271059"],
                "displayCategories": ["Food Cupboard", "Long Life Milk"],
            },
        ],
    }
    checkers_fetcher = _FakePlaywrightFetcher(
        PlaywrightPageResult(
            url="https://www.checkers.co.za/search?Search=milk",
            status_code=200,
            html="<html></html>",
            intercepted_json=[
                (
                    "https://www.checkers.co.za/api/catalogue/get-products-filter",
                    sixty60_payload,
                )
            ],
        )
    )
    async with CheckersScraper(
        engine="playwright",
        min_delay_seconds=0.0,
        browser_fetcher=checkers_fetcher,
    ) as scraper:
        c_items = await scraper.scrape_catalog(["milk"])

    assert len(c_items) == 2
    assert c_items[0].raw_price == "R 39.99"
    assert c_items[0].raw_promo_price == "R 34.99"
    norm_0 = normalize_scraped_item(c_items[0])
    assert norm_0.barcode == "6001299015274"
    assert str(norm_0.price) == "34.99"
    assert norm_0.is_promotional is True
    assert norm_0.unit_type == "L"
    assert str(norm_0.unit_size) == "2.00"
    norm_1 = normalize_scraped_item(c_items[1])
    assert norm_1.unit_type == "L"
    assert str(norm_1.unit_size) == "6.00"

    cnstrc_payload = {
        "response": {
            "results": [
                {
                    "value": "Fresh Full Cream Ayrshire Milk 2 L",
                    "data": {
                        "id": "6001009001733",
                        "brand": "Woolies Brands",
                        "p10": 42.99,
                        "p10_wp": 45.99,
                        "prodtype": "Food",
                        "subtype": "foods",
                        "badges": {"SAVE": "/images/save.png"},
                        "url": (
                            "prod/Food/Milk-Dairy-Eggs/Milk/"
                            "Ayrshire-2-L/_/A-6001009001733"
                        ),
                    },
                },
                {
                    "value": "Milk White Cotton T-Shirt",
                    "data": {
                        "id": "99999999",
                        "brand": "RE:",
                        "p10": 199.00,
                        "p10_wp": 0,
                        "prodtype": "Clothing",
                        "subtype": "apparel",
                        "url": "prod/Clothing/T-Shirts/Milk-Tee",
                    },
                },
            ]
        }
    }
    ww_fetcher = _FakePlaywrightFetcher(
        PlaywrightPageResult(
            url="https://www.woolworths.co.za/browse?searchterm=milk",
            status_code=200,
            html="<html></html>",
            intercepted_json=[
                ("https://wpkmgeuco-zone.cnstrc.com/v1/search/milk", cnstrc_payload)
            ],
        )
    )
    async with WoolworthsScraper(
        engine="playwright",
        min_delay_seconds=0.0,
        browser_fetcher=ww_fetcher,
    ) as scraper:
        ww_items = await scraper.scrape_catalog(["milk"])

    # Clothing result filtered out; Food result parsed with ZA p10/p10_wp prices
    assert len(ww_items) == 1
    assert ww_items[0].raw_price == "R 45.99"
    assert ww_items[0].raw_promo_price == "R 42.99"
    ww_norm = normalize_scraped_item(ww_items[0])
    assert ww_norm.brand == "Woolworths"
    assert ww_norm.barcode == "6001009001733"
    assert str(ww_norm.price) == "42.99"
    assert ww_norm.is_promotional is True
    assert ww_norm.unit_type == "L"
    assert str(ww_norm.unit_size) == "2.00"


@pytest.mark.asyncio
async def test_woolworths_and_spar_playwright_parse_json_and_dom() -> None:
    ww_payload = json.loads(
        (FIXTURES_DIR / "woolworths_search_staples.json").read_text(encoding="utf-8")
    )
    ww_fetcher = _FakePlaywrightFetcher(
        PlaywrightPageResult(
            url="https://www.woolworths.co.za/cat?Ntt=milk",
            status_code=200,
            html="<html></html>",
            intercepted_json=[
                (
                    "https://www.woolworths.co.za/server/searchCategory?Ntt=milk",
                    ww_payload,
                )
            ],
        )
    )
    async with WoolworthsScraper(
        engine="playwright",
        min_delay_seconds=0.0,
        browser_fetcher=ww_fetcher,
    ) as scraper:
        ww_items = await scraper.scrape_catalog(["milk"])

    assert len(ww_items) >= 3
    assert (
        ww_fetcher.calls[0]["url"]
        == "https://www.woolworths.co.za/browse?searchterm=milk"
    )

    spar_html = (FIXTURES_DIR / "spar_search_staples.html").read_text(encoding="utf-8")
    spar_fetcher = _FakePlaywrightFetcher(
        PlaywrightPageResult(
            url="https://www.spar.co.za/?q=milk",
            status_code=200,
            html=spar_html,
            intercepted_json=[],
        )
    )
    async with SparScraper(
        engine="playwright",
        min_delay_seconds=0.0,
        browser_fetcher=spar_fetcher,
    ) as scraper:
        spar_items = await scraper.scrape_catalog(["milk"])

    assert len(spar_items) == 2
    assert spar_fetcher.calls[0]["url"] == "https://www.spar.co.za/?q=milk"


@pytest.mark.asyncio
async def test_playwright_hard_block_halts_gracefully_with_warning(
    caplog: pytest.LogCaptureFixture,
) -> None:
    blocked_fetcher = _FakePlaywrightFetcher(
        PlaywrightPageResult(
            url="https://www.pnp.co.za/search/milk",
            status_code=403,
            html="<html>Access Denied</html>",
            blocked=True,
            block_reason="HTTP 403 access control block",
        )
    )
    with caplog.at_level(logging.WARNING):
        async with PickNPayScraper(
            engine="playwright",
            min_delay_seconds=0.0,
            browser_fetcher=blocked_fetcher,
        ) as scraper:
            items = await scraper.scrape_catalog(["milk"])

    assert items == []
    assert any("halting respectfully" in rec.message.lower() for rec in caplog.records)


@pytest.mark.asyncio
async def test_playwright_unavailable_error_halts_gracefully(
    caplog: pytest.LogCaptureFixture,
) -> None:
    missing_fetcher = _FakePlaywrightFetcher(
        error=PlaywrightUnavailableError("Run: playwright install chromium")
    )
    with caplog.at_level(logging.WARNING):
        async with CheckersScraper(
            engine="playwright",
            min_delay_seconds=0.0,
            browser_fetcher=missing_fetcher,
        ) as scraper:
            items = await scraper.scrape_catalog(["milk"])

    assert items == []
    assert any(
        "playwright install chromium" in rec.message.lower() for rec in caplog.records
    )


@pytest.mark.asyncio
async def test_spar_playwright_logs_spar2u_notice_when_empty(
    caplog: pytest.LogCaptureFixture,
) -> None:
    empty_fetcher = _FakePlaywrightFetcher(
        PlaywrightPageResult(
            url="https://www.spar.co.za/?q=milk",
            status_code=200,
            html="<html><body>SPAR Corporate Home</body></html>",
            intercepted_json=[],
        )
    )
    with caplog.at_level(logging.WARNING):
        async with SparScraper(
            engine="playwright",
            min_delay_seconds=0.0,
            browser_fetcher=empty_fetcher,
        ) as scraper:
            items = await scraper.scrape_catalog(["milk"])

    assert items == []
    assert any("spar2u" in rec.message.lower() for rec in caplog.records)


# ---------------------------------------------------------------------------
# 5. CLI --engine & --headed flags
# ---------------------------------------------------------------------------


def test_cli_parser_engine_and_headed_flags() -> None:
    parser = build_parser()

    defaults = parser.parse_args([])
    assert defaults.engine == "playwright"
    assert defaults.headed is False

    custom = parser.parse_args(
        ["--retailer", "checkers", "--engine", "http", "--headed", "--dry-run"]
    )
    assert custom.retailer == "checkers"
    assert custom.engine == "http"
    assert custom.headed is True
    assert custom.dry_run is True


def test_build_live_registry_propagates_engine_and_headed() -> None:
    registry = build_live_registry(
        ["checkers", "pick-n-pay", "spar"],
        engine="http",
        headed=True,
    )
    assert set(registry.keys()) == {"checkers", "pick-n-pay", "spar"}
    checkers = registry["checkers"]()
    assert isinstance(checkers, CheckersScraper)
    assert checkers.engine == "http"
    assert checkers.headed is True
