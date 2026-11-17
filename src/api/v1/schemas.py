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


class ErrorResponse(BaseModel):
    """Standard error response payload."""

    detail: str
