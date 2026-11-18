"""Supermarket chains and store branches API routes."""

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
            "description": "Paginated list of matching store branches.",
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
    summary="List supermarket chains and store branches",
    description=(
        "Retrieve supermarket branches with parent retailer relationship, "
        "address details, and active monitoring status. Supports filtering "
        "by retailer chain UUID, active status, and search query."
    ),
    response_description="Paginated list of supermarket store branches.",
)
def list_stores(
    db: Annotated[Session, Depends(get_db)],
    retailer_id: Annotated[
        uuid.UUID | None,
        Query(description="Filter stores by parent retailer UUID"),
    ] = None,
    is_active: Annotated[
        bool | None,
        Query(description="Filter by active status"),
    ] = None,
    q: Annotated[
        str | None,
        Query(description="Search term for store name, branch code, or address"),
    ] = None,
    limit: Annotated[
        int,
        Query(ge=1, le=100, description="Maximum number of stores to return"),
    ] = 50,
    offset: Annotated[
        int,
        Query(ge=0, description="Number of stores to skip for pagination"),
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
