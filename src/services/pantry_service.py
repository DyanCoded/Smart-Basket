"""Pantry inventory domain service and offline synchronization engine."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional, Sequence, Tuple

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from src.api.v1.schemas import (
    PantryItemCreateRequest,
    PantryItemUpdateRequest,
    PantrySyncMutation,
)
from src.models.entities import (
    Basket,
    BasketItem,
    Category,
    PantryItem,
    PantryLog,
    Product,
)
from src.services.pubsub_service import (
    EVENT_ITEM_DELETED,
    EVENT_ITEM_UPDATED,
    publish_pantry_event,
)


def serialize_pantry_item_dict(item: PantryItem) -> dict:
    """Format PantryItem into JSON-serializable dictionary for event broadcasts."""
    return {
        "id": str(item.id),
        "home_id": str(item.home_id),
        "product_id": str(item.product_id) if item.product_id else None,
        "category_id": str(item.category_id) if item.category_id else None,
        "custom_name": item.custom_name,
        "barcode": item.barcode,
        "quantity": str(item.quantity),
        "unit_type": item.unit_type,
        "low_stock_threshold": str(item.low_stock_threshold),
        "status": item.status,
        "is_deleted": item.is_deleted,
        "updated_at": item.updated_at.isoformat() if item.updated_at else None,
        "product_name": item.product.name if item.product else None,
        "category_name": item.category.name if item.category else None,
    }


def auto_replenish_basket_item(
    session: Session,
    home_id: uuid.UUID,
    product_id: uuid.UUID,
    quantity: Decimal = Decimal("1.00"),
) -> BasketItem:
    """Automatically upsert a low/finished catalog product into household basket.

    Args:
        session: Active database session.
        home_id: Household ID.
        product_id: Linked catalog product ID to replenish.
        quantity: Quantity to ensure in the replenishment basket.

    Returns:
        The created or updated BasketItem record.
    """
    # 1. Fetch active household basket or create one
    basket = session.scalar(
        select(Basket)
        .where(Basket.home_id == home_id)
        .order_by(Basket.created_at.desc())
    )
    if not basket:
        basket = Basket(
            home_id=home_id,
            name="Household Smart Basket",
        )
        session.add(basket)
        session.flush()

    # 2. Check if product already present in basket
    basket_item = session.scalar(
        select(BasketItem).where(
            BasketItem.basket_id == basket.id,
            BasketItem.product_id == product_id,
        )
    )
    effective_qty = max(quantity, Decimal("1.00"))
    if basket_item:
        if basket_item.quantity < effective_qty:
            basket_item.quantity = effective_qty
    else:
        basket_item = BasketItem(
            basket_id=basket.id,
            product_id=product_id,
            quantity=effective_qty,
        )
        session.add(basket_item)
        session.flush()

    return basket_item


def get_pantry_items(
    session: Session,
    home_id: uuid.UUID,
    status_filter: Optional[str] = None,
    category_id: Optional[uuid.UUID] = None,
    query: Optional[str] = None,
    include_deleted: bool = False,
) -> Sequence[PantryItem]:
    """Retrieve pantry items for a household with filtering and search.

    Args:
        session: Database session.
        home_id: Household UUID.
        status_filter: Optional stock status ('ok', 'low', 'finished').
        category_id: Optional category UUID.
        query: Optional search keyword.
        include_deleted: If True, includes soft-deleted tombstones.

    Returns:
        List of matching PantryItem records.
    """
    stmt = (
        select(PantryItem)
        .where(PantryItem.home_id == home_id)
        .options(
            joinedload(PantryItem.product),
            joinedload(PantryItem.category),
        )
    )

    if not include_deleted:
        stmt = stmt.where(PantryItem.is_deleted.is_(False))

    if status_filter:
        clean_status = status_filter.strip().lower()
        stmt = stmt.where(PantryItem.status == clean_status)

    if category_id:
        stmt = stmt.where(PantryItem.category_id == category_id)

    if query:
        clean_q = f"%{query.strip()}%"
        stmt = stmt.join(PantryItem.product, isouter=True).where(
            or_(
                PantryItem.custom_name.ilike(clean_q),
                PantryItem.barcode.ilike(clean_q),
                Product.name.ilike(clean_q),
                Product.brand.ilike(clean_q),
            )
        )

    stmt = stmt.order_by(PantryItem.updated_at.desc())
    return session.scalars(stmt).unique().all()


def get_pantry_item_by_id(
    session: Session,
    home_id: uuid.UUID,
    item_id: uuid.UUID,
) -> PantryItem:
    """Retrieve a single pantry item, ensuring household isolation.

    Args:
        session: Database session.
        home_id: Household UUID.
        item_id: Pantry item UUID.

    Returns:
        Matching PantryItem entity.

    Raises:
        HTTPException: 404 if item does not exist or belongs to another home.
    """
    item = session.scalar(
        select(PantryItem)
        .where(
            PantryItem.id == item_id,
            PantryItem.home_id == home_id,
        )
        .options(
            joinedload(PantryItem.product),
            joinedload(PantryItem.category),
        )
    )
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pantry item with id '{item_id}' not found in household",
        )
    return item


def create_pantry_item(
    session: Session,
    home_id: uuid.UUID,
    user_id: uuid.UUID,
    data: PantryItemCreateRequest,
) -> PantryItem:
    """Create a new pantry item and record creation audit log.

    Args:
        session: Database session.
        home_id: Household UUID.
        user_id: ID of user adding the item.
        data: Pantry item creation request.

    Returns:
        The newly created PantryItem.
    """
    if not data.product_id and not (data.custom_name and data.custom_name.strip()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Either a catalog 'product_id' or a non-empty 'custom_name' "
                "must be provided"
            ),
        )

    clean_status = data.status.strip().lower()
    if clean_status not in ("ok", "low", "finished"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Status must be one of: 'ok', 'low', 'finished'",
        )

    if data.product_id:
        product_exists = session.scalar(
            select(Product.id).where(Product.id == data.product_id)
        )
        if not product_exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Catalog product with id '{data.product_id}' not found",
            )

    now_utc = datetime.now(timezone.utc)
    item = PantryItem(
        home_id=home_id,
        product_id=data.product_id,
        category_id=data.category_id,
        custom_name=data.custom_name.strip() if data.custom_name else None,
        barcode=data.barcode.strip() if data.barcode else None,
        quantity=data.quantity,
        unit_type=data.unit_type.strip(),
        low_stock_threshold=data.low_stock_threshold,
        status=clean_status,
        updated_at=now_utc,
        is_deleted=False,
    )
    session.add(item)
    session.flush()

    # Determine audit action
    if clean_status == "low":
        log_action = "marked_low"
    elif clean_status == "finished":
        log_action = "marked_finished"
    else:
        log_action = "restocked"

    log = PantryLog(
        item_id=item.id,
        user_id=user_id,
        action=log_action,
        note=data.note or "Added item to pantry",
        timestamp=now_utc,
    )
    session.add(log)

    # Auto-replenish hook if low/finished catalog product
    if clean_status in ("low", "finished") and item.product_id is not None:
        auto_replenish_basket_item(
            session=session,
            home_id=home_id,
            product_id=item.product_id,
            quantity=max(item.low_stock_threshold, Decimal("1.00")),
        )

    session.commit()
    session.refresh(item)
    publish_pantry_event(
        home_id=home_id,
        event_type=EVENT_ITEM_UPDATED,
        data=serialize_pantry_item_dict(item),
    )
    return item


def update_pantry_item(
    session: Session,
    home_id: uuid.UUID,
    item_id: uuid.UUID,
    user_id: uuid.UUID,
    data: PantryItemUpdateRequest,
) -> PantryItem:
    """Partially update pantry item stock or metadata and log changes.

    Args:
        session: Database session.
        home_id: Household UUID.
        item_id: Pantry item UUID.
        user_id: Acting user UUID.
        data: Partial update payload.

    Returns:
        Updated PantryItem entity.
    """
    item = get_pantry_item_by_id(session, home_id, item_id)
    prev_status = item.status

    if data.quantity is not None:
        item.quantity = data.quantity
    if data.unit_type is not None:
        item.unit_type = data.unit_type.strip()
    if data.low_stock_threshold is not None:
        item.low_stock_threshold = data.low_stock_threshold
    if data.custom_name is not None:
        item.custom_name = data.custom_name.strip() or None
    if data.barcode is not None:
        item.barcode = data.barcode.strip() or None
    if data.category_id is not None:
        item.category_id = data.category_id
    if data.product_id is not None:
        item.product_id = data.product_id

    new_status = data.status.strip().lower() if data.status else item.status
    if new_status not in ("ok", "low", "finished"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Status must be one of: 'ok', 'low', 'finished'",
        )
    item.status = new_status
    item.is_deleted = False

    now_utc = datetime.now(timezone.utc)
    item.updated_at = now_utc

    # Determine audit action
    if new_status == "low" and prev_status != "low":
        log_action = "marked_low"
    elif new_status == "finished" and prev_status != "finished":
        log_action = "marked_finished"
    elif new_status == "ok" and prev_status in ("low", "finished"):
        log_action = "restocked"
    else:
        log_action = "updated"

    log = PantryLog(
        item_id=item.id,
        user_id=user_id,
        action=log_action,
        note=data.note or "Updated pantry item",
        timestamp=now_utc,
    )
    session.add(log)

    # Auto-replenishment hook
    if new_status in ("low", "finished") and item.product_id is not None:
        auto_replenish_basket_item(
            session=session,
            home_id=home_id,
            product_id=item.product_id,
            quantity=max(item.low_stock_threshold, Decimal("1.00")),
        )

    session.commit()
    session.refresh(item)
    publish_pantry_event(
        home_id=home_id,
        event_type=EVENT_ITEM_UPDATED,
        data=serialize_pantry_item_dict(item),
    )
    return item


def delete_pantry_item(
    session: Session,
    home_id: uuid.UUID,
    item_id: uuid.UUID,
    user_id: uuid.UUID,
) -> None:
    """Soft-delete a pantry item by recording tombstone and audit log.

    Args:
        session: Database session.
        home_id: Household UUID.
        item_id: Pantry item UUID.
        user_id: Acting user UUID.
    """
    item = get_pantry_item_by_id(session, home_id, item_id)
    now_utc = datetime.now(timezone.utc)

    item.is_deleted = True
    item.updated_at = now_utc

    log = PantryLog(
        item_id=item.id,
        user_id=user_id,
        action="updated",
        note="Item soft-deleted from pantry",
        timestamp=now_utc,
    )
    session.add(log)
    session.commit()
    publish_pantry_event(
        home_id=home_id,
        event_type=EVENT_ITEM_DELETED,
        data={
            "id": str(item.id),
            "home_id": str(home_id),
            "is_deleted": True,
            "updated_at": item.updated_at.isoformat() if item.updated_at else None,
        },
    )


def sync_pantry_mutations(
    session: Session,
    home_id: uuid.UUID,
    user_id: uuid.UUID,
    last_synced_at: Optional[datetime],
    mutations: List[PantrySyncMutation],
) -> Tuple[datetime, Sequence[PantryItem], int]:
    """Reconcile offline client mutations via last-write-wins and return deltas.

    Args:
        session: Database session.
        home_id: Household UUID.
        user_id: Acting user UUID.
        last_synced_at: Timestamp of client's last sync checkpoint.
        mutations: Array of client mutation records.

    Returns:
        Tuple of (synced_at timestamp, updated server deltas, applied mutations count).
    """
    applied_count = 0

    for mut in mutations:
        clean_status = mut.status.strip().lower()
        if clean_status not in ("ok", "low", "finished"):
            clean_status = "ok"

        # Gracefully validate foreign keys so stale/unknown client UUIDs
        # degrade to custom items rather than failing with ForeignKeyViolation
        resolved_product_id = mut.product_id
        if resolved_product_id is not None:
            product_exists = session.scalar(
                select(Product.id).where(Product.id == resolved_product_id)
            )
            if not product_exists:
                resolved_product_id = None

        resolved_category_id = mut.category_id
        if resolved_category_id is not None:
            category_exists = session.scalar(
                select(Category.id).where(Category.id == resolved_category_id)
            )
            if not category_exists:
                resolved_category_id = None

        existing = session.scalar(
            select(PantryItem).where(
                PantryItem.id == mut.id,
                PantryItem.home_id == home_id,
            )
        )

        if existing:
            # Last-write-wins: apply mutation if client timestamp is newer or equal
            client_time = mut.updated_at
            server_time = existing.updated_at

            # Normalize timezone comparison
            if client_time.tzinfo is None:
                client_time = client_time.replace(tzinfo=timezone.utc)
            if server_time.tzinfo is None:
                server_time = server_time.replace(tzinfo=timezone.utc)

            if client_time >= server_time:
                prev_status = existing.status
                existing.product_id = resolved_product_id
                existing.category_id = resolved_category_id
                if mut.custom_name is not None:
                    existing.custom_name = mut.custom_name.strip() or None
                if mut.barcode is not None:
                    existing.barcode = mut.barcode.strip() or None
                existing.quantity = mut.quantity
                existing.unit_type = mut.unit_type.strip()
                existing.low_stock_threshold = mut.low_stock_threshold
                existing.status = clean_status
                existing.is_deleted = mut.is_deleted
                existing.updated_at = client_time

                # Log mutation
                if clean_status == "low" and prev_status != "low":
                    act = "marked_low"
                elif clean_status == "finished" and prev_status != "finished":
                    act = "marked_finished"
                elif clean_status == "ok" and prev_status in ("low", "finished"):
                    act = "restocked"
                else:
                    act = "updated"

                session.add(
                    PantryLog(
                        item_id=existing.id,
                        user_id=user_id,
                        action=act,
                        note=mut.note or "Offline delta sync mutation",
                        timestamp=client_time,
                    )
                )

                if (
                    clean_status in ("low", "finished")
                    and existing.product_id is not None
                    and not existing.is_deleted
                ):
                    auto_replenish_basket_item(
                        session=session,
                        home_id=home_id,
                        product_id=existing.product_id,
                        quantity=max(existing.low_stock_threshold, Decimal("1.00")),
                    )
                applied_count += 1
        else:
            # Create new item from client mutation
            client_time = mut.updated_at
            if client_time.tzinfo is None:
                client_time = client_time.replace(tzinfo=timezone.utc)

            new_item = PantryItem(
                id=mut.id,
                home_id=home_id,
                product_id=resolved_product_id,
                category_id=resolved_category_id,
                custom_name=mut.custom_name.strip() if mut.custom_name else None,
                barcode=mut.barcode.strip() if mut.barcode else None,
                quantity=mut.quantity,
                unit_type=mut.unit_type.strip(),
                low_stock_threshold=mut.low_stock_threshold,
                status=clean_status,
                is_deleted=mut.is_deleted,
                updated_at=client_time,
            )
            session.add(new_item)
            session.flush()

            act = (
                "marked_low"
                if clean_status == "low"
                else ("marked_finished" if clean_status == "finished" else "restocked")
            )
            session.add(
                PantryLog(
                    item_id=new_item.id,
                    user_id=user_id,
                    action=act,
                    note=mut.note or "Offline sync new item",
                    timestamp=client_time,
                )
            )

            if (
                clean_status in ("low", "finished")
                and new_item.product_id is not None
                and not new_item.is_deleted
            ):
                auto_replenish_basket_item(
                    session=session,
                    home_id=home_id,
                    product_id=new_item.product_id,
                    quantity=max(new_item.low_stock_threshold, Decimal("1.00")),
                )
            applied_count += 1

    session.commit()

    # Query all server-side items updated since last_synced_at
    synced_at = datetime.now(timezone.utc)
    delta_stmt = (
        select(PantryItem)
        .where(PantryItem.home_id == home_id)
        .options(
            joinedload(PantryItem.product),
            joinedload(PantryItem.category),
        )
    )
    if last_synced_at:
        normalized_last = (
            last_synced_at
            if last_synced_at.tzinfo is not None
            else last_synced_at.replace(tzinfo=timezone.utc)
        )
        delta_stmt = delta_stmt.where(PantryItem.updated_at >= normalized_last)

    delta_stmt = delta_stmt.order_by(PantryItem.updated_at.asc())
    deltas = session.scalars(delta_stmt).unique().all()

    # Broadcast deltas via Redis Pub/Sub
    for d_item in deltas:
        if d_item.is_deleted:
            publish_pantry_event(
                home_id=home_id,
                event_type=EVENT_ITEM_DELETED,
                data={
                    "id": str(d_item.id),
                    "home_id": str(home_id),
                    "is_deleted": True,
                    "updated_at": (
                        d_item.updated_at.isoformat() if d_item.updated_at else None
                    ),
                },
            )
        else:
            publish_pantry_event(
                home_id=home_id,
                event_type=EVENT_ITEM_UPDATED,
                data=serialize_pantry_item_dict(d_item),
            )

    return synced_at, deltas, applied_count


def get_household_basket(
    session: Session,
    home_id: uuid.UUID,
) -> Basket:
    """Retrieve active household basket with all line items and catalog details.

    Args:
        session: Database session.
        home_id: Household UUID.

    Returns:
        Active Basket entity.
    """
    basket = session.scalar(
        select(Basket)
        .where(Basket.home_id == home_id)
        .order_by(Basket.created_at.desc())
        .options(
            joinedload(Basket.items).joinedload(BasketItem.product),
        )
    )
    if not basket:
        basket = Basket(
            home_id=home_id,
            name="Household Smart Basket",
        )
        session.add(basket)
        session.commit()
        session.refresh(basket)
    return basket
