"""Database seeding script and verification tool for Smart Basket.

Populates local and test databases with supermarket chains, store branches,
grocery categories, universal products, store-specific pricing, and price history.
"""

from __future__ import annotations

import argparse
import sys
import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from src.core.database import SessionLocal, engine
from src.models.entities import (
    Base,
    Category,
    PriceHistory,
    Product,
    Retailer,
    Store,
    StorePrice,
)
from src.models.fixtures import (
    CATEGORIES,
    PRICE_HISTORY,
    PRODUCTS,
    RETAILERS,
    STORE_PRICES,
    STORES,
)


def seed_database(session: Session, reset: bool = True) -> dict[str, int]:
    """Seed the database with catalog fixture data.

    Args:
        session: SQLAlchemy database session.
        reset: If True, clears existing catalog data before inserting.

    Returns:
        Dictionary mapping entity names to inserted record counts.
    """
    if reset:
        # Delete in reverse foreign-key dependency order
        session.execute(delete(PriceHistory))
        session.execute(delete(StorePrice))
        session.execute(delete(Product))
        session.execute(delete(Category))
        session.execute(delete(Store))
        session.execute(delete(Retailer))
        session.flush()

    # 1. Retailers
    retailers = [
        Retailer(
            id=item["id"],
            name=item["name"],
            slug=item["slug"],
        )
        for item in RETAILERS
    ]
    session.add_all(retailers)
    session.flush()

    # 2. Stores (Branches)
    stores = [
        Store(
            id=item["id"],
            retailer_id=item["retailer_id"],
            name=item["name"],
            branch_code=item.get("branch_code"),
            address=item.get("address"),
            is_active=item.get("is_active", True),
        )
        for item in STORES
    ]
    session.add_all(stores)
    session.flush()

    # 3. Categories
    categories = [
        Category(
            id=item["id"],
            name=item["name"],
            slug=item["slug"],
            parent_id=item.get("parent_id"),
        )
        for item in CATEGORIES
    ]
    session.add_all(categories)
    session.flush()

    # 4. Products
    products = [
        Product(
            id=item["id"],
            category_id=item.get("category_id"),
            name=item["name"],
            brand=item.get("brand"),
            barcode=item.get("barcode"),
            unit_size=item["unit_size"],
            unit_type=item["unit_type"],
        )
        for item in PRODUCTS
    ]
    session.add_all(products)
    session.flush()

    # 5. Store Prices
    store_prices = [
        StorePrice(
            id=item["id"],
            store_id=item["store_id"],
            product_id=item["product_id"],
            price=item["price"],
            is_promotional=item.get("is_promotional", False),
            is_in_stock=item.get("is_in_stock", True),
        )
        for item in STORE_PRICES
    ]
    session.add_all(store_prices)
    session.flush()

    # 6. Price History
    history_records = [
        PriceHistory(
            id=item["id"],
            store_id=item["store_id"],
            product_id=item["product_id"],
            price=item["price"],
            is_promotional=item.get("is_promotional", False),
            recorded_at=item["recorded_at"],
        )
        for item in PRICE_HISTORY
    ]
    session.add_all(history_records)
    session.commit()

    return {
        "retailers": len(retailers),
        "stores": len(stores),
        "categories": len(categories),
        "products": len(products),
        "store_prices": len(store_prices),
        "price_history": len(history_records),
    }


