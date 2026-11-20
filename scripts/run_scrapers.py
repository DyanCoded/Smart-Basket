"""CLI entrypoint for SmartBasket Phase 3 national chain price scrapers.

Usage:
    python scripts/run_scrapers.py --retailer all --dry-run
    python scripts/run_scrapers.py --retailer checkers --queries "milk,bread,eggs"
    python scripts/run_scrapers.py --retailer all --force-history
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path
from typing import Callable, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy.orm import Session  # noqa: E402

from src.core.database import SessionLocal  # noqa: E402
from src.scrapers.base import BaseRetailerScraper  # noqa: E402
from src.scrapers.models import NormalizedPriceRecord, PublishSummary  # noqa: E402
from src.scrapers.normalizer import normalize_scraped_item  # noqa: E402
from src.scrapers.publisher import CatalogPublisher  # noqa: E402
from src.scrapers.retailers.pick_n_pay import PickNPayScraper  # noqa: E402
from src.scrapers.retailers.shoprite_group import (  # noqa: E402
    CheckersScraper,
    ShopriteScraper,
)
from src.scrapers.retailers.spar import SparScraper  # noqa: E402
from src.scrapers.retailers.woolworths import WoolworthsScraper  # noqa: E402

logger = logging.getLogger("smart_basket.scrapers")

CANONICAL_RETAILERS: tuple[str, ...] = (
    "shoprite",
    "checkers",
    "pick-n-pay",
    "woolworths-food",
    "spar",
)

# Registry of live catalog scraper factories across all 5 South African national chains
# (Shoprite & Checkers #20, Pick n Pay #21, Woolworths Food #22, SPAR #23).
SCRAPER_REGISTRY: dict[str, Callable[[], BaseRetailerScraper]] = {
    "shoprite": ShopriteScraper,
    "checkers": CheckersScraper,
    "pick-n-pay": PickNPayScraper,
    "woolworths-food": WoolworthsScraper,
    "spar": SparScraper,
}


async def scrape_and_normalize_retailer(
    retailer_slug: str,
    query_terms: list[str],
    *,
    scraper_registry: Optional[dict[str, Callable[[], BaseRetailerScraper]]] = None,
) -> list[NormalizedPriceRecord]:
    """Run a single retailer scraper and normalize all extracted raw items."""
    registry = scraper_registry if scraper_registry is not None else SCRAPER_REGISTRY
    factory = registry.get(retailer_slug)
    if factory is None:
        raise ValueError(f"Unsupported retailer slug: {retailer_slug!r}")

    normalized: list[NormalizedPriceRecord] = []
    async with factory() as scraper:
        raw_items = await scraper.scrape_catalog(query_terms)

    for raw in raw_items:
        try:
            normalized.append(normalize_scraped_item(raw))
        except ValueError as exc:
            logger.warning(
                "[%s] Skipping unparseable item %r: %s",
                retailer_slug,
                raw.raw_name,
                exc,
            )

    return normalized


async def run_pipeline(
    retailer_slugs: list[str],
    query_terms: list[str],
    *,
    dry_run: bool = False,
    force_history: bool = False,
    session: Optional[Session] = None,
    scraper_registry: Optional[dict[str, Callable[[], BaseRetailerScraper]]] = None,
) -> list[PublishSummary]:
    """Execute scrape -> normalize -> publish across selected national chains."""
    owns_session = session is None
    db_session = session or SessionLocal()
    summaries: list[PublishSummary] = []

    try:
        publisher = CatalogPublisher(db_session)
        for slug in retailer_slugs:
            records = await scrape_and_normalize_retailer(
                slug,
                query_terms,
                scraper_registry=scraper_registry,
            )
            summary = publisher.publish_records(
                records,
                retailer_slug=slug,
                dry_run=dry_run,
                force_history_snapshot=force_history,
                commit=not dry_run,
            )
            summaries.append(summary)
    finally:
        if owns_session:
            db_session.close()

    return summaries


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run SmartBasket national chain price scrapers & catalog publisher."
    )
    parser.add_argument(
        "--retailer",
        choices=["all", *CANONICAL_RETAILERS],
        default="all",
        help="Target national retailer chain slug or 'all' (default: all).",
    )
    parser.add_argument(
        "--queries",
        default="milk,bread,eggs",
        help="Comma-separated product search terms (default: 'milk,bread,eggs').",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Scrape, normalize, and diff against DB without writing changes.",
    )
    parser.add_argument(
        "--force-history",
        action="store_true",
        help="Append price_history snapshots even when prices have not changed.",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s [%(name)s] %(message)s",
    )
    parser = build_parser()
    args = parser.parse_args(argv)

    target_retailers = (
        list(CANONICAL_RETAILERS) if args.retailer == "all" else [args.retailer]
    )
    query_terms = [q.strip() for q in args.queries.split(",") if q.strip()]

    mode_label = "DRY-RUN" if args.dry_run else "LIVE PUBLISH"
    print(f"SmartBasket Scraper Pipeline ({mode_label})")
    print(f"Retailers : {', '.join(target_retailers)}")
    print(f"Queries   : {', '.join(query_terms) or '(all)'}")
    print("-" * 72)

    summaries = asyncio.run(
        run_pipeline(
            target_retailers,
            query_terms,
            dry_run=args.dry_run,
            force_history=args.force_history,
        )
    )

    for summary in summaries:
        print(
            f"  {summary.retailer_slug:<16} | processed={summary.records_processed} "
            f"matched={summary.products_matched} created={summary.products_created} "
            f"inserted={summary.prices_inserted} updated={summary.prices_updated} "
            f"unchanged={summary.prices_unchanged} history={summary.history_appended} "
            f"skipped={summary.skipped}"
        )

    print("-" * 72)
    print("Pipeline run completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
