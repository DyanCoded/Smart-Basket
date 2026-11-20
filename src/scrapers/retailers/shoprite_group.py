"""Checkers and Shoprite catalog scrapers (shared Shoprite Group platform).

Both Checkers (www.checkers.co.za) and Shoprite (www.shoprite.co.za) operate on
Shoprite Group's shared SAP Commerce Cloud / Hybris storefront infrastructure.
This module provides a unified parser supporting both storefront HTML product
cards (.item-product + data-product-ga) and JSON catalog search responses,
emitting standardized RawScrapedItem records for the SmartBasket normalizer
and canonical-chain publisher pipeline.
"""

from __future__ import annotations

import html as html_lib
import json
import logging
import re
from html.parser import HTMLParser
from typing import Any, Optional
from urllib.parse import urljoin

import httpx

from src.scrapers.base import BaseRetailerScraper
from src.scrapers.models import RawScrapedItem

logger = logging.getLogger(__name__)

# Core grocery staple search queries grouped by SmartBasket category slug
DEFAULT_CORE_STAPLES: dict[str, tuple[str, ...]] = {
    "dairy-eggs": ("milk", "eggs", "butter", "yogurt"),
    "bakery": ("white bread", "brown bread"),
    "pantry-staples": (
        "rice",
        "maize meal",
        "pasta",
        "cooking oil",
        "sugar",
        "baked beans",
    ),
    "fresh-produce": ("apples", "potatoes", "bananas", "tomatoes"),
    "household": ("washing powder", "dishwashing liquid", "toilet paper"),
}

# Category keyword mapping for Shoprite Group department breadcrumbs
_CATEGORY_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("dairy-eggs", ("dairy", "milk", "egg", "butter", "yogurt", "yoghurt", "cheese")),
    ("bakery", ("bakery", "bread", "rolls", "wraps", "buns")),
    (
        "pantry-staples",
        (
            "pantry",
            "food cupboard",
            "rice",
            "pasta",
            "maize",
            "oil",
            "sugar",
            "beans",
            "flour",
            "tea",
            "coffee",
            "cereal",
        ),
    ),
    (
        "fresh-produce",
        ("fresh", "fruit", "veg", "produce", "apple", "potato", "banana", "tomato"),
    ),
    (
        "household",
        (
            "household",
            "cleaning",
            "laundry",
            "washing",
            "dishwash",
            "toilet",
            "detergent",
            "paper",
        ),
    ),
    ("beverages", ("beverage", "drink", "juice", "soda", "cola", "water")),
)

# Anti-bot / WAF challenge signatures (never bypassed; scraper stops gracefully)
_ANTI_BOT_MARKERS: tuple[str, ...] = (
    "cf-browser-verification",
    "attention required! | cloudflare",
    "verify you are human",
    "request unsuccessful. incapsula",
    "/_incapsula_resource",
    "g-recaptcha",
    "h-captcha",
)

# Price token extractor handling multi-buy promos ("2 FOR R60") or Rand ("R 34.99")
_MULTI_BUY_FRAGMENT_RE = re.compile(
    r"(?:buy\s+)?\d+\s*(?:for|@)\s*(?:zar|r)?\s*\d[\d\s,]*(?:[.,]\d{1,2})?",
    re.IGNORECASE,
)
_RAND_FRAGMENT_RE = re.compile(
    r"(?:zar|r)\s*\d[\d\s,]*(?:[.,]\d{1,2})?",
    re.IGNORECASE,
)
_PURE_DIGITS_RE = re.compile(r"^\d{8,14}$")
_WHITESPACE_RE = re.compile(r"\s+")


def _clean_text(value: Optional[str]) -> str:
    if not value:
        return ""
    return _WHITESPACE_RE.sub(
        " ", html_lib.unescape(value).replace("\xa0", " ")
    ).strip()


def _extract_price_fragment(raw_text: Optional[str]) -> Optional[str]:
    """Extract clean ZAR or multi-buy expression from promo/shelf text."""
    text = _clean_text(raw_text)
    if not text:
        return None
    multi = _MULTI_BUY_FRAGMENT_RE.search(text)
    if multi:
        return _clean_text(multi.group(0))
    rand = _RAND_FRAGMENT_RE.search(text)
    if rand:
        return _clean_text(rand.group(0))
    return text


