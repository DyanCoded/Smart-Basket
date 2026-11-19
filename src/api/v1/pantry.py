"""Pantry inventory, offline delta-sync, and auto-basket replenishment endpoints."""

from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from src.api.v1.schemas import (
    COMMON_ERROR_RESPONSES,
    STANDARD_400_RESPONSE,
    STANDARD_401_RESPONSE,
    STANDARD_403_RESPONSE,
    STANDARD_404_RESPONSE,
    STANDARD_422_RESPONSE,
    HouseholdBasketItemResponse,
    HouseholdBasketResponse,
    PantryItemCreateRequest,
    PantryItemResponse,
    PantryItemUpdateRequest,
    PantrySyncRequest,
    PantrySyncResponse,
)
from src.core.database import get_db
from src.core.security import get_current_user, verify_home_membership
from src.models.entities import Membership, PantryItem, User
from src.services.pantry_service import (
    create_pantry_item,
    delete_pantry_item,
    get_household_basket,
    get_pantry_item_by_id,
    get_pantry_items,
    sync_pantry_mutations,
    update_pantry_item,
)

router = APIRouter(prefix="/homes/{home_id}", tags=["pantry"])


def _serialize_pantry_item(item: PantryItem) -> PantryItemResponse:
    """Format SQLAlchemy PantryItem into API DTO response."""
    return PantryItemResponse(
        id=item.id,
        home_id=item.home_id,
        product_id=item.product_id,
        category_id=item.category_id,
        custom_name=item.custom_name,
        barcode=item.barcode,
        quantity=item.quantity,
        unit_type=item.unit_type,
        low_stock_threshold=item.low_stock_threshold,
        status=item.status,
        is_deleted=item.is_deleted,
        updated_at=item.updated_at,
        product_name=item.product.name if item.product else None,
        category_name=item.category.name if item.category else None,
    )


@router.get(
    "/pantry",
    response_model=List[PantryItemResponse],
    summary="List household pantry items",
    description=(
        "Retrieve household pantry inventory with search and category " "filtering."
    ),
    responses={
        **STANDARD_401_RESPONSE,
        **STANDARD_403_RESPONSE,
        **STANDARD_404_RESPONSE,
        **COMMON_ERROR_RESPONSES,
    },
)
def list_pantry_items(
    home_id: uuid.UUID,
    status_filter: Optional[str] = Query(
        default=None,
        alias="status",
        description="Filter by status: 'ok', 'low', 'finished'",
    ),
    category_id: Optional[uuid.UUID] = Query(
        default=None, description="Filter by category UUID"
    ),
    q: Optional[str] = Query(
        default=None, description="Search by item name or barcode"
    ),
    include_deleted: bool = Query(
        default=False, description="Include soft-deleted items"
    ),
    membership: Membership = Depends(verify_home_membership),
    db: Session = Depends(get_db),
) -> List[PantryItemResponse]:
    """List pantry items for the authorized household."""
    items = get_pantry_items(
        session=db,
        home_id=home_id,
        status_filter=status_filter,
        category_id=category_id,
        query=q,
        include_deleted=include_deleted,
    )
    return [_serialize_pantry_item(item) for item in items]


