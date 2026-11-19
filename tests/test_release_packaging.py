"""Tests for release packaging, documentation completeness, and milestone delivery."""

from __future__ import annotations

from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DOCS_DIR = ROOT_DIR / "docs"


def test_readme_completeness() -> None:
    """Verify README.md contains architecture, quickstart, and status sections."""
    readme_path = ROOT_DIR / "README.md"
    assert readme_path.exists(), "README.md is missing"

    content = readme_path.read_text(encoding="utf-8")

    # Architecture diagram
    assert "```mermaid" in content
    assert "flowchart TD" in content

    # Quickstart instructions
    assert "docker compose up -d" in content
    assert "alembic upgrade head" in content
    assert "python scripts/seed.py --verify" in content
    assert "python scripts/check.py" in content
    assert "uvicorn src.main:app" in content

    # All 12 milestones marked as Completed
    for milestone_num in range(1, 13):
        prefix = f"{milestone_num:02d}."
        assert prefix in content, f"Milestone {prefix} missing from README.md"

    # Verify all 12 milestones are completed
    completed_count = content.count("🟢 Completed")
    assert (
        completed_count >= 12
    ), f"Expected 12 completed milestones, found {completed_count}"
    assert (
        "⚪ Planned" not in content
    ), "Unfinished planned milestones remain in status table"


def test_academic_retrospective_documentation() -> None:
    """Verify docs/RETROSPECTIVE.md contains grading and architecture artifacts."""
    retro_path = DOCS_DIR / "RETROSPECTIVE.md"
    assert retro_path.exists(), "docs/RETROSPECTIVE.md is missing"

    content = retro_path.read_text(encoding="utf-8")

    # Verify ERD diagram
    assert "```mermaid" in content
    assert "erDiagram" in content
    assert "STORE_PRICES" in content
    assert "PRICE_HISTORY" in content

    # Verify Algorithmic Analysis
    assert "Algorithmic Complexity" in content
    assert "Single-Store Basket Ranking" in content
    assert "Smart Split-Basket Optimization" in content
    assert "Promotional Deal Veracity Scoring" in content

    # Verify Query Performance & Indexing
    assert "ix_price_hist_lookup" in content
    assert "ix_store_prices_store_product" in content
    assert "Performance Benchmarks" in content

    # Verify Phase 2 Roadmap
    assert "Phase 2 Roadmap" in content
    assert "Distributed Scraping" in content
    assert "Redis" in content
    assert "PostGIS" in content


def test_release_notes_v1_0_0() -> None:
    """Verify docs/RELEASE_NOTES_v1.0.0.md contains Phase 1 release notes."""
    rel_path = DOCS_DIR / "RELEASE_NOTES_v1.0.0.md"
    assert rel_path.exists(), "docs/RELEASE_NOTES_v1.0.0.md is missing"

    content = rel_path.read_text(encoding="utf-8")
    assert "Release Notes v1.0.0" in content
    assert "Phase 1 Final Release" in content
    assert "What's New in v1.0.0" in content
    assert "Catalog & Multi-Store Pricing" in content
    assert "Smart Basket Optimization Engine" in content
    assert "Price History & Trend Intelligence" in content


def test_decisions_log_covers_all_milestones() -> None:
    """Verify docs/DECISIONS.md records decisions through Issue #12."""
    decisions_path = DOCS_DIR / "DECISIONS.md"
    assert decisions_path.exists(), "docs/DECISIONS.md is missing"

    content = decisions_path.read_text(encoding="utf-8")
    assert "Issue #12" in content
    assert "Issue #11" in content
    assert "Issue #10" in content
