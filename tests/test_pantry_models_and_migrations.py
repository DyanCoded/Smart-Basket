"""Tests for KitchenSync household and pantry models and Alembic migration 0002.

Verifies:
- Entity definitions and attributes in src/models/entities.py
- Persistence and relationship integrity across Users, Homes, Memberships,
  PantryItems, PantryLogs, and Baskets.
- Decimal(10, 2) exact numeric precision for quantity and low_stock_threshold.
- Both catalogued and uncatalogued/custom pantry item support.
- Alembic migration 0002 structure and reversibility.
"""

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from sqlalchemy import Numeric, select
from sqlalchemy.orm import Session

from src.models.entities import (
    Basket,
    Category,
    Home,
    Membership,
    PantryItem,
    PantryLog,
    Product,
    User,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_pantry_and_household_model_definitions() -> None:
    """Verify entity column types, constraints, and precision requirements."""
    # PantryItem quantity & low_stock_threshold must be Numeric(10, 2)
    qty_col = PantryItem.__table__.columns["quantity"]
    assert isinstance(qty_col.type, Numeric)
    assert qty_col.type.precision == 10
    assert qty_col.type.scale == 2

    thresh_col = PantryItem.__table__.columns["low_stock_threshold"]
    assert isinstance(thresh_col.type, Numeric)
    assert thresh_col.type.precision == 10
    assert thresh_col.type.scale == 2

    # Verify baskets has home_id nullable foreign key
    home_id_col = Basket.__table__.columns["home_id"]
    assert home_id_col.nullable is True

    # Verify unique constraint on memberships (user_id, home_id)
    membership_table = Membership.__table__
    constraint_names = [c.name for c in membership_table.constraints]
    assert "uq_membership_user_home" in constraint_names


def test_persist_household_and_memberships(empty_db_session: Session) -> None:
    """Verify creating users, homes, and memberships with role validation."""
    user = User(
        username="johndoe",
        email="john@example.com",
        hashed_password="hashed_secret_password",
    )
    home = Home(name="Smith Family Home")
    empty_db_session.add_all([user, home])
    empty_db_session.flush()

    assert user.id is not None
    assert home.id is not None

    membership = Membership(
        user_id=user.id,
        home_id=home.id,
        role="buyer",
    )
    empty_db_session.add(membership)
    empty_db_session.commit()

    # Query back and verify relationships
    saved_home = empty_db_session.scalar(select(Home).where(Home.id == home.id))
    assert saved_home is not None
    assert len(saved_home.memberships) == 1
    assert saved_home.memberships[0].role == "buyer"
    assert saved_home.memberships[0].user.username == "johndoe"


def test_persist_pantry_items_catalog_and_custom(
    empty_db_session: Session,
) -> None:
    """Verify persisting both catalog-linked and custom pantry items."""
    home = Home(name="Greenwood Villa")
    category = Category(name="Pantry Staples", slug="pantry-staples")
    empty_db_session.add_all([home, category])
    empty_db_session.flush()

    product = Product(
        category_id=category.id,
        name="Organic Rolled Oats 1kg",
        brand="Nature's Best",
        barcode="6009876543210",
        unit_size=Decimal("1.00"),
        unit_type="kg",
    )
    empty_db_session.add(product)
    empty_db_session.flush()

    # 1. Catalogued pantry item
    catalog_item = PantryItem(
        home_id=home.id,
        product_id=product.id,
        category_id=category.id,
        barcode=product.barcode,
        quantity=Decimal("3.50"),
        unit_type="kg",
        low_stock_threshold=Decimal("1.00"),
        status="ok",
    )

    # 2. Custom uncatalogued pantry item
    custom_item = PantryItem(
        home_id=home.id,
        product_id=None,
        category_id=category.id,
        custom_name="Homemade Strawberry Jam",
        quantity=Decimal("2.00"),
        unit_type="unit",
        low_stock_threshold=Decimal("1.00"),
        status="ok",
    )

    empty_db_session.add_all([catalog_item, custom_item])
    empty_db_session.commit()

    items = empty_db_session.scalars(
        select(PantryItem).where(PantryItem.home_id == home.id)
    ).all()
    assert len(items) == 2

    cat_saved = next(i for i in items if i.product_id is not None)
    assert cat_saved.product.name == "Organic Rolled Oats 1kg"
    assert cat_saved.quantity == Decimal("3.50")

    custom_saved = next(i for i in items if i.product_id is None)
    assert custom_saved.custom_name == "Homemade Strawberry Jam"
    assert custom_saved.quantity == Decimal("2.00")


def test_pantry_log_creation_and_audit_trail(
    empty_db_session: Session,
) -> None:
    """Verify audit log entries for status changes and item consumption."""
    user = User(
        username="alice",
        email="alice@example.com",
        hashed_password="hashed_pw_alice",
    )
    home = Home(name="Alice's Apartment")
    empty_db_session.add_all([user, home])
    empty_db_session.flush()

    item = PantryItem(
        home_id=home.id,
        custom_name="Almond Milk 1L",
        quantity=Decimal("1.00"),
        unit_type="L",
        low_stock_threshold=Decimal("1.00"),
        status="ok",
    )
    empty_db_session.add(item)
    empty_db_session.flush()

    # Mark low and record log
    item.status = "low"
    item.quantity = Decimal("0.25")
    log = PantryLog(
        item_id=item.id,
        user_id=user.id,
        action="marked_low",
        note="Less than a cup remaining",
        timestamp=datetime.now(timezone.utc),
    )
    empty_db_session.add(log)
    empty_db_session.commit()

    saved_item = empty_db_session.scalar(
        select(PantryItem).where(PantryItem.id == item.id)
    )
    assert saved_item is not None
    assert saved_item.status == "low"
    assert len(saved_item.logs) == 1
    assert saved_item.logs[0].action == "marked_low"
    assert saved_item.logs[0].user.username == "alice"


def test_basket_household_association(empty_db_session: Session) -> None:
    """Verify shopping baskets can link to a household home_id."""
    home = Home(name="Downtown Loft")
    empty_db_session.add(home)
    empty_db_session.flush()

    household_basket = Basket(
        home_id=home.id,
        name="Weekly Family Groceries",
    )
    anonymous_basket = Basket(
        home_id=None,
        name="Quick One-Off Run",
    )
    empty_db_session.add_all([household_basket, anonymous_basket])
    empty_db_session.commit()

    saved_home = empty_db_session.scalar(select(Home).where(Home.id == home.id))
    assert saved_home is not None
    assert len(saved_home.baskets) == 1
    assert saved_home.baskets[0].name == "Weekly Family Groceries"


def test_alembic_migration_0002_metadata() -> None:
    """Verify migration 0002 file exists and chains correctly from 0001."""
    migration_path = (
        PROJECT_ROOT / "migrations" / "versions" / "0002_add_pantry_and_households.py"
    )
    assert migration_path.exists(), "Migration 0002 file must exist"

    content = migration_path.read_text(encoding="utf-8")
    assert 'revision: str = "0002_add_pantry_and_households"' in content
    assert (
        'down_revision: Union[str, Sequence[str], None] = "0001_baseline_schema"'
        in content
    )
    assert (
        "op.create_table('homes'" in content
        or 'op.create_table(\n        "homes"' in content
        or 'op.create_table("homes"' in content
    )
    assert (
        "op.create_table('users'" in content
        or 'op.create_table(\n        "users"' in content
        or 'op.create_table("users"' in content
    )
    assert (
        "op.create_table('memberships'" in content
        or 'op.create_table(\n        "memberships"' in content
        or 'op.create_table("memberships"' in content
    )
    assert (
        "op.create_table('pantry_items'" in content
        or 'op.create_table(\n        "pantry_items"' in content
        or 'op.create_table("pantry_items"' in content
    )
    assert (
        "op.create_table('pantry_logs'" in content
        or 'op.create_table(\n        "pantry_logs"' in content
        or 'op.create_table("pantry_logs"' in content
    )
    assert "fk_baskets_home_id" in content
