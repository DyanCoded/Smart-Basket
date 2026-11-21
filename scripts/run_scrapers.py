"""CLI entrypoint for SmartBasket Phase 3 national chain price scrapers.

Usage:
    python scripts/run_scrapers.py --retailer all --dry-run
    python scripts/run_scrapers.py --retailer checkers --queries "milk,bread,eggs"
    python scripts/run_scrapers.py --retailer all --force-history
    python scripts/run_scrapers.py --retailer all --source-dir tests/fixtures/feeds
    python scripts/run_scrapers.py --retailer all --summary-json scraper_summary.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy.orm import Session  # noqa: E402

from src.core.database import SessionLocal  # noqa: E402
from src.scrapers.base import BaseRetailerScraper  # noqa: E402
from src.scrapers.feed_loader import (  # noqa: E402
    FeedSnapshotScraper,
    load_feed_items_from_dir,
)
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


def build_feed_registry(
    source_dir: Path,
    retailer_slugs: list[str],
) -> dict[str, Callable[[], BaseRetailerScraper]]:
    """Build a scraper registry backed by structured JSON/CSV feed snapshots."""
    grouped = load_feed_items_from_dir(source_dir, retailer_slugs=retailer_slugs)
    return {
        slug: (
            lambda s=slug, items=grouped.get(slug, []): FeedSnapshotScraper(
                retailer_slug=s, items=items
            )
        )
        for slug in retailer_slugs
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
    source_dir: Optional[Path] = None,
) -> list[PublishSummary]:
    """Execute scrape -> normalize -> publish across selected national chains.

    Isolates per-retailer exceptions: if one retailer adapter fails, logs a
    structured warning, rolls back any pending DB state for that retailer,
    records a failed PublishSummary, and continues processing the rest.
    Retailers finishing with 0 processed items are explicitly marked `partial`
    so blocked or empty runs are never silently reported as healthy.
    """
    owns_session = session is None
    db_session = session or SessionLocal()
    summaries: list[PublishSummary] = []

    active_registry = scraper_registry
    if active_registry is None and source_dir is not None:
        active_registry = build_feed_registry(source_dir, retailer_slugs)

    try:
        publisher = CatalogPublisher(db_session)
        for slug in retailer_slugs:
            started = time.monotonic()
            try:
                records = await scrape_and_normalize_retailer(
                    slug,
                    query_terms,
                    scraper_registry=active_registry,
                )
                summary = publisher.publish_records(
                    records,
                    retailer_slug=slug,
                    dry_run=dry_run,
                    force_history_snapshot=force_history,
                    commit=not dry_run,
                )
                summary.duration_seconds = round(time.monotonic() - started, 3)
                summary.synced_at = datetime.now(timezone.utc)
                if summary.records_processed == 0:
                    summary.status = "partial"
                    summary.error = "0 items extracted (blocked, empty, or no matches)"
                    logger.warning(
                        "Retailer scraper returned 0 items | retailer=%s "
                        "duration=%.3fs",
                        slug,
                        summary.duration_seconds,
                    )
                else:
                    summary.status = "ok"
                summaries.append(summary)
            except Exception as exc:  # noqa: BLE001
                elapsed = round(time.monotonic() - started, 3)
                if owns_session and not dry_run:
                    try:
                        db_session.rollback()
                    except Exception:  # noqa: BLE001
                        logger.debug(
                            "[%s] Rollback after failure skipped", slug, exc_info=True
                        )
                error_detail = f"{type(exc).__name__}: {exc}"
                logger.warning(
                    "Retailer scraper failed | retailer=%s error=%s duration=%.3fs",
                    slug,
                    error_detail,
                    elapsed,
                )
                summaries.append(
                    PublishSummary(
                        retailer_slug=slug,
                        dry_run=dry_run,
                        status="failed",
                        error=error_detail,
                        duration_seconds=elapsed,
                        synced_at=datetime.now(timezone.utc),
                    )
                )
    finally:
        if owns_session:
            db_session.close()

    return summaries


def build_telemetry_report(summaries: list[PublishSummary]) -> dict[str, Any]:
    """Aggregate per-retailer summaries into a structured JSON telemetry payload."""
    total = len(summaries)
    failed = sum(1 for s in summaries if s.status == "failed")
    partial = sum(1 for s in summaries if s.status == "partial")
    succeeded = sum(1 for s in summaries if s.status == "ok")

    if total > 0 and failed == total:
        overall_status = "failed"
    elif failed > 0 or partial > 0:
        overall_status = "degraded"
    else:
        overall_status = "ok"

    return {
        "overall_status": overall_status,
        "total_retailers": total,
        "succeeded": succeeded,
        "partial": partial,
        "failed": failed,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "retailers": [s.model_dump(mode="json") for s in summaries],
    }


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
        default=None,
        help=(
            "Comma-separated search terms (default: 'milk,bread,eggs' for live "
            "scrapers; all items for --source-dir)."
        ),
    )
    parser.add_argument(
        "--source-dir",
        default=None,
        help=(
            "Directory containing structured JSON/CSV retailer price snapshot "
            "files to ingest through normalizer & publisher."
        ),
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
    parser.add_argument(
        "--summary-json",
        default=None,
        help="Optional file path to export structured JSON run telemetry.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero if any retailer fails or returns 0 items.",
    )
    return parser


def main(
    argv: Optional[list[str]] = None,
    *,
    session: Optional[Session] = None,
    scraper_registry: Optional[dict[str, Callable[[], BaseRetailerScraper]]] = None,
) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s [%(name)s] %(message)s",
    )
    parser = build_parser()
    args = parser.parse_args(argv)

    target_retailers = (
        list(CANONICAL_RETAILERS) if args.retailer == "all" else [args.retailer]
    )
    source_path = Path(args.source_dir) if args.source_dir else None

    if args.queries is not None:
        query_terms = [q.strip() for q in args.queries.split(",") if q.strip()]
    elif source_path is not None:
        query_terms = []
    else:
        query_terms = ["milk", "bread", "eggs"]

    mode_label = "DRY-RUN" if args.dry_run else "LIVE PUBLISH"
    source_label = f"FEED ({source_path})" if source_path else "LIVE HTTP"
    print(f"SmartBasket Scraper Pipeline ({mode_label} | {source_label})")
    print(f"Retailers : {', '.join(target_retailers)}")
    print(f"Queries   : {', '.join(query_terms) or '(all)'}")
    print("-" * 78)

    summaries = asyncio.run(
        run_pipeline(
            target_retailers,
            query_terms,
            dry_run=args.dry_run,
            force_history=args.force_history,
            session=session,
            scraper_registry=scraper_registry,
            source_dir=source_path,
        )
    )

    for summary in summaries:
        if summary.status == "failed":
            print(
                f"  {summary.retailer_slug:<16} | STATUS=FAILED "
                f"duration={summary.duration_seconds:.2f}s "
                f"error={summary.error}"
            )
        elif summary.status == "partial":
            print(
                f"  {summary.retailer_slug:<16} | STATUS=PARTIAL (0 items) "
                f"duration={summary.duration_seconds:.2f}s "
                f"detail={summary.error}"
            )
        else:
            print(
                f"  {summary.retailer_slug:<16} | STATUS=OK "
                f"processed={summary.records_processed} "
                f"matched={summary.products_matched} "
                f"created={summary.products_created} "
                f"inserted={summary.prices_inserted} "
                f"updated={summary.prices_updated} "
                f"unchanged={summary.prices_unchanged} "
                f"history={summary.history_appended} "
                f"skipped={summary.skipped} "
                f"duration={summary.duration_seconds:.2f}s"
            )

    report = build_telemetry_report(summaries)
    if args.summary_json:
        out_path = Path(args.summary_json)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("-" * 78)
    overall = report["overall_status"]
    if overall == "failed":
        print(
            f"Pipeline run FAILED: 0/{report['total_retailers']} retailers succeeded."
        )
        return 1
    if overall == "degraded":
        failed_slugs = [s.retailer_slug for s in summaries if s.status == "failed"]
        partial_slugs = [s.retailer_slug for s in summaries if s.status == "partial"]
        print(
            f"Pipeline run PARTIAL SUCCESS (DEGRADED): "
            f"{report['succeeded']}/{report['total_retailers']} ok; "
            f"partial(0 items)={partial_slugs}; failed={failed_slugs}"
        )
        return 1 if args.strict else 0

    print(
        f"Pipeline run completed successfully: "
        f"{report['succeeded']}/{report['total_retailers']} retailers synced."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
