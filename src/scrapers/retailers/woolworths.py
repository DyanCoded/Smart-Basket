"""Woolworths Food live catalog scraper adapter (South African national chain).

Targets Woolworths South Africa (www.woolworths.co.za) Oracle ATG / Endeca
Guided Search JSON payloads and storefront HTML listings, normalizing
Woolworths-specific spaced unit descriptions (e.g. '2 L', '500 g', '200 g')
and multi-buy / WRewards promotional tags into RawScrapedItem contracts.
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
    "akamai",
    "access denied",
    "g-recaptcha",
    "h-captcha",
)

# Multi-buy promos including Woolworths "Any 2 for R90" / "Buy 2 for R75"
_MULTI_BUY_RE = re.compile(
    r"(?:(?:buy|any)\s+)?(?P<qty>\d+)\s*(?:for|@)\s*(?:zar|r)?\s*"
    r"(?P<amount>\d[\d\s,]*(?:[.,]\d{1,2})?)",
    re.IGNORECASE,
)
# Explicit final price after promo keywords (e.g. "WRewards: R36.99", "Pay R34.99")
_EXPLICIT_PROMO_PRICE_RE = re.compile(
    r"(?:pay|now|only|wrewards\s*:?)\s*(?:zar|r)\s*\d[\d\s,]*(?:[.,]\d{1,2})?",
    re.IGNORECASE,
)
# Guard against discount-only labels ("Save R10", "Save 20%", "Buy 2 Save 20%")
_DISCOUNT_ONLY_RE = re.compile(
    r"^\s*(?:wrewards\s+)?(?:buy\s+\d+\s+)?save\s+(?:up\s+to\s+)?(?:(?:zar|r)\s*\d|\d+\s*%)",
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


def _unwrap_endeca_scalar(value: Any) -> Any:
    """Unwrap Oracle Endeca single-element attribute lists (['Clover'] -> 'Clover')."""
    if isinstance(value, list):
        for item in value:
            if item is not None and str(item).strip():
                return item
        return None
    return value


def _extract_ww_price(
    raw_text: Optional[str],
    *,
    is_promo_tag: bool = False,
) -> Optional[str]:
    """Extract a clean ZAR or multi-buy expression from Woolworths pricing text."""
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

    if is_promo_tag and _DISCOUNT_ONLY_RE.match(text):
        return None

    rand = _RAND_RE.search(text)
    if rand:
        return _clean_text(rand.group(0))

    return None if is_promo_tag else text


def _extract_ww_barcode(ean: Any = None, sku: Any = None) -> Optional[str]:
    """Return EAN/GTIN barcode; fall back to SKU only for strict 13-digit EAN-13."""
    ean_val = _unwrap_endeca_scalar(ean)
    if ean_val:
        digits = re.sub(r"\D+", "", str(ean_val))
        if 8 <= len(digits) <= 14:
            return digits

    sku_val = _unwrap_endeca_scalar(sku)
    if sku_val:
        sku_str = str(sku_val).strip()
        if _PURE_EAN13_RE.match(sku_str):
            return sku_str

    return None


def _extract_json_price(value: Any, *, is_promo_tag: bool = False) -> Optional[str]:
    val = _unwrap_endeca_scalar(value)
    if val is None:
        return None
    if isinstance(val, dict):
        formatted = (
            val.get("formattedValue")
            or val.get("formatted")
            or val.get("display")
            or val.get("text")
        )
        if formatted:
            return _extract_ww_price(str(formatted), is_promo_tag=is_promo_tag)
        numeric = val.get("value") or val.get("amount") or val.get("price")
        if numeric is not None:
            return f"R {numeric}"
        return None
    if isinstance(val, (int, float)):
        return f"R {val}"
    text = str(val).strip()
    if re.match(r"^\d+(?:\.\d{1,2})?$", text):
        return f"R {text}"
    return _extract_ww_price(text, is_promo_tag=is_promo_tag)


def _extract_ww_promo_tags(raw_promos: Any) -> tuple[Optional[str], bool]:
    """Parse Woolworths promo tags into (promo_price_str, has_promo_badge)."""
    if raw_promos is None:
        return (None, False)

    entries = raw_promos if isinstance(raw_promos, list) else [raw_promos]
    has_badge = False

    for entry in entries:
        if isinstance(entry, dict):
            has_badge = True
            for key in ("promoPrice", "wrewardsPrice", "salePrice", "price"):
                parsed = _extract_json_price(entry.get(key))
                if parsed:
                    return (parsed, True)
            for text_key in ("description", "label", "text", "promotionText", "title"):
                parsed = _extract_ww_price(entry.get(text_key), is_promo_tag=True)
                if parsed:
                    return (parsed, True)
        elif entry is not None:
            text = _clean_text(str(entry))
            if not text:
                continue
            has_badge = True
            parsed = _extract_ww_price(text, is_promo_tag=True)
            if parsed:
                return (parsed, True)

    return (None, has_badge)


def _collect_endeca_records(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten Oracle Endeca / ATG nested contents->mainContent->records payloads."""
    direct = payload.get("products") or payload.get("records") or payload.get("items")
    if isinstance(direct, list):
        return [r for r in direct if isinstance(r, dict)]

    found: list[dict[str, Any]] = []

    def _walk(node: Any) -> None:
        if isinstance(node, dict):
            records = node.get("records")
            if isinstance(records, list):
                for rec in records:
                    if isinstance(rec, dict):
                        attrs = rec.get("attributes")
                        if isinstance(attrs, dict):
                            merged = {**rec, **attrs}
                            found.append(merged)
                        else:
                            found.append(rec)
            for key, val in node.items():
                if key != "records" and isinstance(val, (dict, list)):
                    _walk(val)
        elif isinstance(node, list):
            for child in node:
                _walk(child)

    _walk(payload)
    return found


