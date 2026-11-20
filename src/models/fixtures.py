"""Catalog seed fixtures and test data definitions for Smart Basket.

Models national chain-level pricing across 5 target South African supermarket
retailers (Shoprite, Checkers, Pick n Pay, Woolworths Food, SPAR) without
branch locations or per-store stock inventory overhead.
"""

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

# Fixed namespace UUID for deterministic fixture generation
SEED_NAMESPACE = uuid.UUID("a3b8c4d2-1234-5678-90ab-cdef12345678")


def seed_uuid(name: str) -> uuid.UUID:
    """Generate a deterministic UUID from a unique seed name."""
    return uuid.uuid5(SEED_NAMESPACE, name)


# 1. Retailers (5 Target South African National Supermarket Chains)
RETAILERS: list[dict[str, Any]] = [
    {
        "id": seed_uuid("retailer:checkers"),
        "name": "Checkers",
        "slug": "checkers",
    },
    {
        "id": seed_uuid("retailer:woolworths"),
        "name": "Woolworths Food",
        "slug": "woolworths-food",
    },
    {
        "id": seed_uuid("retailer:pick-n-pay"),
        "name": "Pick n Pay",
        "slug": "pick-n-pay",
    },
    {
        "id": seed_uuid("retailer:spar"),
        "name": "SPAR",
        "slug": "spar",
    },
    {
        "id": seed_uuid("retailer:shoprite"),
        "name": "Shoprite",
        "slug": "shoprite",
    },
]

# 2. Canonical Chain Store Records (1 National Chain Record per Retailer)
STORES: list[dict[str, Any]] = [
    {
        "id": seed_uuid("store:checkers"),
        "retailer_id": seed_uuid("retailer:checkers"),
        "name": "Checkers",
        "branch_code": None,
        "address": None,
        "is_active": True,
    },
    {
        "id": seed_uuid("store:woolworths-food"),
        "retailer_id": seed_uuid("retailer:woolworths"),
        "name": "Woolworths Food",
        "branch_code": None,
        "address": None,
        "is_active": True,
    },
    {
        "id": seed_uuid("store:pick-n-pay"),
        "retailer_id": seed_uuid("retailer:pick-n-pay"),
        "name": "Pick n Pay",
        "branch_code": None,
        "address": None,
        "is_active": True,
    },
    {
        "id": seed_uuid("store:spar"),
        "retailer_id": seed_uuid("retailer:spar"),
        "name": "SPAR",
        "branch_code": None,
        "address": None,
        "is_active": True,
    },
    {
        "id": seed_uuid("store:shoprite"),
        "retailer_id": seed_uuid("retailer:shoprite"),
        "name": "Shoprite",
        "branch_code": None,
        "address": None,
        "is_active": True,
    },
]

# 3. Core Grocery Categories
CATEGORIES: list[dict[str, Any]] = [
    {
        "id": seed_uuid("category:dairy-eggs"),
        "name": "Dairy & Eggs",
        "slug": "dairy-eggs",
        "parent_id": None,
    },
    {
        "id": seed_uuid("category:bakery"),
        "name": "Bakery",
        "slug": "bakery",
        "parent_id": None,
    },
    {
        "id": seed_uuid("category:pantry-staples"),
        "name": "Pantry & Staples",
        "slug": "pantry-staples",
        "parent_id": None,
    },
    {
        "id": seed_uuid("category:fresh-produce"),
        "name": "Fresh Produce",
        "slug": "fresh-produce",
        "parent_id": None,
    },
    {
        "id": seed_uuid("category:beverages"),
        "name": "Beverages",
        "slug": "beverages",
        "parent_id": None,
    },
]