@router.post(
    "/pantry",
    response_model=PantryItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add an item to the household pantry",
    description=(
        "Add a catalog-linked or custom item to the household pantry. "
        "Marking item low or finished auto-populates the household Smart Basket."
    ),
    responses={
        status.HTTP_200_OK: {
            "model": PantryItemResponse,
            "description": "Item created successfully.",
        },
        **STANDARD_400_RESPONSE,
        **STANDARD_401_RESPONSE,
        **STANDARD_403_RESPONSE,
        **STANDARD_404_RESPONSE,
        **STANDARD_422_RESPONSE,
        **COMMON_ERROR_RESPONSES,
    },
)
def add_pantry_item(
    home_id: uuid.UUID,
    payload: PantryItemCreateRequest,
    membership: Membership = Depends(verify_home_membership),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PantryItemResponse:
    """Create a new pantry item in the household."""
    item = create_pantry_item(
        session=db,
        home_id=home_id,
        user_id=current_user.id,
        data=payload,
    )
    return _serialize_pantry_item(item)


@router.get(
    "/pantry/{item_id}",
    response_model=PantryItemResponse,
    summary="Get single pantry item details",
    description="Retrieve details and stock levels for a specific pantry item.",
    responses={
        **STANDARD_401_RESPONSE,
        **STANDARD_403_RESPONSE,
        **STANDARD_404_RESPONSE,
        **COMMON_ERROR_RESPONSES,
    },
)
def get_pantry_item(
    home_id: uuid.UUID,
    item_id: uuid.UUID,
    membership: Membership = Depends(verify_home_membership),
    db: Session = Depends(get_db),
) -> PantryItemResponse:
    """Retrieve a single pantry item."""
    item = get_pantry_item_by_id(session=db, home_id=home_id, item_id=item_id)
    return _serialize_pantry_item(item)


@router.patch(
    "/pantry/{item_id}",
    response_model=PantryItemResponse,
    summary="Update pantry item stock or status",
    description=(
        "Partially update pantry item stock or metadata. "
        "Transitioning to 'low' or 'finished' automatically triggers "
        "Smart Basket replenishment for catalog products."
    ),
    responses={
        **STANDARD_400_RESPONSE,
        **STANDARD_401_RESPONSE,
        **STANDARD_403_RESPONSE,
        **STANDARD_404_RESPONSE,
        **STANDARD_422_RESPONSE,
        **COMMON_ERROR_RESPONSES,
    },
)
def patch_pantry_item(
    home_id: uuid.UUID,
    item_id: uuid.UUID,
    payload: PantryItemUpdateRequest,
    membership: Membership = Depends(verify_home_membership),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PantryItemResponse:
    """Update stock or status of an existing pantry item."""
    item = update_pantry_item(
        session=db,
        home_id=home_id,
        item_id=item_id,
        user_id=current_user.id,
        data=payload,
    )
    return _serialize_pantry_item(item)


@router.delete(
    "/pantry/{item_id}",
    summary="Soft-delete a pantry item",
    description=(
        "Soft-delete an item from household inventory, leaving a tombstone "
        "for offline sync."
    ),
    responses={
        **STANDARD_401_RESPONSE,
        **STANDARD_403_RESPONSE,
        **STANDARD_404_RESPONSE,
        **COMMON_ERROR_RESPONSES,
    },
)
def remove_pantry_item(
    home_id: uuid.UUID,
    item_id: uuid.UUID,
    membership: Membership = Depends(verify_home_membership),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Soft-delete an item from the household pantry."""
    delete_pantry_item(
        session=db,
        home_id=home_id,
        item_id=item_id,
        user_id=current_user.id,
    )
    return {"detail": "Pantry item removed successfully"}


@router.post(
    "/pantry/sync",
    response_model=PantrySyncResponse,
    summary="Offline delta synchronization",
    description=(
        "Reconcile offline client mutations via last-write-wins conflict "
        "resolution, record audit logs, auto-replenish Smart Baskets, and return "
        "all server modifications since last_synced_at."
    ),
    responses={
        **STANDARD_400_RESPONSE,
        **STANDARD_401_RESPONSE,
        **STANDARD_403_RESPONSE,
        **STANDARD_422_RESPONSE,
        **COMMON_ERROR_RESPONSES,
    },
)
def sync_pantry(
    home_id: uuid.UUID,
    payload: PantrySyncRequest,
    membership: Membership = Depends(verify_home_membership),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PantrySyncResponse:
    """Synchronize offline client mutations and return server deltas."""
    synced_at, deltas, applied_count = sync_pantry_mutations(
        session=db,
        home_id=home_id,
        user_id=current_user.id,
        last_synced_at=payload.last_synced_at,
        mutations=payload.mutations,
    )
    return PantrySyncResponse(
        synced_at=synced_at,
        items=[_serialize_pantry_item(d) for d in deltas],
        applied_mutations_count=applied_count,
    )


@router.get(
    "/basket",
    response_model=HouseholdBasketResponse,
    summary="Get active household Smart Basket",
    description=(
        "Retrieve the active auto-replenished shopping basket containing items "
        "flagged as low or finished in the household pantry."
    ),
    responses={
        **STANDARD_401_RESPONSE,
        **STANDARD_403_RESPONSE,
        **STANDARD_404_RESPONSE,
        **COMMON_ERROR_RESPONSES,
    },
)
def get_home_basket(
    home_id: uuid.UUID,
    membership: Membership = Depends(verify_home_membership),
    db: Session = Depends(get_db),
) -> HouseholdBasketResponse:
    """Retrieve the auto-replenished household basket."""
    basket = get_household_basket(session=db, home_id=home_id)
    basket_items_response = [
        HouseholdBasketItemResponse(
            id=bi.id,
            product_id=bi.product_id,
            product_name=bi.product.name if bi.product else "Catalog Product",
            quantity=bi.quantity,
        )
        for bi in basket.items
    ]
    return HouseholdBasketResponse(
        id=basket.id,
        home_id=basket.home_id or home_id,
        name=basket.name,
        created_at=basket.created_at,
        items=basket_items_response,
    )
