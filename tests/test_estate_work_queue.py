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


def test_queue_routes_every_repository_exactly_once() -> None:
    module = _load_module()
    records = [
        _record(0, "priority", "PRIORITY_SPINE"),
        _record(1, "recruiter", "RECRUITER_PORTFOLIO"),
        _record(2, "candidate", "CANDIDATE_EXPANSION"),
        _record(3, "public", "UNGOVERNED_PUBLIC_INVENTORY"),
        _record(
            4,
            "private",
            "PRIVATE_REVIEW_REQUIRED",
            visibility="private",
        ),
        _record(
            5,
            "fork",
            "UPSTREAM_OR_FORK_REVIEW",
            fork=True,
        ),
        _record(
            6,
            "archive",
            "ARCHIVE_BACKUP_OR_FORK",
            visibility="private",
            archived=True,
        ),
    ]

    result = module.build_queue(_receipt(records))

    assert result["coverage_count"] == 7
    assert result["native_work_count"] == 3
    assert result["fork_reference_work_count"] == 1
    assert result["preserve_count"] == 3
    assert [item["lane"] for item in result["native_work_queue"]] == [
        "NATIVE_CANDIDATE_AUDIT",
        "NATIVE_PUBLIC_AUDIT",
        "NATIVE_PRIVATE_AUDIT",
    ]
    assert result["fork_reference_queue"][0]["lane"] == "FORK_REFERENCE_REVIEW"
    assert {item["repository"] for item in result["preserve_queue"]} == {
        "GlacierEQ/priority",
        "GlacierEQ/recruiter",
        "GlacierEQ/archive",
    }


def test_governed_repository_retains_lane_even_when_archived() -> None:
    module = _load_module()
    records = [
        _record(0, "priority-archive", "PRIORITY_SPINE", archived=True),
        _record(
            1,
            "recruiter-archive",
            "RECRUITER_PORTFOLIO",
            archived=True,
        ),
    ]

    result = module.build_queue(_receipt(records))

    assert {item["lane"] for item in result["preserve_queue"]} == {
        "PRESERVE_GOVERNED_PRIORITY",
        "PRESERVE_GOVERNED_RECRUITER",
    }


def test_archived_or_backup_classification_is_preserved_before_fork_review() -> None:
    module = _load_module()
    records = [
        _record(
            0,
            "archived-fork",
            "ARCHIVE_BACKUP_OR_FORK",
            fork=True,
            archived=True,
        )
    ]

    result = module.build_queue(_receipt(records))

    assert result["fork_reference_work_count"] == 0
    assert result["preserve_queue"][0]["lane"] == "PRESERVE_ARCHIVE_BACKUP"


def test_unknown_classification_routes_to_manual_triage() -> None:
    module = _load_module()
    records = [_record(0, "future-class", "FUTURE_CLASSIFICATION")]

    result = module.build_queue(_receipt(records))

    item = result["native_work_queue"][0]
    assert item["lane"] == "MANUAL_TRIAGE"
    assert item["priority"] == 0


def test_queue_fails_closed_when_census_cardinality_does_not_reconcile() -> None:
    module = _load_module()
    receipt = _receipt(
        [_record(0, "public", "UNGOVERNED_PUBLIC_INVENTORY")]
    )
    receipt["native_repository_count"] = 2

    with pytest.raises(module.QueueError, match="native_repository_count"):
        module.build_queue(receipt)


def test_queue_does_not_infer_subject_matter_from_repository_name() -> None:
    module = _load_module()
    records = [
        _record(0, "legal-mcp-super-system", "UNGOVERNED_PUBLIC_INVENTORY")
    ]

    result = module.build_queue(_receipt(records))

    item = result["native_work_queue"][0]
    assert item["lane"] == "NATIVE_PUBLIC_AUDIT"
    assert "legal" not in item["lane"].lower()
    assert "mcp" not in item["lane"].lower()