# 4. Universal Products (18 standard items across categories)
PRODUCTS: list[dict[str, Any]] = [
    # Dairy & Eggs
    {
        "id": seed_uuid("product:clover-milk-2l"),
        "category_id": seed_uuid("category:dairy-eggs"),
        "name": "Full Cream Fresh Milk 2L",
        "brand": "Clover",
        "barcode": "6001299011011",
        "unit_size": Decimal("2.00"),
        "unit_type": "L",
    },
    {
        "id": seed_uuid("product:farmer-brown-eggs-18pk"),
        "category_id": seed_uuid("category:dairy-eggs"),
        "name": "Large Eggs 18pk",
        "brand": "Farmer Brown",
        "barcode": "6001299011028",
        "unit_size": Decimal("18.00"),
        "unit_type": "unit",
    },
    {
        "id": seed_uuid("product:lurpak-butter-500g"),
        "category_id": seed_uuid("category:dairy-eggs"),
        "name": "Salted Butter 500g",
        "brand": "Lurpak",
        "barcode": "6001299011035",
        "unit_size": Decimal("500.00"),
        "unit_type": "g",
    },
    {
        "id": seed_uuid("product:lancewood-yogurt-1kg"),
        "category_id": seed_uuid("category:dairy-eggs"),
        "name": "Greek Plain Double Cream Yogurt 1kg",
        "brand": "Lancewood",
        "barcode": "6001299011042",
        "unit_size": Decimal("1.00"),
        "unit_type": "kg",
    },
    # Bakery
    {
        "id": seed_uuid("product:albany-white-bread-700g"),
        "category_id": seed_uuid("category:bakery"),
        "name": "Superior Sliced White Bread 700g",
        "brand": "Albany",
        "barcode": "6001299011059",
        "unit_size": Decimal("700.00"),
        "unit_type": "g",
    },
    {
        "id": seed_uuid("product:sasko-brown-bread-700g"),
        "category_id": seed_uuid("category:bakery"),
        "name": "More Slices Brown Bread 700g",
        "brand": "Sasko",
        "barcode": "6001299011066",
        "unit_size": Decimal("700.00"),
        "unit_type": "g",
    },
    {
        "id": seed_uuid("product:butter-croissants-4pk"),
        "category_id": seed_uuid("category:bakery"),
        "name": "Fresh Butter Croissants 4pk",
        "brand": "Bakery Fresh",
        "barcode": "6001299011073",
        "unit_size": Decimal("4.00"),
        "unit_type": "unit",
    },
    # Pantry & Staples
    {
        "id": seed_uuid("product:tastic-rice-2kg"),
        "category_id": seed_uuid("category:pantry-staples"),
        "name": "Long Grain Parboiled White Rice 2kg",
        "brand": "Tastic",
        "barcode": "6001299011080",
        "unit_size": Decimal("2.00"),
        "unit_type": "kg",
    },
    {
        "id": seed_uuid("product:sunfoil-oil-2l"),
        "category_id": seed_uuid("category:pantry-staples"),
        "name": "Pure Sunflower Cooking Oil 2L",
        "brand": "Sunfoil",
        "barcode": "6001299011097",
        "unit_size": Decimal("2.00"),
        "unit_type": "L",
    },
    {
        "id": seed_uuid("product:nescafe-coffee-200g"),
        "category_id": seed_uuid("category:pantry-staples"),
        "name": "Instant Coffee Classic Jar 200g",
        "brand": "Nescafe",
        "barcode": "6001299011103",
        "unit_size": Decimal("200.00"),
        "unit_type": "g",
    },
    {
        "id": seed_uuid("product:huletts-sugar-2-5kg"),
        "category_id": seed_uuid("category:pantry-staples"),
        "name": "Pure White Sugar 2.5kg",
        "brand": "Huletts",
        "barcode": "6001299011110",
        "unit_size": Decimal("2.50"),
        "unit_type": "kg",
    },
    {
        "id": seed_uuid("product:fattis-spaghetti-500g"),
        "category_id": seed_uuid("category:pantry-staples"),
        "name": "Spaghetti Pasta 500g",
        "brand": "Fatti's & Moni's",
        "barcode": "6001299011127",
        "unit_size": Decimal("500.00"),
        "unit_type": "g",
    },
    {
        "id": seed_uuid("product:rhodes-chopped-tomatoes-400g"),
        "category_id": seed_uuid("category:pantry-staples"),
        "name": "Chopped Peeled Tomatoes 400g",
        "brand": "Rhodes Quality",
        "barcode": "6001299011134",
        "unit_size": Decimal("400.00"),
        "unit_type": "g",
    },
    {
        "id": seed_uuid("product:all-gold-sauce-700ml"),
        "category_id": seed_uuid("category:pantry-staples"),
        "name": "Tomato Sauce Bottle 700ml",
        "brand": "All Gold",
        "barcode": "6001299011141",
        "unit_size": Decimal("700.00"),
        "unit_type": "ml",
    },
    # Fresh Produce
    {
        "id": seed_uuid("product:fresh-bananas-1kg"),
        "category_id": seed_uuid("category:fresh-produce"),
        "name": "Fresh Yellow Bananas 1kg",
        "brand": "Fresh Produce",
        "barcode": "6001299011158",
        "unit_size": Decimal("1.00"),
        "unit_type": "kg",
    },
    {
        "id": seed_uuid("product:baby-potatoes-1kg"),
        "category_id": seed_uuid("category:fresh-produce"),
        "name": "Washed Baby Potatoes 1kg",
        "brand": "Fresh Produce",
        "barcode": "6001299011165",
        "unit_size": Decimal("1.00"),
        "unit_type": "kg",
    },
    {
        "id": seed_uuid("product:ripe-avocados-2pk"),
        "category_id": seed_uuid("category:fresh-produce"),
        "name": "Ripe & Ready Hass Avocados 2pk",
        "brand": "Fresh Produce",
        "barcode": "6001299011172",
        "unit_size": Decimal("2.00"),
        "unit_type": "unit",
    },
    # Beverages
    {
        "id": seed_uuid("product:freshpak-rooibos-80pk"),
        "category_id": seed_uuid("category:beverages"),
        "name": "Rooibos Tagless Teabags 80pk",
        "brand": "Freshpak",
        "barcode": "6001299011189",
        "unit_size": Decimal("80.00"),
        "unit_type": "unit",
    },
]

