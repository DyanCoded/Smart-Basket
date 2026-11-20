"""Phase 3 live data scraper, tidy-data normalizer, and catalog publisher package."""

from src.scrapers.base import BaseRetailerScraper, PlaceholderFixtureScraper
from src.scrapers.models import (
    CanonicalRetailerSlug,
    CanonicalUnitType,
    NormalizedPriceRecord,
    PublishSummary,
    RawScrapedItem,
)
from src.scrapers.normalizer import (
    ParsedPrice,
    clean_barcode,
    match_product,
    normalize_scraped_item,
    normalize_text_key,
    normalize_unit,
    parse_zar_price,
)
from src.scrapers.publisher import (
    CatalogPublisher,
    publish_normalized_records,
    resolve_canonical_store,
)
from src.scrapers.retailers import (
    CheckersScraper,
    PickNPayScraper,
    ShopriteGroupBaseScraper,
    ShopriteScraper,
)

__all__ = [
    "BaseRetailerScraper",
    "PlaceholderFixtureScraper",
    "ShopriteGroupBaseScraper",
    "CheckersScraper",
    "ShopriteScraper",
    "PickNPayScraper",
    "CanonicalRetailerSlug",
    "CanonicalUnitType",
    "RawScrapedItem",
    "NormalizedPriceRecord",
    "PublishSummary",
    "ParsedPrice",
    "parse_zar_price",
    "normalize_unit",
    "clean_barcode",
    "normalize_text_key",
    "normalize_scraped_item",
    "match_product",
    "resolve_canonical_store",
    "CatalogPublisher",
    "publish_normalized_records",
]