def verify_catalog_divergence(session: Session) -> list[dict[str, Any]]:
    """Run verification query confirming multi-store price divergence.

    Returns:
        List of divergence records with product names, store counts,
        min/max prices, and price divergence spread.
    """
    stmt = (
        select(
            Product.id.label("product_id"),
            Product.name.label("product_name"),
            func.count(StorePrice.store_id).label("store_count"),
            func.min(StorePrice.price).label("min_price"),
            func.max(StorePrice.price).label("max_price"),
            (func.max(StorePrice.price) - func.min(StorePrice.price)).label(
                "price_spread"
            ),
        )
        .join(StorePrice, Product.id == StorePrice.product_id)
        .group_by(Product.id, Product.name)
        .having(
            func.count(StorePrice.store_id) > 1,
            (func.max(StorePrice.price) - func.min(StorePrice.price)) > Decimal("0.00"),
        )
        .order_by(
            (func.max(StorePrice.price) - func.min(StorePrice.price)).desc(),
            Product.name,
        )
    )

    results = session.execute(stmt).all()
    records = []
    for row in results:
        records.append(
            {
                "product_id": str(row.product_id),
                "product_name": row.product_name,
                "store_count": row.store_count,
                "min_price": row.min_price,
                "max_price": row.max_price,
                "price_spread": row.price_spread,
            }
        )
    return records


def format_sql_value(val: Any) -> str:
    """Format a Python value into a SQL literal."""
    if val is None:
        return "NULL"
    if isinstance(val, uuid.UUID):
        return f"'{val}'"
    if isinstance(val, bool):
        return "TRUE" if val else "FALSE"
    if isinstance(val, (int, float, Decimal)):
        return str(val)
    escaped = str(val).replace("'", "''")
    return f"'{escaped}'"


