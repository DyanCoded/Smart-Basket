"""SPAR South Africa live catalog scraper adapter (national chain).

Targets SPAR South Africa (www.spar.co.za) national catalog search JSON
endpoints and web specials HTML listings, normalizing SPAR product titles,
packaging sizes, SPAR Rewards specials, and multi-buy promotional deals into
RawScrapedItem contracts.
"""

from __future__ import annotations

import html as html_lib
import json
import logging
import re
from html.parser import HTMLParser
from typing import Any, Optional
from urllib.parse import quote_plus, urljoin

import httpx

from src.scrapers.base import BaseRetailerScraper
from src.scrapers.browser import PlaywrightUnavailableError
from src.scrapers.models import RawScrapedItem
from src.scrapers.retailers.shoprite_group import (
    DEFAULT_CORE_STAPLES,
    infer_category_slug,
)

logger = logging.getLogger(__name__)

# Anti-bot / WAF challenge signatures (halted respectfully without bypass)
_ANTI_BOT_MARKERS: tuple[str, ...] = (
    "cf-browser-verification",
    "attention required! | cloudflare",
    "verify you are human",
    "request unsuccessful. incapsula",
    "/_incapsula_resource",
    "access denied",
    "g-recaptcha",
    "h-captcha",
)

# Multi-buy promos ("2 FOR R60", "Any 2 for R72", "Buy 2 for R109.98", "3 @ R99")
_MULTI_BUY_RE = re.compile(
    r"(?:(?:buy|any)\s+)?(?P<qty>\d+)\s*(?:for|@)\s*(?:zar|r)?\s*"
    r"(?P<amount>\d[\d\s,]*(?:[.,]\d{1,2})?)",
    re.IGNORECASE,
)
# Explicit final price after SPAR promo keywords ("SPAR Rewards: R34.99", "Pay R34.99")
_EXPLICIT_PROMO_PRICE_RE = re.compile(
    r"(?:pay|now|only|special\s*:?|spar\s*rewards\s*:?|rewards\s*:?)\s*"
    r"(?:zar|r)\s*\d[\d\s,]*(?:[.,]\d{1,2})?",
    re.IGNORECASE,
)
# Guard against discount-only copy ("SPAR Rewards Save R5.00", "Save 15%")
_DISCOUNT_ONLY_RE = re.compile(
    r"^\s*(?:spar\s+rewards\s+|rewards\s+)?(?:buy\s+\d+\s+)?"
    r"save\s+(?:up\s+to\s+)?(?:(?:zar|r)\s*\d|\d+\s*%)",
    re.IGNORECASE,
)
_RAND_RE = re.compile(
    r"(?:zar|r)\s*\d[\d\s,]*(?:[.,]\d{1,2})?",
    re.IGNORECASE,
)
_PURE_EAN13_RE = re.compile(r"^\d{13}$")
_WHITESPACE_RE = re.compile(r"\s+")


def _clean_text(value: Optional[str]) -> str:
    if not value:
        return ""
    return _WHITESPACE_RE.sub(
        " ", html_lib.unescape(value).replace("\xa0", " ")
    ).strip()


def _extract_spar_price(
    raw_text: Optional[str],
    *,
    is_promo_text: bool = False,
) -> Optional[str]:
    """Extract a clean ZAR or multi-buy expression from SPAR shelf/special text."""
    text = _clean_text(raw_text)
    if not text:
        return None

    multi = _MULTI_BUY_RE.search(text)
    if multi:
        qty = multi.group("qty")
        amount = _clean_text(multi.group("amount"))
        return f"{qty} FOR R{amount}"

    explicit = _EXPLICIT_PROMO_PRICE_RE.search(text)
    if explicit:
        rand_inside = _RAND_RE.search(explicit.group(0))
        if rand_inside:
            return _clean_text(rand_inside.group(0))

    if is_promo_text and _DISCOUNT_ONLY_RE.match(text):
        return None

    rand = _RAND_RE.search(text)
    if rand:
        return _clean_text(rand.group(0))

    return None if is_promo_text else text


