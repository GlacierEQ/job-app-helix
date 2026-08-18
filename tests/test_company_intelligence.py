from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from job_app_helix.application_operations import load_candidate_profile
from job_app_helix.company_fit import assess_company_fit
from job_app_helix.company_intelligence import load_company_intelligence


def _profile(tmp_path: Path) -> Path:
    path = tmp_path / "candidate.json"
    path.write_text(
        json.dumps(
            {
                "name": "Casey Barton",
                "headline": "Systems architect and full-stack AI engineer",
                "summary": "Builds safe agent systems, observability, evaluation, and automation.",
                "skills": [
                    "Python",
                    "AI safety evaluation",
                    "observability",
                    "distributed systems",
                    "agent systems",
                ],
                "experience": [
                    "Designed evidence-grounded automation, containment, and failure recovery systems."
                ],
                "achievements": ["Shipped public technical repositories with verification."],
            }
        ),
        encoding="utf-8",
    )
    return path


def _intelligence(tmp_path: Path, observed_at: str) -> Path:
    path = tmp_path / "company.json"
    path.write_text(
        json.dumps(
            {
                "company_id": "example",
                "company": "Example",
                "collected_at": observed_at,
                "max_age_days": 30,
                "signals": [
                    {
                        "kind": "engineering",
                        "statement": "Build safe agent systems with containment and observability.",
                        "source_url": "https://example.com/engineering",
                        "observed_at": observed_at,
                    },
                    {
                        "kind": "hiring",
                        "statement": "Hiring compiler kernel specialists for custom accelerators.",
                        "source_url": "https://example.com/jobs",
                        "observed_at": observed_at,
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    return path


def test_company_fit_uses_fresh_sourced_signals_without_inventing_fit(tmp_path: Path) -> None:
    observed = "2026-08-18T00:00:00Z"
    profile = load_candidate_profile(_profile(tmp_path))
    intelligence = load_company_intelligence(_intelligence(tmp_path, observed))

    assessment = assess_company_fit(
        profile,
        intelligence,
        now=datetime(2026, 8, 18, 6, tzinfo=UTC),
    )

    assert assessment.fresh_signal_count == 2
    assert assessment.stale_signal_count == 0
    assert len(assessment.matched_signals) == 1
    assert len(assessment.unmatched_signals) == 1
    assert "compiler kernel specialists" in assessment.unmatched_signals[0]
    assert assessment.source_urls == (
        "https://example.com/engineering",
        "https://example.com/jobs",
    )


def test_stale_signals_are_excluded_from_fit(tmp_path: Path) -> None:
    observed = "2026-01-01T00:00:00Z"
    profile = load_candidate_profile(_profile(tmp_path))
    intelligence = load_company_intelligence(_intelligence(tmp_path, observed))

    assessment = assess_company_fit(
        profile,
        intelligence,
        now=datetime(2026, 8, 18, tzinfo=UTC),
    )

    assert assessment.fresh_signal_count == 0
    assert assessment.stale_signal_count == 2
    assert assessment.score == 0.0
    assert assessment.strategic_hooks == ()
    assert assessment.source_urls == ()


def test_company_signal_requires_absolute_source_url(tmp_path: Path) -> None:
    path = _intelligence(tmp_path, "2026-08-18T00:00:00Z")
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["signals"][0]["source_url"] = "not-a-source"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="absolute HTTP"):
        load_company_intelligence(path)
