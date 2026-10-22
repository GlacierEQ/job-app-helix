from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_portfolio_live_freshness_workflow_checks_current_receipt_schema() -> None:
    workflow = (
        ROOT / ".github" / "workflows" / "portfolio-live-freshness.yml"
    ).read_text(encoding="utf-8")

    assert "receipt['portfolio']['source_admitted_systems'] > 0" in workflow
    assert "receipt['portfolio']['flagships']" not in workflow