def _extract_spar_barcode(ean: Any = None, sku: Any = None) -> Optional[str]:
    """Return digits-only EAN/GTIN barcode; SKU fallback requires 13-digit EAN-13."""
    if ean:
        digits = re.sub(r"\D+", "", str(ean))
        if 8 <= len(digits) <= 14:
            return digits

    if sku:
        sku_str = str(sku).strip()
        if _PURE_EAN13_RE.match(sku_str):
            return sku_str

    return None


def _extract_json_price(value: Any, *, is_promo_text: bool = False) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, dict):
        formatted = (
            value.get("formattedValue")
            or value.get("formatted")
            or value.get("display")
            or value.get("text")
        )
        if formatted:
            return _extract_spar_price(str(formatted), is_promo_text=is_promo_text)
        numeric = value.get("value") or value.get("amount") or value.get("price")
        if numeric is not None:
            return f"R {numeric}"
        return None
    if isinstance(value, (int, float)):
        return f"R {value}"
    text = str(value).strip()
    if re.match(r"^\d+(?:\.\d{1,2})?$", text):
        return f"R {text}"
    return _extract_spar_price(text, is_promo_text=is_promo_text)


def _is_anti_bot_challenge(status_code: int, body: str) -> bool:
    if status_code in (403, 451):
        return True
    lowered = body[:4000].lower()
    return any(marker in lowered for marker in _ANTI_BOT_MARKERS)


