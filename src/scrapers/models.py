"""Pydantic v2 data contracts for the Phase 3 live scraper & normalizer pipeline.

Enforces exact Decimal precision (NUMERIC(10, 2)) for ZAR prices and standardized
package unit sizes across all 5 South African national supermarket chains.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

CanonicalRetailerSlug = Literal[
    "shoprite",
    "checkers",
    "pick-n-pay",
    "woolworths-food",
    "spar",
]

CanonicalUnitType = Literal["L", "ml", "kg", "g", "unit"]

TWO_DECIMAL_PLACES = Decimal("0.01")


class RawScrapedItem(BaseModel):
    """Unnormalized item extracted directly from a retailer web storefront or API."""

    model_config = ConfigDict(str_strip_whitespace=True)

    retailer_slug: str = Field(
        min_length=2,
        max_length=100,
        description="Canonical retailer slug (e.g. 'checkers', 'shoprite')",
    )
    raw_name: str = Field(
        min_length=1,
        max_length=300,
        description="Raw product title scraped from retailer listing",
    )
    raw_price: str = Field(
        min_length=1,
        max_length=100,
        description="Raw ZAR price string (e.g. 'R 34.99', 'R39.99 / ea', '2 FOR R60')",
    )
    raw_promo_price: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Optional promotional price string if listed separately",
    )
    brand: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Raw brand name if explicitly structured by retailer",
    )
    barcode: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Raw EAN-13 / EAN-8 / GTIN barcode if available",
    )
    category_slug: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Optional mapped SmartBasket category slug",
    )
    raw_unit: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Optional package size string (e.g. '2 Litre', '2000ml', '700g')",
    )
    is_promotional: bool = Field(
        default=False,
        description="Whether retailer explicitly flagged item as promotional",
    )
    source_url: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Source storefront URL or API endpoint reference",
    )
    scraped_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when the raw item was extracted",
    )

    @field_validator("retailer_slug")
    @classmethod
    def normalize_slug(cls, value: str) -> str:
        return value.strip().lower()


class NormalizedPriceRecord(BaseModel):
    """Tidy, schema-validated price record ready for canonical chain DB publishing."""

    model_config = ConfigDict(str_strip_whitespace=True)

    retailer_slug: str = Field(
        min_length=2,
        max_length=100,
        description="Canonical national retailer chain slug",
    )
    name: str = Field(
        min_length=1,
        max_length=200,
        description="Cleaned universal product display name",
    )
    brand: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Cleaned brand name",
    )
    barcode: Optional[str] = Field(
        default=None,
        max_length=64,
        description="Validated digits-only EAN/GTIN barcode when present",
    )
    category_slug: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Optional SmartBasket category slug",
    )
    unit_size: Decimal = Field(
        gt=Decimal("0.00"),
        description="Standardized numeric package size (NUMERIC(10, 2))",
    )
    unit_type: CanonicalUnitType = Field(
        description="Canonical unit of measure ('L', 'ml', 'kg', 'g', 'unit')",
    )
    price: Decimal = Field(
        gt=Decimal("0.00"),
        description="Exact single-unit shelf price in ZAR (NUMERIC(10, 2))",
    )
    is_promotional: bool = Field(
        default=False,
        description="True when active price reflects a promotion or multi-buy deal",
    )
    multi_buy_quantity: Optional[int] = Field(
        default=None,
        ge=2,
        description="Bundle unit count for multi-buy deals (e.g. 2 for '2 FOR R60')",
    )
    multi_buy_total: Optional[Decimal] = Field(
        default=None,
        gt=Decimal("0.00"),
        description="Bundle total in ZAR for multi-buy promotions",
    )
    source_url: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Originating source URL for auditability",
    )
    scraped_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC observation timestamp",
    )

    @field_validator("price", "unit_size")
    @classmethod
    def quantize_two_decimals(cls, value: Decimal) -> Decimal:
        return Decimal(value).quantize(TWO_DECIMAL_PLACES, rounding=ROUND_HALF_UP)

    @field_validator("multi_buy_total")
    @classmethod
    def quantize_optional_decimal(cls, value: Optional[Decimal]) -> Optional[Decimal]:
        if value is None:
            return None
        return Decimal(value).quantize(TWO_DECIMAL_PLACES, rounding=ROUND_HALF_UP)


class PublishSummary(BaseModel):
    """Telemetry summary returned by CatalogPublisher after a publish run."""

    retailer_slug: str = Field(description="Target national retailer chain slug")
    dry_run: bool = Field(
        default=False, description="True when no DB mutations were committed"
    )
    status: Literal["ok", "partial", "failed"] = Field(
        default="ok",
        description="Execution outcome for this retailer ('ok', 'partial', 'failed')",
    )
    error: Optional[str] = Field(
        default=None,
        description="Structured error description when retailer scrape/publish failed",
    )
    duration_seconds: float = Field(
        default=0.0,
        ge=0.0,
        description="Wall-clock execution duration for this retailer in seconds",
    )
    synced_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC completion timestamp for this retailer run",
    )
    records_processed: int = Field(default=0, ge=0)
    products_matched: int = Field(default=0, ge=0)
    products_created: int = Field(default=0, ge=0)
    prices_inserted: int = Field(default=0, ge=0)
    prices_updated: int = Field(default=0, ge=0)
    prices_unchanged: int = Field(default=0, ge=0)
    history_appended: int = Field(default=0, ge=0)
    skipped: int = Field(default=0, ge=0)
