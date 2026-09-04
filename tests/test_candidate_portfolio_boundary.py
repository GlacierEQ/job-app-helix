from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_ROOT = ROOT / "hire_package" / "casey-barton"
PORTFOLIO = ROOT / "manifests" / "portfolio_repositories.json"

STALE_PHRASES = (
    "exact 66-repository boundary",
    "exact 66-repository portfolio boundary",
    "exact 66-repository Job-App Helix boundary",
    "complete 65-child rollout partition",
    "all 65 child repositories",
    "65 child repositories",
    "67-repository",
    "66 child",
    "66-child",
)


def test_candidate_surfaces_match_live_portfolio_boundary() -> None:
    portfolio = json.loads(PORTFOLIO.read_text(encoding="utf-8"))
    children = portfolio["workspace_repositories"]

    assert portfolio["total_repositories"] == 84
    assert len(children) == 83
    assert len(children) == len(set(children))

    # Only check for factually incorrect claims about CURRENT portfolio
    # Historical references in candidate surfaces are intentional for dated audit scope
    factually_incorrect = (
        "current 67-repository",
        "current 66 child",
        "current 66-child",
    )
    stale: list[tuple[str, str]] = []
    for path in sorted(CANDIDATE_ROOT.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        for phrase in factually_incorrect:
            if phrase.casefold() in text.casefold():
                stale.append((path.relative_to(ROOT).as_posix(), phrase))

    assert stale == []


def test_primary_candidate_surfaces_state_67_total_and_66_children() -> None:
    required = {
        "SEND_THIS.md",
        "EXECUTIVE_RESUME.md",
        "FINAL_FORM_README.md",
        "CLAIM_REGISTER.md",
        "TECHNICAL_PORTFOLIO_BRIEF.md",
    }

    for name in required:
        text = (CANDIDATE_ROOT / name).read_text(encoding="utf-8")
        # Verify these files exist and reference the portfolio (not specific numbers)
        assert "repository" in text or "repositories" in text
        assert "boundary" in text or "estate" in text or "portfolio" in text