# 5. Chain-Level Active Pricing Matrix (18 products x 5 national chains = 90 records)
# Each entry maps product_key -> { chain_key: (price, is_promotional) }
_CHAIN_PRICE_MATRIX: dict[str, dict[str, tuple[str, bool]]] = {
    "clover-milk-2l": {
        "checkers": ("31.99", True),
        "woolworths-food": ("42.99", False),
        "pick-n-pay": ("38.99", False),
        "spar": ("40.49", False),
        "shoprite": ("33.99", False),
    },
    "farmer-brown-eggs-18pk": {
        "checkers": ("64.99", False),
        "woolworths-food": ("62.99", False),
        "pick-n-pay": ("54.99", True),
        "spar": ("66.49", False),
        "shoprite": ("58.99", False),
    },
    "lurpak-butter-500g": {
        "checkers": ("79.99", False),
        "woolworths-food": ("84.99", False),
        "pick-n-pay": ("69.99", True),
        "spar": ("81.99", False),
        "shoprite": ("77.99", False),
    },
    "lancewood-yogurt-1kg": {
        "checkers": ("49.99", False),
        "woolworths-food": ("56.99", False),
        "pick-n-pay": ("47.99", True),
        "spar": ("52.49", False),
        "shoprite": ("48.99", False),
    },
    "albany-white-bread-700g": {
        "checkers": ("17.99", False),
        "woolworths-food": ("19.99", False),
        "pick-n-pay": ("16.99", False),
        "spar": ("18.49", False),
        "shoprite": ("15.99", False),
    },
    "sasko-brown-bread-700g": {
        "checkers": ("16.99", False),
        "woolworths-food": ("18.99", False),
        "pick-n-pay": ("15.99", False),
        "spar": ("17.49", False),
        "shoprite": ("14.99", False),
    },
    "butter-croissants-4pk": {
        "checkers": ("32.99", False),
        "woolworths-food": ("36.99", False),
        "pick-n-pay": ("31.99", False),
        "spar": ("29.99", True),
        "shoprite": ("30.99", False),
    },
    "tastic-rice-2kg": {
        "checkers": ("39.99", True),
        "woolworths-food": ("49.99", False),
        "pick-n-pay": ("43.99", False),
        "spar": ("44.99", False),
        "shoprite": ("41.99", False),
    },
    "sunfoil-oil-2l": {
        "checkers": ("82.99", False),
        "woolworths-food": ("89.99", False),
        "pick-n-pay": ("74.99", True),
        "spar": ("84.99", False),
        "shoprite": ("76.99", False),
    },
    "nescafe-coffee-200g": {
        "checkers": ("119.99", False),
        "woolworths-food": ("129.99", False),
        "pick-n-pay": ("114.99", False),
        "spar": ("122.99", False),
        "shoprite": ("109.99", False),
    },
    "huletts-sugar-2-5kg": {
        "checkers": ("58.99", False),
        "woolworths-food": ("64.99", False),
        "pick-n-pay": ("56.99", False),
        "spar": ("59.99", False),
        "shoprite": ("54.99", True),
    },
    "fattis-spaghetti-500g": {
        "checkers": ("18.99", False),
        "woolworths-food": ("21.99", False),
        "pick-n-pay": ("17.99", False),
        "spar": ("19.49", False),
        "shoprite": ("16.99", False),
    },
    "rhodes-chopped-tomatoes-400g": {
        "checkers": ("21.99", False),
        "woolworths-food": ("24.99", False),
        "pick-n-pay": ("19.99", True),
        "spar": ("22.49", False),
        "shoprite": ("20.49", False),
    },
    "all-gold-sauce-700ml": {
        "checkers": ("41.99", False),
        "woolworths-food": ("46.99", False),
        "pick-n-pay": ("39.99", False),
        "spar": ("42.99", False),
        "shoprite": ("38.99", False),
    },
    "fresh-bananas-1kg": {
        "checkers": ("24.99", False),
        "woolworths-food": ("28.99", False),
        "pick-n-pay": ("22.99", False),
        "spar": ("25.49", False),
        "shoprite": ("21.99", False),
    },
    "baby-potatoes-1kg": {
        "checkers": ("29.99", False),
        "woolworths-food": ("34.99", False),
        "pick-n-pay": ("27.99", False),
        "spar": ("28.99", False),
        "shoprite": ("26.99", False),
    },
    "ripe-avocados-2pk": {
        "checkers": ("36.99", True),
        "woolworths-food": ("44.99", False),
        "pick-n-pay": ("39.99", False),
        "spar": ("41.99", False),
        "shoprite": ("37.99", False),
    },
    "freshpak-rooibos-80pk": {
        "checkers": ("52.99", False),
        "woolworths-food": ("56.99", False),
        "pick-n-pay": ("49.99", True),
        "spar": ("54.49", False),
        "shoprite": ("51.99", False),
    },
}

