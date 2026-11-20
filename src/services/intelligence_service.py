"""Price history tracking and trend intelligence business logic service."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.models.entities import PriceHistory, Retailer, Store, StorePrice


class StoreNotFoundError(Exception):
    """Raised when a specified store ID does not exist."""

    def __init__(self, store_id: uuid.UUID):
        self.store_id = store_id
        super().__init__(f"Store with id '{store_id}' not found")


def get_price_history(
    session: Session,
    product_id: uuid.UUID,
    store_id: uuid.UUID | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[Sequence[dict[str, Any]], int]:
    """Retrieve chronological price timeseries data for a product.

    Utilizes index on (product_id, store_id, recorded_at).
    """
    stmt = (
        select(PriceHistory, Store, Retailer)
        .join(Store, PriceHistory.store_id == Store.id)
        .join(Retailer, Store.retailer_id == Retailer.id)
        .where(PriceHistory.product_id == product_id)
    )

    if store_id:
        stmt = stmt.where(PriceHistory.store_id == store_id)

    if start_date:
        stmt = stmt.where(PriceHistory.recorded_at >= start_date)

    if end_date:
        stmt = stmt.where(PriceHistory.recorded_at <= end_date)

    # Count total matching records
    count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    total = session.scalar(count_stmt) or 0

    # Order chronologically for charts
    paginated_stmt = (
        stmt.order_by(PriceHistory.recorded_at.asc()).offset(offset).limit(limit)
    )
    rows = session.execute(paginated_stmt).all()

    points: list[dict[str, Any]] = []
    for ph, store, retailer in rows:
        points.append(
            {
                "id": ph.id,
                "store_id": store.id,
                "store_name": retailer.name,
                "retailer_name": retailer.name,
                "price": ph.price,
                "is_promotional": ph.is_promotional,
                "recorded_at": ph.recorded_at,
            }
        )

    return points, total


def get_price_intelligence(
    session: Session,
    product_id: uuid.UUID,
    store_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    """Compute high/low/average prices, trend directions, and deal veracity score."""
    # 1. Fetch historical observations
    hist_stmt = (
        select(PriceHistory)
        .where(PriceHistory.product_id == product_id)
        .order_by(PriceHistory.recorded_at.asc())
    )
    if store_id:
        hist_stmt = hist_stmt.where(PriceHistory.store_id == store_id)

    hist_records = session.scalars(hist_stmt).all()

    # 2. Fetch current active national chain prices
    active_stmt = select(StorePrice).where(
        StorePrice.product_id == product_id,
    )
    if store_id:
        active_stmt = active_stmt.where(StorePrice.store_id == store_id)

    active_prices = session.scalars(active_stmt).all()

    # 3. Combine all price points to determine high/low
    all_prices = [h.price for h in hist_records] + [sp.price for sp in active_prices]

    if not all_prices:
        zero_dec = Decimal("0.00")
        return {
            "all_time_lowest_price": zero_dec,
            "all_time_highest_price": zero_dec,
            "current_lowest_price": None,
            "current_average_price": None,
            "historical_average_price": None,
            "price_change_percentage": zero_dec,
            "trend_direction": "STABLE",
            "is_on_promotion": False,
            "current_promotional_price": None,
            "is_genuine_deal": False,
            "discount_veracity_score": zero_dec,
            "veracity_rating": "NO_PROMOTION",
            "sample_size_days": 0,
        }

    all_time_lowest = min(all_prices)
    all_time_highest = max(all_prices)

    # Current price metrics
    curr_lowest = min(sp.price for sp in active_prices) if active_prices else None
    curr_avg = (
        (
            sum((sp.price for sp in active_prices), Decimal("0.00"))
            / len(active_prices)
        ).quantize(Decimal("0.01"))
        if active_prices
        else None
    )

    # Historical average
    hist_avg = (
        (
            sum((h.price for h in hist_records), Decimal("0.00")) / len(hist_records)
        ).quantize(Decimal("0.01"))
        if hist_records
        else curr_avg
    )

    # 4. Trend direction and price change percentage
    price_change_pct = Decimal("0.00")
    trend_direction = "STABLE"

    if hist_records:
        oldest_price = hist_records[0].price
        latest_price = curr_avg or hist_records[-1].price
        if oldest_price > Decimal("0.00"):
            price_change_pct = (
                (latest_price - oldest_price) / oldest_price * Decimal("100.00")
            ).quantize(Decimal("0.01"))

        if price_change_pct > Decimal("1.00"):
            trend_direction = "INCREASING"
        elif price_change_pct < Decimal("-1.00"):
            trend_direction = "DECREASING"
        else:
            trend_direction = "STABLE"

    # 5. Deal veracity & discount authenticity
    promo_prices = [sp for sp in active_prices if sp.is_promotional]
    is_on_promo = len(promo_prices) > 0
    current_promo_price = min(sp.price for sp in promo_prices) if promo_prices else None

    is_genuine_deal = False
    veracity_score = Decimal("0.00")
    veracity_rating = "NO_PROMOTION"

    if is_on_promo and current_promo_price is not None and hist_avg is not None:
        if current_promo_price < hist_avg:
            discount_diff = hist_avg - current_promo_price
            discount_pct = (discount_diff / hist_avg * Decimal("100.00")).quantize(
                Decimal("0.01")
            )
            is_genuine_deal = True
            # Score between 50 and 100 based on discount depth
            calculated_score = min(
                Decimal("100.00"), Decimal("50.00") + (discount_pct * 2)
            )
            veracity_score = calculated_score.quantize(Decimal("0.01"))
            veracity_rating = "GENUINE_SAVINGS"
        else:
            # Promotional price is >= historical average (artificial mark-up/sale)
            is_genuine_deal = False
            veracity_score = Decimal("15.00")
            veracity_rating = "ARTIFICIAL_DISCOUNT"
    elif is_on_promo and current_promo_price is not None:
        # Promotion active without older historical records
        is_genuine_deal = True
        veracity_score = Decimal("75.00")
        veracity_rating = "GENUINE_SAVINGS"

    # Calculate days span in sample
    sample_days = 0
    if hist_records:
        now = datetime.now(timezone.utc)
        oldest_time = hist_records[0].recorded_at
        if oldest_time.tzinfo is None:
            oldest_time = oldest_time.replace(tzinfo=timezone.utc)
        sample_days = max(1, (now - oldest_time).days)

    return {
        "all_time_lowest_price": all_time_lowest,
        "all_time_highest_price": all_time_highest,
        "current_lowest_price": curr_lowest,
        "current_average_price": curr_avg,
        "historical_average_price": hist_avg,
        "price_change_percentage": price_change_pct,
        "trend_direction": trend_direction,
        "is_on_promotion": is_on_promo,
        "current_promotional_price": current_promo_price,
        "is_genuine_deal": is_genuine_deal,
        "discount_veracity_score": veracity_score,
        "veracity_rating": veracity_rating,
        "sample_size_days": sample_days,
    }
