from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ELEVATOR = ROOT / "excellence" / "tools" / "elite_estate_elevator.py"


def load_elevator():
    spec = importlib.util.spec_from_file_location("elite_elevator_under_test", ELEVATOR)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_elevator_source_contains_no_hmac_authority_factory() -> None:
    text = ELEVATOR.read_text(encoding="utf-8")
    assert "import hmac" not in text
    assert "def issue_grant" not in text
    assert "_load_promo_auth" not in text
    assert "PromotionAuthority" not in text


def test_continuous_history_uses_projection_truth_not_authority_gate() -> None:
    module = load_elevator()
    state = module.continuous_history(
        "GlacierEQ/example",
        {
            "operable": "operate PASS",
            "proof": "proof receipt PASS",
            "projection_truth": "projection truth closed",
        },
    )
    assert state["principal_state"] == "PROMOTED"
    assert "AUTHORITY_BOUND" not in state["gates"]
    assert state["gates"]["PROJECTION_TRUTH_CLOSED"]["status"] == "PASS"
    assert state["project_direction_authority"] == "OPERATOR"
    assert state["machine_state_creates_project_authority"] is False
    assert state["compatibility_semantics"]["PROMOTED"] == (
        "evidence_bounded_outward_claim_readiness_only"
    )


def test_compatibility_receipt_is_explicitly_non_authoritative() -> None:
    module = load_elevator()
    receipt = module.proof_compatibility_record(
        "GlacierEQ/example",
        "a" * 64,
        "b" * 64,
    )
    assert receipt["status"] == "EVIDENCE_BOUND_NON_AUTHORITATIVE"
    assert receipt["project_direction_authority"] is False
    assert receipt["repository_lifecycle_authority"] is False
    assert receipt["cross_repository_authority"] is False
    assert receipt["proof_receipt_digest"] == "b" * 64
    assert "mac" not in receipt
    assert "secret_ref" not in receipt
