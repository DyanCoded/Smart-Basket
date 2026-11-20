"""Pydantic schemas and DTOs for API v1."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, List, Optional

from fastapi import status
from pydantic import BaseModel, ConfigDict, Field

_EX_MILK_ID = "6e2941e3-033d-5768-8143-5e7ebc24b874"
_EX_BREAD_ID = "ab9928f5-221a-5546-8b6c-c4ec04fbe933"
_EX_MILK_NAME = "Full Cream Fresh Milk 2L"
_EX_BREAD_NAME = "Superior Sliced White Bread 700g"
_EX_CAT_DAIRY_ID = "dcda34e0-efd6-5f43-b188-db739a0deab7"
_EX_RET_CHK_ID = "3ae15000-8907-5fb5-9904-c47dba4bcc3e"
_EX_STORE_CHK_ID = "26f7a89e-0e58-56e3-a225-8c7310382985"
_EX_STORE_PNP_ID = "cd86c9b4-176c-551e-aebc-b91bfdce86c1"


class CategorySummary(BaseModel):
    """Category summary schema."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": "dcda34e0-efd6-5f43-b188-db739a0deab7",
                    "name": "Dairy & Eggs",
                    "slug": "dairy-eggs",
                }
            ]
        },
    )

    id: uuid.UUID = Field(description="Unique category identifier")
    name: str = Field(description="Category display name")
    slug: str = Field(description="URL-friendly unique slug")


class ProductResponse(BaseModel):
    """Detailed product metadata response."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": "6e2941e3-033d-5768-8143-5e7ebc24b874",
                    "name": "Full Cream Fresh Milk 2L",
                    "brand": "Clover",
                    "barcode": "6001299011011",
                    "unit_size": "2.00",
                    "unit_type": "L",
                    "category_id": "dcda34e0-efd6-5f43-b188-db739a0deab7",
                    "category": {
                        "id": "dcda34e0-efd6-5f43-b188-db739a0deab7",
                        "name": "Dairy & Eggs",
                        "slug": "dairy-eggs",
                    },
                    "created_at": "2026-01-15T08:00:00Z",
                }
            ]
        },
    )

    id: uuid.UUID = Field(description="Unique product identifier")
    name: str = Field(description="Universal item name")
    brand: Optional[str] = Field(default=None, description="Manufacturer brand name")
    barcode: Optional[str] = Field(default=None, description="Standard barcode or UPC")
    unit_size: Decimal = Field(description="Standard packaging quantity or volume")
    unit_type: str = Field(description="Unit of measurement (e.g. L, g, kg, unit)")
    category_id: Optional[uuid.UUID] = Field(
        default=None, description="Parent category UUID"
    )
    category: Optional[CategorySummary] = Field(
        default=None, description="Expanded category details"
    )
    created_at: datetime = Field(
        description="Timestamp when product was added to catalog"
    )


class ProductListResponse(BaseModel):
    """Paginated list of products."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "items": [
                        {
                            "id": "6e2941e3-033d-5768-8143-5e7ebc24b874",
                            "name": "Full Cream Fresh Milk 2L",
                            "brand": "Clover",
                            "barcode": "6001299011011",
                            "unit_size": "2.00",
                            "unit_type": "L",
                            "category_id": "dcda34e0-efd6-5f43-b188-db739a0deab7",
                            "category": {
                                "id": "dcda34e0-efd6-5f43-b188-db739a0deab7",
                                "name": "Dairy & Eggs",
                                "slug": "dairy-eggs",
                            },
                            "created_at": "2026-01-15T08:00:00Z",
                        }
                    ],
                    "total": 1,
                    "limit": 20,
                    "offset": 0,
                }
            ]
        }
    )

    items: List[ProductResponse] = Field(
        description="List of product records matching criteria"
    )
    total: int = Field(ge=0, description="Total matching items count")
    limit: int = Field(ge=1, le=100, description="Items limit per page")
    offset: int = Field(ge=0, description="Items offset")


class RetailerSummary(BaseModel):
    """Retailer chain summary."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": "3ae15000-8907-5fb5-9904-c47dba4bcc3e",
                    "name": "Checkers",
                    "slug": "checkers",
                }
            ]
        },
    )

    id: uuid.UUID = Field(description="Unique retailer chain UUID")
    name: str = Field(description="Supermarket chain name")
    slug: str = Field(description="Unique slug for chain")


class StoreResponse(BaseModel):
    """Store branch response with retailer info."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": _EX_STORE_CHK_ID,
                    "name": "Checkers",
                    "branch_code": None,
                    "address": None,
                    "is_active": True,
                    "retailer_id": _EX_RET_CHK_ID,
                    "retailer": {
                        "id": _EX_RET_CHK_ID,
                        "name": "Checkers",
                        "slug": "checkers",
                    },
                    "created_at": "2026-01-15T08:00:00Z",
                }
            ]
        },
    )

    id: uuid.UUID = Field(description="Canonical retailer chain store UUID")
    name: str = Field(description="National retailer chain name")
    branch_code: Optional[str] = Field(
        default=None, description="Unused at national chain level (always null)"
    )
    address: Optional[str] = Field(
        default=None, description="Unused at national chain level (always null)"
    )
    is_active: bool = Field(description="Whether the retailer chain is monitored")
    retailer_id: uuid.UUID = Field(description="Parent retailer chain UUID")
    retailer: Optional[RetailerSummary] = Field(
        default=None, description="Expanded parent retailer details"
    )
    created_at: datetime = Field(description="Timestamp when chain was registered")


