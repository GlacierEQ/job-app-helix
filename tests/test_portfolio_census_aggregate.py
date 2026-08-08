from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]


def load_script(name: str) -> ModuleType:
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"Unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_receipt(
    directory: Path,
    slug: str,
    repository: str,
    *,
    admission: str,
    provenance: str,
    verification: str = "NO_TEST_PATH",
    schema: str = "glaciereq.portfolio.audit.v2",
) -> None:
    payload = {
        "schema": schema,
        "repository": repository,
        "admission_class": admission,
        "provenance": {"state": provenance, "markers": []},
        "verification": {"python": {"status": verification}},
    }
    (directory / f"census-{slug}.json").write_text(
        json.dumps(payload),
        encoding="utf-8",
    )


def inventory() -> dict[str, object]:
    return {
        "owner": "GlacierEQ",
        "portfolio_root": "job-app-helix",
        "total_repositories": 3,
        "workspace_repositories": ["alpha", "downstream"],
    }


def test_aggregate_reconciles_exact_inventory_and_action_queues(
    tmp_path: Path,
) -> None:
    module = load_script("aggregate_portfolio_census")
    write_receipt(tmp_path,"job-app-helix","GlacierEQ/job-app-helix",admission="candidate_public_unresolved_provenance",provenance="UNRESOLVED",verification="VERIFIED")
    write_receipt(tmp_path,"alpha","GlacierEQ/alpha",admission="candidate_public_unresolved_provenance",provenance="UNRESOLVED",verification="FAILED")
    write_receipt(tmp_path,"downstream","GlacierEQ/downstream",admission="candidate_attributed_downstream",provenance="EXPLICIT_DOWNSTREAM",verification="BLOCKED_DEPENDENCY")
    summary = module.build_summary(tmp_path, inventory())
    assert summary["schema"] == "glaciereq.portfolio.census.summary.v1"
    assert summary["declared_repository_count"] == 3
    assert summary["expected_repository_count"] == 3
    assert summary["workspace_repository_count"] == 2
    assert summary["coverage"]["complete"] is True
    assert summary["workspace"]["admission_classes"] == {"candidate_attributed_downstream": 1,"candidate_public_unresolved_provenance": 1}
    assert summary["workspace"]["provenance_states"] == {"EXPLICIT_DOWNSTREAM": 1,"UNRESOLVED": 1}
    assert summary["workspace"]["python_verification_states"] == {"BLOCKED_DEPENDENCY": 1,"FAILED": 1}
    queues = summary["workspace"]["action_queues"]
    assert queues["provenance_review"] == ["GlacierEQ/alpha"]
    assert queues["attributed_downstream_review"] == ["GlacierEQ/downstream"]
    assert queues["verification_failed"] == ["GlacierEQ/alpha"]
    assert queues["verification_dependency_blocked"] == ["GlacierEQ/downstream"]
    assert queues["verification_no_test_path"] == []


def test_inventory_declared_total_must_match_root_plus_workspace() -> None:
    module = load_script("aggregate_portfolio_census")
    bad_inventory = inventory(); bad_inventory["total_repositories"] = 4
    try: module.expected_repositories(bad_inventory)
    except ValueError as exc:
        assert "total_repositories" in str(exc); assert "declared=4 calculated=3" in str(exc)
    else: raise AssertionError("Mismatched declared repository total did not fail closed")


def test_inventory_rejects_empty_workspace() -> None:
    module = load_script("aggregate_portfolio_census")
    bad_inventory = inventory(); bad_inventory["total_repositories"] = 1; bad_inventory["workspace_repositories"] = []
    try: module.expected_repositories(bad_inventory)
    except ValueError as exc: assert "workspace_repositories" in str(exc)
    else: raise AssertionError("Empty canonical workspace did not fail closed")


def test_aggregate_fails_on_missing_expected_receipt(tmp_path: Path) -> None:
    module = load_script("aggregate_portfolio_census")
    write_receipt(tmp_path,"job-app-helix","GlacierEQ/job-app-helix",admission="candidate_public_unresolved_provenance",provenance="UNRESOLVED")
    write_receipt(tmp_path,"alpha","GlacierEQ/alpha",admission="candidate_public_unresolved_provenance",provenance="UNRESOLVED")
    try: module.build_summary(tmp_path, inventory())
    except ValueError as exc: assert "GlacierEQ/downstream" in str(exc)
    else: raise AssertionError("Missing census receipt did not fail closed")


def test_aggregate_fails_on_duplicate_repository_receipt(tmp_path: Path) -> None:
    module = load_script("aggregate_portfolio_census")
    write_receipt(tmp_path,"job-app-helix","GlacierEQ/job-app-helix",admission="candidate_public_unresolved_provenance",provenance="UNRESOLVED")
    write_receipt(tmp_path,"alpha","GlacierEQ/alpha",admission="candidate_public_unresolved_provenance",provenance="UNRESOLVED")
    write_receipt(tmp_path,"alpha-copy","GlacierEQ/alpha",admission="candidate_public_unresolved_provenance",provenance="UNRESOLVED")
    write_receipt(tmp_path,"downstream","GlacierEQ/downstream",admission="candidate_attributed_downstream",provenance="EXPLICIT_DOWNSTREAM")
    try: module.build_summary(tmp_path, inventory())
    except ValueError as exc: assert "Duplicate census receipt" in str(exc)
    else: raise AssertionError("Duplicate census receipt did not fail closed")


def test_aggregate_rejects_legacy_audit_schema(tmp_path: Path) -> None:
    module = load_script("aggregate_portfolio_census")
    write_receipt(tmp_path,"job-app-helix","GlacierEQ/job-app-helix",admission="candidate_public_unresolved_provenance",provenance="UNRESOLVED",schema="glaciereq.portfolio.audit.v1")
    try: module.build_summary(tmp_path, inventory())
    except ValueError as exc: assert "Unexpected census schema" in str(exc)
    else: raise AssertionError("Legacy census schema did not fail closed")
