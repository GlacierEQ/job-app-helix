from __future__ import annotations

from pathlib import Path

import pytest

from job_app_helix.genius_engine import (
    APEX_IDENTITY,
    CRAFT_STANDARD,
    CRAFT_VERB,
    ENGINE_ID,
    EXECUTION_LAW,
    MASTER_GRADE_FLOOR,
    GeniusEngineError,
    GeniusSolution,
    attack_solution,
    build_solution,
    compose_advance_brief,
    invent,
    invent_estate,
    invent_restoration,
    novelty_score,
    render_markdown,
    select_mechanisms,
)
from job_app_helix.genius_research import (
    ResearchDossier,
    accumulate_knowledge,
    publish_library_link,
    research_subject,
)


def _offline_invent(repo: str, tmp_path: Path, **extra):
    subject = {"repository": repo, **extra}
    return invent(
        subject,
        limit=3,
        include_atlas_seeds=False,
        root=tmp_path,
        live_research=False,
        accumulate=True,
        publish_links=False,
    )


def test_invent_produces_scored_primary(tmp_path: Path) -> None:
    run = _offline_invent(
        "GlacierEQ/spacex-telemetry",
        tmp_path,
        neutralization_stamps=2,
        paper_recovery_only=True,
        description="SpaceX-style telemetry plane",
        language="Go",
    )
    assert run.engine_id == ENGINE_ID
    assert ENGINE_ID.endswith("v3")
    assert run.identity == APEX_IDENTITY
    assert run.law == EXECUTION_LAW
    assert run.craft == CRAFT_STANDARD
    assert CRAFT_VERB == "ENGINEERED"
    assert run.research
    assert "signals" in run.research
    assert run.primary is not None
    assert run.primary.genius_score >= MASTER_GRADE_FLOOR
    assert not run.primary.missing_fields()
    assert run.primary.is_engineered()
    assert run.receipt_sha256
    assert "spacex-telemetry" in run.primary.problem.lower() or "telemetry" in run.primary.problem.lower()
    assert "Module:" in run.primary.implementation
    assert "tests/" in run.primary.measurement or "test" in run.primary.measurement.lower()
    assert run.advance_brief and run.advance_brief.get("status") == "READY"
    assert run.knowledge_path
    ok, blockers = attack_solution(run.primary)
    assert ok, blockers


def test_restore_mode_flags_neutralization_problem(tmp_path: Path) -> None:
    run = invent_restoration(
        {"repository": "GlacierEQ/glaciereq-mcp-stack", "description": "MCP provider stack"},
        limit=2,
        root=tmp_path,
        live_research=False,
        publish_links=False,
    )
    assert run.primary is not None
    assert "reduced" in run.primary.problem.lower() or "capability" in run.primary.problem.lower()
    md = render_markdown(run)
    assert "Genius Engine Run" in md
    assert "Research signals" in md


def test_estate_ranks_multiple(tmp_path: Path) -> None:
    out = invent_estate(
        [
            {
                "repository": "GlacierEQ/spacex-mission-control",
                "paper_recovery_only": True,
                "description": "mission control",
            },
            {
                "repository": "GlacierEQ/xai-colossus-cooling",
                "description": "thermal cooling control",
                "language": "Python",
            },
        ],
        limit_per=1,
        live_research=False,
        accumulate=True,
        publish_links=False,
    )
    # invent_estate doesn't take root — uses repository_root; accumulate still ok
    assert out["count"] == 2
    assert out["runs"][0]["primary"] is not None
    assert out["engine_id"].endswith("v3")


def test_empty_subject_refuses() -> None:
    try:
        invent({})
    except GeniusEngineError:
        return
    raise AssertionError("expected GeniusEngineError")


def test_attack_rejects_theater() -> None:
    sol = GeniusSolution(
        solution_id="x",
        title="bad",
        problem="todo later",
        cause="tbd",
        mechanism="coming soon wrapper only rename only",
        implementation="as needed",
        measurement="tbd",
        failure_mode="tbd",
        boundary="tbd",
        value="tbd",
        genius_score=0.9,
    )
    ok, blockers = attack_solution(sol)
    assert not ok
    assert any("theater" in b or "shallow" in b or "incomplete" in b for b in blockers)


def test_attack_rejects_paralysis() -> None:
    sol = GeniusSolution(
        solution_id="y",
        title="freeze",
        problem="real bottleneck at scale needs a mechanism",
        cause="governance freeze treated unfinished ambition as defect permanently",
        mechanism="Wait for approval before implementing full restore path with receipts",
        implementation="defer implement until cannot ship until fully verified forever",
        measurement="paper only forever checklist",
        failure_mode="shrink product until green",
        boundary="mvp amputation allowed",
        value="reports over power",
        genius_score=0.9,
    )
    ok, blockers = attack_solution(sol)
    assert not ok
    assert any("paralysis" in b for b in blockers)


