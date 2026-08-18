from __future__ import annotations

import json
from pathlib import Path

import pytest

from job_app_helix.application_operations import load_candidate_profile
from job_app_helix.candidate_profile_compiler import (
    CandidateProfileCompileError,
    compile_candidate_profile,
    write_candidate_profile,
)


RESUME = """# Casey Barton — Senior Infrastructure Engineer

**Email**: casey@example.com | **GitHub**: github.com/GlacierEQ | **Location**: Honolulu, HI

## Summary

Infrastructure engineer focused on reliable AI and physical systems.

## Core Competencies

| Domain | Skills |
|--------|--------|
| **AI Systems** | multi-agent orchestration, MCP connectors |
| **DevOps** | Docker, Kubernetes, GitHub Actions |

## Key Projects

### Mastermind AI Orchestration
- 9 specialized agents with task chaining
- Real-time health monitoring and self-healing

### FILEBOSS
- SHA-256 and SHA-512 dual hashing

## Technical Skills

| Category | Technologies |
|----------|--------------|
| Languages | Python, TypeScript, SQL |
| Cloud | AWS, GCP, Vercel |
"""


SECONDARY = """# Casey Barton — AI Systems Engineer

**Email**: casey@example.com | **GitHub**: github.com/GlacierEQ | **Location**: Honolulu, HI

## Summary

Systems engineer building evidence-backed automation.

## Core Competencies

| Domain | Skills |
|--------|--------|
| **AI Systems** | Python, provenance graphs |

## Key Projects

### Evidence Runtime
- 37 connector routes mapped across 9 power dimensions

## Technical Skills

| Category | Technologies |
|----------|--------------|
| Languages | Python, Rust |
"""


def _write(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


def test_compile_single_resume_is_helix_loadable_and_source_bound(tmp_path: Path) -> None:
    resume = _write(tmp_path / "resume.md", RESUME)
    output = tmp_path / "profile.json"

    payload = write_candidate_profile([resume], output, profile_id="casey-production")
    loaded = load_candidate_profile(output)

    assert payload["name"] == "Casey Barton"
    assert payload["headline"] == "Senior Infrastructure Engineer"
    assert loaded.profile_id == "casey-production"
    assert "multi-agent orchestration" in loaded.skills
    assert "Python" in loaded.skills
    assert loaded.contact["email"] == "casey@example.com"
    assert loaded.contact["location"] == "Honolulu, HI"
    assert any(item.startswith("Mastermind AI Orchestration:") for item in loaded.experience)
    assert any("9 specialized agents" in item for item in loaded.achievements)
    provenance = payload["provenance"]
    assert isinstance(provenance, dict)
    assert provenance["policy"] == "source_text_only_no_claim_invention"
    assert provenance["sources"][0]["sha256"]


def test_multi_resume_composition_deduplicates_and_preserves_primary_voice(tmp_path: Path) -> None:
    primary = _write(tmp_path / "general.md", RESUME)
    secondary = _write(tmp_path / "specialized.md", SECONDARY)

    payload = compile_candidate_profile([primary, secondary])

    assert payload["headline"] == "Senior Infrastructure Engineer"
    assert payload["summary"] == (
        "Infrastructure engineer focused on reliable AI and physical systems."
    )
    assert payload["skills"].count("Python") == 1
    assert "Rust" in payload["skills"]
    assert any("37 connector routes" in item for item in payload["experience"])
    assert len(payload["provenance"]["sources"]) == 2


def test_conflicting_contact_evidence_fails_closed(tmp_path: Path) -> None:
    primary = _write(tmp_path / "general.md", RESUME)
    conflicting = _write(
        tmp_path / "conflicting.md",
        SECONDARY.replace("casey@example.com", "different@example.com"),
    )

    with pytest.raises(CandidateProfileCompileError, match="conflicting contact evidence"):
        compile_candidate_profile([primary, conflicting])


def test_identity_conflict_fails_closed(tmp_path: Path) -> None:
    primary = _write(tmp_path / "general.md", RESUME)
    conflicting = _write(
        tmp_path / "conflicting.md",
        SECONDARY.replace("Casey Barton", "Another Person", 1),
    )

    with pytest.raises(CandidateProfileCompileError, match="disagree on candidate identity"):
        compile_candidate_profile([primary, conflicting])


def test_missing_required_evidence_is_rejected(tmp_path: Path) -> None:
    resume = _write(
        tmp_path / "thin.md",
        "# Casey Barton — Engineer\n\n## Summary\n\nA real summary.\n",
    )

    with pytest.raises(CandidateProfileCompileError, match="no structured skills"):
        compile_candidate_profile([resume])


def test_output_contains_no_generated_claim_fields(tmp_path: Path) -> None:
    resume = _write(tmp_path / "resume.md", RESUME)
    payload = compile_candidate_profile([resume])
    rendered = json.dumps(payload)

    assert "world-class" not in rendered
    assert "expert in" not in rendered
    assert "source_text_only_no_claim_invention" in rendered
