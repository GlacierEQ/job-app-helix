from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "manifests/application_intelligence/p0_innovation_semantic_audit_2026-08-11.json"
QUEUE = ROOT / "manifests/application_intelligence/company_innovation_execution_queue.v1.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_semantic_audit_covers_exact_p0_queue_in_order() -> None:
    audit = load(AUDIT)
    queue = load(QUEUE)
    assert audit["summary"]["count"] == queue["count"] == 25
    assert [item["company_id"] for item in audit["items"]] == [
        item["company_id"] for item in queue["queue"]
    ]
    assert [item["rank"] for item in audit["items"]] == list(range(1, 26))


def test_semantic_audit_counts_are_fail_closed() -> None:
    audit = load(AUDIT)
    counts: dict[str, int] = {}
    for item in audit["items"]:
        counts[item["verdict"]] = counts.get(item["verdict"], 0) + 1
    assert counts == {
        "ALIGNED_REFERENCE": 7,
        "PARTIAL_REFERENCE": 10,
        "REPAIR_REQUIRED": 8,
    }
    assert audit["summary"]["semantic_gate"] == "FAIL"
    assert audit["summary"]["ALIGNED_REFERENCE"] == 7
    assert audit["summary"]["PARTIAL_REFERENCE"] == 10
    assert audit["summary"]["REPAIR_REQUIRED"] == 8


def test_build_success_is_not_semantic_verification() -> None:
    audit = load(AUDIT)
    boundary = audit["truth_boundary"]
    assert boundary["prior_25_of_25_build_receipt_remains_valid_for_execution"] is True
    assert boundary["execution_success_does_not_prove_semantic_correctness"] is True
    promotion_key = "partial_or_repair_required_items_must_not_be_promoted_as_semantically_verified"
    assert boundary[promotion_key] is True
    assert sum(item["verdict"] == "ALIGNED_REFERENCE" for item in audit["items"]) < 25


def test_every_non_aligned_item_has_a_concrete_repair() -> None:
    audit = load(AUDIT)
    non_aligned = [item for item in audit["items"] if item["verdict"] != "ALIGNED_REFERENCE"]
    assert len(non_aligned) == 18
    assert all(item.get("repair") for item in non_aligned)
