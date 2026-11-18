"""Smart Basket calculation and multi-store optimization engine."""

from __future__ import annotations

import itertools
import uuid
from collections import defaultdict
from decimal import Decimal
from typing import Any, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from src.api.v1.schemas import (
    BasketCalculationResponse,
    BasketItemDetail,
    BasketItemRequest,
    MissingItemDetail,
    OptimalSplitResult,
    SplitStoreAllocation,
    StoreBasketTotal,
)
from src.models.entities import Product, Store, StorePrice


class ProductNotFoundError(Exception):
    """Raised when a requested product ID is not found in the catalog."""

    def __init__(self, product_id: uuid.UUID):
        self.product_id = product_id
        super().__init__(f"Product with id '{product_id}' not found")


def calculate_basket(
    session: Session,
    items: Sequence[BasketItemRequest],
) -> BasketCalculationResponse:
    """Calculate multi-store basket totals and optimal split-basket savings.

    Args:
        session: Active SQLAlchemy database session.
        items: List of product UUIDs and requested quantities.

    Returns:
        BasketCalculationResponse containing ranked single-store totals,
        the cheapest single store, and optimal multi-store split allocation.

    Raises:
        ProductNotFoundError: If any requested product does not exist.
    """
    # 1. Aggregate quantities for duplicate product IDs in the basket
    aggregated_quantities: dict[uuid.UUID, Decimal] = defaultdict(
        lambda: Decimal("0.00")
    )
    for item in items:
        aggregated_quantities[item.product_id] += item.quantity

    requested_product_ids = list(aggregated_quantities.keys())

    # 2. Fetch and validate products
    products = session.scalars(
        select(Product).where(Product.id.in_(requested_product_ids))
    ).all()
    product_map = {p.id: p.name for p in products}

    # Verify all requested products exist
    for pid in requested_product_ids:
        if pid not in product_map:
            raise ProductNotFoundError(pid)

    # 3. Fetch active stores
    stores = (
        session.scalars(
            select(Store)
            .options(joinedload(Store.retailer))
            .where(Store.is_active.is_(True))
            .order_by(Store.name.asc())
        )
        .unique()
        .all()
    )

    # 4. Fetch all active in-stock prices for the requested products
    prices = session.scalars(
        select(StorePrice).where(
            StorePrice.product_id.in_(requested_product_ids),
            StorePrice.is_in_stock.is_(True),
        )
    ).all()

    # Map (store_id, product_id) -> StorePrice
    price_map: dict[tuple[uuid.UUID, uuid.UUID], StorePrice] = {
        (sp.store_id, sp.product_id): sp for sp in prices
    }

    # 5. Calculate Single-Store Basket Totals
    store_totals: list[StoreBasketTotal] = []
    for store in stores:
        store_items: list[BasketItemDetail] = []
        missing_items: list[MissingItemDetail] = []
        total_price = Decimal("0.00")

        for pid in requested_product_ids:
            qty = aggregated_quantities[pid]
            pname = product_map[pid]
            sp = price_map.get((store.id, pid))

            if sp is not None:
                subtotal = (sp.price * qty).quantize(Decimal("0.01"))
                total_price += subtotal
                store_items.append(
                    BasketItemDetail(
                        product_id=pid,
                        product_name=pname,
                        quantity=qty,
                        unit_price=sp.price,
                        subtotal=subtotal,
                        is_promotional=sp.is_promotional,
                    )
                )
            else:
                missing_items.append(
                    MissingItemDetail(
                        product_id=pid,
                        product_name=pname,
                        quantity=qty,
                    )
                )

        is_complete = len(missing_items) == 0
        store_totals.append(
            StoreBasketTotal(
                store_id=store.id,
                store_name=store.name,
                branch_code=store.branch_code,
                retailer_name=store.retailer.name,
                total_price=total_price.quantize(Decimal("0.01")),
                is_complete_match=is_complete,
                items_available_count=len(store_items),
                total_items_count=len(requested_product_ids),
                items=store_items,
                missing_items=missing_items,
            )
        )

    # Sort stores deterministically:
    # 1. Complete matches first
    # 2. Lowest total price
    # 3. Store name ascending
    ranked_stores = sorted(
        store_totals,
        key=lambda s: (not s.is_complete_match, s.total_price, s.store_name),
    )

    cheapest_single_store = next(
        (s for s in ranked_stores if s.is_complete_match), None
    )

    # 6. Multi-Store Split Optimization (Smart Mode)
    optimal_split = _optimize_two_store_split(
        stores=stores,
        requested_product_ids=requested_product_ids,
        aggregated_quantities=aggregated_quantities,
        product_map=product_map,
        price_map=price_map,
        cheapest_single_store=cheapest_single_store,
    )

    return BasketCalculationResponse(
        ranked_stores=ranked_stores,
        cheapest_single_store=cheapest_single_store,
        optimal_split=optimal_split,
        total_items_requested=len(requested_product_ids),
    )


