"""Catalog querying and store pricing business logic service."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Sequence

from sqlalchemy import and_, func, or_, select
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
    """Search and filter products, prioritizing multi-chain priced items."""
    stmt = select(Product).options(joinedload(Product.category))

    if query:
        stripped = query.strip()
        if stripped:
            clean_q = f"%{stripped}%"
            full_match = or_(
                Product.name.ilike(clean_q),
                Product.brand.ilike(clean_q),
                Product.barcode.ilike(clean_q),
            )
            tokens = [tok for tok in stripped.split() if tok]
            if len(tokens) > 1:
                token_clauses = [
                    or_(
                        Product.name.ilike(f"%{tok}%"),
                        Product.brand.ilike(f"%{tok}%"),
                        Product.barcode.ilike(f"%{tok}%"),
                    )
                    for tok in tokens
                ]
                stmt = stmt.where(or_(full_match, and_(*token_clauses)))
            else:
                stmt = stmt.where(full_match)

    if brand:
        stmt = stmt.where(Product.brand.ilike(f"%{brand.strip()}%"))

    if category_id:
        stmt = stmt.where(Product.category_id == category_id)

    # Compute total count
    count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    total = session.scalar(count_stmt) or 0

    # Prioritize products with active store_prices across multiple national chains
    chain_counts = (
        select(
            StorePrice.product_id.label("product_id"),
            func.count(func.distinct(StorePrice.store_id)).label("chain_count"),
        )
        .join(Store, StorePrice.store_id == Store.id)
        .where(Store.is_active.is_(True))
        .group_by(StorePrice.product_id)
        .subquery()
    )

    paginated_stmt = (
        stmt.outerjoin(chain_counts, Product.id == chain_counts.c.product_id)
        .order_by(
            func.coalesce(chain_counts.c.chain_count, 0).desc(),
            Product.name.asc(),
            Product.id.asc(),
        )
        .offset(offset)
        .limit(limit)
    )
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


def get_store_freshness_map(
    session: Session,
    store_ids: Sequence[uuid.UUID],
) -> dict[uuid.UUID, tuple[datetime | None, int]]:
    """Return {store_id: (latest_updated_at, tracked_products_count)} in one query."""
    if not store_ids:
        return {}

    stmt = (
        select(
            StorePrice.store_id,
            func.max(StorePrice.updated_at).label("last_sync"),
            func.count(StorePrice.id).label("tracked_count"),
        )
        .where(StorePrice.store_id.in_(store_ids))
        .group_by(StorePrice.store_id)
    )
    rows = session.execute(stmt).all()
    return {row.store_id: (row.last_sync, int(row.tracked_count or 0)) for row in rows}


def get_catalog_freshness_telemetry(session: Session) -> dict[str, Any]:
    """Return global catalog price refresh telemetry for /health & clients."""
    last_price_sync_at = session.scalar(select(func.max(StorePrice.updated_at)))
    tracked_prices = int(session.scalar(select(func.count(StorePrice.id))) or 0)
    active_chains = int(
        session.scalar(select(func.count(Store.id)).where(Store.is_active.is_(True)))
        or 0
    )
    return {
        "status": "ok",
        "last_price_sync_at": (
            last_price_sync_at.isoformat() if last_price_sync_at is not None else None
        ),
        "active_chains": active_chains,
        "tracked_prices": tracked_prices,
    }
