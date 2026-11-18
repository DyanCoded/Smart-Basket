"""Basket evaluation and multi-store optimization API routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api.v1.schemas import (
    BasketCalculationRequest,
    BasketCalculationResponse,
    ErrorResponse,
)
from src.core.database import get_db
from src.services import basket_service
from src.services.basket_service import ProductNotFoundError

router = APIRouter(
    prefix="/baskets",
    tags=["baskets"],
    responses={
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "model": ErrorResponse,
            "description": "Internal server error occurred.",
        },
    },
)

_EX_MILK_UUID = "6e2941e3-033d-5768-8143-5e7ebc24b874"
_EX_BREAD_UUID = "ab9928f5-221a-5546-8b6c-c4ec04fbe933"
_EX_EGGS_UUID = "4ca9f9c4-dea2-5f16-8ffb-4ec70ea08382"


@router.post(
    "/calculate",
    response_model=BasketCalculationResponse,
    responses={
        status.HTTP_200_OK: {
            "model": BasketCalculationResponse,
            "description": "Multi-store basket totals and optimal split calculated.",
        },
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorResponse,
            "description": "Invalid basket calculation request or constraints.",
        },
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponse,
            "description": "One or more requested product IDs not found in catalog.",
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "model": ErrorResponse,
            "description": "Validation error in basket request schema or quantities.",
        },
    },
    summary="Calculate multi-store basket prices and smart split optimization",
    description=(
        "Evaluates a grocery shopping basket across all monitored supermarket "
        "stores. Returns a deterministic price ranking of single-store totals "
        "(cheapest first), missing item alerts, and the optimal 2-store split "
        "(Smart Mode) that maximizes consumer savings."
    ),
    response_description=(
        "Ranked store totals and optimal multi-store split optimization."
    ),
)
def calculate_basket(
    db: Annotated[Session, Depends(get_db)],
    payload: BasketCalculationRequest = Body(
        ...,
        openapi_examples={
            "two_item_basket": {
                "summary": "Standard 2-item basket (Milk & Bread)",
                "description": (
                    "Regular shopping run comparing prices for Clover Milk 2L and "
                    "Albany White Bread."
                ),
                "value": {
                    "items": [
                        {
                            "product_id": _EX_MILK_UUID,
                            "quantity": 2.0,
                        },
                        {
                            "product_id": _EX_BREAD_UUID,
                            "quantity": 1.0,
                        },
                    ]
                },
            },
            "family_pantry_basket": {
                "summary": "Pantry staples basket (Milk, Bread & Eggs)",
                "description": (
                    "Larger shopping basket evaluating single-store totals and "
                    "split savings for Milk, Bread, and 18pk Eggs."
                ),
                "value": {
                    "items": [
                        {
                            "product_id": _EX_MILK_UUID,
                            "quantity": 2.0,
                        },
                        {
                            "product_id": _EX_BREAD_UUID,
                            "quantity": 1.0,
                        },
                        {
                            "product_id": _EX_EGGS_UUID,
                            "quantity": 1.0,
                        },
                    ]
                },
            },
        },
    ),
) -> BasketCalculationResponse:
    """Calculate basket total across stores and find optimal split basket."""
    try:
        return basket_service.calculate_basket(
            session=db,
            items=payload.items,
        )
    except ProductNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