class _SparHTMLParser(HTMLParser):
    """Lightweight stdlib HTMLParser for SPAR web catalog & specials cards."""

    _CARD_CLASSES = {
        "spar-product-card",
        "special-card",
        "product-tile",
        "product-item",
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.cards: list[dict[str, Any]] = []
        self._in_card: bool = False
        self._card_depth: int = 0
        self._current_card: dict[str, Any] = {}
        self._active_capture: Optional[str] = None
        self._capture_depth: int = 0
        self._capture_buf: list[str] = []
        self._in_sup: bool = False

    @staticmethod
    def _classes(attrs_dict: dict[str, Optional[str]]) -> set[str]:
        raw = attrs_dict.get("class") or ""
        return {c.strip().lower() for c in raw.split() if c.strip()}

    def _begin_capture(self, field_name: str) -> None:
        self._active_capture = field_name
        self._capture_depth = 1
        self._capture_buf = []

    def _flush_capture(self) -> None:
        if not self._active_capture:
            return
        text = _clean_text("".join(self._capture_buf))
        if text:
            field = self._active_capture
            if field in ("price", "was", "promo"):
                text = re.sub(r"(\d)\s+\.(\d{2})\b", r"\1.\2", text)
            if not self._current_card.get(field):
                self._current_card[field] = text
        self._active_capture = None
        self._capture_depth = 0
        self._capture_buf = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        attrs_dict = dict(attrs)
        classes = self._classes(attrs_dict)

        if not self._in_card:
            if classes & self._CARD_CLASSES:
                self._in_card = True
                self._card_depth = 1
                self._current_card = {
                    "data_ean": (
                        attrs_dict.get("data-ean") or attrs_dict.get("data-barcode")
                    ),
                    "data_sku": (
                        attrs_dict.get("data-sku")
                        or attrs_dict.get("data-product-code")
                    ),
                    "data_brand": attrs_dict.get("data-brand"),
                    "data_unit": (
                        attrs_dict.get("data-unit") or attrs_dict.get("data-size")
                    ),
                    "data_category": attrs_dict.get("data-category"),
                    "data_promo": (
                        attrs_dict.get("data-rewards-price")
                        or attrs_dict.get("data-special-price")
                    ),
                    "has_promo_badge": "special-card" in classes,
                }
            return

        self._card_depth += 1

        if tag == "a":
            href = attrs_dict.get("href")
            if href and not self._current_card.get("href"):
                self._current_card["href"] = href
            title_attr = attrs_dict.get("title")
            if title_attr:
                self._current_card.setdefault("title_attr", title_attr)

        if classes & {"spar-rewards-badge", "special-badge", "promo-badge"}:
            self._current_card["has_promo_badge"] = True

        if self._active_capture is not None:
            self._capture_depth += 1
            if tag == "sup":
                self._in_sup = True
            return

        if classes & {
            "spar-product-card__title",
            "special-card__title",
            "product-title",
            "product-name",
        }:
            self._begin_capture("name")
        elif classes & {"spar-product-card__brand", "product-brand"}:
            self._begin_capture("brand")
        elif classes & {
            "spar-product-card__size",
            "special-card__size",
            "product-size",
        }:
            self._begin_capture("unit")
        elif classes & {"price-was", "regular-price", "spar-price__was"}:
            self._begin_capture("was")
        elif classes & {"price-now", "spar-price", "product-price"}:
            self._begin_capture("price")
        elif classes & {"spar-rewards-price", "special-price", "promo-deal"}:
            self._begin_capture("promo")

    def handle_data(self, data: str) -> None:
        if not self._in_card or self._active_capture is None:
            return
        if self._in_sup and self._active_capture in ("price", "was", "promo"):
            stripped = data.strip()
            if stripped and stripped.isdigit() and len(stripped) == 2:
                self._capture_buf.append(f".{stripped}")
            else:
                self._capture_buf.append(stripped)
        else:
            self._capture_buf.append(data)

    def handle_endtag(self, tag: str) -> None:
        if not self._in_card:
            return

        if tag == "sup":
            self._in_sup = False

        if self._active_capture is not None:
            self._capture_depth -= 1
            if self._capture_depth <= 0:
                self._flush_capture()

        self._card_depth -= 1
        if self._card_depth <= 0:
            self.cards.append(self._current_card)
            self._current_card = {}
            self._in_card = False
            self._card_depth = 0


def parse_spar_json(
    payload: dict[str, Any],
    *,
    base_url: str = "https://www.spar.co.za",
    default_category_slug: Optional[str] = None,
    query_term: Optional[str] = None,
) -> list[RawScrapedItem]:
    """Parse SPAR South Africa catalog/specials JSON payloads into RawScrapedItem."""
    container = (
        payload.get("data") if isinstance(payload.get("data"), dict) else payload
    )
    raw_entries = (
        container.get("products")
        or container.get("specials")
        or container.get("items")
        or container.get("results")
        or []
    )
    if not isinstance(raw_entries, list):
        return []

    items: list[RawScrapedItem] = []

    for entry in raw_entries:
        if not isinstance(entry, dict):
            continue

        raw_name = _clean_text(
            entry.get("name")
            or entry.get("title")
            or entry.get("productName")
            or entry.get("description")
        )
        if not raw_name:
            continue

        brand = (
            _clean_text(
                entry.get("brand")
                or entry.get("brandName")
                or entry.get("manufacturer")
            )
            or None
        )
        if brand is None and raw_name.lower().startswith("spar "):
            brand = "SPAR"

        barcode = _extract_spar_barcode(
            ean=(
                entry.get("ean")
                or entry.get("barcode")
                or entry.get("barcodeNumber")
                or entry.get("gtin")
            ),
            sku=(
                entry.get("sku")
                or entry.get("productCode")
                or entry.get("code")
                or entry.get("id")
            ),
        )

        raw_unit = (
            _clean_text(
                entry.get("packSize")
                or entry.get("size")
                or entry.get("unitSize")
                or entry.get("weight")
                or entry.get("uom")
            )
            or None
        )

        regular_price = _extract_json_price(
            entry.get("regularPrice")
            or entry.get("normalPrice")
            or entry.get("wasPrice")
            or entry.get("sellingPrice")
            or entry.get("price")
        )

        raw_promo_source = (
            entry.get("sparRewardsPrice")
            or entry.get("rewardsPrice")
            or entry.get("multiBuyText")
            or entry.get("specialPrice")
            or entry.get("promoPrice")
            or entry.get("promotionalPrice")
            or entry.get("dealPrice")
            or entry.get("promoText")
        )
        has_promo_source = raw_promo_source is not None and bool(
            str(raw_promo_source).strip()
        )
        promo_price = _extract_json_price(raw_promo_source, is_promo_text=True)

        if not regular_price and not promo_price:
            continue

        raw_price: str
        raw_promo_price: Optional[str] = None
        is_promotional = bool(
            has_promo_source
            or entry.get("isPromotional")
            or entry.get("isSpecial")
            or entry.get("onSpecial")
        )

        if promo_price and promo_price != regular_price:
            raw_price = regular_price or promo_price
            raw_promo_price = promo_price
            is_promotional = True
        else:
            raw_price = regular_price or promo_price or ""

        raw_category = (
            entry.get("category")
            or entry.get("department")
            or entry.get("categoryName")
        )
        category_slug = (
            infer_category_slug(
                str(raw_category) if raw_category else None,
                query_term,
                raw_name,
            )
            or default_category_slug
        )

        raw_url = entry.get("url") or entry.get("productUrl") or entry.get("specialUrl")
        source_url = urljoin(base_url, str(raw_url)) if raw_url else None

        items.append(
            RawScrapedItem(
                retailer_slug="spar",
                raw_name=raw_name,
                raw_price=raw_price,
                raw_promo_price=raw_promo_price,
                brand=brand,
                barcode=barcode,
                category_slug=category_slug,
                raw_unit=raw_unit,
                is_promotional=is_promotional,
                source_url=source_url,
            )
        )

    return items


def parse_spar_html(
    html_text: str,
    *,
    base_url: str = "https://www.spar.co.za",
    default_category_slug: Optional[str] = None,
    query_term: Optional[str] = None,
) -> list[RawScrapedItem]:
    """Parse SPAR South Africa HTML catalog & specials cards into RawScrapedItem."""
    parser = _SparHTMLParser()
    parser.feed(html_text)
    parser.close()

    items: list[RawScrapedItem] = []

    for card in parser.cards:
        raw_name = _clean_text(card.get("name") or card.get("title_attr"))
        if not raw_name:
            continue

        brand = _clean_text(card.get("brand") or card.get("data_brand")) or None
        if brand is None and raw_name.lower().startswith("spar "):
            brand = "SPAR"

        barcode = _extract_spar_barcode(
            ean=card.get("data_ean"),
            sku=card.get("data_sku"),
        )
        raw_unit = _clean_text(card.get("unit") or card.get("data_unit")) or None

        was_price = _extract_spar_price(card.get("was"))
        shelf_price = _extract_spar_price(card.get("price"))
        raw_promo_attr = card.get("promo") or card.get("data_promo")
        promo_price = _extract_spar_price(raw_promo_attr, is_promo_text=True)

        if not shelf_price and not was_price and not promo_price:
            continue

        raw_price: str
        raw_promo_price: Optional[str] = None
        is_promotional = bool(
            card.get("has_promo_badge")
            or (raw_promo_attr and str(raw_promo_attr).strip())
        )

        if promo_price:
            raw_price = was_price or shelf_price or promo_price
            raw_promo_price = promo_price
            is_promotional = True
        elif was_price and shelf_price and was_price != shelf_price:
            raw_price = was_price
            raw_promo_price = shelf_price
            is_promotional = True
        else:
            raw_price = shelf_price or was_price or ""

        category_slug = (
            infer_category_slug(card.get("data_category"), query_term, raw_name)
            or default_category_slug
        )
        href = card.get("href")
        source_url = urljoin(base_url, href) if href else None

        items.append(
            RawScrapedItem(
                retailer_slug="spar",
                raw_name=raw_name,
                raw_price=raw_price,
                raw_promo_price=raw_promo_price,
                brand=brand,
                barcode=barcode,
                category_slug=category_slug,
                raw_unit=raw_unit,
                is_promotional=is_promotional,
                source_url=source_url,
            )
        )

    return items


class SparScraper(BaseRetailerScraper):
    """Live catalog scraper for SPAR South Africa (`spar`)."""

    retailer_slug = "spar"
    base_url = "https://www.spar.co.za"
    search_path = "/api/catalog/search"
    playwright_wait_selector = ".spar-product-card, .special-card, .product-tile"
    playwright_json_patterns: tuple[str, ...] = (
        "/api/",
        "catalog",
        "products",
        "specials",
    )

    def __init__(self, *, max_pages: int = 1, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.max_pages = max(1, max_pages)

    @property
    def default_queries(self) -> list[str]:
        return [term for terms in DEFAULT_CORE_STAPLES.values() for term in terms]

    def build_storefront_search_url(self, term: str) -> str:
        """Build live SPAR South Africa storefront search URL for Playwright."""
        return f"{self.base_url}/?q={quote_plus(term)}"

    async def _scrape_via_playwright(self, terms: list[str]) -> list[RawScrapedItem]:
        fetcher = self.get_browser_fetcher()
        collected: list[RawScrapedItem] = []
        seen_keys: set[str] = set()

        for term in terms:
            await self._throttle()
            default_cat = infer_category_slug(query_term=term)
            url = self.build_storefront_search_url(term)
            try:
                result = await fetcher.fetch_page(
                    url,
                    wait_selector=self.playwright_wait_selector,
                    json_url_patterns=self.playwright_json_patterns,
                )
            except PlaywrightUnavailableError as exc:
                logger.warning("[%s] %s", self.retailer_slug, exc)
                break

            if result.blocked:
                logger.warning(
                    "[%s] Blocked on %s (%s); halting respectfully without bypass.",
                    self.retailer_slug,
                    url,
                    result.block_reason,
                )
                break

            page_items: list[RawScrapedItem] = []
            for _resp_url, payload in result.intercepted_json:
                if isinstance(payload, dict):
                    page_items.extend(
                        parse_spar_json(
                            payload,
                            base_url=self.base_url,
                            default_category_slug=default_cat,
                            query_term=term,
                        )
                    )
            if not page_items and result.html:
                page_items = parse_spar_html(
                    result.html,
                    base_url=self.base_url,
                    default_category_slug=default_cat,
                    query_term=term,
                )

            for item in page_items:
                dedup_key = (
                    f"ean:{item.barcode}"
                    if item.barcode
                    else f"name:{item.raw_name.lower()}"
                )
                if dedup_key in seen_keys:
                    continue
                seen_keys.add(dedup_key)
                collected.append(item)

        return collected

    async def scrape_catalog(self, query_terms: list[str]) -> list[RawScrapedItem]:
        """Query SPAR catalog/specials endpoint and extract RawScrapedItem list."""
        terms = [t.strip() for t in query_terms if t.strip()] or self.default_queries
        if self.engine == "playwright":
            return await self._scrape_via_playwright(terms)
        collected: list[RawScrapedItem] = []
        seen_keys: set[str] = set()

        for term in terms:
            default_cat = infer_category_slug(query_term=term)
            for page in range(1, self.max_pages + 1):
                params: dict[str, Any] = {"q": term, "page": page}
                try:
                    response = await self._fetch_with_retry(
                        "GET", self.search_path, params=params
                    )
                except httpx.HTTPStatusError as exc:
                    if exc.response.status_code in (403, 451):
                        logger.warning(
                            "[%s] Blocked by storefront access control (HTTP %s) "
                            "for query %r; halting query respectfully.",
                            self.retailer_slug,
                            exc.response.status_code,
                            term,
                        )
                        break
                    raise

                if _is_anti_bot_challenge(response.status_code, response.text):
                    logger.warning(
                        "[%s] Anti-bot challenge detected for query %r; "
                        "halting respectfully without bypass.",
                        self.retailer_slug,
                        term,
                    )
                    break

                content_type = response.headers.get("content-type", "").lower()
                if (
                    "application/json" in content_type
                    or response.text.lstrip().startswith("{")
                ):
                    try:
                        payload = response.json()
                    except json.JSONDecodeError:
                        page_items = []
                    else:
                        page_items = parse_spar_json(
                            payload,
                            base_url=self.base_url,
                            default_category_slug=default_cat,
                            query_term=term,
                        )
                else:
                    page_items = parse_spar_html(
                        response.text,
                        base_url=self.base_url,
                        default_category_slug=default_cat,
                        query_term=term,
                    )

                if not page_items:
                    break

                for item in page_items:
                    dedup_key = (
                        f"ean:{item.barcode}"
                        if item.barcode
                        else f"name:{item.raw_name.lower()}"
                    )
                    if dedup_key in seen_keys:
                        continue
                    seen_keys.add(dedup_key)
                    collected.append(item)

        return collected
