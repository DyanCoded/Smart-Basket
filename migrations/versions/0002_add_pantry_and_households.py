"""add pantry and households

Revision ID: 0002_add_pantry_and_households
Revises: 0001_baseline_schema
Create Date: 2026-11-19 14:15:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0002_add_pantry_and_households"
down_revision: Union[str, Sequence[str], None] = "0001_baseline_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema to include households and pantry tracking."""
    # 1. Homes (Households)
    op.create_table(
        "homes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 2. Users
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("username", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("username"),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_username", "users", ["username"])

    # 3. Memberships
    op.create_table(
        "memberships",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "home_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("homes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "home_id", name="uq_membership_user_home"),
        sa.CheckConstraint("role IN ('buyer', 'consumer')", name="chk_membership_role"),
    )
    op.create_index("ix_memberships_user_home", "memberships", ["user_id", "home_id"])

    # 4. Pantry Items
    op.create_table(
        "pantry_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "home_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("homes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "product_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("products.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "category_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("categories.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("custom_name", sa.String(length=200), nullable=True),
        sa.Column("barcode", sa.String(length=64), nullable=True),
        sa.Column(
            "quantity",
            sa.Numeric(precision=10, scale=2),
            nullable=False,
            server_default="0.00",
        ),
        sa.Column(
            "unit_type", sa.String(length=20), nullable=False, server_default="unit"
        ),
        sa.Column(
            "low_stock_threshold",
            sa.Numeric(precision=10, scale=2),
            nullable=False,
            server_default="1.00",
        ),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="ok"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
        sa.CheckConstraint(
            "status IN ('ok', 'low', 'finished')", name="chk_pantry_item_status"
        ),
        sa.CheckConstraint("quantity >= 0", name="chk_positive_pantry_quantity"),
        sa.CheckConstraint(
            "low_stock_threshold >= 0", name="chk_positive_low_stock_threshold"
        ),
    )
    op.create_index("ix_pantry_items_barcode", "pantry_items", ["barcode"])
    op.create_index("ix_pantry_items_home_id", "pantry_items", ["home_id"])
    op.create_index("ix_pantry_items_status", "pantry_items", ["status"])

    # 5. Pantry Logs
    op.create_table(
        "pantry_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "item_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("pantry_items.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "action IN ('marked_low', 'marked_finished', 'restocked', 'updated')",
            name="chk_pantry_log_action",
        ),
    )
    op.create_index(
        "ix_pantry_logs_item_timestamp", "pantry_logs", ["item_id", "timestamp"]
    )

    # 6. Update Baskets with optional home_id
    op.add_column(
        "baskets",
        sa.Column("home_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_baskets_home_id",
        "baskets",
        "homes",
        ["home_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    """Downgrade schema to remove households and pantry tracking."""
    op.drop_constraint("fk_baskets_home_id", "baskets", type_="foreignkey")
    op.drop_column("baskets", "home_id")
    op.drop_table("pantry_logs")
    op.drop_table("pantry_items")
    op.drop_table("memberships")
    op.drop_table("users")
    op.drop_table("homes")
