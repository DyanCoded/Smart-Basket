"""Structured JSON & CSV catalog price feed loader for offline/partner snapshots.

Allows ingesting pre-collected or partner-provided South African national chain
price snapshots via `--source-dir` through the exact same `normalizer.py` and
`publisher.py` pipeline into `store_prices` and `price_history`.
"""

from __future__ import annotations

import csv
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from src.scrapers.base import BaseRetailerScraper
from src.scrapers.models import RawScrapedItem

logger = logging.getLogger(__name__)

_CANONICAL_SLUGS = {
    "shoprite",
    "checkers",
    "pick-n-pay",
    "woolworths-food",
    "spar",
}

_TRUE_STRINGS = {"true", "1", "yes", "y", "on"}


def _parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in _TRUE_STRINGS


def _parse_optional_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


def _parse_scraped_at(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    if value:
        text = str(value).strip()
        if text:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
            return (
                parsed
                if parsed.tzinfo is not None
                else parsed.replace(tzinfo=timezone.utc)
            )
    return datetime.now(timezone.utc)


def _infer_slug_from_filename(path: Path) -> Optional[str]:
    stem = path.stem.lower().replace("_", "-")
    for slug in _CANONICAL_SLUGS:
        if stem == slug or stem.startswith(f"{slug}-"):
            return slug
    return None


def _row_to_raw_item(
    row: dict[str, Any],
    *,
    default_retailer_slug: Optional[str] = None,
) -> Optional[RawScrapedItem]:
    """Convert a JSON/CSV dict row into a validated RawScrapedItem."""
    retailer = _parse_optional_str(
        row.get("retailer_slug")
        or row.get("retailer")
        or row.get("chain")
        or default_retailer_slug
    )
    raw_name = _parse_optional_str(
        row.get("raw_name")
        or row.get("name")
        or row.get("product_name")
        or row.get("title")
    )
    raw_price = _parse_optional_str(
        row.get("raw_price") or row.get("price") or row.get("regular_price")
    )
    if not retailer or not raw_name or not raw_price:
        return None

    raw_promo_price = _parse_optional_str(
        row.get("raw_promo_price")
        or row.get("promo_price")
        or row.get("promotional_price")
        or row.get("special_price")
    )
    brand = _parse_optional_str(row.get("brand"))
    barcode = _parse_optional_str(
        row.get("barcode") or row.get("ean") or row.get("gtin")
    )
    category_slug = _parse_optional_str(row.get("category_slug") or row.get("category"))
    raw_unit = _parse_optional_str(
        row.get("raw_unit")
        or row.get("unit")
        or row.get("pack_size")
        or row.get("size")
    )
    source_url = _parse_optional_str(row.get("source_url") or row.get("url"))
    is_promotional = _parse_bool(row.get("is_promotional")) or bool(raw_promo_price)
    scraped_at = _parse_scraped_at(row.get("scraped_at"))

    return RawScrapedItem(
        retailer_slug=retailer.lower(),
        raw_name=raw_name,
        raw_price=raw_price,
        raw_promo_price=raw_promo_price,
        brand=brand,
        barcode=barcode,
        category_slug=category_slug,
        raw_unit=raw_unit,
        is_promotional=is_promotional,
        source_url=source_url,
        scraped_at=scraped_at,
    )


def load_feed_items_from_file(
    file_path: Path,
    *,
    default_retailer_slug: Optional[str] = None,
) -> list[RawScrapedItem]:
    """Load RawScrapedItem rows from a single JSON or CSV price feed file."""
    suffix = file_path.suffix.lower()
    inferred_slug = default_retailer_slug or _infer_slug_from_filename(file_path)
    items: list[RawScrapedItem] = []

    if suffix == ".json":
        payload = json.loads(file_path.read_text(encoding="utf-8-sig"))
        if isinstance(payload, list):
            rows = payload
            file_slug = inferred_slug
        elif isinstance(payload, dict):
            file_slug = (
                _parse_optional_str(
                    payload.get("retailer_slug") or payload.get("retailer")
                )
                or inferred_slug
            )
            rows = (
                payload.get("items")
                or payload.get("products")
                or payload.get("records")
                or []
            )
        else:
            rows = []
            file_slug = inferred_slug

        for idx, row in enumerate(rows):
            if not isinstance(row, dict):
                continue
            item = _row_to_raw_item(row, default_retailer_slug=file_slug)
            if item is None:
                logger.warning(
                    "Skipping incomplete JSON row %d in %s", idx, file_path.name
                )
                continue
            items.append(item)

    elif suffix == ".csv":
        with file_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            for idx, row in enumerate(reader, start=1):
                item = _row_to_raw_item(row, default_retailer_slug=inferred_slug)
                if item is None:
                    logger.warning(
                        "Skipping incomplete CSV row %d in %s", idx, file_path.name
                    )
                    continue
                items.append(item)
    else:
        logger.debug("Ignoring unsupported feed file %s", file_path.name)

    return items


def load_feed_items_from_dir(
    source_dir: Path,
    *,
    retailer_slugs: Optional[list[str]] = None,
) -> dict[str, list[RawScrapedItem]]:
    """Scan a directory of JSON/CSV feed snapshots and group items by retailer slug."""
    if not source_dir.exists() or not source_dir.is_dir():
        raise FileNotFoundError(
            f"Catalog feed source directory does not exist: {source_dir}"
        )

    allowed = {s.strip().lower() for s in retailer_slugs} if retailer_slugs else None
    grouped: dict[str, list[RawScrapedItem]] = {}

    for path in sorted(source_dir.iterdir()):
        if not path.is_file() or path.suffix.lower() not in {".json", ".csv"}:
            continue
        for item in load_feed_items_from_file(path):
            if allowed is not None and item.retailer_slug not in allowed:
                continue
            grouped.setdefault(item.retailer_slug, []).append(item)

    return grouped


class FeedSnapshotScraper(BaseRetailerScraper):
    """BaseRetailerScraper adapter backed by local JSON/CSV feed snapshot items."""

    def __init__(
        self,
        retailer_slug: str,
        items: list[RawScrapedItem],
        **kwargs: Any,
    ) -> None:
        self.retailer_slug = retailer_slug.strip().lower()
        super().__init__(min_delay_seconds=0.0, **kwargs)
        self._items = list(items)

    async def scrape_catalog(self, query_terms: list[str]) -> list[RawScrapedItem]:
        """Return pre-loaded snapshot items, optionally filtered by query_terms."""
        cleaned_terms = [t.strip().lower() for t in query_terms if t.strip()]
        if not cleaned_terms:
            return list(self._items)
        return [
            item
            for item in self._items
            if any(
                term in item.raw_name.lower()
                or (item.brand and term in item.brand.lower())
                for term in cleaned_terms
            )
        ]
