from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = ROOT / "ci_audit_portfolio.py"


def _load_audit_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("ci_audit_portfolio", AUDIT_PATH)
    if spec is None or spec.loader is None:
        raise AssertionError(f"Unable to load {AUDIT_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(spec.name, None)
    return module


def test_portfolio_audit_does_not_claim_portfolio_wide_deployability() -> None:
    source = AUDIT_PATH.read_text(encoding="utf-8")

    assert "100% SOLID & DEPLOYABLE" not in source
    assert '"conclusion": "PARTIALLY_VERIFIED"' in source
    assert "NO PORTFOLIO-WIDE DEPLOYABILITY CLAIM WAS MADE" in source


def test_runtime_verification_scope_is_explicit_and_bounded() -> None:
    module = _load_audit_module()

    repositories = tuple(check.repository for check in module.RUNTIME_CHECKS)
    assert repositories == (
        "spacex-thermal-protection",
        "xai-colossus-cooling",
        "AKOS",
    )


def test_integrity_coverage_is_not_described_as_runtime_verification() -> None:
    source = AUDIT_PATH.read_text(encoding="utf-8")

    assert "Inventory integrity coverage (not runtime verification)" in source
    assert "Integrity coverage and mesh health are not runtime verification" in source
