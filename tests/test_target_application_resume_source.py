from __future__ import annotations

import json
from pathlib import Path

import pytest

from job_app_helix.target_application_cycle import (
    COMPILED_PROFILE_FILENAME,
    ApplicationReadinessError,
    resolve_candidate_profile,
)


def _resume(path: Path, *, name: str = "Casey Barton", project_suffix: str = "") -> Path:
    path.write_text(
        "\n".join(
            [
                f"# {name} - Systems Architect",
                "**Email**: casey@example.com | **Location**: Honolulu, HI",
                "",
                "## Summary",
                "Systems architect building production automation and intelligence systems.",
                "",
                "## Core Competencies",
                "| Domain | Skills |",
                "| --- | --- |",
                "| Engineering | Python, TypeScript, SQL |",
                "",
                "## Key Projects",
                f"### Helix{project_suffix}",
                "- Built an attributable job intelligence pipeline across 4 ATS providers.",
                "- Reduced stale recruiter packet rebuilds with field-sensitive change detection.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def test_resume_native_resolution_persists_provenance_bound_profile(tmp_path: Path) -> None:
    resume = _resume(tmp_path / "RESUME.md")
    state_dir = tmp_path / "state"

    profile = resolve_candidate_profile(
        profile_path=None,
        resume_paths=(resume,),
        state_dir=state_dir,
        profile_id="casey-production",
    )

    assert profile.profile_id == "casey-production"
    assert profile.name == "Casey Barton"
    assert "Python" in profile.skills

    compiled = json.loads((state_dir / COMPILED_PROFILE_FILENAME).read_text(encoding="utf-8"))
    assert compiled["profile_id"] == "casey-production"
    assert compiled["provenance"]["policy"] == "source_text_only_no_claim_invention"
    sources = compiled["provenance"]["sources"]
    assert len(sources) == 1
    assert sources[0]["path"] == str(resume.resolve())
    assert len(sources[0]["sha256"]) == 64


def test_resume_native_resolution_composes_specialized_resume_evidence(tmp_path: Path) -> None:
    primary = _resume(tmp_path / "RESUME_GENERAL.md")
    specialist = _resume(tmp_path / "RESUME_SPECIALIST.md", project_suffix=" Specialist")

    profile = resolve_candidate_profile(
        profile_path=None,
        resume_paths=(primary, specialist),
        state_dir=tmp_path / "state",
    )

    assert len(profile.experience) == 4
    assert any("Helix Specialist" in item for item in profile.experience)


def test_static_profile_path_remains_supported_without_compilation(tmp_path: Path) -> None:
    profile_path = tmp_path / "profile.json"
    profile_path.write_text(
        json.dumps(
            {
                "profile_id": "existing-profile",
                "name": "Casey Barton",
                "headline": "Systems Architect",
                "summary": "Production systems engineering.",
                "skills": ["Python"],
                "experience": ["Built job intelligence systems."],
                "achievements": ["Shipped production automation."],
            }
        ),
        encoding="utf-8",
    )
    state_dir = tmp_path / "state"

    profile = resolve_candidate_profile(
        profile_path=profile_path,
        resume_paths=(),
        state_dir=state_dir,
    )

    assert profile.profile_id == "existing-profile"
    assert not (state_dir / COMPILED_PROFILE_FILENAME).exists()


def test_candidate_source_is_exclusive_and_required(tmp_path: Path) -> None:
    resume = _resume(tmp_path / "RESUME.md")
    profile_path = tmp_path / "profile.json"
    profile_path.write_text("{}", encoding="utf-8")

    with pytest.raises(ApplicationReadinessError, match="either --profile or --resume"):
        resolve_candidate_profile(
            profile_path=profile_path,
            resume_paths=(resume,),
            state_dir=tmp_path / "state",
        )

    with pytest.raises(ApplicationReadinessError, match="requires --profile or --resume"):
        resolve_candidate_profile(
            profile_path=None,
            resume_paths=(),
            state_dir=tmp_path / "state",
        )


def test_resume_compile_failure_is_translated_to_application_error(tmp_path: Path) -> None:
    broken = tmp_path / "BROKEN.md"
    broken.write_text("# Casey Barton - Systems Architect\n", encoding="utf-8")

    with pytest.raises(ApplicationReadinessError, match="candidate resume compilation failed"):
        resolve_candidate_profile(
            profile_path=None,
            resume_paths=(broken,),
            state_dir=tmp_path / "state",
        )
