from job_app_helix.p0_builds import (
    P0_IDS,
    agent_relationship_graph_firewall,
    nondeterminism_envelope,
    optimization_safety_envelope,
    patch_intent_twin,
    persistent_world_state_compiler,
    typed_agent_capability_graph,
    verify_reference_builds,
)


def test_all_25_reference_builds_verify() -> None:
    receipt = verify_reference_builds()
    assert receipt["status"] == "PASS"
    assert receipt["verified_count"] == 25
    assert receipt["expected_count"] == 25
    assert receipt["failed"] == []
    assert tuple(receipt["checks"]) == P0_IDS
    assert all(receipt["checks"].values())


def test_patch_intent_twin_rejects_forbidden_touch() -> None:
    result = patch_intent_twin({"src/core.py"}, {"secrets.env"}, {"src/core.py", "secrets.env"}, {"unit"}, {"unit"})
    assert result["aligned"] is False
    assert result["forbidden_touches"] == ["secrets.env"]


def test_typed_agent_graph_rejects_authority_escalation() -> None:
    result = typed_agent_capability_graph(
        {
            "reader": {"authority": 1, "retryable": False, "idempotent": True},
            "admin": {"authority": 3, "retryable": False, "idempotent": True},
        },
        [("reader", "admin")],
    )
    assert result["valid"] is False
    assert result["violations"] == ["authority-escalation:reader->admin"]


def test_relationship_firewall_blocks_sensitive_path_expansion() -> None:
    result = agent_relationship_graph_firewall(
        [("agent", "tool")],
        ("agent", "payroll"),
        {"payroll"},
    )
    assert result["allowed"] is False
    assert result["sensitive_expansion"] == ["payroll"]


def test_nondeterminism_envelope_rejects_state_changing_drift() -> None:
    result = nondeterminism_envelope(
        {
            "required_keys": ["status", "score"],
            "immutable": {"status": "ok"},
            "numeric_ranges": {"score": (0.8, 1.0)},
        },
        {"status": "error", "score": 0.91},
    )
    assert result["equivalent"] is False
    assert result["reasons"] == ["immutable-drift:status"]


def test_optimization_safety_envelope_rejects_excess_quality_drift() -> None:
    result = optimization_safety_envelope(0.95, 0.90, 100, 50, 0.01)
    assert result["accepted"] is False


def test_world_state_compiler_rejects_identity_conflict() -> None:
    result = persistent_world_state_compiler(
        [
            {"object_id": "o1", "timestamp": 1, "state": {"identity": "box", "x": 0}},
            {"object_id": "o1", "timestamp": 2, "state": {"identity": "sphere", "x": 1}},
        ]
    )
    assert result["consistent"] is False
    assert result["conflicts"] == ["o1"]