class StoreListResponse(BaseModel):
    """Paginated list of canonical national retailer chains."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "items": [
                        {
                            "id": _EX_STORE_CHK_ID,
                            "name": "Checkers",
                            "branch_code": None,
                            "address": None,
                            "is_active": True,
                            "retailer_id": _EX_RET_CHK_ID,
                            "retailer": {
                                "id": _EX_RET_CHK_ID,
                                "name": "Checkers",
                                "slug": "checkers",
                            },
                            "created_at": "2026-01-15T08:00:00Z",
                        }
                    ],
                    "total": 5,
                    "limit": 50,
                    "offset": 0,
                }
            ]
        }
    )

    items: List[StoreResponse] = Field(description="Retailer chains matching filter")
    total: int = Field(ge=0, description="Total matching retailer chains count")
    limit: int = Field(ge=1, le=100, description="Items limit per page")
    offset: int = Field(ge=0, description="Items offset")


class StorePriceItem(BaseModel):
    """Active national chain-level price of a product at a retailer."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": "c1d2e3f4-1234-5678-90ab-cdef12345678",
                    "store_id": _EX_STORE_CHK_ID,
                    "store_name": "Checkers",
                    "branch_code": None,
                    "retailer_name": "Checkers",
                    "price": "34.99",
                    "is_promotional": True,
                    "is_in_stock": True,
                    "updated_at": "2026-01-15T08:00:00Z",
                }
            ]
        },
    )

    id: uuid.UUID = Field(description="Chain price observation record UUID")
    store_id: uuid.UUID = Field(description="Canonical retailer chain UUID")
    store_name: str = Field(description="National retailer chain name")
    branch_code: Optional[str] = Field(
        default=None, description="Unused at national chain level (always null)"
    )
    retailer_name: str = Field(description="National retailer chain name")
    price: Decimal = Field(description="Active national chain shelf price in ZAR")
    is_promotional: bool = Field(
        description="Whether price is an active promotional discount"
    )
    is_in_stock: bool = Field(description="Active catalog listing indicator")
    updated_at: datetime = Field(description="Timestamp of latest price verification")


class ProductPricesResponse(BaseModel):
    """Active prices across all monitored stores for a specific item."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "product_id": "6e2941e3-033d-5768-8143-5e7ebc24b874",
                    "product_name": "Full Cream Fresh Milk 2L",
                    "prices": [
                        {
                            "id": "c1d2e3f4-1234-5678-90ab-cdef12345678",
                            "store_id": "a3b3c260-9228-54dd-ba6d-3b216931987e",
                            "store_name": "Checkers",
                            "branch_code": None,
                            "retailer_name": "Checkers",
                            "price": "36.99",
                            "is_promotional": False,
                            "is_in_stock": True,
                            "updated_at": "2026-01-15T08:00:00Z",
                        }
                    ],
                    "total_stores": 1,
                }
            ]
        }
    )

    product_id: uuid.UUID = Field(description="Target product identifier")
    product_name: str = Field(description="Product display name")
    prices: List[StorePriceItem] = Field(
        description="Active prices across retail store branches"
    )
    total_stores: int = Field(description="Count of reporting stores")


class BasketItemRequest(BaseModel):
    """Individual item requested in a shopping basket calculation."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "product_id": "6e2941e3-033d-5768-8143-5e7ebc24b874",
                    "quantity": "2.00",
                }
            ]
        }
    )

    product_id: uuid.UUID = Field(
        description="Catalog product UUID to add to the basket"
    )
    quantity: Decimal = Field(
        gt=Decimal("0.00"),
        default=Decimal("1.00"),
        description="Required quantity, must be greater than zero",
    )