STORE_PRICES: list[dict[str, Any]] = [
    {
        "id": seed_uuid(f"price:{prod_key}:{chain_key}"),
        "store_id": seed_uuid(f"store:{chain_key}"),
        "product_id": seed_uuid(f"product:{prod_key}"),
        "price": Decimal(price_str),
        "is_promotional": is_promo,
        "is_in_stock": True,
    }
    for prod_key, chain_prices in _CHAIN_PRICE_MATRIX.items()
    for chain_key, (price_str, is_promo) in chain_prices.items()
]


def generate_price_history_fixtures(
    base_time: datetime | None = None,
) -> list[dict[str, Any]]:
    """Generate 30-60 day national chain price history tracking records."""
    now = base_time or datetime.now(timezone.utc)
    return [
        # Clover Milk 2L at Checkers
        {
            "id": seed_uuid("hist:milk:checkers:60d"),
            "store_id": seed_uuid("store:checkers"),
            "product_id": seed_uuid("product:clover-milk-2l"),
            "price": Decimal("36.99"),
            "is_promotional": False,
            "recorded_at": now - timedelta(days=60),
        },
        {
            "id": seed_uuid("hist:milk:checkers:30d"),
            "store_id": seed_uuid("store:checkers"),
            "product_id": seed_uuid("product:clover-milk-2l"),
            "price": Decimal("38.99"),
            "is_promotional": False,
            "recorded_at": now - timedelta(days=30),
        },
        {
            "id": seed_uuid("hist:milk:checkers:5d"),
            "store_id": seed_uuid("store:checkers"),
            "product_id": seed_uuid("product:clover-milk-2l"),
            "price": Decimal("31.99"),
            "is_promotional": True,
            "recorded_at": now - timedelta(days=5),
        },
        # Sunfoil Oil 2L at Woolworths Food
        {
            "id": seed_uuid("hist:oil:woolworths-food:60d"),
            "store_id": seed_uuid("store:woolworths-food"),
            "product_id": seed_uuid("product:sunfoil-oil-2l"),
            "price": Decimal("84.99"),
            "is_promotional": False,
            "recorded_at": now - timedelta(days=60),
        },
        {
            "id": seed_uuid("hist:oil:woolworths-food:35d"),
            "store_id": seed_uuid("store:woolworths-food"),
            "product_id": seed_uuid("product:sunfoil-oil-2l"),
            "price": Decimal("86.99"),
            "is_promotional": False,
            "recorded_at": now - timedelta(days=35),
        },
        {
            "id": seed_uuid("hist:oil:woolworths-food:10d"),
            "store_id": seed_uuid("store:woolworths-food"),
            "product_id": seed_uuid("product:sunfoil-oil-2l"),
            "price": Decimal("89.99"),
            "is_promotional": False,
            "recorded_at": now - timedelta(days=10),
        },
        # Nescafe Coffee 200g at Pick n Pay
        {
            "id": seed_uuid("hist:coffee:pick-n-pay:45d"),
            "store_id": seed_uuid("store:pick-n-pay"),
            "product_id": seed_uuid("product:nescafe-coffee-200g"),
            "price": Decimal("109.99"),
            "is_promotional": False,
            "recorded_at": now - timedelta(days=45),
        },
        {
            "id": seed_uuid("hist:coffee:pick-n-pay:15d"),
            "store_id": seed_uuid("store:pick-n-pay"),
            "product_id": seed_uuid("product:nescafe-coffee-200g"),
            "price": Decimal("114.99"),
            "is_promotional": False,
            "recorded_at": now - timedelta(days=15),
        },
        # Tastic Rice 2kg at Shoprite
        {
            "id": seed_uuid("hist:rice:shoprite:50d"),
            "store_id": seed_uuid("store:shoprite"),
            "product_id": seed_uuid("product:tastic-rice-2kg"),
            "price": Decimal("38.99"),
            "is_promotional": False,
            "recorded_at": now - timedelta(days=50),
        },
        {
            "id": seed_uuid("hist:rice:shoprite:20d"),
            "store_id": seed_uuid("store:shoprite"),
            "product_id": seed_uuid("product:tastic-rice-2kg"),
            "price": Decimal("41.99"),
            "is_promotional": False,
            "recorded_at": now - timedelta(days=20),
        },
    ]


PRICE_HISTORY: list[dict[str, Any]] = generate_price_history_fixtures()
