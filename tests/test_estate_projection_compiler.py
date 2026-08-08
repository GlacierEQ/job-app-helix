from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

spec = importlib.util.spec_from_file_location(
    "estate_projection", SCRIPTS / "compile_estate_projection.py"
)
assert spec is not None and spec.loader is not None
compiler = importlib.util.module_from_spec(spec)
spec.loader.exec_module(compiler)


def _policy() -> dict:
    return {
        "promotion_score_weights": {
            "originality": 0.2,
            "technical_depth": 0.2,
            "verification": 0.2,
            "transferability": 0.2,
            "target_relevance": 0.2,
        },
        "audience_caps": {
            "recruiter": 10,
            "senior_engineer": 20,
            "company_reviewer": 5,
        },
        "restricted_namespace_tokens": ["legal", "case", "court"],
        "capability_taxonomy": {
            "agent_orchestration": {"signals": ["orchestration"]},
            "provenance": {"signals": ["receipt", "provenance"]},
        },
    }


def _census() -> dict:
    rows = [
        ("GlacierEQ/AKOS", "public", False, False, "PRIORITY_SPINE"),
        ("GlacierEQ/alpha", "public", False, False, "RECRUITER_PORTFOLIO"),
        (
            "GlacierEQ/alpha-old",
            "public",
            False,
            False,
            "UNGOVERNED_PUBLIC_INVENTORY",
        ),
        (
            "GlacierEQ/dep-reference",
            "public",
            False,
            False,
            "UNGOVERNED_PUBLIC_INVENTORY",
        ),
        (
            "GlacierEQ/AKOS-backup",
            "private",
            True,
            False,
            "ARCHIVE_BACKUP_OR_FORK",
        ),
        (
            "GlacierEQ/legal-case",
            "private",
            False,
            False,
            "PRIVATE_REVIEW_REQUIRED",
        ),
        (
            "GlacierEQ/upstream",
            "public",
            False,
            True,
            "UPSTREAM_OR_FORK_REVIEW",
        ),
    ]
    records = [
        {
            "repository": repo,
            "visibility": visibility,
            "archived": archived,
            "fork": fork,
            "classification": classification,
        }
        for repo, visibility, archived, fork, classification in rows
    ]
    return {
        "repository_count": 7,
        "native_repository_count": 6,
        "fork_repository_count": 1,
        "repositories": records,
    }


def _flagships() -> dict:
    return {
        "flagships": [
            {
                "system_id": "akos",
                "repository": "GlacierEQ/AKOS",
                "level": "L5",
                "state": "PROMOTED",
                "public_surface": "PUBLIC",
                "role": "orchestration",
                "evidence": "provenance receipt",
            },
            {
                "system_id": "alpha",
                "repository": "GlacierEQ/alpha",
                "level": "L4",
                "state": "PROMOTED",
                "public_surface": "PUBLIC",
                "role": "orchestration",
                "evidence": "provenance receipt",
            },
        ]
    }


def _lineage(state: str = "VERIFIED") -> dict:
    return {
        "canonical_assertions": [],
        "namespace_assertions": [],
        "relationships": [
            {
                "member_repository": "GlacierEQ/alpha-old",
                "canonical_repository": "GlacierEQ/alpha",
                "relation": "SUCCESSOR_OF",
                "state": state,
            },
            {
                "member_repository": "GlacierEQ/dep-reference",
                "canonical_repository": "GlacierEQ/AKOS",
                "relation": "REFERENCE_OF",
                "state": "VERIFIED",
            },
        ],
    }


def _assessment(repo: str) -> dict:
    dimensions = {
        key: {
            "state": "VERIFIED",
            "raw_score": 90,
            "findings": ["orchestration provenance receipt"],
            "receipts": ["https://example.test/proof"],
        }
        for key in ("architecture", "reality", "integration", "ai_readiness")
    }
    return {
        "repository": repo,
        "health_score": 90,
        "evidence_coverage": 100,
        "dimensions": dimensions,
    }


def _catalog() -> tuple[dict, dict]:
    repos = [
        {
            "repository": repo,
            "promotion_state": "PROMOTED",
            "visibility": "public",
            "provenance_state": "ORIGINAL_CANDIDATE",
        }
        for repo in ("GlacierEQ/AKOS", "GlacierEQ/alpha")
    ]
    company = {
        "company_id": "acme",
        "display_name": "Acme",
        "track_state": "ACTIVE",
        "target_roles": ["Systems Engineer"],
        "recruiter_thesis": "Proof bound",
        "repositories": repos,
    }
    return {"acme": company}, {row["repository"]: row for row in repos}


