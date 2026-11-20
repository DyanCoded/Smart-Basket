"""Idempotent canonical-chain catalog publisher for normalized scraper records.

Publishes NormalizedPriceRecord items into the 5 canonical national supermarket
chain stores (1 Store record per Retailer; no physical branch locations or stock
inventory tracking per ADR-011) and appends timestamped PriceHistory snapshots
whenever prices change or on scheduled full-snapshot runs.
"""

from __future__ import annotations

import logging
from decimal import ROUND_HALF_UP, Decimal
from typing import Iterable, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.entities import (
    Category,
    PriceHistory,
    Product,
    Retailer,
    Store,
    StorePrice,
)
from src.scrapers.models import (
    TWO_DECIMAL_PLACES,
    NormalizedPriceRecord,
    PublishSummary,
)
from src.scrapers.normalizer import match_product, normalize_text_key

logger = logging.getLogger(__name__)


def resolve_canonical_store(session: Session, retailer_slug: str) -> Optional[Store]:
    """Return the single canonical national chain Store for a retailer slug."""
    slug = retailer_slug.strip().lower()
    stmt = (
        select(Store)
        .join(Retailer, Store.retailer_id == Retailer.id)
        .where(Retailer.slug == slug, Store.is_active.is_(True))
        .order_by(Store.branch_code.is_(None).desc(), Store.created_at.asc())
    )
    return session.execute(stmt).scalars().first()


class CatalogPublisher:
    """Upserts normalized prices into canonical chain store_prices & price_history."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self._store_cache: dict[str, Optional[Store]] = {}
        self._category_cache: dict[str, Optional[Category]] = {}

    def _get_canonical_store(self, retailer_slug: str) -> Optional[Store]:
        slug = retailer_slug.strip().lower()
        if slug not in self._store_cache:
            self._store_cache[slug] = resolve_canonical_store(self.session, slug)
        return self._store_cache[slug]

    def _get_category(self, category_slug: Optional[str]) -> Optional[Category]:
        if not category_slug:
            return None
        slug = category_slug.strip().lower()
        if slug not in self._category_cache:
            self._category_cache[slug] = self.session.execute(
                select(Category).where(Category.slug == slug)
            ).scalar_one_or_none()
        return self._category_cache[slug]

    @staticmethod
    def _batch_dedup_key(record: NormalizedPriceRecord) -> str:
        """Deterministic key used to avoid intra-batch product duplicates in dry-run."""
        if record.barcode:
            return f"barcode:{record.barcode}"
        brand_key = normalize_text_key(record.brand)
        name_key = normalize_text_key(record.name)
        return f"sig:{brand_key}|{name_key}|{record.unit_size}|{record.unit_type}"

    def publish_records(
        self,
        records: Iterable[NormalizedPriceRecord],
        *,
        retailer_slug: Optional[str] = None,
        dry_run: bool = False,
        force_history_snapshot: bool = False,
        commit: bool = True,
    ) -> PublishSummary:
        """Idempotently publish normalized records into store_prices & price_history.

        Args:
            records: NormalizedPriceRecord objects from the scraper/normalizer pipeline.
            retailer_slug: Optional retailer slug label for telemetry summary.
            dry_run: When True, simulates matching & diffing without writing to the DB.
            force_history_snapshot: When True, appends PriceHistory even if price is
                unchanged (intended for scheduled daily/weekly trend snapshots).
            commit: When True (and not dry_run), commits the transaction on completion.

        Returns:
            PublishSummary detailing matched/created products and price/history deltas.
        """
        record_list = list(records)
        summary_slug = retailer_slug or (
            record_list[0].retailer_slug if record_list else "unknown"
        )
        summary = PublishSummary(retailer_slug=summary_slug, dry_run=dry_run)

        dry_run_created_keys: set[str] = set()

        for record in record_list:
            summary.records_processed += 1

            store = self._get_canonical_store(record.retailer_slug)
            if store is None:
                logger.warning(
                    "Skipping '%s': canonical chain store not found for slug '%s'",
                    record.name,
                    record.retailer_slug,
                )
                summary.skipped += 1
                continue

            product = match_product(self.session, record)
            if product is not None:
                summary.products_matched += 1
            else:
                dedup_key = self._batch_dedup_key(record)
                if dry_run:
                    if dedup_key in dry_run_created_keys:
                        summary.products_matched += 1
                    else:
                        dry_run_created_keys.add(dedup_key)
                        summary.products_created += 1
                    summary.prices_inserted += 1
                    summary.history_appended += 1
                    continue

                category = self._get_category(record.category_slug)
                product = Product(
                    category_id=category.id if category is not None else None,
                    name=record.name,
                    brand=record.brand,
                    barcode=record.barcode,
                    unit_size=record.unit_size,
                    unit_type=record.unit_type,
                )
                self.session.add(product)
                self.session.flush()
                summary.products_created += 1

            existing_price = self.session.execute(
                select(StorePrice).where(
                    StorePrice.store_id == store.id,
                    StorePrice.product_id == product.id,
                )
            ).scalar_one_or_none()

            if existing_price is None:
                summary.prices_inserted += 1
                summary.history_appended += 1
                if not dry_run:
                    self.session.add(
                        StorePrice(
                            store_id=store.id,
                            product_id=product.id,
                            price=record.price,
                            is_promotional=record.is_promotional,
                            is_in_stock=True,
                            updated_at=record.scraped_at,
                        )
                    )
                    self.session.add(
                        PriceHistory(
                            store_id=store.id,
                            product_id=product.id,
                            price=record.price,
                            is_promotional=record.is_promotional,
                            recorded_at=record.scraped_at,
                        )
                    )
                    self.session.flush()
                continue

            current_price = Decimal(existing_price.price).quantize(
                TWO_DECIMAL_PLACES, rounding=ROUND_HALF_UP
            )
            price_changed = (
                current_price != record.price
                or bool(existing_price.is_promotional) != record.is_promotional
            )

            if price_changed:
                summary.prices_updated += 1
                summary.history_appended += 1
                if not dry_run:
                    existing_price.price = record.price
                    existing_price.is_promotional = record.is_promotional
                    existing_price.is_in_stock = True
                    existing_price.updated_at = record.scraped_at
                    self.session.add(
                        PriceHistory(
                            store_id=store.id,
                            product_id=product.id,
                            price=record.price,
                            is_promotional=record.is_promotional,
                            recorded_at=record.scraped_at,
                        )
                    )
                    self.session.flush()
            else:
                summary.prices_unchanged += 1
                if not dry_run:
                    existing_price.updated_at = record.scraped_at
                if force_history_snapshot:
                    summary.history_appended += 1
                    if not dry_run:
                        self.session.add(
                            PriceHistory(
                                store_id=store.id,
                                product_id=product.id,
                                price=record.price,
                                is_promotional=record.is_promotional,
                                recorded_at=record.scraped_at,
                            )
                        )
                if not dry_run:
                    self.session.flush()

        if not dry_run and commit:
            self.session.commit()

        return summary


def publish_normalized_records(
    session: Session,
    records: Iterable[NormalizedPriceRecord],
    *,
    retailer_slug: Optional[str] = None,
    dry_run: bool = False,
    force_history_snapshot: bool = False,
    commit: bool = True,
) -> PublishSummary:
    """Convenience wrapper around CatalogPublisher.publish_records."""
    publisher = CatalogPublisher(session)
    return publisher.publish_records(
        records,
        retailer_slug=retailer_slug,
        dry_run=dry_run,
        force_history_snapshot=force_history_snapshot,
        commit=commit,
    )
