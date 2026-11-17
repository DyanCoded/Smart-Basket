"""Supermarket chains and store branches API routes."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.api.v1.schemas import StoreListResponse, StoreResponse
from src.core.database import get_db
from src.services import catalog_service

router = APIRouter(prefix="/stores", tags=["stores"])


@router.get(
    "",
    response_model=StoreListResponse,
    summary="List supermarket chains and store branches",
    description="Retrieve available store locations with chain relationships.",
)
def list_stores(
    db: Annotated[Session, Depends(get_db)],
    retailer_id: Annotated[
        uuid.UUID | None, Query(description="Filter stores by parent retailer UUID")
    ] = None,
    is_active: Annotated[
        bool | None, Query(description="Filter by active status")
    ] = None,
    q: Annotated[
        str | None,
        Query(description="Search term for store name, branch code, or address"),
    ] = None,
    limit: Annotated[
        int, Query(ge=1, le=100, description="Maximum number of stores to return")
    ] = 50,
    offset: Annotated[
        int, Query(ge=0, description="Number of stores to skip for pagination")
    ] = 0,
) -> StoreListResponse:
    """Retrieve supermarket store branches matching filter criteria."""
    items, total = catalog_service.get_stores(
        session=db,
        retailer_id=retailer_id,
        is_active=is_active,
        query=q,
        limit=limit,
        offset=offset,
    )
    return StoreListResponse(
        items=[StoreResponse.model_validate(s) for s in items],
        total=total,
        limit=limit,
        offset=offset,
    )