class BasketCalculationRequest(BaseModel):
    """Shopping basket calculation payload containing required items."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "items": [
                        {
                            "product_id": "6e2941e3-033d-5768-8143-5e7ebc24b874",
                            "quantity": "2.00",
                        },
                        {
                            "product_id": "ab9928f5-221a-5546-8b6c-c4ec04fbe933",
                            "quantity": "1.00",
                        },
                    ]
                }
            ]
        }
    )

    items: List[BasketItemRequest] = Field(
        min_length=1,
        description="List of grocery products and required quantities",
    )


class BasketItemDetail(BaseModel):
    """Individual item line calculation for a specific store."""

    product_id: uuid.UUID = Field(description="Product UUID")
    product_name: str = Field(description="Item name")
    quantity: Decimal = Field(description="Requested quantity")
    unit_price: Decimal = Field(description="Unit price at store in ZAR")
    subtotal: Decimal = Field(description="Line total (quantity * unit_price)")
    is_promotional: bool = Field(description="Whether priced on promotion")


class MissingItemDetail(BaseModel):
    """Missing or out-of-stock item warning for a specific store."""

    product_id: uuid.UUID = Field(description="Missing product UUID")
    product_name: str = Field(description="Missing product name")
    quantity: Decimal = Field(description="Unfulfilled quantity requested")


class StoreBasketTotal(BaseModel):
    """Total basket cost calculation for a single store location."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "store_id": "a3b3c260-9228-54dd-ba6d-3b216931987e",
                    "store_name": "Checkers",
                    "branch_code": None,
                    "retailer_name": "Checkers",
                    "total_price": "92.97",
                    "is_complete_match": True,
                    "items_available_count": 2,
                    "total_items_count": 2,
                    "items": [
                        {
                            "product_id": "6e2941e3-033d-5768-8143-5e7ebc24b874",
                            "product_name": "Full Cream Fresh Milk 2L",
                            "quantity": "2.00",
                            "unit_price": "36.99",
                            "subtotal": "73.98",
                            "is_promotional": False,
                        },
                        {
                            "product_id": "ab9928f5-221a-5546-8b6c-c4ec04fbe933",
                            "product_name": "Superior Sliced White Bread 700g",
                            "quantity": "1.00",
                            "unit_price": "18.99",
                            "subtotal": "18.99",
                            "is_promotional": False,
                        },
                    ],
                    "missing_items": [],
                }
            ]
        }
    )

    store_id: uuid.UUID = Field(description="Store branch UUID")
    store_name: str = Field(description="Store branch location name")
    branch_code: Optional[str] = Field(default=None, description="Retailer branch code")
    retailer_name: str = Field(description="Parent retailer chain name")
    total_price: Decimal = Field(
        description="Calculated total cost for available basket items in ZAR"
    )
    is_complete_match: bool = Field(
        description="True if store carries 100% of requested items in-stock"
    )
    items_available_count: int = Field(description="Number of basket items fulfilled")
    total_items_count: int = Field(description="Total distinct items in basket")
    items: List[BasketItemDetail] = Field(description="Fulfilled item line breakdowns")
    missing_items: List[MissingItemDetail] = Field(
        description="Items unavailable or missing at this store"
    )


class SplitStoreAllocation(BaseModel):
    """Assigned items and subtotal for a store participating in a split."""

    store_id: uuid.UUID = Field(description="Participating store UUID")
    store_name: str = Field(description="Store branch name")
    retailer_name: str = Field(description="Retailer chain name")
    items: List[BasketItemDetail] = Field(
        description="Items allocated to this store for cheapest price"
    )
    subtotal: Decimal = Field(description="Subtotal for this store's portion")


