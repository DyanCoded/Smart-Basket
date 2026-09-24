"""baseline schema

Revision ID: 0001_baseline_schema
Revises:
Create Date: 2026-09-25 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_baseline_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Retailers
    op.create_table(
        "retailers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("name"),
        sa.UniqueConstraint("slug"),
    )

    # 2. Stores
    op.create_table(
        "stores",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "retailer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("retailers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("branch_code", sa.String(length=50), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("retailer_id", "name", name="uq_store_retailer_name"),
    )

    # 3. Categories
    op.create_table(
        "categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column(
            "parent_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("categories.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.UniqueConstraint("name"),
        sa.UniqueConstraint("slug"),
    )

    # 4. Products
    op.create_table(
        "products",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "category_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("categories.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("brand", sa.String(length=100), nullable=True),
        sa.Column("barcode", sa.String(length=64), nullable=True),
        sa.Column("unit_size", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("unit_type", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("barcode"),
    )
    op.create_index("ix_products_name", "products", ["name"])
    op.create_index("ix_products_barcode", "products", ["barcode"])

    # 5. Store Prices
    op.create_table(
        "store_prices",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "store_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("stores.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "product_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("products.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("price", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column(
            "is_promotional", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.Column("is_in_stock", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("store_id", "product_id", name="uq_store_product_price"),
        sa.CheckConstraint("price >= 0", name="chk_positive_price"),
    )
    op.create_index(
        "ix_store_prices_store_product", "store_prices", ["store_id", "product_id"]
    )

    # 6. Price History
    op.create_table(
        "price_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "store_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("stores.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "product_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("products.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("price", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column(
            "is_promotional", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("price >= 0", name="chk_positive_hist_price"),
    )
    op.create_index(
        "ix_price_hist_lookup",
        "price_history",
        ["product_id", "store_id", "recorded_at"],
    )

    # 7. Baskets & Basket Items
    op.create_table(
        "baskets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "basket_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "basket_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("baskets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "product_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("products.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("quantity", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.UniqueConstraint("basket_id", "product_id", name="uq_basket_product"),
        sa.CheckConstraint("quantity > 0", name="chk_positive_quantity"),
    )


def downgrade() -> None:
    op.drop_table("basket_items")
    op.drop_table("baskets")
    op.drop_table("price_history")
    op.drop_table("store_prices")
    op.drop_table("products")
    op.drop_table("categories")
    op.drop_table("stores")
    op.drop_table("retailers")
