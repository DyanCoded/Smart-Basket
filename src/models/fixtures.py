"""Catalog seed fixtures and test data definitions for Smart Basket."""

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

# Fixed namespace UUID for deterministic fixture generation
SEED_NAMESPACE = uuid.UUID("a3b8c4d2-1234-5678-90ab-cdef12345678")


def seed_uuid(name: str) -> uuid.UUID:
    """Generate a deterministic UUID from a unique seed name."""
    return uuid.uuid5(SEED_NAMESPACE, name)


# 1. Retailers (South African Supermarket Chains)
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

# 2. Stores (Retailer Branches across Johannesburg and Cape Town)
STORES: list[dict[str, Any]] = [
    # Checkers Branches
    {
        "id": seed_uuid("store:checkers-sandton"),
        "retailer_id": seed_uuid("retailer:checkers"),
        "name": "Checkers Sandton City",
        "branch_code": "CHK-JHB-001",
        "address": "Sandton City Shopping Centre, Rivonia Rd, Sandton, Johannesburg",
        "is_active": True,
    },
    {
        "id": seed_uuid("store:checkers-sea-point"),
        "retailer_id": seed_uuid("retailer:checkers"),
        "name": "Checkers Sea Point",
        "branch_code": "CHK-CPT-002",
        "address": "Regent Rd, Sea Point, Cape Town",
        "is_active": True,
    },
    # Woolworths Food Branches
    {
        "id": seed_uuid("store:woolworths-sandton"),
        "retailer_id": seed_uuid("retailer:woolworths"),
        "name": "Woolworths Sandton City",
        "branch_code": "WW-JHB-001",
        "address": "Sandton City Mall, 83 Rivonia Rd, Sandton, Johannesburg",
        "is_active": True,
    },
    {
        "id": seed_uuid("store:woolworths-waterfront"),
        "retailer_id": seed_uuid("retailer:woolworths"),
        "name": "Woolworths V&A Waterfront",
        "branch_code": "WW-CPT-002",
        "address": "Victoria Wharf Shopping Centre, V&A Waterfront, Cape Town",
        "is_active": True,
    },
    # Pick n Pay Branches
    {
        "id": seed_uuid("store:pnp-on-nicol"),
        "retailer_id": seed_uuid("retailer:pick-n-pay"),
        "name": "Pick n Pay On Nicol",
        "branch_code": "PNP-JHB-001",
        "address": "William Nicol Dr & Republic Rd, Bryanston, Johannesburg",
        "is_active": True,
    },
    {
        "id": seed_uuid("store:pnp-claremont"),
        "retailer_id": seed_uuid("retailer:pick-n-pay"),
        "name": "Pick n Pay Claremont",
        "branch_code": "PNP-CPT-002",
        "address": "Main Rd, Claremont, Cape Town",
        "is_active": True,
    },
    # SPAR Branch
    {
        "id": seed_uuid("store:spar-rosebank"),
        "retailer_id": seed_uuid("retailer:spar"),
        "name": "SUPERSPAR Rosebank",
        "branch_code": "SPR-JHB-001",
        "address": "The Zone @ Rosebank, Oxford Rd, Rosebank, Johannesburg",
        "is_active": True,
    },
    # Shoprite Branch
    {
        "id": seed_uuid("store:shoprite-jhb-central"),
        "retailer_id": seed_uuid("retailer:shoprite"),
        "name": "Shoprite Johannesburg Central",
        "branch_code": "SHP-JHB-001",
        "address": "Plein & Wanderers St, Johannesburg Central",
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

# 5. Store-Specific Active Prices (Demonstrating Multi-Store Price Divergence)
STORE_PRICES: list[dict[str, Any]] = [
    # Clover Milk 2L across branches
    {
        "id": seed_uuid("price:clover-milk:chk-sandton"),
        "store_id": seed_uuid("store:checkers-sandton"),
        "product_id": seed_uuid("product:clover-milk-2l"),
        "price": Decimal("34.99"),
        "is_promotional": True,
        "is_in_stock": True,
    },
    {
        "id": seed_uuid("price:clover-milk:chk-sea-point"),
        "store_id": seed_uuid("store:checkers-sea-point"),
        "product_id": seed_uuid("product:clover-milk-2l"),
        "price": Decimal("36.99"),
        "is_promotional": False,
        "is_in_stock": True,
    },
    {
        "id": seed_uuid("price:clover-milk:ww-sandton"),
        "store_id": seed_uuid("store:woolworths-sandton"),
        "product_id": seed_uuid("product:clover-milk-2l"),
        "price": Decimal("42.99"),
        "is_promotional": False,
        "is_in_stock": True,
    },
    {
        "id": seed_uuid("price:clover-milk:ww-waterfront"),
        "store_id": seed_uuid("store:woolworths-waterfront"),
        "product_id": seed_uuid("product:clover-milk-2l"),
        "price": Decimal("44.99"),
        "is_promotional": False,
        "is_in_stock": True,
    },
    {
        "id": seed_uuid("price:clover-milk:pnp-on-nicol"),
        "store_id": seed_uuid("store:pnp-on-nicol"),
        "product_id": seed_uuid("product:clover-milk-2l"),
        "price": Decimal("38.99"),
        "is_promotional": False,
        "is_in_stock": True,
    },
    {
        "id": seed_uuid("price:clover-milk:pnp-claremont"),
        "store_id": seed_uuid("store:pnp-claremont"),
        "product_id": seed_uuid("product:clover-milk-2l"),
        "price": Decimal("37.99"),
        "is_promotional": False,
        "is_in_stock": True,
    },
    {
        "id": seed_uuid("price:clover-milk:spar-rosebank"),
        "store_id": seed_uuid("store:spar-rosebank"),
        "product_id": seed_uuid("product:clover-milk-2l"),
        "price": Decimal("40.49"),
        "is_promotional": False,
        "is_in_stock": True,
    },
    {
        "id": seed_uuid("price:clover-milk:shoprite-jhb"),
        "store_id": seed_uuid("store:shoprite-jhb-central"),
        "product_id": seed_uuid("product:clover-milk-2l"),
        "price": Decimal("33.99"),
        "is_promotional": False,
        "is_in_stock": True,
    },
    # Farmer Brown Large Eggs 18pk across branches
    {
        "id": seed_uuid("price:eggs:chk-sandton"),
        "store_id": seed_uuid("store:checkers-sandton"),
        "product_id": seed_uuid("product:farmer-brown-eggs-18pk"),
        "price": Decimal("64.99"),
        "is_promotional": False,
        "is_in_stock": True,
    },
    {
        "id": seed_uuid("price:eggs:ww-sandton"),
        "store_id": seed_uuid("store:woolworths-sandton"),
        "product_id": seed_uuid("product:farmer-brown-eggs-18pk"),
        "price": Decimal("62.99"),
        "is_promotional": True,
        "is_in_stock": True,
    },
    {
        "id": seed_uuid("price:eggs:ww-waterfront"),
        "store_id": seed_uuid("store:woolworths-waterfront"),
        "product_id": seed_uuid("product:farmer-brown-eggs-18pk"),
        "price": Decimal("69.99"),
        "is_promotional": False,
        "is_in_stock": True,
    },
    {
        "id": seed_uuid("price:eggs:pnp-on-nicol"),
        "store_id": seed_uuid("store:pnp-on-nicol"),
        "product_id": seed_uuid("product:farmer-brown-eggs-18pk"),
        "price": Decimal("63.99"),
        "is_promotional": False,
        "is_in_stock": True,
    },
    {
        "id": seed_uuid("price:eggs:shoprite-jhb"),
        "store_id": seed_uuid("store:shoprite-jhb-central"),
        "product_id": seed_uuid("product:farmer-brown-eggs-18pk"),
        "price": Decimal("58.99"),
        "is_promotional": False,
        "is_in_stock": True,
    },
    # Lurpak Salted Butter 500g
    {
        "id": seed_uuid("price:butter:chk-sandton"),
        "store_id": seed_uuid("store:checkers-sandton"),
        "product_id": seed_uuid("product:lurpak-butter-500g"),
        "price": Decimal("79.99"),
        "is_promotional": False,
        "is_in_stock": True,
    },
    {
        "id": seed_uuid("price:butter:ww-sandton"),
        "store_id": seed_uuid("store:woolworths-sandton"),
        "product_id": seed_uuid("product:lurpak-butter-500g"),
        "price": Decimal("84.99"),
        "is_promotional": False,
        "is_in_stock": True,
    },
    {
        "id": seed_uuid("price:butter:pnp-on-nicol"),
        "store_id": seed_uuid("store:pnp-on-nicol"),
        "product_id": seed_uuid("product:lurpak-butter-500g"),
        "price": Decimal("69.99"),
        "is_promotional": True,
        "is_in_stock": True,
    },
    {
        "id": seed_uuid("price:butter:spar-rosebank"),
        "store_id": seed_uuid("store:spar-rosebank"),
        "product_id": seed_uuid("product:lurpak-butter-500g"),
        "price": Decimal("81.99"),
        "is_promotional": False,
        "is_in_stock": True,
    },
    # Albany Superior Sliced White Bread 700g
    {
        "id": seed_uuid("price:white-bread:chk-sandton"),
        "store_id": seed_uuid("store:checkers-sandton"),
        "product_id": seed_uuid("product:albany-white-bread-700g"),
        "price": Decimal("17.99"),
        "is_promotional": False,
        "is_in_stock": True,
    },
    {
        "id": seed_uuid("price:white-bread:ww-sandton"),
        "store_id": seed_uuid("store:woolworths-sandton"),
        "product_id": seed_uuid("product:albany-white-bread-700g"),
        "price": Decimal("19.99"),
        "is_promotional": False,
        "is_in_stock": True,
    },
    {
        "id": seed_uuid("price:white-bread:pnp-on-nicol"),
        "store_id": seed_uuid("store:pnp-on-nicol"),
        "product_id": seed_uuid("product:albany-white-bread-700g"),
        "price": Decimal("16.99"),
        "is_promotional": False,
        "is_in_stock": True,
    },
    {
        "id": seed_uuid("price:white-bread:shoprite-jhb"),
        "store_id": seed_uuid("store:shoprite-jhb-central"),
        "product_id": seed_uuid("product:albany-white-bread-700g"),
        "price": Decimal("15.99"),
        "is_promotional": False,
        "is_in_stock": True,
    },
    # Sasko Brown Bread 700g
    {
        "id": seed_uuid("price:brown-bread:chk-sandton"),
        "store_id": seed_uuid("store:checkers-sandton"),
        "product_id": seed_uuid("product:sasko-brown-bread-700g"),
        "price": Decimal("16.99"),
        "is_promotional": False,
        "is_in_stock": True,
    },
    {
        "id": seed_uuid("price:brown-bread:ww-sandton"),
        "store_id": seed_uuid("store:woolworths-sandton"),
        "product_id": seed_uuid("product:sasko-brown-bread-700g"),
        "price": Decimal("18.99"),
        "is_promotional": False,
        "is_in_stock": True,
    },
    {
        "id": seed_uuid("price:brown-bread:shoprite-jhb"),
        "store_id": seed_uuid("store:shoprite-jhb-central"),
        "product_id": seed_uuid("product:sasko-brown-bread-700g"),
        "price": Decimal("14.99"),
        "is_promotional": False,
        "is_in_stock": True,
    },
    # Tastic Rice 2kg
    {
        "id": seed_uuid("price:rice:chk-sandton"),
        "store_id": seed_uuid("store:checkers-sandton"),
        "product_id": seed_uuid("product:tastic-rice-2kg"),
        "price": Decimal("39.99"),
        "is_promotional": True,
        "is_in_stock": True,
    },
    {
        "id": seed_uuid("price:rice:ww-sandton"),
        "store_id": seed_uuid("store:woolworths-sandton"),
        "product_id": seed_uuid("product:tastic-rice-2kg"),
        "price": Decimal("49.99"),
        "is_promotional": False,
        "is_in_stock": True,
    },
    {
        "id": seed_uuid("price:rice:pnp-on-nicol"),
        "store_id": seed_uuid("store:pnp-on-nicol"),
        "product_id": seed_uuid("product:tastic-rice-2kg"),
        "price": Decimal("43.99"),
        "is_promotional": False,
        "is_in_stock": True,
    },
    {
        "id": seed_uuid("price:rice:shoprite-jhb"),
        "store_id": seed_uuid("store:shoprite-jhb-central"),
        "product_id": seed_uuid("product:tastic-rice-2kg"),
        "price": Decimal("41.99"),
        "is_promotional": False,
        "is_in_stock": True,
    },
    # Sunfoil Oil 2L
    {
        "id": seed_uuid("price:oil:chk-sandton"),
        "store_id": seed_uuid("store:checkers-sandton"),
        "product_id": seed_uuid("product:sunfoil-oil-2l"),
        "price": Decimal("82.99"),
        "is_promotional": False,
        "is_in_stock": True,
    },
    {
        "id": seed_uuid("price:oil:ww-sandton"),
        "store_id": seed_uuid("store:woolworths-sandton"),
        "product_id": seed_uuid("product:sunfoil-oil-2l"),
        "price": Decimal("89.99"),
        "is_promotional": False,
        "is_in_stock": True,
    },
    {
        "id": seed_uuid("price:oil:pnp-on-nicol"),
        "store_id": seed_uuid("store:pnp-on-nicol"),
        "product_id": seed_uuid("product:sunfoil-oil-2l"),
        "price": Decimal("74.99"),
        "is_promotional": True,
        "is_in_stock": True,
    },
    {
        "id": seed_uuid("price:oil:shoprite-jhb"),
        "store_id": seed_uuid("store:shoprite-jhb-central"),
        "product_id": seed_uuid("product:sunfoil-oil-2l"),
        "price": Decimal("76.99"),
        "is_promotional": False,
        "is_in_stock": True,
    },
    # Nescafe Classic Coffee 200g
    {
        "id": seed_uuid("price:coffee:chk-sandton"),
        "store_id": seed_uuid("store:checkers-sandton"),
        "product_id": seed_uuid("product:nescafe-coffee-200g"),
        "price": Decimal("119.99"),
        "is_promotional": False,
        "is_in_stock": True,
    },
    {
        "id": seed_uuid("price:coffee:ww-sandton"),
        "store_id": seed_uuid("store:woolworths-sandton"),
        "product_id": seed_uuid("product:nescafe-coffee-200g"),
        "price": Decimal("129.99"),
        "is_promotional": False,
        "is_in_stock": True,
    },
    {
        "id": seed_uuid("price:coffee:pnp-on-nicol"),
        "store_id": seed_uuid("store:pnp-on-nicol"),
        "product_id": seed_uuid("product:nescafe-coffee-200g"),
        "price": Decimal("114.99"),
        "is_promotional": False,
        "is_in_stock": True,
    },
    {
        "id": seed_uuid("price:coffee:shoprite-jhb"),
        "store_id": seed_uuid("store:shoprite-jhb-central"),
        "product_id": seed_uuid("product:nescafe-coffee-200g"),
        "price": Decimal("109.99"),
        "is_promotional": False,
        "is_in_stock": True,
    },
    # Bananas 1kg
    {
        "id": seed_uuid("price:bananas:chk-sandton"),
        "store_id": seed_uuid("store:checkers-sandton"),
        "product_id": seed_uuid("product:fresh-bananas-1kg"),
        "price": Decimal("24.99"),
        "is_promotional": False,
        "is_in_stock": True,
    },
    {
        "id": seed_uuid("price:bananas:ww-sandton"),
        "store_id": seed_uuid("store:woolworths-sandton"),
        "product_id": seed_uuid("product:fresh-bananas-1kg"),
        "price": Decimal("28.99"),
        "is_promotional": False,
        "is_in_stock": True,
    },
    {
        "id": seed_uuid("price:bananas:pnp-on-nicol"),
        "store_id": seed_uuid("store:pnp-on-nicol"),
        "product_id": seed_uuid("product:fresh-bananas-1kg"),
        "price": Decimal("22.99"),
        "is_promotional": False,
        "is_in_stock": True,
    },
    {
        "id": seed_uuid("price:bananas:shoprite-jhb"),
        "store_id": seed_uuid("store:shoprite-jhb-central"),
        "product_id": seed_uuid("product:fresh-bananas-1kg"),
        "price": Decimal("21.99"),
        "is_promotional": False,
        "is_in_stock": True,
    },
    # Teabags 80pk
    {
        "id": seed_uuid("price:teabags:chk-sandton"),
        "store_id": seed_uuid("store:checkers-sandton"),
        "product_id": seed_uuid("product:freshpak-rooibos-80pk"),
        "price": Decimal("52.99"),
        "is_promotional": False,
        "is_in_stock": True,
    },
    {
        "id": seed_uuid("price:teabags:pnp-on-nicol"),
        "store_id": seed_uuid("store:pnp-on-nicol"),
        "product_id": seed_uuid("product:freshpak-rooibos-80pk"),
        "price": Decimal("49.99"),
        "is_promotional": True,
        "is_in_stock": True,
    },
    {
        "id": seed_uuid("price:teabags:ww-sandton"),
        "store_id": seed_uuid("store:woolworths-sandton"),
        "product_id": seed_uuid("product:freshpak-rooibos-80pk"),
        "price": Decimal("56.99"),
        "is_promotional": False,
        "is_in_stock": True,
    },
]


def generate_price_history_fixtures(
    base_time: datetime | None = None,
) -> list[dict[str, Any]]:
    """Generate 30-60 day price history tracking records for products across stores."""
    now = base_time or datetime.now(timezone.utc)
    return [
        # Clover Milk 2L at Checkers Sandton
        {
            "id": seed_uuid("hist:milk:chk-sandton:60d"),
            "store_id": seed_uuid("store:checkers-sandton"),
            "product_id": seed_uuid("product:clover-milk-2l"),
            "price": Decimal("36.99"),
            "is_promotional": False,
            "recorded_at": now - timedelta(days=60),
        },
        {
            "id": seed_uuid("hist:milk:chk-sandton:30d"),
            "store_id": seed_uuid("store:checkers-sandton"),
            "product_id": seed_uuid("product:clover-milk-2l"),
            "price": Decimal("38.99"),
            "is_promotional": False,
            "recorded_at": now - timedelta(days=30),
        },
        {
            "id": seed_uuid("hist:milk:chk-sandton:5d"),
            "store_id": seed_uuid("store:checkers-sandton"),
            "product_id": seed_uuid("product:clover-milk-2l"),
            "price": Decimal("34.99"),
            "is_promotional": True,
            "recorded_at": now - timedelta(days=5),
        },
        # Sunfoil Oil 2L at Woolworths Sandton
        {
            "id": seed_uuid("hist:oil:ww-sandton:60d"),
            "store_id": seed_uuid("store:woolworths-sandton"),
            "product_id": seed_uuid("product:sunfoil-oil-2l"),
            "price": Decimal("84.99"),
            "is_promotional": False,
            "recorded_at": now - timedelta(days=60),
        },
        {
            "id": seed_uuid("hist:oil:ww-sandton:35d"),
            "store_id": seed_uuid("store:woolworths-sandton"),
            "product_id": seed_uuid("product:sunfoil-oil-2l"),
            "price": Decimal("86.99"),
            "is_promotional": False,
            "recorded_at": now - timedelta(days=35),
        },
        {
            "id": seed_uuid("hist:oil:ww-sandton:10d"),
            "store_id": seed_uuid("store:woolworths-sandton"),
            "product_id": seed_uuid("product:sunfoil-oil-2l"),
            "price": Decimal("89.99"),
            "is_promotional": False,
            "recorded_at": now - timedelta(days=10),
        },
        # Nescafe Coffee 200g at Pick n Pay On Nicol
        {
            "id": seed_uuid("hist:coffee:pnp:45d"),
            "store_id": seed_uuid("store:pnp-on-nicol"),
            "product_id": seed_uuid("product:nescafe-coffee-200g"),
            "price": Decimal("109.99"),
            "is_promotional": False,
            "recorded_at": now - timedelta(days=45),
        },
        {
            "id": seed_uuid("hist:coffee:pnp:15d"),
            "store_id": seed_uuid("store:pnp-on-nicol"),
            "product_id": seed_uuid("product:nescafe-coffee-200g"),
            "price": Decimal("114.99"),
            "is_promotional": False,
            "recorded_at": now - timedelta(days=15),
        },
        # Tastic Rice 2kg at Shoprite JHB Central
        {
            "id": seed_uuid("hist:rice:shoprite:50d"),
            "store_id": seed_uuid("store:shoprite-jhb-central"),
            "product_id": seed_uuid("product:tastic-rice-2kg"),
            "price": Decimal("38.99"),
            "is_promotional": False,
            "recorded_at": now - timedelta(days=50),
        },
        {
            "id": seed_uuid("hist:rice:shoprite:20d"),
            "store_id": seed_uuid("store:shoprite-jhb-central"),
            "product_id": seed_uuid("product:tastic-rice-2kg"),
            "price": Decimal("41.99"),
            "is_promotional": False,
            "recorded_at": now - timedelta(days=20),
        },
    ]


PRICE_HISTORY: list[dict[str, Any]] = generate_price_history_fixtures()
