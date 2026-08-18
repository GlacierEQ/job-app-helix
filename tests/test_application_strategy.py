from __future__ import annotations

import json
from pathlib import Path

import pytest

from job_app_helix.application_engine import find_target, load_targets
from job_app_helix.application_operations import (
    ApplicationStore,
    ingest_job_opening,
    load_candidate_profile,
)
from job_app_helix.application_strategy import (
    compile_requirement_aware_lifecycle,
    project_company_aware_application,
    project_requirement_aware_application,
)
from job_app_helix.company_intelligence import load_company_intelligence

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
                ],
                "experience": [
                    "Designed evidence-grounded automation and failure recovery systems.",
                    "Built distributed agent coordination and production software tooling.",
                    "Engineered containment and observability for capable agent systems.",
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


def _opening():
    return ingest_job_opening(
        {
            "company": "Anthropic",
            "title": "Safety Systems Engineer",
            "description": "Build reliable Python evaluation and observability systems.",
            "requirements": ["Python", "observability", "AI safety evaluation"],
            "preferred": ["systems architecture"],
        }
    )


def _intelligence():
    return load_company_intelligence(ROOT / "manifests/company_intelligence/anthropic.json")


def test_projection_places_explicit_requirement_evidence_in_recruiter_copy(
    tmp_path: Path,
) -> None:
    profile = load_candidate_profile(_profile(tmp_path))
    _, _, assessment, projection = project_requirement_aware_application(
        _opening(),
        _target(),
        profile,
        role="Safety Systems Engineer",
    )

    assert assessment.recommendation == "APPLY_PRIORITY"
    assert "## Role-aligned evidence" in projection.resume_markdown
    assert "**Python:** Python" in projection.resume_markdown
    assert "**observability:** observability" in projection.resume_markdown
    assert "Against the role's explicit qualifications" in projection.cover_letter_markdown
    assert "Explicit-role evidence:" in projection.outreach_markdown
    assert any(source.startswith("job-opening:") for source in projection.claim_sources)


def test_strategy_never_invents_missing_requirement_evidence(tmp_path: Path) -> None:
    profile = load_candidate_profile(_profile(tmp_path))
    opening = ingest_job_opening(
        {
            "company": "Anthropic",
            "title": "Safety Systems Engineer",
            "description": "Python CUDA ASIC compiler role.",
            "requirements": [
                "Python",
                "CUDA kernel optimization",
                "ASIC verification",
                "compiler backend development",
            ],
        }
    )

    _, _, assessment, projection = project_requirement_aware_application(
        opening,
        _target(),
        profile,
        role="Safety Systems Engineer",
    )

    assert assessment.recommendation == "GAPS_TO_CLOSE"
    assert "CUDA kernel optimization" not in projection.resume_markdown
    assert "ASIC verification" not in projection.resume_markdown
    assert "compiler backend development" not in projection.resume_markdown


def test_company_direction_changes_recruiter_copy_only_when_evidence_exists(
    tmp_path: Path,
) -> None:
    profile = load_candidate_profile(_profile(tmp_path))
    _, _, opportunity, company_fit, projection = project_company_aware_application(
        _opening(),
        _target(),
        profile,
        _intelligence(),
        role="Safety Systems Engineer",
    )

    assert opportunity.recommendation == "APPLY_PRIORITY"
    assert company_fit.fresh_signal_count == 5
    assert company_fit.matched_signals
    assert "## Current company-direction alignment" in projection.resume_markdown
    assert "containment" in projection.resume_markdown.lower()
    assert "Current company direction also intersects" in projection.cover_letter_markdown
    assert "Current-company alignment:" in projection.outreach_markdown
    assert "5GW" not in projection.resume_markdown
    assert "100 billion" not in projection.resume_markdown
    assert all("anthropic.com" not in source for source in projection.claim_sources)


def test_company_intelligence_must_match_application_target(tmp_path: Path) -> None:
    profile = load_candidate_profile(_profile(tmp_path))
    payload = json.loads(
        (ROOT / "manifests/company_intelligence/anthropic.json").read_text(encoding="utf-8")
    )
    payload["company_id"] = "not-anthropic"
    bad_path = tmp_path / "wrong-company.json"
    bad_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="company intelligence does not match target"):
        project_company_aware_application(
            _opening(),
            _target(),
            profile,
            load_company_intelligence(bad_path),
            role="Safety Systems Engineer",
        )


def test_compile_lifecycle_persists_company_strategy_receipts(tmp_path: Path) -> None:
    profile = load_candidate_profile(_profile(tmp_path))
    output_dir = tmp_path / "output"
    with ApplicationStore(tmp_path / "applications.sqlite3") as store:
        packet = compile_requirement_aware_lifecycle(
            _opening(),
            _target(),
            profile,
            output_dir=output_dir,
            store=store,
            role="Safety Systems Engineer",
            company_intelligence=_intelligence(),
        )
        application = store.get_application(str(packet["application_id"]))

    artifacts = packet["artifacts"]
    assert isinstance(artifacts, dict)
    assessment_path = Path(str(artifacts["opportunity_assessment"]))
    company_fit_path = Path(str(artifacts["company_fit_assessment"]))
    receipt_path = Path(str(artifacts["strategy_receipt"]))
    assert assessment_path.exists()
    assert company_fit_path.exists()
    assert receipt_path.exists()
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["opportunity_recommendation"] == "APPLY_PRIORITY"
    assert receipt["matched_requirements"] == [
        "Python",
        "observability",
        "AI safety evaluation",
    ]
    assert receipt["company_fresh_signal_count"] == 5
    assert len(receipt["company_source_urls"]) == 5
    assert packet["schema"] == "glaciereq.company-aware-application-packet.v1"
    assert application["status"] == "READY"