class OptimalSplitResult(BaseModel):
    """Smart Mode multi-store split optimization results."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "stores": [
                        {
                            "store_id": _EX_STORE_CHK_ID,
                            "store_name": "Checkers",
                            "retailer_name": "Checkers",
                            "items": [
                                {
                                    "product_id": _EX_MILK_ID,
                                    "product_name": "Full Cream Fresh Milk 2L",
                                    "quantity": "2.00",
                                    "unit_price": "36.99",
                                    "subtotal": "73.98",
                                    "is_promotional": False,
                                }
                            ],
                            "subtotal": "73.98",
                        },
                        {
                            "store_id": _EX_STORE_PNP_ID,
                            "store_name": "Pick n Pay",
                            "retailer_name": "Pick n Pay",
                            "items": [
                                {
                                    "product_id": _EX_BREAD_ID,
                                    "product_name": "Superior Sliced White Bread 700g",
                                    "quantity": "1.00",
                                    "unit_price": "17.49",
                                    "subtotal": "17.49",
                                    "is_promotional": True,
                                }
                            ],
                            "subtotal": "17.49",
                        },
                    ],
                    "total_price": "91.47",
                    "savings_amount": "1.50",
                    "savings_percentage": "1.61",
                    "is_complete_match": True,
                    "cheaper_than_single_store": True,
                }
            ]
        }
    )

    stores: List[SplitStoreAllocation] = Field(
        description="Stores chosen for optimal combination"
    )
    total_price: Decimal = Field(description="Combined total price across stores")
    savings_amount: Decimal = Field(
        description="Absolute savings vs best single store in ZAR"
    )
    savings_percentage: Decimal = Field(
        description="Percentage savings vs best single store"
    )
    is_complete_match: bool = Field(
        description="True if all basket items are fulfilled across split stores"
    )
    cheaper_than_single_store: bool = Field(
        description="True if split basket achieves lower total than any single store"
    )


class BasketCalculationResponse(BaseModel):
    """Response payload for multi-store basket evaluation and optimization."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "ranked_stores": [
                        {
                            "store_id": _EX_STORE_CHK_ID,
                            "store_name": "Checkers",
                            "branch_code": None,
                            "retailer_name": "Checkers",
                            "total_price": "92.97",
                            "is_complete_match": True,
                            "items_available_count": 2,
                            "total_items_count": 2,
                            "items": [
                                {
                                    "product_id": _EX_MILK_ID,
                                    "product_name": "Full Cream Fresh Milk 2L",
                                    "quantity": "2.00",
                                    "unit_price": "36.99",
                                    "subtotal": "73.98",
                                    "is_promotional": False,
                                },
                                {
                                    "product_id": _EX_BREAD_ID,
                                    "product_name": "Superior Sliced White Bread 700g",
                                    "quantity": "1.00",
                                    "unit_price": "18.99",
                                    "subtotal": "18.99",
                                    "is_promotional": False,
                                },
                            ],
                            "missing_items": [],
                        }
                    ],
                    "cheapest_single_store": {
                        "store_id": _EX_STORE_CHK_ID,
                        "store_name": "Checkers",
                        "branch_code": None,
                        "retailer_name": "Checkers",
                        "total_price": "92.97",
                        "is_complete_match": True,
                        "items_available_count": 2,
                        "total_items_count": 2,
                        "items": [
                            {
                                "product_id": _EX_MILK_ID,
                                "product_name": "Full Cream Fresh Milk 2L",
                                "quantity": "2.00",
                                "unit_price": "36.99",
                                "subtotal": "73.98",
                                "is_promotional": False,
                            },
                            {
                                "product_id": _EX_BREAD_ID,
                                "product_name": "Superior Sliced White Bread 700g",
                                "quantity": "1.00",
                                "unit_price": "18.99",
                                "subtotal": "18.99",
                                "is_promotional": False,
                            },
                        ],
                        "missing_items": [],
                    },
                    "optimal_split": {
                        "stores": [
                            {
                                "store_id": _EX_STORE_CHK_ID,
                                "store_name": "Checkers",
                                "retailer_name": "Checkers",
                                "items": [
                                    {
                                        "product_id": _EX_MILK_ID,
                                        "product_name": "Full Cream Fresh Milk 2L",
                                        "quantity": "2.00",
                                        "unit_price": "36.99",
                                        "subtotal": "73.98",
                                        "is_promotional": False,
                                    }
                                ],
                                "subtotal": "73.98",
                            },
                            {
                                "store_id": _EX_STORE_PNP_ID,
                                "store_name": "Pick n Pay",
                                "retailer_name": "Pick n Pay",
                                "items": [
                                    {
                                        "product_id": _EX_BREAD_ID,
                                        "product_name": _EX_BREAD_NAME,
                                        "quantity": "1.00",
                                        "unit_price": "17.49",
                                        "subtotal": "17.49",
                                        "is_promotional": True,
                                    }
                                ],
                                "subtotal": "17.49",
                            },
                        ],
                        "total_price": "91.47",
                        "savings_amount": "1.50",
                        "savings_percentage": "1.61",
                        "is_complete_match": True,
                        "cheaper_than_single_store": True,
                    },
                    "total_items_requested": 2,
                }
            ]
        }
    )

    ranked_stores: List[StoreBasketTotal] = Field(
        description="Stores ranked deterministically by total price (ascending)"
    )
    cheapest_single_store: Optional[StoreBasketTotal] = Field(
        default=None,
        description="Cheapest single-store location capable of fulfilling items",
    )
    optimal_split: Optional[OptimalSplitResult] = Field(
        default=None,
        description="Smart Mode multi-store split optimization recommendation",
    )
    total_items_requested: int = Field(
        description="Total distinct item types in the calculation request"
    )


class PriceHistoryPoint(BaseModel):
    """Single historical price log record."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": "e5f6a7b8-1234-5678-90ab-cdef12345678",
                    "store_id": "a3b3c260-9228-54dd-ba6d-3b216931987e",
                    "store_name": "Checkers",
                    "retailer_name": "Checkers",
                    "price": "34.99",
                    "is_promotional": True,
                    "recorded_at": "2026-01-01T10:00:00Z",
                }
            ]
        },
    )

    id: uuid.UUID = Field(description="Historical price entry UUID")
    store_id: uuid.UUID = Field(description="Store branch UUID")
    store_name: str = Field(description="Store branch location name")
    retailer_name: str = Field(description="Parent retailer chain name")
    price: Decimal = Field(description="Historical observed price in ZAR")
    is_promotional: bool = Field(description="Promotional status at observation time")
    recorded_at: datetime = Field(description="Timestamp when price was recorded")


class ProductPriceHistoryResponse(BaseModel):
    """Historical timeseries of price observations for a product."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "product_id": "6e2941e3-033d-5768-8143-5e7ebc24b874",
                    "product_name": "Full Cream Fresh Milk 2L",
                    "store_id": "a3b3c260-9228-54dd-ba6d-3b216931987e",
                    "total_points": 1,
                    "history": [
                        {
                            "id": "e5f6a7b8-1234-5678-90ab-cdef12345678",
                            "store_id": "a3b3c260-9228-54dd-ba6d-3b216931987e",
                            "store_name": "Checkers",
                            "retailer_name": "Checkers",
                            "price": "34.99",
                            "is_promotional": True,
                            "recorded_at": "2026-01-01T10:00:00Z",
                        }
                    ],
                }
            ]
        }
    )

    product_id: uuid.UUID = Field(description="Target product UUID")
    product_name: str = Field(description="Product item name")
    store_id: Optional[uuid.UUID] = Field(
        default=None, description="Optional store filter applied"
    )
    total_points: int = Field(description="Total historical data points matched")
    history: List[PriceHistoryPoint] = Field(
        description="Chronological list of price observations"
    )


