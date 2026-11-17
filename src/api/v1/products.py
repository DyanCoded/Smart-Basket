"""Product catalog search and pricing API routes."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.api.v1.schemas import (
    ErrorResponse,
    ProductListResponse,
    ProductPricesResponse,
    ProductResponse,
    StorePriceItem,
)
from src.core.database import get_db
from src.services import catalog_service

router = APIRouter(prefix="/products", tags=["products"])


@router.get(
    "",
    response_model=ProductListResponse,
    summary="Search and filter product catalog",
    description="Search products by partial name, brand, or barcode with pagination.",
)
def list_products(
    db: Annotated[Session, Depends(get_db)],
    q: Annotated[
        str | None,
        Query(description="Case-insensitive search term for name, brand, or barcode"),
    ] = None,
    brand: Annotated[
        str | None, Query(description="Filter by exact or partial brand name")
    ] = None,
    category_id: Annotated[
        uuid.UUID | None, Query(description="Filter by category UUID")
    ] = None,
    limit: Annotated[
        int, Query(ge=1, le=100, description="Maximum number of items to return")
    ] = 20,
    offset: Annotated[
        int, Query(ge=0, description="Number of items to skip for pagination")
    ] = 0,
) -> ProductListResponse:
    """Retrieve catalog products matching optional filter criteria."""
    items, total = catalog_service.get_products(
        session=db,
        query=q,
        brand=brand,
        category_id=category_id,
        limit=limit,
        offset=offset,
    )
    return ProductListResponse(
        items=[ProductResponse.model_validate(p) for p in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{product_id}",
    response_model=ProductResponse,
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
    summary="Get product details",
    description="Retrieve detailed product metadata including barcode and packaging.",
)
def get_product(
    product_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
) -> ProductResponse:
    """Retrieve detailed product information by unique identifier."""
    product = catalog_service.get_product_by_id(session=db, product_id=product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with id '{product_id}' not found",
        )
    return ProductResponse.model_validate(product)


@router.get(
    "/{product_id}/prices",
    response_model=ProductPricesResponse,
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
    summary="Get store pricing for product",
    description="List active prices and stock status across stores.",
)
def get_product_prices(
    product_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
) -> ProductPricesResponse:
    """Retrieve active prices across all store branches for a product."""
    product = catalog_service.get_product_by_id(session=db, product_id=product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with id '{product_id}' not found",
        )

    raw_prices = catalog_service.get_product_prices(session=db, product_id=product_id)
    prices = [StorePriceItem.model_validate(p) for p in raw_prices]

    return ProductPricesResponse(
        product_id=product.id,
        product_name=product.name,
        prices=prices,
        total_stores=len(prices),
    )