def _is_anti_bot_challenge(status_code: int, body: str) -> bool:
    if status_code in (403, 451):
        return True
    lowered = body[:4000].lower()
    return any(marker in lowered for marker in _ANTI_BOT_MARKERS)


class _WoolworthsHTMLParser(HTMLParser):
    """Lightweight stdlib HTMLParser for Woolworths Food product listing cards."""

    _CARD_CLASSES = {"product-list__item", "product-card", "product-tile"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.cards: list[dict[str, Any]] = []
        self._in_card: bool = False
        self._card_depth: int = 0
        self._current_card: dict[str, Any] = {}
        self._active_capture: Optional[str] = None
        self._capture_depth: int = 0
        self._capture_buf: list[str] = []

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
        if text and not self._current_card.get(self._active_capture):
            self._current_card[self._active_capture] = text
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
                        attrs_dict.get("data-sku") or attrs_dict.get("data-product-id")
                    ),
                    "data_brand": attrs_dict.get("data-brand"),
                    "data_size": (
                        attrs_dict.get("data-size") or attrs_dict.get("data-unit")
                    ),
                    "data_category": attrs_dict.get("data-category"),
                    "data_promo": (
                        attrs_dict.get("data-promo")
                        or attrs_dict.get("data-wrewards-price")
                    ),
                    "has_promo_badge": False,
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

        if classes & {"wrewards-badge", "promo-tag", "product-card__badge"}:
            self._current_card["has_promo_badge"] = True

        if self._active_capture is not None:
            self._capture_depth += 1
            return

        if classes & {"range--title", "product-card__name", "product-tile__title"}:
            self._begin_capture("name")
        elif classes & {"product-card__brand", "range--brand"}:
            self._begin_capture("brand")
        elif classes & {"product-card__size", "product-card__unit"}:
            self._begin_capture("unit")
        elif classes & {"price--was", "product-card__price-was"}:
            self._begin_capture("was")
        elif classes & {"price", "price--now", "product-card__price"}:
            self._begin_capture("price")
        elif classes & {"product-card__promo", "wrewards-price", "promo-tag"}:
            self._begin_capture("promo")

    def handle_data(self, data: str) -> None:
        if self._in_card and self._active_capture is not None:
            self._capture_buf.append(data)

    def handle_endtag(self, tag: str) -> None:
        if not self._in_card:
            return

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


