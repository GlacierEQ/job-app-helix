from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_estate_work_queue.py"


def _load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("build_estate_work_queue", SCRIPT)
    if spec is None or spec.loader is None:
        raise AssertionError(f"Unable to load {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(spec.name, None)
    return module


def _record(
    position: int,
    name: str,
    classification: str,
    *,
    visibility: str = "public",
    fork: bool = False,
    archived: bool = False,
) -> dict[str, object]:
    return {
        "position": position,
        "repository": f"GlacierEQ/{name}",
        "repository_id": position + 1,
        "visibility": visibility,
        "default_branch": "main",
        "archived": archived,
        "fork": fork,
        "classification": classification,
    }


def _receipt(records: list[dict[str, object]]) -> dict[str, object]:
    native = sum(not bool(record["fork"]) for record in records)
    forks = len(records) - native
    return {
        "schema": "glaciereq.owned-library-census-receipt.v1",
        "owner": "GlacierEQ",
        "repository_count": len(records),
        "native_repository_count": native,
        "fork_repository_count": forks,
        "repositories": records,
    }


def test_queue_routes_every_repository_exactly_once_and_actionable() -> None:
    module = _load_module()
    records = [
        _record(0, "priority", "PRIORITY_SPINE"),
        _record(1, "recruiter", "RECRUITER_PORTFOLIO"),
        _record(2, "candidate", "CANDIDATE_EXPANSION"),
        _record(3, "public", "UNGOVERNED_PUBLIC_INVENTORY"),
        _record(4, "private", "PRIVATE_REVIEW_REQUIRED", visibility="private"),
        _record(5, "fork", "UPSTREAM_OR_FORK_REVIEW", fork=True),
        _record(6, "archive", "ARCHIVE_BACKUP_OR_FORK", visibility="private", archived=True),
    ]

    result = module.build_queue(_receipt(records))

    assert result["schema"] == "glaciereq.crystallization-work-queue.v1"
    assert result["coverage_count"] == 7
    assert result["actionable_count"] == 7
    assert result["exempt_count"] == 0
    assert result["unrouted_count"] == 0
    assert all(item["actionable"] is True for item in result["work_queue"])
    assert {item["repository"] for item in result["work_queue"]} == {
        record["repository"] for record in records
    }


def test_priority_and_recruiter_repositories_are_not_exempt() -> None:
    module = _load_module()
    records = [
        _record(0, "priority", "PRIORITY_SPINE"),
        _record(1, "recruiter", "RECRUITER_PORTFOLIO"),
    ]

    result = module.build_queue(_receipt(records))
    by_repo = {item["repository"]: item for item in result["work_queue"]}

    assert by_repo["GlacierEQ/priority"]["lane"] == "CRYSTALLIZE_PRIORITY"
    assert by_repo["GlacierEQ/recruiter"]["lane"] == "CRYSTALLIZE_RECRUITER"
    assert by_repo["GlacierEQ/priority"]["required_exit"] == "CRYSTALLIZED"
    assert by_repo["GlacierEQ/recruiter"]["required_exit"] == "CRYSTALLIZED"


def test_archive_requires_verification_instead_of_disappearing() -> None:
    module = _load_module()
    result = module.build_queue(
        _receipt([_record(0, "old", "ARCHIVE_BACKUP_OR_FORK", archived=True)])
    )
    item = result["work_queue"][0]

    assert item["lane"] == "VERIFY_ARCHIVE_OR_SUCCESSOR"
    assert item["actionable"] is True
    assert item["required_exit"] == "CRYSTALLIZED_OR_VERIFIED_ARCHIVE_OR_VERIFIED_SUCCESSOR"


def test_fork_requires_delta_or_upstream_verification() -> None:
    module = _load_module()
    result = module.build_queue(
        _receipt([_record(0, "fork", "UPSTREAM_OR_FORK_REVIEW", fork=True)])
    )
    item = result["fork_reference_queue"][0]

    assert item["lane"] == "VERIFY_FORK_DELTA_OR_UPSTREAM"
    assert item["actionable"] is True


def test_unknown_classification_remains_actionable_manual_triage() -> None:
    module = _load_module()
    result = module.build_queue(
        _receipt([_record(0, "future-class", "FUTURE_CLASSIFICATION")])
    )
    item = result["native_work_queue"][0]

    assert item["lane"] == "CRYSTALLIZE_MANUAL_TRIAGE"
    assert item["priority"] == 0
    assert item["actionable"] is True


def test_queue_fails_closed_when_census_cardinality_does_not_reconcile() -> None:
    module = _load_module()
    receipt = _receipt([_record(0, "public", "UNGOVERNED_PUBLIC_INVENTORY")])
    receipt["native_repository_count"] = 2

    with pytest.raises(module.QueueError, match="native_repository_count"):
        module.build_queue(receipt)


def test_queue_does_not_infer_subject_matter_from_repository_name() -> None:
    module = _load_module()
    result = module.build_queue(
        _receipt([_record(0, "legal-mcp-super-system", "UNGOVERNED_PUBLIC_INVENTORY")])
    )
    item = result["native_work_queue"][0]

    assert item["lane"] == "CRYSTALLIZE_NATIVE_PUBLIC"
    assert "legal" not in item["lane"].lower()
    assert "mcp" not in item["lane"].lower()


def test_acceptance_contract_forbids_partial_estate_exit() -> None:
    module = _load_module()
    result = module.build_queue(
        _receipt([_record(0, "public", "UNGOVERNED_PUBLIC_INVENTORY")])
    )

    assert result["acceptance"] == {
        "unknown_allowed": 0,
        "broken_allowed": 0,
        "materially_incomplete_allowed": 0,
        "representative_sampling_allowed": False,
    }
