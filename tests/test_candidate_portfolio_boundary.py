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
)


def test_candidate_surfaces_match_live_portfolio_boundary() -> None:
    portfolio = json.loads(PORTFOLIO.read_text(encoding="utf-8"))
    children = portfolio["workspace_repositories"]

    assert portfolio["total_repositories"] == 67
    assert len(children) == 66
    assert len(children) == len(set(children))

    stale: list[tuple[str, str]] = []
    for path in sorted(CANDIDATE_ROOT.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        for phrase in STALE_PHRASES:
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
        assert "67-repository" in text
        assert "66 child" in text or "66-child" in text