def parse_woolworths_json(
    payload: dict[str, Any],
    *,
    base_url: str = "https://www.woolworths.co.za",
    default_category_slug: Optional[str] = None,
    query_term: Optional[str] = None,
) -> list[RawScrapedItem]:
    """Parse Woolworths Food Endeca / ATG JSON catalog payloads into RawScrapedItem."""
    entries = _collect_endeca_records(payload)
    items: list[RawScrapedItem] = []

    for entry in entries:
        raw_name = _clean_text(
            _unwrap_endeca_scalar(
                entry.get("displayName")
                or entry.get("p_displayName")
                or entry.get("name")
                or entry.get("title")
            )
        )
        if not raw_name:
            continue

        brand = (
            _clean_text(
                _unwrap_endeca_scalar(
                    entry.get("brand")
                    or entry.get("brandName")
                    or entry.get("p_brand")
                    or entry.get("manufacturer")
                )
            )
            or None
        )
        if brand is None and raw_name.lower().startswith(("woolworths ", "wfoods ")):
            brand = "Woolworths"

        barcode = _extract_ww_barcode(
            ean=(
                entry.get("ean")
                or entry.get("p_ean")
                or entry.get("barcode")
                or entry.get("gtin")
            ),
            sku=(
                entry.get("sku")
                or entry.get("p_sku")
                or entry.get("productId")
                or entry.get("id")
            ),
        )

        raw_unit = (
            _clean_text(
                _unwrap_endeca_scalar(
                    entry.get("packSize")
                    or entry.get("p_packSize")
                    or entry.get("unitSize")
                    or entry.get("unitDescription")
                    or entry.get("size")
                )
            )
            or None
        )

        list_price = _extract_json_price(
            entry.get("listPrice")
            or entry.get("wasPrice")
            or entry.get("p_listPrice")
            or entry.get("startingPrice")
            or entry.get("price")
            or entry.get("p_price")
        )
        sale_price = _extract_json_price(
            entry.get("salePrice")
            or entry.get("p_salePrice")
            or entry.get("promoPrice")
            or entry.get("promotionalPrice")
            or entry.get("wrewardsPrice"),
            is_promo_tag=True,
        )
        tag_promo, has_promo_badge = _extract_ww_promo_tags(
            entry.get("promotions")
            or entry.get("promoBadges")
            or entry.get("p_promotion")
            or entry.get("promotionText")
        )

        effective_promo = tag_promo or sale_price
        if not list_price and not effective_promo:
            continue

        raw_price: str
        raw_promo_price: Optional[str] = None
        is_promotional = bool(
            has_promo_badge
            or effective_promo
            or entry.get("isPromotional")
            or entry.get("onPromotion")
        )

        if effective_promo and effective_promo != list_price:
            raw_price = list_price or effective_promo
            raw_promo_price = effective_promo
            is_promotional = True
        else:
            raw_price = list_price or effective_promo or ""

        raw_category_val = _unwrap_endeca_scalar(
            entry.get("category") or entry.get("p_category") or entry.get("department")
        )
        if not raw_category_val and isinstance(entry.get("breadcrumbs"), list):
            raw_category_val = "/".join(str(b) for b in entry["breadcrumbs"])

        category_slug = (
            infer_category_slug(
                str(raw_category_val) if raw_category_val else None,
                query_term,
                raw_name,
            )
            or default_category_slug
        )

        raw_url = _unwrap_endeca_scalar(
            entry.get("detailPageUrl")
            or entry.get("p_detailPageUrl")
            or entry.get("url")
            or entry.get("productUrl")
        )
        source_url = urljoin(base_url, str(raw_url)) if raw_url else None

        items.append(
            RawScrapedItem(
                retailer_slug="woolworths-food",
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


def parse_woolworths_html(
    html_text: str,
    *,
    base_url: str = "https://www.woolworths.co.za",
    default_category_slug: Optional[str] = None,
    query_term: Optional[str] = None,
) -> list[RawScrapedItem]:
    """Parse Woolworths Food storefront HTML listings into RawScrapedItem list."""
    parser = _WoolworthsHTMLParser()
    parser.feed(html_text)
    parser.close()

    items: list[RawScrapedItem] = []

    for card in parser.cards:
        raw_name = _clean_text(card.get("name") or card.get("title_attr"))
        if not raw_name:
            continue

        brand = _clean_text(card.get("brand") or card.get("data_brand")) or None
        if brand is None and raw_name.lower().startswith(("woolworths ", "wfoods ")):
            brand = "Woolworths"

        barcode = _extract_ww_barcode(
            ean=card.get("data_ean"),
            sku=card.get("data_sku"),
        )
        raw_unit = _clean_text(card.get("unit") or card.get("data_size")) or None

        was_price = _extract_ww_price(card.get("was"))
        shelf_price = _extract_ww_price(card.get("price"))
        promo_price, has_promo_tag = _extract_ww_promo_tags(
            card.get("promo") or card.get("data_promo")
        )

        if not shelf_price and not was_price and not promo_price:
            continue

        raw_price: str
        raw_promo_price: Optional[str] = None
        is_promotional = bool(card.get("has_promo_badge") or has_promo_tag)

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
                retailer_slug="woolworths-food",
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


class WoolworthsScraper(BaseRetailerScraper):
    """Live catalog scraper for Woolworths Food South Africa (`woolworths-food`)."""

    retailer_slug = "woolworths-food"
    base_url = "https://www.woolworths.co.za"
    search_path = "/server/searchCategory"

    def __init__(self, *, max_pages: int = 1, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.max_pages = max(1, max_pages)

    @property
    def default_queries(self) -> list[str]:
        return [term for terms in DEFAULT_CORE_STAPLES.values() for term in terms]

    async def scrape_catalog(self, query_terms: list[str]) -> list[RawScrapedItem]:
        """Query Woolworths Food catalog search and extract RawScrapedItem list."""
        terms = [t.strip() for t in query_terms if t.strip()] or self.default_queries
        collected: list[RawScrapedItem] = []
        seen_keys: set[str] = set()

        for term in terms:
            default_cat = infer_category_slug(query_term=term)
            for page in range(self.max_pages):
                page_url = f"/cat?Ntt={term}"
                if page > 0:
                    page_url = f"{page_url}&No={page * 24}"
                params: dict[str, Any] = {
                    "pageURL": page_url,
                    "format": "json",
                }
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
                        page_items = parse_woolworths_json(
                            payload,
                            base_url=self.base_url,
                            default_category_slug=default_cat,
                            query_term=term,
                        )
                else:
                    page_items = parse_woolworths_html(
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