def _normalize_barcode_candidate(
    ean: Optional[str],
    sku: Optional[str] = None,
) -> Optional[str]:
    """Return EAN/GTIN barcode; fall back to SKU only if it is a pure 8-14 digit EAN."""
    if ean:
        digits = re.sub(r"\D+", "", str(ean))
        if 8 <= len(digits) <= 14:
            return digits
    if sku:
        sku_str = str(sku).strip()
        if _PURE_DIGITS_RE.match(sku_str):
            return sku_str
    return None


def infer_category_slug(
    raw_category: Optional[str] = None,
    query_term: Optional[str] = None,
    product_name: Optional[str] = None,
) -> Optional[str]:
    """Map Shoprite Group department breadcrumb or staple query to SmartBasket slug."""
    for source in (raw_category, query_term, product_name):
        if not source:
            continue
        lowered = source.lower()
        for slug, keywords in _CATEGORY_KEYWORDS:
            if any(kw in lowered for kw in keywords):
                return slug
    return None


def _is_anti_bot_challenge(status_code: int, body: str) -> bool:
    """Detect WAF / CAPTCHA challenges so the scraper halts respectfully."""
    if status_code in (403, 451):
        return True
    lowered = body[:4000].lower()
    return any(marker in lowered for marker in _ANTI_BOT_MARKERS)


class _ShopriteGroupHTMLParser(HTMLParser):
    """Lightweight stdlib HTMLParser for Shoprite Group .item-product cards."""

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
            if field in ("now", "before", "promo"):
                # Normalize split superscripts like "R34 .99" -> "R34.99"
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
            if "item-product" in classes:
                self._in_card = True
                self._card_depth = 1
                self._current_card = {
                    "data_product_ga": attrs_dict.get("data-product-ga"),
                    "data_product_code": attrs_dict.get("data-product-code"),
                    "data_barcode": (
                        attrs_dict.get("data-barcode")
                        or attrs_dict.get("data-product-ean")
                    ),
                    "data_brand": attrs_dict.get("data-brand"),
                    "data_unit": (
                        attrs_dict.get("data-unit") or attrs_dict.get("data-pack-size")
                    ),
                    "data_category": attrs_dict.get("data-category"),
                    "data_promo_price": attrs_dict.get("data-promo-price"),
                    "has_promo_badge": False,
                }
            return

        self._card_depth += 1

        if tag == "a":
            href = attrs_dict.get("href")
            if href and (
                "product-listening-click" in classes
                or not self._current_card.get("href")
            ):
                self._current_card["href"] = href
            title_attr = attrs_dict.get("title")
            if title_attr and "product-listening-click" in classes:
                self._current_card.setdefault("title_attr", title_attr)

        if any(
            badge in classes
            for badge in (
                "item-product__badge--promo",
                "xtra-savings-badge",
                "promo-badge",
                "special-price__badge",
            )
        ):
            self._current_card["has_promo_badge"] = True

        if self._active_capture is not None:
            self._capture_depth += 1
            if tag == "sup":
                self._in_sup = True
            return

        if "item-product__name" in classes:
            self._begin_capture("name")
        elif "item-product__brand" in classes:
            self._begin_capture("brand")
        elif "item-product__unit" in classes:
            self._begin_capture("unit")
        elif "now" in classes or "item-product__price-now" in classes:
            self._begin_capture("now")
        elif "before" in classes or "item-product__price-before" in classes:
            self._begin_capture("before")
        elif (
            "special-price__extra__price" in classes
            or "xtra-savings-price" in classes
            or "promo-price" in classes
        ):
            self._begin_capture("promo")

    def handle_data(self, data: str) -> None:
        if not self._in_card or self._active_capture is None:
            return
        if self._in_sup and self._active_capture in ("now", "before", "promo"):
            stripped = data.strip()
            if stripped and stripped.isdigit() and len(stripped) == 2:
                # Handle "R34<sup>99</sup>" -> "R34.99"
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


