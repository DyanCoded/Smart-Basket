"""Tidy-data cleaning, SA Rand currency parsing, unit standardization & matching.

Converts messy retailer storefront strings into schema-validated NormalizedPriceRecord
objects using exact Decimal arithmetic (ADR-003) and reconciles items against the
universal SmartBasket product catalog (EAN/barcode first, normalized brand+name+unit
fallback).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.entities import Product
from src.scrapers.models import (
    TWO_DECIMAL_PLACES,
    CanonicalUnitType,
    NormalizedPriceRecord,
    RawScrapedItem,
)

# Multi-buy promo patterns: "2 FOR R60", "3 for R 99.00", "Buy 2 for R50", "2 @ R45"
_MULTI_BUY_RE = re.compile(
    r"(?:buy\s+)?(?P<qty>\d+)\s*(?:for|@)\s*(?:zar|r)?\s*(?P<amount>[\d\s,]+(?:[.,]\d{1,2})?)",
    re.IGNORECASE,
)

# Cents-only pricing: "99c", "59 c"
_CENTS_RE = re.compile(r"^\s*(?P<cents>\d{1,3})\s*c(?:ents?)?\b", re.IGNORECASE)

# Standard Rand pricing: "R 34.99", "R39.99 / ea", "ZAR 1,299.50", "34.99"
_RAND_RE = re.compile(
    r"(?:zar|r)?\s*(?P<amount>\d[\d\s,]*(?:[.,]\d{1,2})?)",
    re.IGNORECASE,
)

# Negative price guard: "-R10", "R -10.00", "-10.00"
_NEGATIVE_RE = re.compile(
    r"(?:^|\s)-\s*(?:zar|r)?\s*\d|(?:zar|r)\s*-\s*\d",
    re.IGNORECASE,
)

# Multipack pattern: "6 x 1L", "6x330ml", "12 x 250g", "2 x 2 Litre"
_MULTIPACK_RE = re.compile(
    r"(?P<count>\d+)\s*[xX×]\s*(?P<size>\d+(?:[.,]\d+)?)\s*"
    r"(?P<unit>ml|millilitres?|milliliters?|litres?|liters?|ltrs?|ltr|lt|l|"
    r"kg|kilograms?|kilos?|grams?|gr|g)\b",
    re.IGNORECASE,
)

# Single volume/mass pattern: "2 Litre", "2000ml", "2L", "700g", "2.5 kg"
_MEASURE_UNIT_RE = re.compile(
    r"(?P<size>\d+(?:[.,]\d+)?)\s*"
    r"(?P<unit>ml|millilitres?|milliliters?|litres?|liters?|ltrs?|ltr|lt|l|"
    r"kg|kilograms?|kilos?|grams?|gr|g)\b",
    re.IGNORECASE,
)

# Count/pack pattern: "18pk", "18 pack", "18-pack", "18s", "18's", "80 bags", "2 units"
_COUNT_UNIT_RE = re.compile(
    r"(?P<size>\d+)\s*(?:-\s*)?"
    r"(?:pk|pack|packs|pck|units?|pcs|pieces?|ea|each|count|ct|'s|s)\b",
    re.IGNORECASE,
)

# Unit tokens stripped during fuzzy name comparison
_STRIP_UNIT_TOKENS_RE = re.compile(
    r"\b\d+\s*[xX×]\s*\d+(?:[.,]\d+)?\s*"
    r"(?:ml|millilitres?|milliliters?|litres?|liters?|ltrs?|ltr|lt|l|"
    r"kg|kilograms?|kilos?|grams?|gr|g)\b|"
    r"\b\d+(?:[.,]\d+)?\s*"
    r"(?:ml|millilitres?|milliliters?|litres?|liters?|ltrs?|ltr|lt|l|"
    r"kg|kilograms?|kilos?|grams?|gr|g)\b|"
    r"\b\d+\s*(?:-\s*)?(?:pk|pack|packs|pck|units?|pcs|pieces?|ea|each|count|ct|'s|s)\b",
    re.IGNORECASE,
)

_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")
_WHITESPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class ParsedPrice:
    """Structured result of parsing a South African Rand shelf or promo price string."""

    unit_price: Decimal
    is_promotional: bool = False
    multi_buy_quantity: Optional[int] = None
    multi_buy_total: Optional[Decimal] = None


def _parse_numeric_amount(raw_amount: str) -> Decimal:
    """Parse a formatted numeric string into a quantized Decimal.

    Handles thousands separators ('1,299.50', '1 299.50') and South African
    comma decimal notation ('34,99').
    """
    cleaned = raw_amount.replace("\xa0", " ").strip()
    cleaned = re.sub(r"\s+", "", cleaned)

    if not cleaned:
        raise ValueError("Empty numeric price amount")

    if "," in cleaned and "." in cleaned:
        cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        parts = cleaned.split(",")
        if len(parts) == 2 and len(parts[1]) in (1, 2):
            cleaned = f"{parts[0]}.{parts[1]}"
        else:
            cleaned = "".join(parts)

    try:
        value = Decimal(cleaned)
    except InvalidOperation as exc:
        raise ValueError(f"Invalid numeric price amount: {raw_amount!r}") from exc

    return value.quantize(TWO_DECIMAL_PLACES, rounding=ROUND_HALF_UP)


def parse_zar_price(raw_price: str) -> ParsedPrice:
    """Parse messy South African Rand (ZAR) price strings into exact Decimal values.

    Examples:
        - "R 34.99" -> ParsedPrice(unit_price=Decimal("34.99"))
        - "R39.99 / ea" -> ParsedPrice(unit_price=Decimal("39.99"))
        - "2 FOR R60" -> ParsedPrice(unit_price=Decimal("30.00"), is_promotional=True,
                                     multi_buy_quantity=2,
                                     multi_buy_total=Decimal("60.00"))
        - "99c" -> ParsedPrice(unit_price=Decimal("0.99"))
    """
    if not raw_price or not raw_price.strip():
        raise ValueError("Price string must not be empty")

    text = raw_price.replace("\xa0", " ").strip()

    if _NEGATIVE_RE.search(text):
        raise ValueError(f"Price must be positive, got: {raw_price!r}")

    multi_match = _MULTI_BUY_RE.search(text)
    if multi_match:
        qty = int(multi_match.group("qty"))
        total = _parse_numeric_amount(multi_match.group("amount"))
        if qty <= 0 or total <= Decimal("0.00"):
            raise ValueError(f"Invalid multi-buy price expression: {raw_price!r}")
        unit_price = (total / Decimal(qty)).quantize(
            TWO_DECIMAL_PLACES, rounding=ROUND_HALF_UP
        )
        if unit_price <= Decimal("0.00"):
            raise ValueError(f"Computed unit price must be positive: {raw_price!r}")
        if qty >= 2:
            return ParsedPrice(
                unit_price=unit_price,
                is_promotional=True,
                multi_buy_quantity=qty,
                multi_buy_total=total,
            )
        return ParsedPrice(unit_price=unit_price, is_promotional=False)

    cents_match = _CENTS_RE.match(text)
    if cents_match:
        cents = Decimal(cents_match.group("cents"))
        if cents <= 0:
            raise ValueError(f"Price must be positive, got: {raw_price!r}")
        return ParsedPrice(
            unit_price=(cents / Decimal("100")).quantize(
                TWO_DECIMAL_PLACES, rounding=ROUND_HALF_UP
            ),
            is_promotional=False,
        )

    rand_match = _RAND_RE.search(text)
    if rand_match:
        amount = _parse_numeric_amount(rand_match.group("amount"))
        if amount <= Decimal("0.00"):
            raise ValueError(f"Price must be positive, got: {raw_price!r}")
        return ParsedPrice(unit_price=amount, is_promotional=False)

    raise ValueError(f"Could not parse ZAR price from: {raw_price!r}")


def _canonicalize_measure(
    value: Decimal, raw_unit_token: str
) -> tuple[Decimal, CanonicalUnitType]:
    """Convert volume/mass measurements into canonical (unit_size, unit_type)."""
    unit_lower = raw_unit_token.lower()

    if unit_lower in ("ml", "millilitre", "millilitres", "milliliter", "milliliters"):
        if value >= Decimal("1000"):
            return (
                (value / Decimal("1000")).quantize(
                    TWO_DECIMAL_PLACES, rounding=ROUND_HALF_UP
                ),
                "L",
            )
        return (value.quantize(TWO_DECIMAL_PLACES, rounding=ROUND_HALF_UP), "ml")

    if unit_lower in ("l", "lt", "ltr", "ltrs", "litre", "litres", "liter", "liters"):
        if value < Decimal("1"):
            return (
                (value * Decimal("1000")).quantize(
                    TWO_DECIMAL_PLACES, rounding=ROUND_HALF_UP
                ),
                "ml",
            )
        return (value.quantize(TWO_DECIMAL_PLACES, rounding=ROUND_HALF_UP), "L")

    if unit_lower in ("g", "gr", "gram", "grams"):
        if value >= Decimal("1000"):
            return (
                (value / Decimal("1000")).quantize(
                    TWO_DECIMAL_PLACES, rounding=ROUND_HALF_UP
                ),
                "kg",
            )
        return (value.quantize(TWO_DECIMAL_PLACES, rounding=ROUND_HALF_UP), "g")

    if unit_lower in ("kg", "kilo", "kilos", "kilogram", "kilograms"):
        if value < Decimal("1"):
            return (
                (value * Decimal("1000")).quantize(
                    TWO_DECIMAL_PLACES, rounding=ROUND_HALF_UP
                ),
                "g",
            )
        return (value.quantize(TWO_DECIMAL_PLACES, rounding=ROUND_HALF_UP), "kg")

    return (value.quantize(TWO_DECIMAL_PLACES, rounding=ROUND_HALF_UP), "unit")


def normalize_unit(raw_text: Optional[str]) -> tuple[Decimal, CanonicalUnitType]:
    """Standardize package size text into canonical (unit_size, unit_type).

    Examples:
        - "2 Litre" -> (Decimal("2.00"), "L")
        - "2000ml" -> (Decimal("2.00"), "L")
        - "750ml" -> (Decimal("750.00"), "ml")
        - "2000g" -> (Decimal("2.00"), "kg")
        - "700g" -> (Decimal("700.00"), "g")
        - "6 x 330ml" -> (Decimal("1.98"), "L")
        - "18pk" -> (Decimal("18.00"), "unit")
        - "" / None -> (Decimal("1.00"), "unit")
    """
    if not raw_text or not raw_text.strip():
        return (Decimal("1.00"), "unit")

    text = raw_text.replace("\xa0", " ").strip()

    multipack = _MULTIPACK_RE.search(text)
    if multipack:
        count = Decimal(multipack.group("count"))
        each_size = Decimal(multipack.group("size").replace(",", "."))
        total_value = count * each_size
        if total_value > Decimal("0"):
            return _canonicalize_measure(total_value, multipack.group("unit"))

    measure = _MEASURE_UNIT_RE.search(text)
    if measure:
        size = Decimal(measure.group("size").replace(",", "."))
        if size > Decimal("0"):
            return _canonicalize_measure(size, measure.group("unit"))

    count_match = _COUNT_UNIT_RE.search(text)
    if count_match:
        count_val = Decimal(count_match.group("size"))
        if count_val > Decimal("0"):
            return (
                count_val.quantize(TWO_DECIMAL_PLACES, rounding=ROUND_HALF_UP),
                "unit",
            )

    return (Decimal("1.00"), "unit")


def clean_barcode(raw_barcode: Optional[str]) -> Optional[str]:
    """Normalize EAN/GTIN barcode strings to digits-only, returning None if invalid."""
    if not raw_barcode:
        return None
    digits = re.sub(r"\D+", "", raw_barcode)
    if 8 <= len(digits) <= 14:
        return digits
    return None


def _clean_whitespace(text: str) -> str:
    return _WHITESPACE_RE.sub(" ", text.replace("\xa0", " ")).strip()


def normalize_scraped_item(raw: RawScrapedItem) -> NormalizedPriceRecord:
    """Transform a RawScrapedItem into a tidy NormalizedPriceRecord."""
    cleaned_name = _clean_whitespace(raw.raw_name)[:200]
    cleaned_brand = _clean_whitespace(raw.brand)[:100] if raw.brand else None

    # Promotional price overrides regular shelf price when present
    if raw.raw_promo_price and raw.raw_promo_price.strip():
        parsed_price = parse_zar_price(raw.raw_promo_price)
        is_promotional = True
    else:
        parsed_price = parse_zar_price(raw.raw_price)
        is_promotional = raw.is_promotional or parsed_price.is_promotional

    # Prefer explicit raw_unit; fall back to extracting unit from raw_name
    if raw.raw_unit and raw.raw_unit.strip():
        unit_size, unit_type = normalize_unit(raw.raw_unit)
        # If raw_unit had no recognizable measure (e.g. "each") try raw_name
        if unit_type == "unit" and unit_size == Decimal("1.00"):
            name_size, name_type = normalize_unit(cleaned_name)
            if name_type != "unit" or name_size != Decimal("1.00"):
                unit_size, unit_type = name_size, name_type
    else:
        unit_size, unit_type = normalize_unit(cleaned_name)

    return NormalizedPriceRecord(
        retailer_slug=raw.retailer_slug.strip().lower(),
        name=cleaned_name,
        brand=cleaned_brand,
        barcode=clean_barcode(raw.barcode),
        category_slug=(
            raw.category_slug.strip().lower() if raw.category_slug else None
        ),
        unit_size=unit_size,
        unit_type=unit_type,
        price=parsed_price.unit_price,
        is_promotional=is_promotional,
        multi_buy_quantity=parsed_price.multi_buy_quantity,
        multi_buy_total=parsed_price.multi_buy_total,
        source_url=raw.source_url,
        scraped_at=raw.scraped_at,
    )


def normalize_text_key(text: Optional[str]) -> str:
    """Normalize text for deterministic brand/name comparison."""
    if not text:
        return ""
    lowered = text.lower()
    without_units = _STRIP_UNIT_TOKENS_RE.sub(" ", lowered)
    return _NON_ALNUM_RE.sub(" ", without_units).strip()


def _canonical_brand_name_signature(
    brand: Optional[str], name: str
) -> tuple[str, str, str]:
    """Return (norm_brand, norm_name_without_brand, full_combined_key)."""
    norm_brand = normalize_text_key(brand)
    norm_name = normalize_text_key(name)

    name_without_brand = norm_name
    if norm_brand and norm_name.startswith(f"{norm_brand} "):
        name_without_brand = norm_name[len(norm_brand) :].strip()
    elif norm_brand and norm_name == norm_brand:
        name_without_brand = ""

    combined = f"{norm_brand} {name_without_brand}".strip() if norm_brand else norm_name
    return (norm_brand, name_without_brand, combined)


def match_product(
    session: Session,
    record: NormalizedPriceRecord,
) -> Optional[Product]:
    """Reconcile a NormalizedPriceRecord against existing catalog products.

    Matching strategy:
    1. Exact EAN/barcode match (highest fidelity).
    2. Fallback normalized (brand + name + unit_size + unit_type) match across
       products sharing the same canonical unit_size and unit_type.
    """
    if record.barcode:
        by_barcode = session.execute(
            select(Product).where(Product.barcode == record.barcode)
        ).scalar_one_or_none()
        if by_barcode is not None:
            return by_barcode

    candidates = (
        session.execute(
            select(Product).where(
                Product.unit_type == record.unit_type,
                Product.unit_size == record.unit_size,
            )
        )
        .scalars()
        .all()
    )
    if not candidates:
        return None

    rec_brand, rec_name_core, rec_combined = _canonical_brand_name_signature(
        record.brand, record.name
    )

    for product in candidates:
        prod_brand, prod_name_core, prod_combined = _canonical_brand_name_signature(
            product.brand, product.name
        )
        if rec_brand and prod_brand:
            if rec_brand == prod_brand and rec_name_core == prod_name_core:
                return product
        if rec_combined and prod_combined and rec_combined == prod_combined:
            return product

    return None