def test_unknown_leaf_not_anti_neutralization(tmp_path: Path) -> None:
    run = _offline_invent("GlacierEQ/unknown-random-leaf-xyz", tmp_path)
    assert run.primary is not None
    mech_id = run.primary.tags[0] if run.primary.tags else ""
    assert mech_id != "anti_neutralization_gate"
    assert mech_id in {
        "engineered_first_class",
        "first_pass_last_pass",
        "bravery_with_governance",
    }
    assert "unknown" in " ".join(run.research.get("signals") or [])


def test_leaf_native_paths_differ(tmp_path: Path) -> None:
    a = _offline_invent(
        "GlacierEQ/spacex-telemetry",
        tmp_path,
        description="telemetry stream",
        language="Go",
    )
    b = _offline_invent(
        "GlacierEQ/xai-colossus-cooling",
        tmp_path,
        description="thermal cooling plant",
        language="Python",
    )
    assert a.primary and b.primary
    assert a.primary.implementation != b.primary.implementation
    assert "spacex_telemetry" in a.primary.implementation or "spacex-telemetry" in a.primary.implementation
    assert "colossus" in b.primary.implementation.lower() or "cooling" in b.primary.implementation.lower()


def test_score_does_not_self_bonus_template_adjectives() -> None:
    weak = GeniusSolution(
        solution_id="w",
        title="weak",
        problem="generic issue",
        cause="generic cause",
        mechanism="Something vague without domain pattern words here at all",
        implementation="ENGINEERED complete born-to-run first-pass pro elite humanized dual-plane MAXIMUM_COHERENT_ADVANCE",
        measurement="tests",
        failure_mode="fail closed",
        boundary="no false affiliation",
        value="power",
        repository="GlacierEQ/x",
        domain="general",
    )
    n = novelty_score(weak, {"repository": "GlacierEQ/x"})
    # implementation craft adjectives must not dominate novelty
    assert n < 0.7


def test_receipt_deterministic(tmp_path: Path) -> None:
    kwargs = dict(
        limit=2,
        include_atlas_seeds=False,
        root=tmp_path,
        live_research=False,
        accumulate=False,
        publish_links=False,
    )
    s = {
        "repository": "GlacierEQ/spacex-telemetry",
        "description": "telemetry",
        "paper_recovery_only": True,
        "neutralization_stamps": 2,
    }
    r1 = invent(s, **kwargs)
    r2 = invent(s, **kwargs)
    assert r1.receipt_sha256 == r2.receipt_sha256


def test_research_accumulates_knowledge(tmp_path: Path) -> None:
    dossier = research_subject(
        {
            "repository": "GlacierEQ/megamind",
            "description": "agent registry mesh",
            "language": "Python",
            "offline": True,
        },
        helix_root=tmp_path,
        live=False,
    )
    assert dossier.schema.startswith("glaciereq.genius-research")
    assert dossier.lite_facts
    path = accumulate_knowledge(
        dossier,
        helix_root=tmp_path,
        primary={"title": "t", "tags": ["authority_half_life"], "genius_score": 0.8},
        receipt_sha256="abc",
    )
    assert path.is_file()
    index = tmp_path / "machine" / "genius_knowledge" / "index.json"
    assert index.is_file()


def test_publish_library_link(tmp_path: Path) -> None:
    dossier = research_subject(
        {
            "repository": "GlacierEQ/the-tower-of-babel",
            "description": "polyglot tower",
            "topics": ["polyglot"],
            "offline": True,
        },
        helix_root=tmp_path,
        live=False,
    )
    out = publish_library_link(
        dossier,
        primary={"title": "First Pass", "tags": ["first_pass_last_pass"]},
        receipt_sha256="deadbeef",
        library_root=tmp_path / "library-of-links",
    )
    assert out is not None and out.is_file()
    assert (tmp_path / "library-of-links" / "registry" / "index.json").is_file()
    assert (tmp_path / "library-of-links" / "README.md").is_file()


def test_select_mechanisms_signal_bias() -> None:
    dossier = ResearchDossier(
        schema="glaciereq.genius-research.v1",
        repository="GlacierEQ/xai-colossus-cooling",
        full_name="GlacierEQ/xai-colossus-cooling",
        description="cooling",
        primary_language="Python",
        languages={},
        topics=(),
        readme_excerpt="",
        default_branch="main",
        exists=True,
        signals=("thermal_energy",),
        lite_facts=("signal:thermal_energy",),
        prior_run_count=0,
        prior_primary_mechanism="",
        sources=("test",),
        researched_at="2026-01-01T00:00:00+00:00",
    )
    mechs = select_mechanisms("colossus", limit=3, research=dossier)
    ids = [m.id for m in mechs]
    assert "receipt_bus" in ids or "split_brain_actuation" in ids


def test_advance_brief_paths(tmp_path: Path) -> None:
    run = _offline_invent(
        "GlacierEQ/orbital-mechanics",
        tmp_path,
        description="lambert solver",
        language="Python",
        domain="orbital",
    )
    brief = compose_advance_brief(run)
    assert brief["status"] == "READY"
    assert brief["paths"]