class PriceIntelligenceResponse(BaseModel):
    """Trend metrics and deal veracity intelligence for a product."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "product_id": "6e2941e3-033d-5768-8143-5e7ebc24b874",
                    "product_name": "Full Cream Fresh Milk 2L",
                    "store_id": None,
                    "all_time_lowest_price": "32.99",
                    "all_time_highest_price": "39.99",
                    "current_lowest_price": "34.99",
                    "current_average_price": "37.15",
                    "historical_average_price": "36.80",
                    "price_change_percentage": "-4.92",
                    "trend_direction": "DECREASING",
                    "is_on_promotion": True,
                    "current_promotional_price": "34.99",
                    "is_genuine_deal": True,
                    "discount_veracity_score": "85.00",
                    "veracity_rating": "GENUINE_SAVINGS",
                    "sample_size_days": 60,
                }
            ]
        }
    )

    product_id: uuid.UUID = Field(description="Target product UUID")
    product_name: str = Field(description="Product item name")
    store_id: Optional[uuid.UUID] = Field(
        default=None, description="Store branch UUID if filtered"
    )
    all_time_lowest_price: Decimal = Field(
        description="All-time lowest recorded price in ZAR"
    )
    all_time_highest_price: Decimal = Field(
        description="All-time highest recorded price in ZAR"
    )
    current_lowest_price: Optional[Decimal] = Field(
        default=None, description="Lowest price among active monitored stores"
    )
    current_average_price: Optional[Decimal] = Field(
        default=None, description="Average active shelf price across stores"
    )
    historical_average_price: Optional[Decimal] = Field(
        default=None, description="Longitudinal average price across time window"
    )
    price_change_percentage: Decimal = Field(
        description="Percentage price change relative to previous benchmark"
    )
    trend_direction: str = Field(
        description="Price trend direction: INCREASING, DECREASING, or STABLE"
    )
    is_on_promotion: bool = Field(
        description="Whether product currently has active promotional prices"
    )
    current_promotional_price: Optional[Decimal] = Field(
        default=None, description="Lowest active promotional price if on promotion"
    )
    is_genuine_deal: bool = Field(
        description="Whether promotion offers genuine savings vs historical average"
    )
    discount_veracity_score: Decimal = Field(
        description=(
            "Rating from 0.00 to 100.00 assessing promotional discount authenticity"
        )
    )
    veracity_rating: str = Field(
        description=(
            "GENUINE_SAVINGS, ARTIFICIAL_DISCOUNT, REGULAR_PRICE, or NO_PROMOTION"
        )
    )
    sample_size_days: int = Field(
        description="Number of days sampled in historical evaluation window"
    )


class ErrorResponse(BaseModel):
    """Standard error response payload."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"detail": f"Product with id '{_EX_MILK_ID}' not found"},
                {"detail": "start_date must be before or equal to end_date"},
                {"detail": "Internal server error occurred"},
            ]
        }
    )

    detail: str = Field(description="Human-readable description of the error")
    errors: Optional[List[dict[str, Any]]] = Field(
        default=None,
        description="Detailed validation issue breakdown when applicable",
    )


# Standard reusable OpenAPI response declarations
COMMON_ERROR_RESPONSES = {
    status.HTTP_500_INTERNAL_SERVER_ERROR: {
        "model": ErrorResponse,
        "description": "Internal server error occurred.",
    },
}

STANDARD_400_RESPONSE = {
    status.HTTP_400_BAD_REQUEST: {
        "model": ErrorResponse,
        "description": "Bad Request - invalid query parameters or logical error.",
    }
}

STANDARD_404_RESPONSE = {
    status.HTTP_404_NOT_FOUND: {
        "model": ErrorResponse,
        "description": "Not Found - requested resource does not exist.",
    }
}

STANDARD_422_RESPONSE = {
    status.HTTP_422_UNPROCESSABLE_CONTENT: {
        "model": ErrorResponse,
        "description": (
            "Unprocessable Content - validation error in parameters or payload."
        ),
    }
}

STANDARD_401_RESPONSE = {
    status.HTTP_401_UNAUTHORIZED: {
        "model": ErrorResponse,
        "description": "Unauthorized - invalid or expired credentials/token.",
    }
}

STANDARD_403_RESPONSE = {
    status.HTTP_403_FORBIDDEN: {
        "model": ErrorResponse,
        "description": "Forbidden - access denied for this household resource.",
    }
}


# ==============================================================================
# Authentication & Household Schemas (KitchenSync Phase 2)
# ==============================================================================


