from __future__ import annotations

import json
from pathlib import Path

import pytest

from job_app_helix.prime_counter_build import build, render_case


def _case(slug: str) -> dict[str, object]:
    return {
        "slug": slug,
        "employer": "Sample Company",
        "role": "Principal Engineering",
        "role_status": "ACTIVE_OFFICIAL",
        "role_url": "https://example.org/jobs/principal",
        "portfolio_url": "https://example.org/portfolio",
        "recruiter_hook": "Built typed tool workflows with durable receipts.",
        "technical_argument": "Identity and readback clarify retry behavior and ambiguous effects.",
        "business_consequence": "Reduce uncertainty during incident diagnosis.",
        "direct_proofs": [
            {"mechanism": "Typed workflows", "source": "https://github.com/GlacierEQ/job-app-helix"},
            {"mechanism": "Durable execution", "source": "https://github.com/GlacierEQ/ECHO"},
        ],
        "transferable": "Independent implementation, not employer production experience.",
        "proposed": "Run a fault-injection trace with a simulated lost acknowledgment.",
        "objection_hypothesis": "Founder role title may be misread.",
        "counter_hypothesis": "Source-grounded evidence enables a real technical conversation.",
        "technical_challenge": "What happens after a write timeout?",
        "defensible_response": "Inspect provider state and preserve ambiguity until confirmed.",
        "next_move": "Discuss an inspectable runtime trace.",
        "constraint": "No submission or human response has been verified.",
    }


def test_five_counter_builds_are_deterministic_and_distinguish_evidence(tmp_path: Path) -> None:
    manifest = tmp_path / "private_manifest.json"
    cases = [_case(f"prime-{i}") for i in range(5)]
    cases[-1]["role_status"] = "STALE_REVALIDATE"
    manifest.write_text(
        json.dumps({"schema": "glaciereq.prime-counter-builds.v1", "cases": cases}),
        encoding="utf-8",
    )
    output = tmp_path / "output"
    receipt = build(manifest, output)
    assert len(receipt["cases"]) == 5
    assert receipt["status"] == "BRIEFS_GENERATED_NOT_SENT"
    for case in receipt["cases"]:
        content = (output / case["file"]).read_text(encoding="utf-8")
        assert "Direct implementation" in content
        assert "Transferable, not employer production experience" in content
        assert "Proposed, not yet deployed at employer" in content
        assert "Counter-hypothesis" in content
        assert "No application, send, employer acknowledgment" in content
    assert "STALE_REVALIDATE" in (output / "prime-4.md").read_text()
    second = build(manifest, output)
    assert second == receipt
    assert json.loads((output / "BUILD_RECEIPT.json").read_text()) == receipt


def test_rejects_untraceable_or_unsafe_source_claims() -> None:
    case = _case("prime")
    proof = case["direct_proofs"]
    assert isinstance(proof, list)
    proof[0]["source"] = "http://example.com/claim"
    with pytest.raises(ValueError, match="HTTPS"):
        render_case(case)


def test_rejects_unknown_role_status() -> None:
    case = _case("prime")
    case["role_status"] = "SUBMITTED"
    with pytest.raises(ValueError, match="role status"):
        render_case(case)