def _optimize_two_store_split(
    stores: Sequence[Store],
    requested_product_ids: list[uuid.UUID],
    aggregated_quantities: dict[uuid.UUID, Decimal],
    product_map: dict[uuid.UUID, str],
    price_map: dict[tuple[uuid.UUID, uuid.UUID], StorePrice],
    cheapest_single_store: StoreBasketTotal | None,
) -> OptimalSplitResult | None:
    """Evaluate 2-store combinations to find maximal shopper savings."""
    if len(stores) < 2 or not requested_product_ids:
        return None

    best_pair_result: dict[str, Any] | None = None
    total_req_count = len(requested_product_ids)

    # Iterate through all store pairs
    for store_a, store_b in itertools.combinations(stores, 2):
        alloc_a: list[BasketItemDetail] = []
        alloc_b: list[BasketItemDetail] = []
        pair_total = Decimal("0.00")
        covered_count = 0

        for pid in requested_product_ids:
            qty = aggregated_quantities[pid]
            pname = product_map[pid]
            sp_a = price_map.get((store_a.id, pid))
            sp_b = price_map.get((store_b.id, pid))

            if sp_a is None and sp_b is None:
                continue

            covered_count += 1
            if sp_a is not None and sp_b is not None:
                # Both have the item: allocate to the cheaper store
                if sp_a.price <= sp_b.price:
                    subtotal = (sp_a.price * qty).quantize(Decimal("0.01"))
                    alloc_a.append(
                        BasketItemDetail(
                            product_id=pid,
                            product_name=pname,
                            quantity=qty,
                            unit_price=sp_a.price,
                            subtotal=subtotal,
                            is_promotional=sp_a.is_promotional,
                        )
                    )
                    pair_total += subtotal
                else:
                    subtotal = (sp_b.price * qty).quantize(Decimal("0.01"))
                    alloc_b.append(
                        BasketItemDetail(
                            product_id=pid,
                            product_name=pname,
                            quantity=qty,
                            unit_price=sp_b.price,
                            subtotal=subtotal,
                            is_promotional=sp_b.is_promotional,
                        )
                    )
                    pair_total += subtotal
            elif sp_a is not None:
                subtotal = (sp_a.price * qty).quantize(Decimal("0.01"))
                alloc_a.append(
                    BasketItemDetail(
                        product_id=pid,
                        product_name=pname,
                        quantity=qty,
                        unit_price=sp_a.price,
                        subtotal=subtotal,
                        is_promotional=sp_a.is_promotional,
                    )
                )
                pair_total += subtotal
            else:
                assert sp_b is not None
                subtotal = (sp_b.price * qty).quantize(Decimal("0.01"))
                alloc_b.append(
                    BasketItemDetail(
                        product_id=pid,
                        product_name=pname,
                        quantity=qty,
                        unit_price=sp_b.price,
                        subtotal=subtotal,
                        is_promotional=sp_b.is_promotional,
                    )
                )
                pair_total += subtotal

        is_complete = covered_count == total_req_count

        # Score candidate pair: prioritize completeness, then lowest price
        # tuple: (is_complete, covered_count, -pair_total)
        candidate = {
            "store_a": store_a,
            "store_b": store_b,
            "alloc_a": alloc_a,
            "alloc_b": alloc_b,
            "total_price": pair_total.quantize(Decimal("0.01")),
            "is_complete": is_complete,
            "covered_count": covered_count,
        }

        if best_pair_result is None:
            best_pair_result = candidate
        else:
            # Better if:
            # 1. More items covered
            # 2. Or same items covered but lower price
            better = False
            if candidate["covered_count"] > best_pair_result["covered_count"]:
                better = True
            elif candidate["covered_count"] == best_pair_result["covered_count"]:
                if candidate["total_price"] < best_pair_result["total_price"]:
                    better = True
            if better:
                best_pair_result = candidate

    if best_pair_result is None:
        return None

    # Calculate savings compared to cheapest single store
    pair_total = best_pair_result["total_price"]
    stores_output: list[SplitStoreAllocation] = []

    sub_a = sum(
        (item.subtotal for item in best_pair_result["alloc_a"]), Decimal("0.00")
    )
    if best_pair_result["alloc_a"]:
        stores_output.append(
            SplitStoreAllocation(
                store_id=best_pair_result["store_a"].id,
                store_name=best_pair_result["store_a"].name,
                retailer_name=best_pair_result["store_a"].retailer.name,
                items=best_pair_result["alloc_a"],
                subtotal=sub_a.quantize(Decimal("0.01")),
            )
        )

    sub_b = sum(
        (item.subtotal for item in best_pair_result["alloc_b"]), Decimal("0.00")
    )
    if best_pair_result["alloc_b"]:
        stores_output.append(
            SplitStoreAllocation(
                store_id=best_pair_result["store_b"].id,
                store_name=best_pair_result["store_b"].name,
                retailer_name=best_pair_result["store_b"].retailer.name,
                items=best_pair_result["alloc_b"],
                subtotal=sub_b.quantize(Decimal("0.01")),
            )
        )

    savings_amount = Decimal("0.00")
    savings_pct = Decimal("0.00")
    cheaper_than_single = False

    if cheapest_single_store and best_pair_result["is_complete"]:
        if pair_total < cheapest_single_store.total_price:
            savings_amount = (cheapest_single_store.total_price - pair_total).quantize(
                Decimal("0.01")
            )
            savings_pct = (
                (savings_amount / cheapest_single_store.total_price) * Decimal("100.00")
            ).quantize(Decimal("0.01"))
            cheaper_than_single = True
    elif best_pair_result["is_complete"] and not cheapest_single_store:
        # No single store covers the basket, but the pair does!
        cheaper_than_single = True

    return OptimalSplitResult(
        stores=stores_output,
        total_price=pair_total,
        savings_amount=savings_amount,
        savings_percentage=savings_pct,
        is_complete_match=best_pair_result["is_complete"],
        cheaper_than_single_store=cheaper_than_single,
    )