class UserRegisterRequest(BaseModel):
    """User account registration payload."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "username": "sarah_shopper",
                    "email": "sarah@example.com",
                    "password": "SecurePassword123!",
                }
            ]
        }
    )

    username: str = Field(
        ..., min_length=3, max_length=100, description="Unique username."
    )
    email: str = Field(..., max_length=255, description="Unique user email address.")
    password: str = Field(..., min_length=6, description="Plaintext password.")


class UserLoginRequest(BaseModel):
    """User authentication login payload."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "username": "sarah_shopper",
                    "password": "SecurePassword123!",
                }
            ]
        }
    )

    username: str = Field(..., description="Username or email address.")
    password: str = Field(..., description="User password.")


class TokenResponse(BaseModel):
    """JWT bearer token response."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "token_type": "bearer",
                    "expires_in": 3600,
                }
            ]
        }
    )

    access_token: str = Field(description="Signed JWT access token.")
    token_type: str = Field(default="bearer", description="Token type (bearer).")
    expires_in: int = Field(description="Token validity lifetime in seconds.")


class UserResponse(BaseModel):
    """Public user identity response."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": "11111111-2222-3333-4444-555555555555",
                    "username": "sarah_shopper",
                    "email": "sarah@example.com",
                    "created_at": "2026-11-19T14:30:00Z",
                }
            ]
        },
    )

    id: uuid.UUID = Field(description="Unique user identifier.")
    username: str = Field(description="User handle.")
    email: str = Field(description="Email address.")
    created_at: datetime = Field(description="Registration timestamp.")


class MembershipSummary(BaseModel):
    """Household membership summary for user profile."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": "22222222-3333-4444-5555-666666666666",
                    "home_id": "33333333-4444-5555-6666-777777777777",
                    "home_name": "Sarah's Apartment",
                    "role": "buyer",
                    "joined_at": "2026-11-19T14:30:00Z",
                }
            ]
        },
    )

    id: uuid.UUID = Field(description="Membership record ID.")
    home_id: uuid.UUID = Field(description="Household ID.")
    home_name: str = Field(description="Household display name.")
    role: str = Field(description="Household role: 'buyer' or 'consumer'.")
    joined_at: datetime = Field(description="Timestamp when user joined home.")


class UserProfileResponse(BaseModel):
    """Authenticated user profile with active household memberships."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": "11111111-2222-3333-4444-555555555555",
                    "username": "sarah_shopper",
                    "email": "sarah@example.com",
                    "created_at": "2026-11-19T14:30:00Z",
                    "memberships": [
                        {
                            "id": "22222222-3333-4444-5555-666666666666",
                            "home_id": "33333333-4444-5555-6666-777777777777",
                            "home_name": "Sarah's Apartment",
                            "role": "buyer",
                            "joined_at": "2026-11-19T14:30:00Z",
                        }
                    ],
                }
            ]
        },
    )

    id: uuid.UUID = Field(description="User ID.")
    username: str = Field(description="User handle.")
    email: str = Field(description="Email address.")
    created_at: datetime = Field(description="Account creation timestamp.")
    memberships: List[MembershipSummary] = Field(
        default_factory=list, description="Active household memberships."
    )


class HomeCreateRequest(BaseModel):
    """Household creation payload."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "name": "Family Beach House",
                }
            ]
        }
    )

    name: str = Field(
        ..., min_length=1, max_length=150, description="Display name for household."
    )


class HomeMemberResponse(BaseModel):
    """Household member details."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": "22222222-3333-4444-5555-666666666666",
                    "user_id": "11111111-2222-3333-4444-555555555555",
                    "username": "sarah_shopper",
                    "email": "sarah@example.com",
                    "role": "buyer",
                    "joined_at": "2026-11-19T14:30:00Z",
                }
            ]
        },
    )

    id: uuid.UUID = Field(description="Membership record ID.")
    user_id: uuid.UUID = Field(description="User ID.")
    username: str = Field(description="User handle.")
    email: str = Field(description="User email.")
    role: str = Field(description="Role: 'buyer' or 'consumer'.")
    joined_at: datetime = Field(description="Join timestamp.")


class HomeResponse(BaseModel):
    """Household summary response."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": "33333333-4444-5555-6666-777777777777",
                    "name": "Family Beach House",
                    "created_at": "2026-11-19T14:30:00Z",
                    "role": "buyer",
                    "member_count": 2,
                }
            ]
        },
    )

    id: uuid.UUID = Field(description="Household ID.")
    name: str = Field(description="Household name.")
    created_at: datetime = Field(description="Creation timestamp.")
    role: Optional[str] = Field(
        default=None, description="Caller's role in this household."
    )
    member_count: Optional[int] = Field(
        default=None, description="Total members in household."
    )


class HomeDetailResponse(BaseModel):
    """Detailed household representation including full member list."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": "33333333-4444-5555-6666-777777777777",
                    "name": "Family Beach House",
                    "created_at": "2026-11-19T14:30:00Z",
                    "role": "buyer",
                    "members": [
                        {
                            "id": "22222222-3333-4444-5555-666666666666",
                            "user_id": "11111111-2222-3333-4444-555555555555",
                            "username": "sarah_shopper",
                            "email": "sarah@example.com",
                            "role": "buyer",
                            "joined_at": "2026-11-19T14:30:00Z",
                        }
                    ],
                }
            ]
        },
    )

    id: uuid.UUID = Field(description="Household ID.")
    name: str = Field(description="Household name.")
    created_at: datetime = Field(description="Creation timestamp.")
    role: str = Field(description="Caller's role in household.")
    members: List[HomeMemberResponse] = Field(
        default_factory=list, description="List of household members."
    )


