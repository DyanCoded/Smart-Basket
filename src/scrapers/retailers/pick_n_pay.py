"""Pick n Pay live catalog scraper adapter (South African national chain).

Targets Pick n Pay Online (www.pnp.co.za) SAP Commerce Cloud OCC v2 JSON search
endpoints and Angular Spartacus storefront HTML listings, extracting standard
shelf prices, Smart Shopper loyalty / promotional pricing, multi-buy deals,
barcodes/EANs, and package units into RawScrapedItem contracts.
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

# Anti-bot / WAF challenge markers (halted respectfully without bypass)
_ANTI_BOT_MARKERS: tuple[str, ...] = (
    "cf-browser-verification",
    "attention required! | cloudflare",
    "verify you are human",
    "request unsuccessful. incapsula",
    "/_incapsula_resource",
    "g-recaptcha",
    "h-captcha",
)

_MULTI_BUY_RE = re.compile(
    r"(?:buy\s+)?\d+\s*(?:for|@)\s*(?:zar|r)?\s*\d[\d\s,]*(?:[.,]\d{1,2})?",
    re.IGNORECASE,
)
# Explicit final price after promo verbs: "Pay R32.99", "Now R32.99", "Only R32.99"
_PAY_PRICE_RE = re.compile(
    r"(?:pay|now|only|smart\s*shopper\s*:?)\s*(?:zar|r)\s*\d[\d\s,]*(?:[.,]\d{1,2})?",
    re.IGNORECASE,
)
# Guard against discount-only labels like "Save R6.00" (not a shelf price)
_SAVE_ONLY_RE = re.compile(
    r"^\s*(?:smart\s*shopper\s+)?save\s+(?:up\s+to\s+)?(?:zar|r)\s*\d",
    re.IGNORECASE,
)
_RAND_RE = re.compile(
    r"(?:zar|r)\s*\d[\d\s,]*(?:[.,]\d{1,2})?",
    re.IGNORECASE,
)
_PURE_EAN_RE = re.compile(r"^\d{8,14}$")
_WHITESPACE_RE = re.compile(r"\s+")


def _clean_text(value: Optional[str]) -> str:
    if not value:
        return ""
    return _WHITESPACE_RE.sub(
        " ", html_lib.unescape(value).replace("\xa0", " ")
    ).strip()


def _extract_pnp_price(
    raw_text: Optional[str],
    *,
    is_promo_description: bool = False,
) -> Optional[str]:
    """Extract a clean ZAR or multi-buy price expression from PnP text.

    Guards against mistakenly treating discount-only copy (e.g. 'Save R6.00')
    as the product's actual shelf price.
    """
    text = _clean_text(raw_text)
    if not text:
        return None

    multi = _MULTI_BUY_RE.search(text)
    if multi:
        return _clean_text(multi.group(0))

    pay_match = _PAY_PRICE_RE.search(text)
    if pay_match:
        rand_inside = _RAND_RE.search(pay_match.group(0))
        if rand_inside:
            return _clean_text(rand_inside.group(0))

    if is_promo_description and _SAVE_ONLY_RE.match(text):
        return None

    rand = _RAND_RE.search(text)
    if rand:
        return _clean_text(rand.group(0))

    return None if is_promo_description else text


def _extract_pnp_barcode(
    ean: Any = None,
    barcodes: Any = None,
    sku: Any = None,
) -> Optional[str]:
    """Extract digits-only EAN/GTIN barcode; ignore non-EAN internal PnP SKUs."""
    candidates: list[Any] = []
    if ean:
        candidates.append(ean)
    if isinstance(barcodes, list):
        candidates.extend(barcodes)
    elif barcodes:
        candidates.append(barcodes)

    for candidate in candidates:
        digits = re.sub(r"\D+", "", str(candidate))
        if 8 <= len(digits) <= 14:
            return digits

    if sku:
        sku_str = str(sku).strip()
        if _PURE_EAN_RE.match(sku_str):
            return sku_str

    return None


def _extract_json_price(
    value: Any, *, is_promo_description: bool = False
) -> Optional[str]:
    """Parse flat or SAP Commerce OCC price objects into a Rand/promo string."""
    if value is None:
        return None
    if isinstance(value, dict):
        formatted = (
            value.get("formattedValue")
            or value.get("formatted")
            or value.get("display")
        )
        if formatted:
            return _extract_pnp_price(
                str(formatted), is_promo_description=is_promo_description
            )
        numeric = value.get("value") or value.get("amount")
        if numeric is not None:
            return f"R {numeric}"
        return None
    if isinstance(value, (int, float)):
        return f"R {value}"
    return _extract_pnp_price(str(value), is_promo_description=is_promo_description)


def _extract_promotion_from_occ_list(promotions: Any) -> Optional[str]:
    """Inspect SAP Commerce OCC `potentialPromotions` for Smart Shopper / multi-buy."""
    if not isinstance(promotions, list):
        return None
    for promo in promotions:
        if not isinstance(promo, dict):
            continue
        for key in ("smartShopperPrice", "promoPrice", "promotionalPrice", "price"):
            price_val = _extract_json_price(promo.get(key))
            if price_val:
                return price_val
        for text_key in ("description", "title", "promotionText", "label"):
            extracted = _extract_pnp_price(
                promo.get(text_key), is_promo_description=True
            )
            if extracted:
                return extracted
    return None


def _is_anti_bot_challenge(status_code: int, body: str) -> bool:
    if status_code in (403, 451):
        return True
    lowered = body[:4000].lower()
    return any(marker in lowered for marker in _ANTI_BOT_MARKERS)


class _PickNPayHTMLParser(HTMLParser):
    """Lightweight stdlib HTMLParser for Pick n Pay storefront product cards."""

    _CARD_CLASSES = {
        "product-grid-item",
        "product-carousel-item",
        "product-card",
        "item-product",
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
            if field in ("current", "was", "promo"):
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
                    "data_sku": (
                        attrs_dict.get("data-sku")
                        or attrs_dict.get("data-product-code")
                    ),
                    "data_ean": (
                        attrs_dict.get("data-ean") or attrs_dict.get("data-barcode")
                    ),
                    "data_brand": attrs_dict.get("data-brand"),
                    "data_unit": (
                        attrs_dict.get("data-unit") or attrs_dict.get("data-size")
                    ),
                    "data_category": attrs_dict.get("data-category"),
                    "data_promo_price": (
                        attrs_dict.get("data-smart-shopper-price")
                        or attrs_dict.get("data-promo-price")
                    ),
                    "has_promo_badge": False,
                }
            return

        self._card_depth += 1

        if tag == "a":
            href = attrs_dict.get("href")
            if href and (
                "product-action" in classes
                or "product-card__link" in classes
                or not self._current_card.get("href")
            ):
                self._current_card["href"] = href
            title_attr = attrs_dict.get("title")
            if title_attr:
                self._current_card.setdefault("title_attr", title_attr)

        if any(
            badge in classes
            for badge in (
                "smart-shopper-badge",
                "promo-badge",
                "promotion-badge",
                "on-promotion",
            )
        ):
            self._current_card["has_promo_badge"] = True

        if self._active_capture is not None:
            self._capture_depth += 1
            if tag == "sup":
                self._in_sup = True
            return

        if classes & {"product-grid-item__name", "item-name", "product-card__title"}:
            self._begin_capture("name")
        elif classes & {"product-grid-item__brand", "product-card__brand"}:
            self._begin_capture("brand")
        elif classes & {"product-grid-item__size", "product-card__unit"}:
            self._begin_capture("unit")
        elif classes & {"price-current", "item-price", "product-price__current"}:
            self._begin_capture("current")
        elif classes & {"price-old", "was-price", "product-price__was"}:
            self._begin_capture("was")
        elif classes & {
            "smart-shopper-price",
            "promo-price",
            "promotion-badge__price",
        }:
            self._begin_capture("promo")

    def handle_data(self, data: str) -> None:
        if not self._in_card or self._active_capture is None:
            return
        if self._in_sup and self._active_capture in ("current", "was", "promo"):
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


def parse_pnp_json(
    payload: dict[str, Any],
    *,
    base_url: str = "https://www.pnp.co.za",
    default_category_slug: Optional[str] = None,
    query_term: Optional[str] = None,
) -> list[RawScrapedItem]:
    """Parse Pick n Pay SAP Commerce OCC v2 JSON search response into RawScrapedItem."""
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

        brand = (
            _clean_text(
                entry.get("brand")
                or entry.get("brandName")
                or entry.get("manufacturer")
            )
            or None
        )

        barcode = _extract_pnp_barcode(
            ean=entry.get("ean") or entry.get("barcode") or entry.get("gtin"),
            barcodes=entry.get("barcodes"),
            sku=entry.get("code") or entry.get("sku"),
        )

        raw_unit = (
            _clean_text(
                entry.get("size")
                or entry.get("packSize")
                or entry.get("unitOfMeasure")
                or entry.get("quantityDescription")
            )
            or None
        )

        was_price = _extract_json_price(
            entry.get("wasPrice") or entry.get("oldPrice") or entry.get("regularPrice")
        )
        current_price = _extract_json_price(entry.get("price"))
        promo_price = _extract_json_price(
            entry.get("smartShopperPrice")
            or entry.get("promotionPrice")
            or entry.get("promotionalPrice")
            or entry.get("promoPrice"),
            is_promo_description=True,
        ) or _extract_promotion_from_occ_list(entry.get("potentialPromotions"))

        if not current_price and not was_price and not promo_price:
            continue

        raw_price: str
        raw_promo_price: Optional[str] = None
        is_promotional = bool(
            entry.get("isPromotional")
            or entry.get("onPromotion")
            or entry.get("smartShopperPromo")
        )

        if promo_price:
            raw_price = was_price or current_price or promo_price
            raw_promo_price = promo_price
            is_promotional = True
        elif was_price and current_price and was_price != current_price:
            raw_price = was_price
            raw_promo_price = current_price
            is_promotional = True
        else:
            raw_price = current_price or was_price or ""

        raw_category: Optional[str] = None
        categories_field = entry.get("categories")
        if isinstance(categories_field, list):
            cat_names = [
                str(c.get("name", "")) if isinstance(c, dict) else str(c)
                for c in categories_field
            ]
            raw_category = "/".join(c for c in cat_names if c)
        elif entry.get("category") or entry.get("department"):
            raw_category = str(entry.get("category") or entry.get("department"))

        category_slug = (
            infer_category_slug(raw_category, query_term, raw_name)
            or default_category_slug
        )

        raw_url = entry.get("url") or entry.get("productUrl")
        source_url = urljoin(base_url, str(raw_url)) if raw_url else None

        items.append(
            RawScrapedItem(
                retailer_slug="pick-n-pay",
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


def parse_pnp_html(
    html_text: str,
    *,
    base_url: str = "https://www.pnp.co.za",
    default_category_slug: Optional[str] = None,
    query_term: Optional[str] = None,
) -> list[RawScrapedItem]:
    """Parse Pick n Pay storefront HTML product cards into RawScrapedItem list."""
    parser = _PickNPayHTMLParser()
    parser.feed(html_text)
    parser.close()

    items: list[RawScrapedItem] = []

    for card in parser.cards:
        raw_name = _clean_text(card.get("name") or card.get("title_attr"))
        if not raw_name:
            continue

        brand = _clean_text(card.get("brand") or card.get("data_brand")) or None
        barcode = _extract_pnp_barcode(
            ean=card.get("data_ean"),
            sku=card.get("data_sku"),
        )
        raw_unit = _clean_text(card.get("unit") or card.get("data_unit")) or None

        current_price = _extract_pnp_price(card.get("current"))
        was_price = _extract_pnp_price(card.get("was"))
        promo_price = _extract_pnp_price(
            card.get("promo") or card.get("data_promo_price"),
            is_promo_description=True,
        )

        if not current_price and not was_price and not promo_price:
            continue

        raw_price: str
        raw_promo_price: Optional[str] = None
        is_promotional = bool(card.get("has_promo_badge"))

        if promo_price:
            raw_price = was_price or current_price or promo_price
            raw_promo_price = promo_price
            is_promotional = True
        elif was_price and current_price and was_price != current_price:
            raw_price = was_price
            raw_promo_price = current_price
            is_promotional = True
        else:
            raw_price = current_price or was_price or ""

        category_slug = (
            infer_category_slug(card.get("data_category"), query_term, raw_name)
            or default_category_slug
        )

        href = card.get("href")
        source_url = urljoin(base_url, href) if href else None

        items.append(
            RawScrapedItem(
                retailer_slug="pick-n-pay",
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


class PickNPayScraper(BaseRetailerScraper):
    """Live catalog scraper for Pick n Pay South Africa (`pick-n-pay`)."""

    retailer_slug = "pick-n-pay"
    base_url = "https://www.pnp.co.za"
    search_path = "/pnphybris/occ/v2/pnp-spa/products/search"

    def __init__(
        self,
        *,
        max_pages: int = 1,
        page_size: int = 24,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.max_pages = max(1, max_pages)
        self.page_size = max(1, page_size)

    @property
    def default_queries(self) -> list[str]:
        return [term for terms in DEFAULT_CORE_STAPLES.values() for term in terms]

    async def scrape_catalog(self, query_terms: list[str]) -> list[RawScrapedItem]:
        """Query Pick n Pay catalog search endpoint and extract RawScrapedItem list."""
        terms = [t.strip() for t in query_terms if t.strip()] or self.default_queries
        collected: list[RawScrapedItem] = []
        seen_keys: set[str] = set()

        for term in terms:
            default_cat = infer_category_slug(query_term=term)
            for page in range(self.max_pages):
                params: dict[str, Any] = {
                    "query": term,
                    "fields": "FULL",
                    "pageSize": self.page_size,
                    "currentPage": page,
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
                        page_items = parse_pnp_json(
                            payload,
                            base_url=self.base_url,
                            default_category_slug=default_cat,
                            query_term=term,
                        )
                else:
                    page_items = parse_pnp_html(
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