def _run(monkeypatch, lineage: dict | None = None) -> dict:
    companies, repo_meta = _catalog()
    monkeypatch.setattr(
        compiler,
        "load_company_catalog",
        lambda _root, _index: (companies, repo_meta),
    )
    assessments = {
        repo: _assessment(repo) for repo in ("GlacierEQ/AKOS", "GlacierEQ/alpha")
    }
    second_depth = {
        "default_company_state": {
            "stage": "MAPPED_ONLY",
            "claim_ceiling": "alignment",
            "next_gate": "Bound problem",
            "problem_evidence": [],
        },
        "company_overrides": {"acme": {"stage": "PROBLEM_BOUNDED"}},
    }
    return compiler.compile_all(
        _census(),
        {},
        second_depth,
        _flagships(),
        _lineage() if lineage is None else lineage,
        _policy(),
        assessments,
    )


def test_verified_lineage_collapses_member_not_history_or_support(monkeypatch) -> None:
    result = _run(monkeypatch)
    registry = result["canonical_system_registry"]
    assert registry["current_declared_canonical_system_count"] == 2
    states = {
        row["repository"]: row["disposition"]
        for row in registry["repository_dispositions"]
    }
    assert states["GlacierEQ/alpha-old"] == "LINEAGE_MEMBER"
    assert states["GlacierEQ/dep-reference"] == "DEPENDENCY_REFERENCE"
    assert states["GlacierEQ/AKOS-backup"] == "HISTORICAL_PROVENANCE"
    assert states["GlacierEQ/legal-case"] == "RESTRICTED_NAMESPACE_CANDIDATE"


def test_candidate_lineage_never_collapses(monkeypatch) -> None:
    result = _run(monkeypatch, _lineage("CANDIDATE_REVIEW_REQUIRED"))
    states = {
        row["repository"]: row["disposition"]
        for row in result["canonical_system_registry"]["repository_dispositions"]
    }
    assert states["GlacierEQ/alpha-old"] == "UNRESOLVED_REVIEW"


def test_verified_standalone_canonical_assertion_requires_evidence(monkeypatch) -> None:
    lineage = _lineage("CANDIDATE_REVIEW_REQUIRED")
    lineage["canonical_assertions"] = [
        {
            "repository": "GlacierEQ/alpha-old",
            "state": "VERIFIED",
            "evidence_refs": ["receipt:alpha-old"],
        }
    ]
    result = _run(monkeypatch, lineage)
    systems = {
        row["canonical_repository"]
        for row in result["canonical_system_registry"]["systems"]
    }
    assert "GlacierEQ/alpha-old" in systems


def test_capability_pattern_requires_multiple_systems(monkeypatch) -> None:
    result = _run(monkeypatch)
    rows = {
        row["capability"]: row
        for row in result["capability_donor_registry"]["capabilities"]
    }
    assert rows["agent_orchestration"]["donor_system_count"] == 2
    assert rows["agent_orchestration"]["repetition_state"] == "MULTI_SYSTEM_PATTERN"


def test_company_projection_is_scored_and_bounded(monkeypatch) -> None:
    result = _run(monkeypatch)
    company = result["company_projection_registry"]["companies"][0]
    assert company["second_depth_stage"] == "PROBLEM_BOUNDED"
    assert company["audience_projection"]["company_reviewer"] == ["akos", "alpha"]
    assert all(row["promotion_score"]["complete"] for row in company["system_candidates"])


def test_public_projection_hides_private_estate(monkeypatch) -> None:
    result = _run(monkeypatch)
    public = json.dumps(result["public_projection"], sort_keys=True)
    assert "GlacierEQ/legal-case" not in public
    assert "GlacierEQ/AKOS-backup" not in public
    assert "GlacierEQ/dep-reference" not in public
    assert "native_repository_count" not in public
    assert "repository_count" not in public


def test_bad_census_fails_closed() -> None:
    bad = _census()
    bad["native_repository_count"] = 99
    with pytest.raises(compiler.EstateCompilerError, match="arithmetic"):
        compiler.native_records(bad)
