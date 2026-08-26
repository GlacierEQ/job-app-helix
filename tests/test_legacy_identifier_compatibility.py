from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "LEGACY_IDENTIFIER_COMPATIBILITY.md"
VALIDATOR = ROOT / "scripts" / "validate_application_registry.py"


def load_validator():
    spec = importlib.util.spec_from_file_location("registry_validator", VALIDATOR)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load registry validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class LegacyIdentifierCompatibilityTests(unittest.TestCase):
    def test_ledger_covers_all_retained_legacy_identifier_consumers(self) -> None:
        ledger = DOC.read_text(encoding="utf-8")
        for path in (
            "manifests/flagship_registry.json",
            "src/job_app_helix/estate_compiler.py",
            "scripts/audit_live_portfolio_freshness.py",
            "scripts/compile_estate_graph.py",
            "scripts/discover_experience_graph.py",
            "scripts/validate_application_registry.py",
            "scripts/validate_portfolio_root_truth.py",
            "tests/test_application_registry.py",
            "tests/test_estate_capability_discovery.py",
            "tests/test_estate_compiler.py",
            "tests/test_estate_intelligence.py",
            "tests/test_experience_graph_discovery.py",
            "tests/test_live_portfolio_freshness.py",
            "tests/test_portfolio_root_truth.py",
        ):
            self.assertIn(path, ledger)

    def test_registry_validation_reports_dynamic_system_cardinality(self) -> None:
        result = load_validator().validate_registry(ROOT)
        self.assertGreater(result["named_systems"], 0)
        self.assertNotIn("named_flagships", result)

    def test_registry_validator_does_not_encode_static_inventory_totals(self) -> None:
        source = VALIDATOR.read_text(encoding="utf-8")
        self.assertNotIn("exactly 66", source)
        self.assertNotIn("!= 66", source)


if __name__ == "__main__":
    unittest.main()
