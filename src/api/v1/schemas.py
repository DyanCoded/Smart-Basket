"""Pydantic schemas and DTOs for API v1."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class CategorySummary(BaseModel):
    """Category summary schema."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str


class ProductResponse(BaseModel):
    """Detailed product metadata response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    brand: Optional[str] = None
    barcode: Optional[str] = None
    unit_size: Decimal
    unit_type: str
    category_id: Optional[uuid.UUID] = None
    category: Optional[CategorySummary] = None
    created_at: datetime


class ProductListResponse(BaseModel):
    """Paginated list of products."""

    items: List[ProductResponse]
    total: int = Field(ge=0, description="Total matching items count")
    limit: int = Field(ge=1, le=100, description="Items limit per page")
    offset: int = Field(ge=0, description="Items offset")


class RetailerSummary(BaseModel):
    """Retailer chain summary."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str


class StoreResponse(BaseModel):
    """Store branch response with retailer info."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    branch_code: Optional[str] = None
    address: Optional[str] = None
    is_active: bool
    retailer_id: uuid.UUID
    retailer: Optional[RetailerSummary] = None
    created_at: datetime


class StoreListResponse(BaseModel):
    """Paginated list of stores."""

    items: List[StoreResponse]
    total: int = Field(ge=0, description="Total matching stores count")
    limit: int = Field(ge=1, le=100, description="Items limit per page")
    offset: int = Field(ge=0, description="Items offset")


class StorePriceItem(BaseModel):
    """Active price and availability of a product at a specific store."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    store_id: uuid.UUID
    store_name: str
    branch_code: Optional[str] = None
    retailer_name: str
    price: Decimal
    is_promotional: bool
    is_in_stock: bool
    updated_at: datetime


class ProductPricesResponse(BaseModel):
    """Active prices across all monitored stores for a specific item."""

    product_id: uuid.UUID
    product_name: str
    prices: List[StorePriceItem]
    total_stores: int


class BasketItemRequest(BaseModel):
    """Individual item requested in a shopping basket calculation."""

    product_id: uuid.UUID
    quantity: Decimal = Field(
        gt=Decimal("0.00"),
        default=Decimal("1.00"),
        description="Required quantity, must be greater than zero",
    )


class BasketCalculationRequest(BaseModel):
    """Shopping basket calculation payload containing required items."""

    items: List[BasketItemRequest] = Field(
        min_length=1,
        description="List of grocery products and required quantities",
    )


class BasketItemDetail(BaseModel):
    """Individual item line calculation for a specific store."""

    product_id: uuid.UUID
    product_name: str
    quantity: Decimal
    unit_price: Decimal
    subtotal: Decimal
    is_promotional: bool


class MissingItemDetail(BaseModel):
    """Missing or out-of-stock item warning for a specific store."""

    product_id: uuid.UUID
    product_name: str
    quantity: Decimal


class StoreBasketTotal(BaseModel):
    """Total basket cost calculation for a single store location."""

    store_id: uuid.UUID
    store_name: str
    branch_code: Optional[str] = None
    retailer_name: str
    total_price: Decimal
    is_complete_match: bool
    items_available_count: int
    total_items_count: int
    items: List[BasketItemDetail]
    missing_items: List[MissingItemDetail]


class SplitStoreAllocation(BaseModel):
    """Assigned items and subtotal for a store participating in a split."""

    store_id: uuid.UUID
    store_name: str
    retailer_name: str
    items: List[BasketItemDetail]
    subtotal: Decimal


class OptimalSplitResult(BaseModel):
    """Smart Mode multi-store split optimization results."""

    stores: List[SplitStoreAllocation]
    total_price: Decimal
    savings_amount: Decimal
    savings_percentage: Decimal
    is_complete_match: bool
    cheaper_than_single_store: bool


class BasketCalculationResponse(BaseModel):
    """Response payload for multi-store basket evaluation and optimization."""

    ranked_stores: List[StoreBasketTotal]
    cheapest_single_store: Optional[StoreBasketTotal] = None
    optimal_split: Optional[OptimalSplitResult] = None
    total_items_requested: int


class PriceHistoryPoint(BaseModel):
    """Single historical price log record."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    store_id: uuid.UUID
    store_name: str
    retailer_name: str
    price: Decimal
    is_promotional: bool
    recorded_at: datetime


class ProductPriceHistoryResponse(BaseModel):
    """Historical timeseries of price observations for a product."""

    product_id: uuid.UUID
    product_name: str
    store_id: Optional[uuid.UUID] = None
    total_points: int
    history: List[PriceHistoryPoint]


class PriceIntelligenceResponse(BaseModel):
    """Trend metrics and deal veracity intelligence for a product."""

    product_id: uuid.UUID
    product_name: str
    store_id: Optional[uuid.UUID] = None
    all_time_lowest_price: Decimal
    all_time_highest_price: Decimal
    current_lowest_price: Optional[Decimal] = None
    current_average_price: Optional[Decimal] = None
    historical_average_price: Optional[Decimal] = None
    price_change_percentage: Decimal
    trend_direction: str = Field(
        description="Price trend direction: INCREASING, DECREASING, or STABLE"
    )
    is_on_promotion: bool
    current_promotional_price: Optional[Decimal] = None
    is_genuine_deal: bool
    discount_veracity_score: Decimal = Field(
        description="Rating from 0.00 to 100.00 on discount authenticity"
    )
    veracity_rating: str = Field(
        description=(
            "GENUINE_SAVINGS, ARTIFICIAL_DISCOUNT, REGULAR_PRICE, or NO_PROMOTION"
        )
    )
    sample_size_days: int


class ErrorResponse(BaseModel):
    """Standard error response payload."""

    detail: str
