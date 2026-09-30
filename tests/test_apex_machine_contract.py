from __future__ import annotations

import copy
import json
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "schemas" / "readme_apex.schema.json").read_text(encoding="utf-8"))
VALIDATOR = jsonschema.Draft202012Validator(SCHEMA)


def valid_contract() -> dict:
    return {
        "schema": "glaciereq.readme.apex.v1",
        "repository": "GlacierEQ/example",
        "human_project_authority": "Casey Barton",
        "apex_source_branch": "main",
        "role": "SPECIALIST_COMPONENT",
        "visibility": "PUBLIC",
        "lineage": {
            "confidence": 0.9,
            "source": "git ancestry receipt",
            "predecessors": [],
            "successors": [],
        },
        "apex_target": {
            "purpose": "maximize coherent system capability",
            "capability": 9,
            "intelligence": 9,
            "reliability": 9,
            "efficiency": 8,
            "leverage": 9,
            "composability": 9,
            "reach": 9,
            "frontier_fitness": 9,
        },
        "current": {
            "proof_state": "VERIFIED",
            "verified_at": "2026-08-16T00:00:00-10:00",
            "exact_head": "a" * 40,
            "receipt": {"path": "receipts/example.json", "sha256": "b" * 64},
        },
        "gap": ["extend the next frontier"],
        "frontier_candidates": [
            {
                "candidate": "specialized runtime",
                "boundary": "kernel_runtime",
                "decision": "EXPERIMENT",
                "advantages": ["higher throughput"],
                "costs": ["interface migration"],
                "evidence": ["benchmark plan"],
            }
        ],
        "lanes": [
            {
                "id": "kernel",
                "concern": "kernel_runtime",
                "technology": "Rust",
                "owner": "runtime",
                "interface": "versioned ABI",
                "proof": "native runtime tests",
                "replacement_trigger": "candidate wins boundary benchmark",
            }
        ],
        "preserved_gains": [
            {
                "capability": "existing recovery behavior",
                "owner": "runtime",
                "status": "PRESERVED",
                "evidence": "tests/recovery",
            }
        ],
        "relationships": [
            {
                "target": "GlacierEQ/the-tower-of-babel",
                "relation": "EVIDENCE_TRACKED_BY",
                "value": "records boundary technology evidence without controlling project intent",
            }
        ],
        "next_apex_turn": "test the strongest non-dominated runtime candidate",
    }


def test_apex_machine_contract_validates_complete_state():
    VALIDATOR.validate(valid_contract())


def test_machine_contract_requires_human_project_authority():
    payload = valid_contract()
    payload["human_project_authority"] = "automation"
    with pytest.raises(jsonschema.ValidationError):
        VALIDATOR.validate(payload)


def test_project_direction_governor_relation_is_not_allowed():
    payload = valid_contract()
    payload["relationships"][0]["relation"] = "GOVERNED_BY"
    with pytest.raises(jsonschema.ValidationError):
        VALIDATOR.validate(payload)


@pytest.mark.parametrize("field", ["verified_at", "exact_head"])
def test_verified_state_requires_concrete_verification_identifiers(field: str):
    payload = valid_contract()
    payload["current"][field] = None
    with pytest.raises(jsonschema.ValidationError):
        VALIDATOR.validate(payload)


def test_unverified_state_may_keep_verification_identifiers_null():
    payload = valid_contract()
    payload["current"]["proof_state"] = "UNVERIFIED"
    payload["current"]["verified_at"] = None
    payload["current"]["exact_head"] = None
    VALIDATOR.validate(payload)


def test_machine_contract_requires_receipt_lineage_lane_owner_and_preservation_status():
    required_paths = [
        ("lineage", "source"),
        ("current", "receipt"),
        ("lanes", 0, "owner"),
        ("preserved_gains", 0, "status"),
        ("frontier_candidates", 0, "decision"),
    ]
    for path in required_paths:
        payload = copy.deepcopy(valid_contract())
        cursor = payload
        for segment in path[:-1]:
            cursor = cursor[segment]
        del cursor[path[-1]]
        with pytest.raises(jsonschema.ValidationError):
            VALIDATOR.validate(payload)


@pytest.mark.parametrize("collection", ["lanes", "preserved_gains", "frontier_candidates"])
def test_required_apex_evidence_collections_cannot_be_empty(collection: str):
    payload = valid_contract()
    payload[collection] = []
    with pytest.raises(jsonschema.ValidationError):
        VALIDATOR.validate(payload)


def test_frontier_candidate_requires_evidence():
    payload = valid_contract()
    payload["frontier_candidates"][0]["evidence"] = []
    with pytest.raises(jsonschema.ValidationError):
        VALIDATOR.validate(payload)


def test_apex_template_points_to_executable_schema_and_machine_json_has_no_governor():
    template = (ROOT / "docs" / "README_APEX_TEMPLATE.md").read_text(encoding="utf-8")
    assert "schemas/readme_apex.schema.json" in template
    machine_section = template.split("## Machine contract", maxsplit=1)[1]
    machine_json = machine_section.split("```json", maxsplit=1)[1].split("```", maxsplit=1)[0]
    assert '"human_project_authority": "Casey Barton"' in machine_json
    assert "GOVERNED_BY" not in machine_json
