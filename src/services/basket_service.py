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
from src.models.entities import Product, Retailer, Store, StorePrice


class ProductNotFoundError(Exception):
    """Raised when a requested product ID is not found in the catalog."""

    def __init__(self, product_id: uuid.UUID):
        self.product_id = product_id
        super().__init__(f"Product with id '{product_id}' not found")


def calculate_basket(
    session: Session,
    items: Sequence[BasketItemRequest],
    store_ids: Sequence[uuid.UUID] | None = None,
    retailer_slugs: Sequence[str] | None = None,
) -> BasketCalculationResponse:
    """Calculate multi-chain basket totals and optimal split-basket savings.

    Args:
        session: Active SQLAlchemy database session.
        items: List of product UUIDs and requested quantities.
        store_ids: Optional subset of canonical chain store UUIDs to include.
        retailer_slugs: Optional subset of retailer slugs to include.

    Returns:
        BasketCalculationResponse containing ranked single-chain totals,
        the cheapest single chain, and optimal Smart Mode split allocation.

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

    # 3. Fetch canonical active retailer chains (filtered if store_ids/slugs provided)
    store_stmt = (
        select(Store)
        .join(Retailer, Store.retailer_id == Retailer.id)
        .options(joinedload(Store.retailer))
        .where(Store.is_active.is_(True))
    )
    if store_ids is not None:
        store_stmt = store_stmt.where(Store.id.in_(list(store_ids)))
    if retailer_slugs is not None:
        normalized_slugs = [
            slug.strip().lower() for slug in retailer_slugs if slug.strip()
        ]
        store_stmt = store_stmt.where(Retailer.slug.in_(normalized_slugs))

    raw_stores = (
        session.scalars(store_stmt.order_by(Retailer.name.asc(), Store.name.asc()))
        .unique()
        .all()
    )
    # Deduplicate to 1 canonical chain per retailer_id
    stores_by_retailer: dict[uuid.UUID, Store] = {}
    for s in raw_stores:
        if s.retailer_id not in stores_by_retailer:
            stores_by_retailer[s.retailer_id] = s
    stores = list(stores_by_retailer.values())

    # 4. Fetch active chain-level prices for the selected chains
    selected_store_ids = [s.id for s in stores]
    prices = (
        session.scalars(
            select(StorePrice).where(
                StorePrice.product_id.in_(requested_product_ids),
                StorePrice.store_id.in_(selected_store_ids),
            )
        ).all()
        if selected_store_ids
        else []
    )

    # Map (store_id, product_id) -> StorePrice
    price_map: dict[tuple[uuid.UUID, uuid.UUID], StorePrice] = {
        (sp.store_id, sp.product_id): sp for sp in prices
    }

    # 5. Calculate Single-Chain Basket Totals across the 5 national retailers
    store_totals: list[StoreBasketTotal] = []
    for store in stores:
        chain_name = store.retailer.name
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
                store_name=chain_name,
                branch_code=None,
                retailer_name=chain_name,
                total_price=total_price.quantize(Decimal("0.01")),
                is_complete_match=is_complete,
                items_available_count=len(store_items),
                total_items_count=len(requested_product_ids),
                items=store_items,
                missing_items=missing_items,
            )
        )

    # Sort national retailer chains deterministically:
    # 1. Full catalog matches first
    # 2. Lowest total price
    # 3. Retailer chain name ascending
    ranked_stores = sorted(
        store_totals,
        key=lambda s: (not s.is_complete_match, s.total_price, s.retailer_name),
    )

    cheapest_single_store = next(
        (s for s in ranked_stores if s.is_complete_match), None
    )

    # 6. Multi-Chain Split Optimization (Smart Mode across selected chains)
    optimal_split = _optimize_multi_chain_split(
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


def _optimize_multi_chain_split(
    stores: Sequence[Store],
    requested_product_ids: list[uuid.UUID],
    aggregated_quantities: dict[uuid.UUID, Decimal],
    product_map: dict[uuid.UUID, str],
    price_map: dict[tuple[uuid.UUID, uuid.UUID], StorePrice],
    cheapest_single_store: StoreBasketTotal | None,
) -> OptimalSplitResult | None:
    """Evaluate subsets of selected national chains to maximize shopper savings.

    Evaluates combinations of size 1..len(stores), allocating each basket item
    to the lowest-priced chain in the subset and breaking ties by fewest chains
    used.
    """
    if len(stores) < 2 or not requested_product_ids:
        return None

    best_result: dict[str, Any] | None = None
    total_req_count = len(requested_product_ids)

    for subset_size in range(1, len(stores) + 1):
        for store_subset in itertools.combinations(stores, subset_size):
            allocations: dict[uuid.UUID, list[BasketItemDetail]] = {
                s.id: [] for s in store_subset
            }
            subset_total = Decimal("0.00")
            covered_count = 0

            for pid in requested_product_ids:
                qty = aggregated_quantities[pid]
                pname = product_map[pid]

                # Pick the lowest-priced chain in this subset for pid
                best_store: Store | None = None
                best_sp: StorePrice | None = None
                for candidate_store in store_subset:
                    sp = price_map.get((candidate_store.id, pid))
                    if sp is None:
                        continue
                    if best_sp is None or sp.price < best_sp.price:
                        best_store = candidate_store
                        best_sp = sp

                if best_store is not None and best_sp is not None:
                    covered_count += 1
                    subtotal = (best_sp.price * qty).quantize(Decimal("0.01"))
                    allocations[best_store.id].append(
                        BasketItemDetail(
                            product_id=pid,
                            product_name=pname,
                            quantity=qty,
                            unit_price=best_sp.price,
                            subtotal=subtotal,
                            is_promotional=best_sp.is_promotional,
                        )
                    )
                    subset_total += subtotal

            active_stores = [s for s in store_subset if allocations[s.id]]
            candidate = {
                "stores": active_stores,
                "allocations": allocations,
                "total_price": subset_total.quantize(Decimal("0.01")),
                "is_complete": covered_count == total_req_count,
                "covered_count": covered_count,
                "stores_used": len(active_stores),
            }

            if best_result is None:
                best_result = candidate
            else:
                # Prioritize: 1) more items covered, 2) lower total, 3) fewer chains
                cand_rank = (
                    candidate["covered_count"],
                    -candidate["total_price"],
                    -candidate["stores_used"],
                )
                best_rank = (
                    best_result["covered_count"],
                    -best_result["total_price"],
                    -best_result["stores_used"],
                )
                if cand_rank > best_rank:
                    best_result = candidate

    if best_result is None:
        return None

    split_total = best_result["total_price"]
    stores_output: list[SplitStoreAllocation] = []
    for chain_store in best_result["stores"]:
        chain_items = best_result["allocations"][chain_store.id]
        chain_subtotal = sum((item.subtotal for item in chain_items), Decimal("0.00"))
        stores_output.append(
            SplitStoreAllocation(
                store_id=chain_store.id,
                store_name=chain_store.retailer.name,
                retailer_name=chain_store.retailer.name,
                items=chain_items,
                subtotal=chain_subtotal.quantize(Decimal("0.01")),
            )
        )

    savings_amount = Decimal("0.00")
    savings_pct = Decimal("0.00")
    cheaper_than_single = False

    if cheapest_single_store and best_result["is_complete"]:
        if split_total < cheapest_single_store.total_price:
            savings_amount = (cheapest_single_store.total_price - split_total).quantize(
                Decimal("0.01")
            )
            savings_pct = (
                (savings_amount / cheapest_single_store.total_price) * Decimal("100.00")
            ).quantize(Decimal("0.01"))
            cheaper_than_single = True
    elif best_result["is_complete"] and not cheapest_single_store:
        cheaper_than_single = True

    return OptimalSplitResult(
        stores=stores_output,
        total_price=split_total,
        savings_amount=savings_amount,
        savings_percentage=savings_pct,
        is_complete_match=best_result["is_complete"],
        cheaper_than_single_store=cheaper_than_single,
    )
