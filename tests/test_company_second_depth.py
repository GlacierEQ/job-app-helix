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


def evidence_reference(
    kind: str,
    *,
    verification_state: str = "VERIFIED",
    visibility: str = "public",
) -> dict[str, str]:
    return {
        "id": f"fixture:{kind}",
        "kind": kind,
        "source_identity": "https://example.com/public-evidence",
        "source_ref": f"sha256:{'a' * 64}",
        "visibility": visibility,
        "verification_state": verification_state,
    }


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

    def company_track_count(self) -> int:
        payload = json.loads(
            (ROOT / "manifests" / "company_dossiers.json").read_text(
                encoding="utf-8"
            )
        )
        return len(payload["required_company_tracks"])

    def test_current_registry_is_fail_closed_and_complete(self) -> None:
        result = validate_second_depth(ROOT)
        track_count = self.company_track_count()
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["company_tracks"], track_count)
        self.assertEqual(result["stage_count"], 8)
        self.assertEqual(result["priority_wave"], 8)
        self.assertEqual(result["stage_counts"]["MAPPED_ONLY"], track_count - 1)
        self.assertEqual(result["stage_counts"]["CLAIM_PROMOTED"], 1)
        for stage in (
            "ROLE_VERIFIED",
            "PROBLEM_BOUNDED",
            "REMEDY_BOUNDED",
            "IMPLEMENTED",
            "PROOF_REPRODUCED",
            "CODE_INSPECTED",
        ):
            self.assertEqual(result["stage_counts"][stage], 0)
        self.assertEqual(sum(result["stage_counts"].values()), track_count)
        self.assertTrue(result["evidence_reference_schema_enforced"])
        self.assertTrue(result["stage_contract_locked"])
        self.assertTrue(result["claim_promotion_requires_receipt"])
        self.assertTrue(result["zero_implicit_completion"])

    def test_lockheed_remains_truth_bounded_without_direct_repository_proof(self) -> None:
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
        self.assertEqual(resolved["stage"], "CLAIM_PROMOTED")
        self.assertEqual(
            resolved["claim_ceiling"], "proof_bound_company_specific"
        )
        self.assertEqual(len(resolved["role_evidence"]), 1)
        self.assertEqual(len(resolved["problem_evidence"]), 1)
        self.assertEqual(len(resolved["inspected_repositories"]), 4)
        self.assertEqual(len(resolved["gap_queue"]), 1)
        self.assertEqual(len(resolved["implementation_receipts"]), 1)
        self.assertEqual(len(resolved["proof_artifacts"]), 1)
        self.assertEqual(
            resolved["proof_artifacts"][0]["verification_state"], "REPRODUCED"
        )
        self.assertEqual(len(resolved["claim_receipts"]), 1)
        self.assertIn("production_scale_not_demonstrated", resolved["blockers"])
        self.assertIn(
            "aerospace_defense_certification_not_claimed", resolved["blockers"]
        )
        self.assertNotIn("no_direct_company_repository_verified", resolved["blockers"])
        self.assertEqual(
            {item["kind"] for item in resolved["inspected_repositories"]},
            {"repository_inspection"},
        )
        self.assertTrue(
            all(
                item["verification_state"] == "VERIFIED"
                for item in resolved["inspected_repositories"]
            )
        )

    def test_repository_inspection_manifest_covers_every_declared_path(self) -> None:
        second_depth = json.loads(
            (ROOT / "manifests" / "company_second_depth.json").read_text(
                encoding="utf-8"
            )
        )
        defaults = second_depth["default_company_state"]
        evidence_root = ROOT / "evidence" / "company_second_depth"

        for company_directory in sorted(evidence_root.iterdir()):
            if not company_directory.is_dir():
                continue
            captures = sorted(
                company_directory.glob("repository_inspection*.json")
            )
            if not captures:
                continue

            company_id = company_directory.name
            override = second_depth["company_overrides"].get(company_id, {})
            state = {**defaults, **override}
            manifest_refs = {
                (item["source_identity"], item["source_ref"])
                for item in state["inspected_repositories"]
            }
            declared_refs: set[tuple[str, str]] = set()

            for capture_path in captures:
                capture = json.loads(capture_path.read_text(encoding="utf-8"))
                self.assertEqual(
                    capture["schema"], "glaciereq.repository-inspection.v1"
                )
                self.assertEqual(capture["company_id"], company_id)
                for inspection in capture["inspections"]:
                    repository = inspection["repository"]
                    commit = inspection["commit"]
                    self.assertEqual(len(commit), 40)
                    for path in inspection["paths"]:
                        declared_refs.add(
                            (
                                f"https://github.com/{repository}/blob/{commit}/{path}",
                                f"commit:{commit}",
                            )
                        )

            self.assertEqual(manifest_refs, declared_refs)

    def test_valid_pinned_public_role_evidence_can_advance_one_stage(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = self.fixture_root(temporary_directory)
            path = root / "manifests" / "company_second_depth.json"
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["company_overrides"]["openai"].update(
                {
                    "stage": "ROLE_VERIFIED",
                    "role_evidence": [evidence_reference("role")],
                    "claim_ceiling": "verified_role_alignment",
                }
            )
            self.write_json(path, payload)
            result = validate_second_depth(root)
            track_count = self.company_track_count()
            self.assertEqual(result["stage_counts"]["ROLE_VERIFIED"], 1)
            self.assertEqual(result["stage_counts"]["CLAIM_PROMOTED"], 1)
            self.assertEqual(
                result["stage_counts"]["MAPPED_ONLY"],
                track_count - 2,
            )

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

    def test_malformed_evidence_object_cannot_satisfy_prerequisite(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = self.fixture_root(temporary_directory)
            path = root / "manifests" / "company_second_depth.json"
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["company_overrides"]["openai"].update(
                {
                    "stage": "ROLE_VERIFIED",
                    "role_evidence": [{"id": "fabricated"}],
                    "claim_ceiling": "verified_role_alignment",
                }
            )
            self.write_json(path, payload)
            with self.assertRaisesRegex(
                SecondDepthValidationError,
                "evidence keys must exactly equal",
            ):
                validate_second_depth(root)

    def test_private_evidence_reference_cannot_satisfy_public_stage(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = self.fixture_root(temporary_directory)
            path = root / "manifests" / "company_second_depth.json"
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["company_overrides"]["openai"].update(
                {
                    "stage": "ROLE_VERIFIED",
                    "role_evidence": [evidence_reference("role", visibility="private")],
                    "claim_ceiling": "verified_role_alignment",
                }
            )
            self.write_json(path, payload)
            with self.assertRaisesRegex(
                SecondDepthValidationError,
                "visibility must be public",
            ):
                validate_second_depth(root)

    def test_proof_artifacts_cannot_appear_at_mapping_stage(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = self.fixture_root(temporary_directory)
            path = root / "manifests" / "company_second_depth.json"
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["company_overrides"]["openai"]["proof_artifacts"] = [
                evidence_reference(
                    "proof_artifact",
                    verification_state="REPRODUCED",
                )
            ]
            self.write_json(path, payload)
            with self.assertRaisesRegex(
                SecondDepthValidationError,
                "proof artifacts cannot precede PROOF_REPRODUCED",
            ):
                validate_second_depth(root)

    def test_stage_contract_cannot_drop_earlier_prerequisites(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = self.fixture_root(temporary_directory)
            path = root / "manifests" / "company_second_depth.json"
            payload = json.loads(path.read_text(encoding="utf-8"))
            proof_stage = next(
                stage
                for stage in payload["stage_order"]
                if stage["id"] == "PROOF_REPRODUCED"
            )
            proof_stage["minimum_evidence"].remove("gap_queue")
            self.write_json(path, payload)
            with self.assertRaisesRegex(
                SecondDepthValidationError,
                "PROOF_REPRODUCED minimum_evidence contract drift",
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
