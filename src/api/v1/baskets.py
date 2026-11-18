"""Basket evaluation and multi-store optimization API routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api.v1.schemas import (
    BasketCalculationRequest,
    BasketCalculationResponse,
    ErrorResponse,
)
from src.core.database import get_db
from src.services import basket_service
from src.services.basket_service import ProductNotFoundError

router = APIRouter(prefix="/baskets", tags=["baskets"])


@router.post(
    "/calculate",
    response_model=BasketCalculationResponse,
    responses={
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ErrorResponse},
    },
    summary="Calculate multi-store basket prices and smart split optimization",
    description=(
        "Evaluates a shopping list across all stores, returning single-store "
        "totals, missing item warnings, and optimal 2-store split savings."
    ),
)
def calculate_basket(
    payload: BasketCalculationRequest,
    db: Annotated[Session, Depends(get_db)],
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