class AddMemberRequest(BaseModel):
    """Request payload to invite/add a member to a household."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "email": "partner@example.com",
                    "role": "consumer",
                }
            ]
        }
    )

    username: Optional[str] = Field(
        default=None, description="Username of existing user."
    )
    email: Optional[str] = Field(
        default=None, description="Email address of existing user."
    )
    user_id: Optional[uuid.UUID] = Field(
        default=None, description="Direct UUID of user to add."
    )
    role: str = Field(
        default="consumer",
        description="Role to assign: 'buyer' or 'consumer'.",
    )


# ==============================================================================
# Pantry & Offline Sync Schemas (KitchenSync Phase 2)
# ==============================================================================


class PantryItemResponse(BaseModel):
    """Pantry inventory item response."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": "44444444-5555-6666-7777-888888888888",
                    "home_id": "33333333-4444-5555-6666-777777777777",
                    "product_id": "6e2941e3-033d-5768-8143-5e7ebc24b874",
                    "category_id": "dcda34e0-efd6-5f43-b188-db739a0deab7",
                    "custom_name": None,
                    "barcode": "600100000001",
                    "quantity": "2.00",
                    "unit_type": "L",
                    "low_stock_threshold": "1.00",
                    "status": "ok",
                    "is_deleted": False,
                    "updated_at": "2026-11-19T14:30:00Z",
                    "product_name": "Full Cream Fresh Milk 2L",
                    "category_name": "Dairy & Eggs",
                }
            ]
        },
    )

    id: uuid.UUID = Field(description="Unique pantry item ID.")
    home_id: uuid.UUID = Field(description="Household ID.")
    product_id: Optional[uuid.UUID] = Field(
        default=None, description="Catalog product ID if mapped."
    )
    category_id: Optional[uuid.UUID] = Field(
        default=None, description="Category classification ID."
    )
    custom_name: Optional[str] = Field(
        default=None, description="Custom name for uncatalogued items."
    )
    barcode: Optional[str] = Field(default=None, description="Item barcode.")
    quantity: Decimal = Field(description="Current stock quantity.")
    unit_type: str = Field(description="Unit type (e.g. L, kg, unit).")
    low_stock_threshold: Decimal = Field(
        description="Threshold quantity triggering low stock alert."
    )
    status: str = Field(description="Stock status: 'ok', 'low', 'finished'.")
    is_deleted: bool = Field(description="Soft-delete tombstone indicator.")
    updated_at: datetime = Field(description="Last modification timestamp.")
    product_name: Optional[str] = Field(
        default=None, description="Linked catalog product title."
    )
    category_name: Optional[str] = Field(
        default=None, description="Category display title."
    )


class PantryItemCreateRequest(BaseModel):
    """Pantry item creation payload."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "product_id": "6e2941e3-033d-5768-8143-5e7ebc24b874",
                    "category_id": "dcda34e0-efd6-5f43-b188-db739a0deab7",
                    "custom_name": None,
                    "barcode": "600100000001",
                    "quantity": 2.0,
                    "unit_type": "L",
                    "low_stock_threshold": 1.0,
                    "status": "ok",
                    "note": "Initial pantry stock",
                }
            ]
        }
    )

    product_id: Optional[uuid.UUID] = Field(
        default=None, description="Catalog product UUID if linked."
    )
    category_id: Optional[uuid.UUID] = Field(default=None, description="Category UUID.")
    custom_name: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Name of custom or artisanal item.",
    )
    barcode: Optional[str] = Field(
        default=None, max_length=64, description="Scanned barcode."
    )
    quantity: Decimal = Field(
        default=Decimal("1.00"), ge=0, description="Initial stock quantity."
    )
    unit_type: str = Field(
        default="unit", max_length=20, description="Measurement unit."
    )
    low_stock_threshold: Decimal = Field(
        default=Decimal("1.00"),
        ge=0,
        description="Threshold quantity below which item is marked low.",
    )
    status: str = Field(
        default="ok",
        description="Stock status: 'ok', 'low', 'finished'.",
    )
    note: Optional[str] = Field(
        default=None, description="Optional log note for history."
    )


class PantryItemUpdateRequest(BaseModel):
    """Pantry item modification payload."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "quantity": 0.5,
                    "status": "low",
                    "note": "Opened second container",
                }
            ]
        }
    )

    quantity: Optional[Decimal] = Field(
        default=None, ge=0, description="New stock quantity."
    )
    unit_type: Optional[str] = Field(
        default=None, max_length=20, description="Measurement unit."
    )
    low_stock_threshold: Optional[Decimal] = Field(
        default=None, ge=0, description="New threshold quantity."
    )
    status: Optional[str] = Field(
        default=None, description="New status: 'ok', 'low', 'finished'."
    )
    custom_name: Optional[str] = Field(
        default=None, max_length=200, description="Updated custom name."
    )
    barcode: Optional[str] = Field(
        default=None, max_length=64, description="Updated barcode."
    )
    category_id: Optional[uuid.UUID] = Field(
        default=None, description="Updated category ID."
    )
    product_id: Optional[uuid.UUID] = Field(
        default=None, description="Updated linked product ID."
    )
    note: Optional[str] = Field(
        default=None, description="Audit note describing modification."
    )


