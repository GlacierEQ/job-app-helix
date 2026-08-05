from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "scripts" / "validate_application_registry.py"


def load_validator_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "application_registry_validator", VALIDATOR_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load validator module: {VALIDATOR_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


VALIDATOR = load_validator_module()
RegistryValidationError = VALIDATOR.RegistryValidationError
validate_registry = VALIDATOR.validate_registry


class ApplicationRegistryTests(unittest.TestCase):
    def fixture_root(self, temporary_directory: str) -> Path:
        root = Path(temporary_directory)
        shutil.copytree(ROOT / "manifests", root / "manifests")
        return root

    def write_json(self, path: Path, payload: dict[str, Any]) -> None:
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def test_zero_omission_registry_gate(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(VALIDATOR_PATH)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        try:
            result = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            self.fail(
                "Validation script output is not valid JSON: "
                f"{exc}\nstdout={completed.stdout!r}\nstderr={completed.stderr!r}"
            )
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["total_inventory_repositories"], 67)
        self.assertEqual(result["helix_children_mapped"], 66)
        self.assertTrue(result["helix_children_exactly_once"])
        self.assertEqual(result["company_tracks"], 48)
        self.assertEqual(result["named_flagships"], 17)
        self.assertEqual(result["external_flagship_repositories"], 9)
        self.assertEqual(result["unresolved_flagships"], 1)
        self.assertEqual(result["inherited_company_dossiers"], 25)
        self.assertGreater(result["l1_private_experiments_documented"], 0)
        self.assertTrue(result["zero_direct_omission_gate"])

    def test_duplicate_workspace_inventory_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = self.fixture_root(temporary_directory)
            path = root / "manifests" / "portfolio_repositories.json"
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["workspace_repositories"].append(
                payload["workspace_repositories"][0]
            )
            payload["total_repositories"] = len(
                payload["workspace_repositories"]
            ) + 1
            self.write_json(path, payload)
            with self.assertRaisesRegex(
                RegistryValidationError, "contains duplicate values"
            ):
                validate_registry(root)

    def test_total_repository_count_mismatch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = self.fixture_root(temporary_directory)
            path = root / "manifests" / "portfolio_repositories.json"
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["total_repositories"] = 999
            self.write_json(path, payload)
            with self.assertRaisesRegex(
                RegistryValidationError, "total_repositories must equal"
            ):
                validate_registry(root)

    def test_wrong_helix_root_repository_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = self.fixture_root(temporary_directory)
            path = root / "manifests" / "flagship_registry.json"
            payload = json.loads(path.read_text(encoding="utf-8"))
            root_record = next(
                record
                for record in payload["flagships"]
                if record["system_id"] == "job_app_helix"
            )
            root_record["repository"] = "GlacierEQ/not-the-helix"
            self.write_json(path, payload)
            with self.assertRaisesRegex(
                RegistryValidationError, "wrong repository"
            ):
                validate_registry(root)

    def test_flagship_level_contract_drift_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = self.fixture_root(temporary_directory)
            path = root / "manifests" / "flagship_registry.json"
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["levels"]["L5"] = "drifted definition"
            self.write_json(path, payload)
            with self.assertRaisesRegex(
                RegistryValidationError, "level definitions drift"
            ):
                validate_registry(root)

    def test_invalid_repository_metadata_enum_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = self.fixture_root(temporary_directory)
            path = root / "manifests" / "company_dossiers" / "frontier_ai.json"
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["companies"][0]["repositories"][0][2] = "NOT_A_STATE"
            self.write_json(path, payload)
            with self.assertRaisesRegex(
                RegistryValidationError, "invalid promotion_state"
            ):
                validate_registry(root)

    def test_defaults_without_inheritance_marker_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = self.fixture_root(temporary_directory)
            path = root / "manifests" / "company_dossiers" / "additional_targets.json"
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload.pop("defaults_apply_to_all_companies")
            self.write_json(path, payload)
            with self.assertRaisesRegex(
                RegistryValidationError, "defines defaults without"
            ):
                validate_registry(root)

    def test_external_flagship_allowlist_drift_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = self.fixture_root(temporary_directory)
            path = root / "manifests" / "flagship_external_repositories.json"
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["verified_owner_estate_external_repositories"].pop()
            self.write_json(path, payload)
            with self.assertRaisesRegex(
                RegistryValidationError, "external flagship repository identity mismatch"
            ):
                validate_registry(root)

    def test_missing_experiment_boundary_note_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = self.fixture_root(temporary_directory)
            path = root / "manifests" / "company_dossiers.json"
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["classification_notes"].pop("l1_private_experiment_boundary")
            self.write_json(path, payload)
            with self.assertRaisesRegex(
                RegistryValidationError, "classification note is required"
            ):
                validate_registry(root)


if __name__ == "__main__":
    unittest.main()
