from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from estate_compiler.common import EstateCompilerError, load_json  # noqa: E402
from estate_compiler.intelligence import load_external_company_intelligence  # noqa: E402
from estate_compiler.projections import _target_relevance  # noqa: E402


def test_external_company_intelligence_replays_47_source_backed_tracks() -> None:
    manifest = load_json(
        ROOT / "manifests/application_intelligence/company_bottleneck_atlas.external.json"
    )
    records = load_external_company_intelligence(ROOT, manifest)

    assert len(records) == 47
    assert "glaciereq_core" not in records
    openai = records["openai"]
    assert openai["observed_current_pressure"]
    assert openai["inferred_bottleneck"]
    assert openai["inference_boundary"]
    assert openai["freshness_state"].startswith("HISTORICAL_SOURCE_SNAPSHOT")
    assert openai["official_sources"][0]["url"].startswith("https://")
    assert len(openai["official_sources"][0]["source_sha256"]) == 64


def test_role_relevance_is_capability_overlap_not_constant() -> None:
    policy = load_json(ROOT / "policies/estate_intelligence_compiler.json")
    role = ["AI Infrastructure Engineer"]
    strong = _target_relevance(
        [
            "distributed_state_and_recovery",
            "infrastructure_diagnostics",
            "permissions_and_fail_closed_control",
            "deterministic_verification",
            "mcp_and_tool_integration",
        ],
        role,
        policy,
    )
    weak = _target_relevance(
        ["document_intelligence"],
        role,
        policy,
    )

    assert strong == 100.0
    assert weak == 0.0
    assert strong > weak


def test_unmapped_role_keeps_relevance_unknown() -> None:
    policy = load_json(ROOT / "policies/estate_intelligence_compiler.json")
    assert _target_relevance(
        ["agent_orchestration"],
        ["Unclassified Specialist 9000"],
        policy,
    ) is None


def test_company_intelligence_rejects_unpinned_source(tmp_path: Path) -> None:
    shard = {
        "records": [
            {
                "company_id": "acme",
                "display_name": "Acme",
                "observed_current_pressure": "Pressure",
                "inferred_bottleneck": "Inference",
                "inferred_brick_wall": "Inference",
                "application_move": "Move",
                "next_deep_dive": "Next",
                "leverage": {
                    "mechanism": "Mechanism",
                    "expected_impact": "Impact",
                },
                "official_sources": [
                    {
                        "title": "Source",
                        "url": "https://example.test/source",
                        "source_sha256": "not-a-hash",
                        "observed_signal": "Observed signal",
                    }
                ],
            }
        ]
    }
    shard_path = tmp_path / "shard.json"
    shard_path.write_text(json.dumps(shard), encoding="utf-8")
    manifest = {
        "schema": "glaciereq.external-company-bottleneck-atlas.v1",
        "record_count": 1,
        "inference_boundary": "Facts and inferences remain distinct.",
        "shards": [{"path": "shard.json", "record_count": 1}],
        "excluded_company_ids": [],
    }

    with pytest.raises(EstateCompilerError, match="source hash"):
        load_external_company_intelligence(tmp_path, manifest)
