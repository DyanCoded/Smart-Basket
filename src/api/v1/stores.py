"""National supermarket chains API routes."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from src.api.v1.schemas import ErrorResponse, StoreListResponse, StoreResponse
from src.core.database import get_db
from src.services import catalog_service

router = APIRouter(
    prefix="/stores",
    tags=["stores"],
    responses={
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "model": ErrorResponse,
            "description": "Internal server error occurred.",
        },
    },
)


@router.get(
    "",
    response_model=StoreListResponse,
    responses={
        status.HTTP_200_OK: {
            "model": StoreListResponse,
            "description": "Paginated list of monitored national supermarket chains.",
        },
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorResponse,
            "description": "Invalid query parameters.",
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "model": ErrorResponse,
            "description": "Validation error in pagination or query parameters.",
        },
    },
    summary="List monitored national supermarket chains",
    description=(
        "Retrieve the 5 canonical South African national supermarket chains "
        "(Shoprite, Checkers, Pick n Pay, Woolworths Food, and SPAR) tracked "
        "for chain-level grocery pricing. Supports filtering by retailer UUID, "
        "active status, and chain name query."
    ),
    response_description="Paginated list of canonical national supermarket chains.",
)
def list_stores(
    db: Annotated[Session, Depends(get_db)],
    retailer_id: Annotated[
        uuid.UUID | None,
        Query(description="Filter by parent retailer UUID"),
    ] = None,
    is_active: Annotated[
        bool | None,
        Query(description="Filter by active monitoring status"),
    ] = None,
    q: Annotated[
        str | None,
        Query(description="Search term for national retailer chain name or slug"),
    ] = None,
    limit: Annotated[
        int,
        Query(ge=1, le=100, description="Maximum number of chains to return"),
    ] = 50,
    offset: Annotated[
        int,
        Query(ge=0, description="Number of chains to skip for pagination"),
    ] = 0,
) -> StoreListResponse:
    """Retrieve canonical national supermarket chains matching filter criteria."""
    items, total = catalog_service.get_stores(
        session=db,
        retailer_id=retailer_id,
        is_active=is_active,
        query=q,
        limit=limit,
        offset=offset,
    )
    freshness_map = catalog_service.get_store_freshness_map(
        db, [store.id for store in items]
    )

    store_responses: list[StoreResponse] = []
    latest_sync_at = None
    for store in items:
        chain_sync_at, tracked_count = freshness_map.get(store.id, (None, 0))
        if chain_sync_at is not None and (
            latest_sync_at is None or chain_sync_at > latest_sync_at
        ):
            latest_sync_at = chain_sync_at

        store_resp = StoreResponse.model_validate(store).model_copy(
            update={
                "last_price_sync_at": chain_sync_at,
                "tracked_products_count": tracked_count,
            }
        )
        store_responses.append(store_resp)

    return StoreListResponse(
        items=store_responses,
        total=total,
        limit=limit,
        offset=offset,
        last_price_sync_at=latest_sync_at,
    )
