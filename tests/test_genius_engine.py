from __future__ import annotations

from job_app_helix.genius_engine import (
    APEX_IDENTITY,
    CRAFT_STANDARD,
    CRAFT_VERB,
    EXECUTION_LAW,
    MASTER_GRADE_FLOOR,
    GeniusEngineError,
    attack_solution,
    invent,
    invent_estate,
    invent_restoration,
    render_markdown,
)


def test_invent_produces_scored_primary() -> None:
    run = invent(
        {
            "repository": "GlacierEQ/spacex-telemetry",
            "neutralization_stamps": 2,
            "paper_recovery_only": True,
        },
        limit=3,
        include_atlas_seeds=False,
    )
    assert run.engine_id.startswith("glaciereq.genius-engine")
    assert run.identity == APEX_IDENTITY
    assert run.law == EXECUTION_LAW
    assert run.craft == CRAFT_STANDARD
    assert CRAFT_VERB == "ENGINEERED"
    assert "ENGINEERED" in run.craft
    assert "FIRST_PASS_IS_LAST_PASS" in run.craft
    assert "GOVERNANCE_BALANCED_WITH_BRAVERY" in run.craft
    assert run.primary is not None
    assert run.primary.genius_score >= MASTER_GRADE_FLOOR
    assert not run.primary.missing_fields()
    assert run.primary.is_engineered()
    assert run.receipt_sha256
    assert "engineer" in run.primary.implementation.lower()
    ok, blockers = attack_solution(run.primary)
    assert ok, blockers


def test_restore_mode_flags_neutralization_problem() -> None:
    run = invent_restoration({"repository": "GlacierEQ/glaciereq-mcp-stack"}, limit=2)
    assert run.primary is not None
    assert "reduced" in run.primary.problem.lower() or "capability" in run.primary.problem.lower()
    md = render_markdown(run)
    assert "Genius Engine Run" in md
    assert run.primary.title.split()[0]


def test_estate_ranks_multiple() -> None:
    out = invent_estate(
        [
            {"repository": "GlacierEQ/spacex-mission-control", "paper_recovery_only": True},
            {"repository": "GlacierEQ/xai-colossus-cooling"},
        ],
        limit_per=1,
    )
    assert out["count"] == 2
    assert out["runs"][0]["primary"] is not None


def test_empty_subject_refuses() -> None:
    try:
        invent({})
        assert False, "expected error"
    except GeniusEngineError:
        pass