def parse_search_html(
    html_text: str,
    *,
    retailer_slug: str,
    base_url: str,
    default_category_slug: Optional[str] = None,
    query_term: Optional[str] = None,
) -> list[RawScrapedItem]:
    """Parse Shoprite Group SAP Commerce storefront HTML into RawScrapedItem list."""
    parser = _ShopriteGroupHTMLParser()
    parser.feed(html_text)
    parser.close()

    items: list[RawScrapedItem] = []

    for card in parser.cards:
        ga_data: dict[str, Any] = {}
        raw_ga = card.get("data_product_ga")
        if raw_ga:
            try:
                parsed_ga = json.loads(html_lib.unescape(raw_ga))
                if isinstance(parsed_ga, dict):
                    ga_data = parsed_ga
            except (json.JSONDecodeError, TypeError):
                logger.debug(
                    "[%s] Ignoring malformed data-product-ga JSON", retailer_slug
                )

        raw_name = _clean_text(
            card.get("name") or ga_data.get("name") or card.get("title_attr")
        )
        if not raw_name:
            continue

        brand = (
            _clean_text(
                card.get("brand") or card.get("data_brand") or ga_data.get("brand")
            )
            or None
        )

        barcode = _normalize_barcode_candidate(
            ean=(
                card.get("data_barcode")
                or ga_data.get("ean")
                or ga_data.get("barcode")
                or ga_data.get("product_ean")
            ),
            sku=card.get("data_product_code") or ga_data.get("id"),
        )

        raw_unit = (
            _clean_text(
                card.get("unit")
                or card.get("data_unit")
                or ga_data.get("pack_size")
                or ga_data.get("unit")
                or ga_data.get("variant")
            )
            or None
        )

        now_price = _extract_price_fragment(card.get("now"))
        before_price = _extract_price_fragment(card.get("before"))
        extra_promo = _extract_price_fragment(
            card.get("promo") or card.get("data_promo_price")
        )

        if not now_price and ga_data.get("price") is not None:
            ga_price_str = str(ga_data["price"]).strip()
            now_price = (
                ga_price_str
                if ga_price_str.upper().startswith(("R", "ZAR"))
                else f"R {ga_price_str}"
            )

        if not now_price and not extra_promo:
            continue

        raw_price: str
        raw_promo_price: Optional[str] = None
        is_promotional = bool(card.get("has_promo_badge"))

        if extra_promo:
            raw_price = before_price or now_price or extra_promo
            raw_promo_price = extra_promo
            is_promotional = True
        elif before_price and now_price and before_price != now_price:
            raw_price = before_price
            raw_promo_price = now_price
            is_promotional = True
        else:
            raw_price = now_price or extra_promo or ""

        raw_category = card.get("data_category") or ga_data.get("category")
        category_slug = (
            infer_category_slug(raw_category, query_term, raw_name)
            or default_category_slug
        )

        href = card.get("href") or ga_data.get("url")
        source_url = urljoin(base_url, href) if href else None

        items.append(
            RawScrapedItem(
                retailer_slug=retailer_slug,
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


def _extract_json_price_field(value: Any) -> Optional[str]:
    """Extract a Rand or multi-buy string from flat or OCC nested price objects."""
    if value is None:
        return None
    if isinstance(value, dict):
        formatted = (
            value.get("formattedValue")
            or value.get("formatted")
            or value.get("display")
            or value.get("label")
        )
        if formatted:
            return _extract_price_fragment(str(formatted))
        numeric = value.get("value") or value.get("amount")
        if numeric is not None:
            return f"R {numeric}"
        return None
    if isinstance(value, (int, float)):
        return f"R {value}"
    return _extract_price_fragment(str(value))


def parse_search_json(
    payload: dict[str, Any],
    *,
    retailer_slug: str,
    base_url: str,
    default_category_slug: Optional[str] = None,
    query_term: Optional[str] = None,
) -> list[RawScrapedItem]:
    """Parse Shoprite Group SAP Commerce OCC / BFF JSON search payloads."""
    raw_entries = (
        payload.get("products") or payload.get("results") or payload.get("items") or []
    )
    if not isinstance(raw_entries, list):
        return []

    items: list[RawScrapedItem] = []

    for entry in raw_entries:
        if not isinstance(entry, dict):
            continue

        raw_name = _clean_text(entry.get("name") or entry.get("title"))
        if not raw_name:
            continue

        brand = _clean_text(entry.get("brand") or entry.get("manufacturer")) or None

        barcode = _normalize_barcode_candidate(
            ean=(entry.get("ean") or entry.get("barcode") or entry.get("gtin")),
            sku=entry.get("code") or entry.get("sku") or entry.get("id"),
        )

        raw_unit = (
            _clean_text(
                entry.get("packSize")
                or entry.get("unitOfMeasure")
                or entry.get("unit")
                or entry.get("size")
            )
            or None
        )

        regular_price = _extract_json_price_field(
            entry.get("regularPrice") or entry.get("wasPrice") or entry.get("price")
        )
        promo_price = _extract_json_price_field(
            entry.get("xtraSavingsPrice")
            or entry.get("promotionalPrice")
            or entry.get("promoPrice")
            or entry.get("specialPrice")
            or entry.get("multiBuyPromo")
        )

        if not regular_price and not promo_price:
            continue

        raw_price = regular_price or promo_price or ""
        is_promotional = bool(
            promo_price
            or entry.get("isPromotional")
            or entry.get("onPromotion")
            or entry.get("xtraSavings")
        )

        raw_category = (
            entry.get("category")
            or entry.get("department")
            or entry.get("categoryPath")
        )
        if isinstance(raw_category, list):
            raw_category = "/".join(str(c) for c in raw_category)
        category_slug = (
            infer_category_slug(
                str(raw_category) if raw_category else None,
                query_term,
                raw_name,
            )
            or default_category_slug
        )

        raw_url = entry.get("url") or entry.get("productUrl")
        source_url = urljoin(base_url, str(raw_url)) if raw_url else None

        items.append(
            RawScrapedItem(
                retailer_slug=retailer_slug,
                raw_name=raw_name,
                raw_price=raw_price,
                raw_promo_price=promo_price,
                brand=brand,
                barcode=barcode,
                category_slug=category_slug,
                raw_unit=raw_unit,
                is_promotional=is_promotional,
                source_url=source_url,
            )
        )

    return items


class ShopriteGroupBaseScraper(BaseRetailerScraper):
    """Shared base scraper for Shoprite Group chains (Checkers & Shoprite)."""

    search_path: str = "/search/all"

    def __init__(self, *, max_pages: int = 1, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.max_pages = max(1, max_pages)

    @property
    def default_queries(self) -> list[str]:
        """Flat list of core grocery staple query terms across 5 departments."""
        return [term for terms in DEFAULT_CORE_STAPLES.values() for term in terms]

    async def scrape_catalog(self, query_terms: list[str]) -> list[RawScrapedItem]:
        """Query Shoprite Group catalog search and extract normalized raw items."""
        terms = [t.strip() for t in query_terms if t.strip()] or self.default_queries
        collected: list[RawScrapedItem] = []
        seen_keys: set[str] = set()

        for term in terms:
            default_cat = infer_category_slug(query_term=term)
            for page in range(self.max_pages):
                params: dict[str, Any] = {"q": f"{term}:relevance"}
                if page > 0:
                    params["page"] = page

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
                page_items: list[RawScrapedItem]
                if (
                    "application/json" in content_type
                    or response.text.lstrip().startswith("{")
                ):
                    try:
                        payload = response.json()
                    except json.JSONDecodeError:
                        page_items = []
                    else:
                        page_items = parse_search_json(
                            payload,
                            retailer_slug=self.retailer_slug,
                            base_url=self.base_url,
                            default_category_slug=default_cat,
                            query_term=term,
                        )
                else:
                    page_items = parse_search_html(
                        response.text,
                        retailer_slug=self.retailer_slug,
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


class CheckersScraper(ShopriteGroupBaseScraper):
    """Live catalog scraper for Checkers (Shoprite Group national chain)."""

    retailer_slug = "checkers"
    base_url = "https://www.checkers.co.za"


class ShopriteScraper(ShopriteGroupBaseScraper):
    """Live catalog scraper for Shoprite (Shoprite Group national chain)."""

    retailer_slug = "shoprite"
    base_url = "https://www.shoprite.co.za"
