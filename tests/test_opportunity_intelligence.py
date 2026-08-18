from __future__ import annotations

import json
from pathlib import Path

from job_app_helix.application_engine import find_target, load_targets
from job_app_helix.application_operations import (
    ingest_job_opening,
    load_candidate_profile,
)
from job_app_helix.opportunity_intelligence import assess_opportunity

ROOT = Path(__file__).resolve().parents[1]


def _profile(tmp_path: Path) -> Path:
    path = tmp_path / "candidate.json"
    path.write_text(
        json.dumps(
            {
                "name": "Casey Barton",
                "headline": "Systems architect and full-stack AI engineer",
                "summary": (
                    "Builds reliable agent systems, AI evaluation, observability, "
                    "and automation."
                ),
                "skills": [
                    "Python",
                    "systems architecture",
                    "AI safety evaluation",
                    "observability",
                    "distributed systems",
                ],
                "experience": [
                    "Designed evidence-grounded automation and failure recovery systems.",
                    "Built distributed agent coordination and production software tooling.",
                ],
                "achievements": [
                    "Shipped public technical repositories with reproducible verification."
                ],
            }
        ),
        encoding="utf-8",
    )
    return path


def _target():
    return find_target("anthropic", load_targets(ROOT / "manifests"))


def test_explicit_requirements_are_not_diluted_by_long_description(
    tmp_path: Path,
) -> None:
    profile = load_candidate_profile(_profile(tmp_path))
    opening = ingest_job_opening(
        {
            "company": "Anthropic",
            "title": "Safety Systems Engineer",
            "description": " ".join(
                [
                    "Join a multidisciplinary organization building ambitious products",
                    (
                        "across research policy operations partnerships infrastructure "
                        "and deployment"
                    ),
                ]
                * 20
            ),
            "requirements": [
                "Python",
                "systems architecture",
                "AI safety evaluation",
                "observability",
            ],
            "preferred": ["distributed systems"],
        }
    )

    assessment = assess_opportunity(
        opening,
        _target(),
        profile,
        mapped_role="Safety Systems Engineer",
    )

    assert assessment.required_coverage == 1.0
    assert assessment.preferred_coverage == 1.0
    assert assessment.missing_requirements == ()
    assert assessment.recommendation == "APPLY_PRIORITY"
    assert assessment.score >= 72


def test_missing_majority_of_explicit_requirements_caps_recommendation(
    tmp_path: Path,
) -> None:
    profile = load_candidate_profile(_profile(tmp_path))
    opening = ingest_job_opening(
        {
            "company": "Anthropic",
            "title": "Safety Systems Engineer",
            "description": (
                "Python systems role with specialized hardware and compiler ownership."
            ),
            "requirements": [
                "Python",
                "CUDA kernel optimization",
                "ASIC verification",
                "compiler backend development",
            ],
        }
    )

    assessment = assess_opportunity(
        opening,
        _target(),
        profile,
        mapped_role="Safety Systems Engineer",
    )

    assert assessment.required_coverage == 0.25
    assert len(assessment.missing_requirements) == 3
    assert assessment.recommendation == "GAPS_TO_CLOSE"
    assert any(
        "missing explicit requirements" in reason for reason in assessment.reasons
    )


def test_assessment_is_explainable_and_proof_aware(tmp_path: Path) -> None:
    profile = load_candidate_profile(_profile(tmp_path))
    opening = ingest_job_opening(
        {
            "company": "Anthropic",
            "title": "Safety Systems Engineer",
            "description": "Build reliable Python evaluation and observability systems.",
            "requirements": ["Python", "observability"],
        }
    )

    assessment = assess_opportunity(
        opening,
        _target(),
        profile,
        mapped_role="Safety Systems Engineer",
    )
    payload = assessment.as_dict()

    assert payload["schema"] == "glaciereq.opportunity-intelligence.v1"
    assert payload["proof_strength"] > 0
    assert payload["matched_requirements"] == ("Python", "observability")
    assert len(payload["reasons"]) >= 3
