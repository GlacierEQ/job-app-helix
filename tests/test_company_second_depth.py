from __future__ import annotations

import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from types import ModuleType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "scripts" / "validate_company_second_depth.py"


def load_validator_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "company_second_depth_validator", VALIDATOR_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load validator module: {VALIDATOR_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


VALIDATOR = load_validator_module()
SecondDepthValidationError = VALIDATOR.SecondDepthValidationError
validate_second_depth = VALIDATOR.validate_second_depth


class CompanySecondDepthTests(unittest.TestCase):
    def fixture_root(self, temporary_directory: str) -> Path:
        root = Path(temporary_directory)
        shutil.copytree(ROOT / "manifests", root / "manifests")
        return root

    def write_json(self, path: Path, payload: dict[str, Any]) -> None:
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def test_current_registry_is_fail_closed_and_complete(self) -> None:
        result = validate_second_depth(ROOT)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["company_tracks"], 49)
        self.assertEqual(result["stage_count"], 8)
        self.assertEqual(result["priority_wave"], 8)
        self.assertEqual(result["stage_counts"]["MAPPED_ONLY"], 49)
        self.assertEqual(sum(result["stage_counts"].values()), 49)
        self.assertTrue(result["claim_promotion_requires_receipt"])
        self.assertTrue(result["zero_implicit_completion"])

    def test_lockheed_is_truth_bounded_scaffold_without_repository_proof(self) -> None:
        dossier_path = ROOT / "manifests" / "company_dossiers" / "additional_targets.json"
        dossier = json.loads(dossier_path.read_text(encoding="utf-8"))
        lockheed = next(
            company
            for company in dossier["companies"]
            if company["company_id"] == "lockheed_martin"
        )
        self.assertEqual(lockheed["display_name"], "Lockheed Martin")
        self.assertEqual(lockheed["repositories"], [])
        self.assertIn("no Lockheed Martin affiliation", lockheed["non_affiliation"])
        self.assertIn("No Lockheed Martin-named repository", lockheed["gap_or_next_gate"])

        second_depth = json.loads(
            (ROOT / "manifests" / "company_second_depth.json").read_text(
                encoding="utf-8"
            )
        )
        defaults = second_depth["default_company_state"]
        override = second_depth["company_overrides"]["lockheed_martin"]
        resolved = {**defaults, **override}
        self.assertEqual(resolved["stage"], "MAPPED_ONLY")
        self.assertEqual(resolved["claim_ceiling"], "company_alignment_only")
        self.assertEqual(resolved["role_evidence"], [])
        self.assertEqual(resolved["problem_evidence"], [])
        self.assertEqual(resolved["inspected_repositories"], [])
        self.assertIn("no_direct_company_repository_verified", resolved["blockers"])

    def test_role_verified_cannot_be_claimed_without_role_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = self.fixture_root(temporary_directory)
            path = root / "manifests" / "company_second_depth.json"
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["company_overrides"]["openai"].update(
                {
                    "stage": "ROLE_VERIFIED",
                    "claim_ceiling": "verified_role_alignment",
                }
            )
            self.write_json(path, payload)
            with self.assertRaisesRegex(
                SecondDepthValidationError,
                "ROLE_VERIFIED requires non-empty role_evidence",
            ):
                validate_second_depth(root)

    def test_proof_artifacts_cannot_appear_at_mapping_stage(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = self.fixture_root(temporary_directory)
            path = root / "manifests" / "company_second_depth.json"
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["company_overrides"]["openai"]["proof_artifacts"] = [
                "unsupported-proof"
            ]
            self.write_json(path, payload)
            with self.assertRaisesRegex(
                SecondDepthValidationError,
                "proof artifacts cannot precede PROOF_REPRODUCED",
            ):
                validate_second_depth(root)

    def test_unknown_company_override_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = self.fixture_root(temporary_directory)
            path = root / "manifests" / "company_second_depth.json"
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["company_overrides"]["invented_company"] = {
                "next_gate": "This must never be accepted."
            }
            self.write_json(path, payload)
            with self.assertRaisesRegex(
                SecondDepthValidationError,
                "overrides reference unknown companies",
            ):
                validate_second_depth(root)

    def test_claim_ceiling_must_match_stage(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = self.fixture_root(temporary_directory)
            path = root / "manifests" / "company_second_depth.json"
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["company_overrides"]["anthropic"]["claim_ceiling"] = (
                "proof_bound_company_specific"
            )
            self.write_json(path, payload)
            with self.assertRaisesRegex(
                SecondDepthValidationError,
                "claim ceiling .* does not match stage MAPPED_ONLY ceiling",
            ):
                validate_second_depth(root)


if __name__ == "__main__":
    unittest.main()