class PantrySyncMutation(BaseModel):
    """Client-side pantry modification payload for offline sync reconciliation."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id": "44444444-5555-6666-7777-888888888888",
                    "product_id": "6e2941e3-033d-5768-8143-5e7ebc24b874",
                    "custom_name": None,
                    "quantity": 0.0,
                    "unit_type": "L",
                    "low_stock_threshold": 1.0,
                    "status": "finished",
                    "is_deleted": False,
                    "updated_at": "2026-11-19T14:35:00Z",
                    "note": "Finished last bottle while offline",
                }
            ]
        }
    )

    id: uuid.UUID = Field(description="Client-side UUID of the pantry item.")
    product_id: Optional[uuid.UUID] = Field(
        default=None, description="Catalog product UUID if linked."
    )
    category_id: Optional[uuid.UUID] = Field(
        default=None, description="Category classification UUID."
    )
    custom_name: Optional[str] = Field(
        default=None, max_length=200, description="Custom item title."
    )
    barcode: Optional[str] = Field(
        default=None, max_length=64, description="EAN-13 barcode."
    )
    quantity: Decimal = Field(
        default=Decimal("0.00"), ge=0, description="Stock quantity."
    )
    unit_type: str = Field(
        default="unit", max_length=20, description="Measurement unit."
    )
    low_stock_threshold: Decimal = Field(
        default=Decimal("1.00"), ge=0, description="Threshold quantity."
    )
    status: str = Field(
        default="ok", description="Item status: 'ok', 'low', 'finished'."
    )
    is_deleted: bool = Field(
        default=False, description="True if item was deleted on client."
    )
    updated_at: datetime = Field(
        description="Client-side timestamp of the mutation event."
    )
    note: Optional[str] = Field(
        default=None, description="Optional note for audit trail."
    )


class PantrySyncRequest(BaseModel):
    """Offline delta synchronization request payload."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "last_synced_at": "2026-11-19T14:00:00Z",
                    "mutations": [
                        {
                            "id": "44444444-5555-6666-7777-888888888888",
                            "product_id": "6e2941e3-033d-5768-8143-5e7ebc24b874",
                            "status": "low",
                            "quantity": 0.5,
                            "updated_at": "2026-11-19T14:35:00Z",
                            "note": "Marked low from pantry scanner",
                        }
                    ],
                }
            ]
        }
    )

    last_synced_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp of client's last successful sync.",
    )
    mutations: List[PantrySyncMutation] = Field(
        default_factory=list,
        description="List of offline mutations to reconcile.",
    )


class PantrySyncResponse(BaseModel):
    """Offline delta synchronization reconciliation response."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "synced_at": "2026-11-19T14:36:00Z",
                    "items": [],
                    "applied_mutations_count": 1,
                }
            ]
        }
    )

    synced_at: datetime = Field(description="Server timestamp of this synchronization.")
    items: List[PantryItemResponse] = Field(
        description="Server-side items updated since last_synced_at."
    )
    applied_mutations_count: int = Field(
        description="Number of client mutations successfully applied."
    )


class HouseholdBasketItemResponse(BaseModel):
    """Item inside the active household auto-replenished basket."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": "55555555-6666-7777-8888-999999999999",
                    "product_id": "6e2941e3-033d-5768-8143-5e7ebc24b874",
                    "product_name": "Full Cream Fresh Milk 2L",
                    "quantity": "1.00",
                }
            ]
        },
    )

    id: uuid.UUID = Field(description="Basket item record ID.")
    product_id: uuid.UUID = Field(description="Catalog product ID.")
    product_name: Optional[str] = Field(
        default=None, description="Catalog product title."
    )
    quantity: Decimal = Field(description="Quantity to purchase.")


class HouseholdBasketResponse(BaseModel):
    """Household active shopping basket representation."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": "66666666-7777-8888-9999-000000000000",
                    "home_id": "33333333-4444-5555-6666-777777777777",
                    "name": "Household Smart Basket",
                    "created_at": "2026-11-19T14:30:00Z",
                    "items": [],
                }
            ]
        },
    )

    id: uuid.UUID = Field(description="Basket ID.")
    home_id: uuid.UUID = Field(description="Household ID.")
    name: str = Field(description="Basket name.")
    created_at: datetime = Field(description="Creation timestamp.")
    items: List[HouseholdBasketItemResponse] = Field(
        default_factory=list, description="Replenishment shopping list."
    )