def export_sql_script(output_path: str = "scripts/seed.sql") -> None:
    """Export the catalog fixtures to an idempotent PostgreSQL seed SQL script."""
    lines: list[str] = [
        "-- scripts/seed.sql",
        "-- Smart Basket: Catalog Seeding & Multi-Store Pricing Test Data",
        "-- PostgreSQL 16 compatible idempotent seed script",
        "",
        "-- Clean up existing data in reverse order of foreign key dependencies",
        (
            "TRUNCATE TABLE price_history, basket_items, baskets, "
            "store_prices, products, categories, stores, retailers CASCADE;"
        ),
        "",
        "-" * 80,
        "-- 1. Retailers (South African Supermarket Chains)",
        "-" * 80,
        "INSERT INTO retailers (id, name, slug, created_at) VALUES",
    ]

    ret_vals = [
        f"  ({format_sql_value(r['id'])}, {format_sql_value(r['name'])}, "
        f"{format_sql_value(r['slug'])}, NOW())"
        for r in RETAILERS
    ]
    lines.append(",\n".join(ret_vals) + ";\n")

    lines.extend(
        [
            "-" * 80,
            "-- 2. Stores (Retailer Branches across Johannesburg and Cape Town)",
            "-" * 80,
            (
                "INSERT INTO stores "
                "(id, retailer_id, name, branch_code, address, is_active, created_at) "
                "VALUES"
            ),
        ]
    )
    store_vals = [
        f"  ({format_sql_value(s['id'])}, {format_sql_value(s['retailer_id'])}, "
        f"{format_sql_value(s['name'])}, {format_sql_value(s['branch_code'])}, "
        f"{format_sql_value(s['address'])}, {format_sql_value(s['is_active'])}, NOW())"
        for s in STORES
    ]
    lines.append(",\n".join(store_vals) + ";\n")

    lines.extend(
        [
            "-" * 80,
            "-- 3. Core Grocery Categories",
            "-" * 80,
            "INSERT INTO categories (id, name, slug, parent_id) VALUES",
        ]
    )
    cat_vals = [
        f"  ({format_sql_value(c['id'])}, {format_sql_value(c['name'])}, "
        f"{format_sql_value(c['slug'])}, {format_sql_value(c['parent_id'])})"
        for c in CATEGORIES
    ]
    lines.append(",\n".join(cat_vals) + ";\n")

    lines.extend(
        [
            "-" * 80,
            "-- 4. Universal Products (Common Grocery Items)",
            "-" * 80,
            (
                "INSERT INTO products "
                "(id, category_id, name, brand, barcode, "
                "unit_size, unit_type, created_at) "
                "VALUES"
            ),
        ]
    )
    prod_vals = [
        f"  ({format_sql_value(p['id'])}, {format_sql_value(p['category_id'])}, "
        f"{format_sql_value(p['name'])}, {format_sql_value(p['brand'])}, "
        f"{format_sql_value(p['barcode'])}, {format_sql_value(p['unit_size'])}, "
        f"{format_sql_value(p['unit_type'])}, NOW())"
        for p in PRODUCTS
    ]
    lines.append(",\n".join(prod_vals) + ";\n")

    lines.extend(
        [
            "-" * 80,
            "-- 5. Store-Specific Active Prices (Multi-Store Price Divergence)",
            "-" * 80,
            (
                "INSERT INTO store_prices "
                "(id, store_id, product_id, price, "
                "is_promotional, is_in_stock, updated_at) "
                "VALUES"
            ),
        ]
    )
    sp_vals = [
        f"  ({format_sql_value(sp['id'])}, {format_sql_value(sp['store_id'])}, "
        f"{format_sql_value(sp['product_id'])}, {format_sql_value(sp['price'])}, "
        f"{format_sql_value(sp['is_promotional'])}, "
        f"{format_sql_value(sp['is_in_stock'])}, NOW())"
        for sp in STORE_PRICES
    ]
    lines.append(",\n".join(sp_vals) + ";\n")

    lines.extend(
        [
            "-" * 80,
            "-- 6. Price History (Simulated 30-60 Day Tracking)",
            "-" * 80,
            (
                "INSERT INTO price_history "
                "(id, store_id, product_id, price, is_promotional, recorded_at) "
                "VALUES"
            ),
        ]
    )
    hist_vals = [
        f"  ({format_sql_value(h['id'])}, {format_sql_value(h['store_id'])}, "
        f"{format_sql_value(h['product_id'])}, {format_sql_value(h['price'])}, "
        f"{format_sql_value(h['is_promotional'])}, '{h['recorded_at'].isoformat()}')"
        for h in PRICE_HISTORY
    ]
    lines.append(",\n".join(hist_vals) + ";\n")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed Smart Basket catalog data.")
    parser.add_argument(
        "--no-reset",
        action="store_true",
        help="Do not truncate/delete existing data prior to seeding.",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        default=True,
        help="Run verification query confirming multi-store price divergence.",
    )
    parser.add_argument(
        "--export-sql",
        action="store_true",
        help="Export data fixtures to scripts/seed.sql",
    )
    args = parser.parse_args()

    if args.export_sql:
        print("--> Exporting fixtures to scripts/seed.sql...")
        export_sql_script("scripts/seed.sql")
        print("[PASS] scripts/seed.sql exported successfully.")

    try:
        # Ensure schema tables exist
        Base.metadata.create_all(bind=engine)
        with SessionLocal() as session:
            print("--> Seeding catalog data into database...")
            counts = seed_database(session, reset=not args.no_reset)
            print(f"[PASS] Successfully seeded database with {counts} records.")

            if args.verify:
                print("\n==========================================")
                print("--> Multi-Store Price Divergence Verification")
                print("==========================================")
                divergence = verify_catalog_divergence(session)
                header = (
                    f"{'Product Name':<38} | {'Stores':<6} | "
                    f"{'Min (R)':<8} | {'Max (R)':<8} | {'Spread (R)':<10}"
                )
                print(header)
                print("-" * len(header))
                for item in divergence:
                    row_str = (
                        f"{item['product_name']:<38} | {item['store_count']:<6} | "
                        f"{item['min_price']:<8} | {item['max_price']:<8} | "
                        f"R{item['price_spread']:<9.2f}"
                    )
                    print(row_str)
                count_div = len(divergence)
                print(
                    f"\n[PASS] Verified price divergence across {count_div} products."
                )

        return 0
    except Exception as exc:
        print(f"[FAIL] Seeding failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
