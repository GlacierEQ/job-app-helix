from __future__ import annotations

import importlib.util
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


def test_action_queues_reject_missing_repository_identity() -> None:
    module = load_script("aggregate_portfolio_census")

    try:
        module.action_queues(
            [
                {
                    "admission_class": "candidate_public_unresolved_provenance",
                    "provenance": {"state": "UNRESOLVED", "markers": []},
                }
            ]
        )
    except ValueError as exc:
        assert "Missing repository identity" in str(exc)
    else:
        raise AssertionError("Malformed action-queue record did not fail closed")
