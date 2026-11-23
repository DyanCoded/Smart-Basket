"""Product catalog search, pricing, history, and intelligence API routes."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.api.v1.schemas import (
    ErrorResponse,
    PriceHistoryPoint,
    PriceIntelligenceResponse,
    ProductListResponse,
    ProductPriceHistoryResponse,
    ProductPricesResponse,
    ProductResponse,
    StorePriceItem,
)
from src.core.database import get_db
from src.services import catalog_service, intelligence_service

router = APIRouter(
    prefix="/products",
    tags=["products"],
    responses={
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "model": ErrorResponse,
            "description": "Internal server error occurred.",
        },
    },
)


@router.get(
    "",
    response_model=ProductListResponse,
    responses={
        status.HTTP_200_OK: {
            "model": ProductListResponse,
            "description": "Paginated list of catalog products.",
        },
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorResponse,
            "description": "Invalid query parameters.",
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "model": ErrorResponse,
            "description": "Validation error in pagination parameters.",
        },
    },
    summary="Search and filter product catalog",
    description=(
        "Search and filter grocery products by case-insensitive partial name, "
        "brand, barcode, or category UUID with offset-based pagination. "
        "Results prioritize products with active store_prices across multiple "
        "national supermarket chains."
    ),
    response_description="Paginated list of matching catalog products.",
)
def list_products(
    db: Annotated[Session, Depends(get_db)],
    q: Annotated[
        str | None,
        Query(description=("Case-insensitive search term for name, brand, or barcode")),
    ] = None,
    brand: Annotated[
        str | None,
        Query(description="Filter by exact or partial brand name"),
    ] = None,
    category_id: Annotated[
        uuid.UUID | None,
        Query(description="Filter by category UUID"),
    ] = None,
    limit: Annotated[
        int,
        Query(ge=1, le=100, description="Maximum number of items to return"),
    ] = 20,
    offset: Annotated[
        int,
        Query(ge=0, description="Number of items to skip for pagination"),
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
    responses={
        status.HTTP_200_OK: {
            "model": ProductResponse,
            "description": "Product metadata retrieved successfully.",
        },
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponse,
            "description": "Product with specified id not found.",
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "model": ErrorResponse,
            "description": "Invalid UUID format in path parameter.",
        },
    },
    summary="Get product details",
    description=(
        "Retrieve detailed product metadata including barcode, packaging "
        "unit size, unit type, and associated category information."
    ),
    response_description="Detailed product metadata record.",
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
    responses={
        status.HTTP_200_OK: {
            "model": ProductPricesResponse,
            "description": "Active prices and stock status across all stores.",
        },
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponse,
            "description": "Product with specified id not found.",
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "model": ErrorResponse,
            "description": "Invalid UUID format in path parameter.",
        },
    },
    summary="Get store pricing for product",
    description=(
        "List active prices, promotional discounts, and inventory stock "
        "status across all monitored supermarket chains and store branches."
    ),
    response_description="Active store prices and stock status for the product.",
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


@router.get(
    "/{product_id}/history",
    response_model=ProductPriceHistoryResponse,
    responses={
        status.HTTP_200_OK: {
            "model": ProductPriceHistoryResponse,
            "description": "Chronological price observations returned.",
        },
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorResponse,
            "description": "Invalid date range parameters (start_date > end_date).",
        },
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponse,
            "description": "Product or store with specified id not found.",
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "model": ErrorResponse,
            "description": "Validation error in query parameters or date formats.",
        },
    },
    summary="Retrieve price timeseries history",
    description=(
        "Fetch timestamped price entries for a product across configurable "
        "time windows and store locations, sorted chronologically for charting."
    ),
    response_description="Historical price timeseries data points.",
)
def get_product_price_history(
    product_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    store_id: Annotated[
        uuid.UUID | None,
        Query(description="Filter timeseries by store UUID"),
    ] = None,
    start_date: Annotated[
        datetime | None,
        Query(description="Beginning of historical window (ISO-8601)"),
    ] = None,
    end_date: Annotated[
        datetime | None,
        Query(description="End of historical window (ISO-8601)"),
    ] = None,
    limit: Annotated[
        int,
        Query(ge=1, le=500, description="Max history points to return"),
    ] = 100,
    offset: Annotated[
        int,
        Query(ge=0, description="History points offset"),
    ] = 0,
) -> ProductPriceHistoryResponse:
    """Retrieve chronological price timeseries data for charting."""
    product = catalog_service.get_product_by_id(session=db, product_id=product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with id '{product_id}' not found",
        )

    if store_id:
        raw_stores, _ = catalog_service.get_stores(session=db, limit=100)
        if not any(s.id == store_id for s in raw_stores):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Store with id '{store_id}' not found",
            )

    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date must be before or equal to end_date",
        )

    points, total = intelligence_service.get_price_history(
        session=db,
        product_id=product_id,
        store_id=store_id,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
    )

    return ProductPriceHistoryResponse(
        product_id=product.id,
        product_name=product.name,
        store_id=store_id,
        total_points=total,
        history=[PriceHistoryPoint.model_validate(pt) for pt in points],
    )


@router.get(
    "/{product_id}/intelligence",
    response_model=PriceIntelligenceResponse,
    responses={
        status.HTTP_200_OK: {
            "model": PriceIntelligenceResponse,
            "description": "Analytical intelligence and deal veracity score computed.",
        },
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponse,
            "description": "Product or store with specified id not found.",
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "model": ErrorResponse,
            "description": "Invalid UUID format in path or query parameter.",
        },
    },
    summary="Get price trend intelligence and deal indicator",
    description=(
        "Compute all-time high/low, current vs historical average prices, "
        "percentage change, trend direction (INCREASING/DECREASING/STABLE), "
        "and promotional discount veracity scoring (0-100 rating)."
    ),
    response_description="Product price trend metrics and discount veracity analytics.",
)
def get_product_intelligence(
    product_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    store_id: Annotated[
        uuid.UUID | None,
        Query(description="Calculate metrics for a specific store location"),
    ] = None,
) -> PriceIntelligenceResponse:
    """Calculate price metrics, historical trend, and deal veracity score."""
    product = catalog_service.get_product_by_id(session=db, product_id=product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with id '{product_id}' not found",
        )

    if store_id:
        raw_stores, _ = catalog_service.get_stores(session=db, limit=100)
        if not any(s.id == store_id for s in raw_stores):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Store with id '{store_id}' not found",
            )

    metrics = intelligence_service.get_price_intelligence(
        session=db, product_id=product_id, store_id=store_id
    )

    return PriceIntelligenceResponse(
        product_id=product.id,
        product_name=product.name,
        store_id=store_id,
        all_time_lowest_price=metrics["all_time_lowest_price"],
        all_time_highest_price=metrics["all_time_highest_price"],
        current_lowest_price=metrics["current_lowest_price"],
        current_average_price=metrics["current_average_price"],
        historical_average_price=metrics["historical_average_price"],
        price_change_percentage=metrics["price_change_percentage"],
        trend_direction=metrics["trend_direction"],
        is_on_promotion=metrics["is_on_promotion"],
        current_promotional_price=metrics["current_promotional_price"],
        is_genuine_deal=metrics["is_genuine_deal"],
        discount_veracity_score=metrics["discount_veracity_score"],
        veracity_rating=metrics["veracity_rating"],
        sample_size_days=metrics["sample_size_days"],
    )
