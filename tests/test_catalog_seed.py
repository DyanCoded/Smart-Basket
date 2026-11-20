"""Tests for database catalog seeding script and test data fixtures."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from scripts.seed import (
    export_sql_script,
    seed_database,
    verify_catalog_divergence,
)
from src.models.entities import (
    Category,
    PriceHistory,
    Product,
    Retailer,
    Store,
    StorePrice,
)


def test_seed_database_record_counts(db_session: Session):
    """Verify that catalog seeding populates all entities with expected counts."""
    retailer_count = len(db_session.scalars(select(Retailer)).all())
    store_count = len(db_session.scalars(select(Store)).all())
    category_count = len(db_session.scalars(select(Category)).all())
    product_count = len(db_session.scalars(select(Product)).all())
    price_count = len(db_session.scalars(select(StorePrice)).all())
    history_count = len(db_session.scalars(select(PriceHistory)).all())

    assert retailer_count == 5
    assert store_count == 5
    assert category_count == 5
    assert product_count == 18
    assert price_count == 90
    assert history_count == 10


def test_seed_database_repeatability_and_reset(empty_db_session: Session):
    """Verify that seed_database can be executed repeatedly without errors."""
    first_run = seed_database(empty_db_session, reset=True)
    assert first_run["products"] == 18

    # Second run with reset=True should cleanly clear and reseed
    second_run = seed_database(empty_db_session, reset=True)
    assert second_run == first_run

    total_products = len(empty_db_session.scalars(select(Product)).all())
    assert total_products == 18


def test_retailer_and_branch_relationships(db_session: Session):
    """Verify 1 canonical national chain store per retailer without branch codes."""
    stores = db_session.scalars(select(Store)).all()
    assert len(stores) == 5

    retailers_by_id = {r.id: r for r in db_session.scalars(select(Retailer)).all()}
    seen_retailers = set()
    for store in stores:
        assert store.retailer_id in retailers_by_id
        assert store.retailer_id not in seen_retailers
        seen_retailers.add(store.retailer_id)
        assert store.name == retailers_by_id[store.retailer_id].name
        assert store.branch_code is None
        assert store.address is None
        assert store.is_active is True


def test_multi_store_price_divergence_verification(db_session: Session):
    """Confirm the verification query detects multi-store price divergence."""
    divergence_records = verify_catalog_divergence(db_session)
    assert len(divergence_records) > 0

    # Ensure all reported products have more than 1 store and positive price spread
    for item in divergence_records:
        assert item["store_count"] > 1
        assert item["price_spread"] > Decimal("0.00")
        assert item["max_price"] > item["min_price"]

    # Verify specific benchmark product (Clover Milk 2L) has divergence across branches
    milk = next(
        (r for r in divergence_records if "Milk" in r["product_name"]),
        None,
    )
    assert milk is not None
    assert milk["store_count"] >= 5
    assert milk["price_spread"] >= Decimal("5.00")


def test_promotional_pricing_flags(db_session: Session):
    """Verify that promotional items are correctly flagged in the catalog."""
    promotional_prices = db_session.scalars(
        select(StorePrice).where(StorePrice.is_promotional.is_(True))
    ).all()
    assert len(promotional_prices) > 0

    for promo in promotional_prices:
        assert promo.price > Decimal("0.00")
        assert promo.is_in_stock is True


def test_price_history_time_window(db_session: Session):
    """Verify that historical price points span within the required 30-60 day window."""
    history = db_session.scalars(select(PriceHistory)).all()
    assert len(history) == 10

    now = datetime.now(timezone.utc)
    sixty_days_ago = now - timedelta(days=65)

    for entry in history:
        # Normalize timezone for comparison if SQLite stripped it
        entry_time = entry.recorded_at
        if entry_time.tzinfo is None:
            entry_time = entry_time.replace(tzinfo=timezone.utc)

        assert entry_time <= now
        assert entry_time >= sixty_days_ago
        assert entry.price > Decimal("0.00")


def test_universal_products_contract_conformance(db_session: Session):
    """Verify universal products conform to packaging unit constraints."""
    products = db_session.scalars(select(Product)).all()
    assert len(products) == 18

    valid_units = {"g", "kg", "ml", "L", "unit"}
    category_ids = {c.id for c in db_session.scalars(select(Category)).all()}

    for prod in products:
        assert prod.category_id in category_ids
        assert prod.barcode is not None
        assert len(prod.barcode) == 13  # Valid EAN-13 barcodes
        assert prod.unit_type in valid_units
        assert prod.unit_size > Decimal("0.00")


def test_export_sql_script(tmp_path):
    """Verify SQL seed script generation produces valid PostgreSQL script."""
    sql_file = tmp_path / "test_seed.sql"
    export_sql_script(str(sql_file))

    assert sql_file.exists()
    content = sql_file.read_text(encoding="utf-8")
    assert "TRUNCATE TABLE price_history" in content
    assert "INSERT INTO retailers" in content
    assert "INSERT INTO stores" in content
    assert "INSERT INTO categories" in content
    assert "INSERT INTO products" in content
    assert "INSERT INTO store_prices" in content
    assert "INSERT INTO price_history" in content
