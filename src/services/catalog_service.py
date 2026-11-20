"""Catalog querying and store pricing business logic service."""

from __future__ import annotations

import uuid
from typing import Any, Sequence

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from src.models.entities import Product, Retailer, Store, StorePrice


def get_products(
    session: Session,
    query: str | None = None,
    brand: str | None = None,
    category_id: uuid.UUID | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[Sequence[Product], int]:
    """Search and filter products with case-insensitive matching and pagination."""
    stmt = select(Product).options(joinedload(Product.category))

    if query:
        clean_q = f"%{query.strip()}%"
        stmt = stmt.where(
            or_(
                Product.name.ilike(clean_q),
                Product.brand.ilike(clean_q),
                Product.barcode.ilike(clean_q),
            )
        )

    if brand:
        stmt = stmt.where(Product.brand.ilike(f"%{brand.strip()}%"))

    if category_id:
        stmt = stmt.where(Product.category_id == category_id)

    # Compute total count
    count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    total = session.scalar(count_stmt) or 0

    # Paginate and order by name
    paginated_stmt = stmt.order_by(Product.name.asc()).offset(offset).limit(limit)
    items = session.scalars(paginated_stmt).unique().all()

    return items, total


def get_product_by_id(session: Session, product_id: uuid.UUID) -> Product | None:
    """Retrieve detailed product metadata by ID."""
    stmt = (
        select(Product)
        .options(joinedload(Product.category))
        .where(Product.id == product_id)
    )
    return session.scalars(stmt).unique().first()


def get_product_prices(session: Session, product_id: uuid.UUID) -> list[dict[str, Any]]:
    """List national chain-level prices across all 5 monitored retailers for an item."""
    stmt = (
        select(StorePrice, Store, Retailer)
        .join(Store, StorePrice.store_id == Store.id)
        .join(Retailer, Store.retailer_id == Retailer.id)
        .where(StorePrice.product_id == product_id)
        .order_by(StorePrice.price.asc(), Retailer.name.asc())
    )

    results = session.execute(stmt).all()
    prices: list[dict[str, Any]] = []

    for sp, store, retailer in results:
        prices.append(
            {
                "id": sp.id,
                "store_id": store.id,
                "store_name": retailer.name,
                "branch_code": None,
                "retailer_name": retailer.name,
                "price": sp.price,
                "is_promotional": sp.is_promotional,
                "is_in_stock": sp.is_in_stock,
                "updated_at": sp.updated_at,
            }
        )

    return prices


def get_stores(
    session: Session,
    retailer_id: uuid.UUID | None = None,
    is_active: bool | None = None,
    query: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[Sequence[Store], int]:
    """List the canonical national supermarket chains with filtering and pagination."""
    stmt = (
        select(Store)
        .join(Retailer, Store.retailer_id == Retailer.id)
        .options(joinedload(Store.retailer))
    )

    if retailer_id:
        stmt = stmt.where(Store.retailer_id == retailer_id)

    if is_active is not None:
        stmt = stmt.where(Store.is_active.is_(is_active))

    if query:
        clean_q = f"%{query.strip()}%"
        stmt = stmt.where(
            or_(
                Store.name.ilike(clean_q),
                Retailer.name.ilike(clean_q),
                Retailer.slug.ilike(clean_q),
            )
        )

    # Compute total count
    count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    total = session.scalar(count_stmt) or 0

    # Paginate and order by canonical retailer name
    paginated_stmt = stmt.order_by(Retailer.name.asc()).offset(offset).limit(limit)
    items = session.scalars(paginated_stmt).unique().all()

    return items, total
