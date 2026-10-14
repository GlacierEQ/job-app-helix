"""Fail-closed public/private applicant-operation regression checks."""
import json
import tempfile
import unittest
from pathlib import Path
from scripts.check_application_privacy_boundary import violations


class ApplicationPrivacyBoundaryGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def write(self, relative, content):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def test_public_source_intelligence_is_allowed(self):
        self.write("manifests/company_intelligence/example.json", json.dumps({"company": "Example", "open_roles": ["engineer"]}))
        self.assertEqual(violations(self.root), [])

    def test_external_application_receipt_in_evidence_is_denied(self):
        self.write("evidence/applications/provider/receipt.json", '{"application_state":"SUBMITTED"}')
        self.assertTrue(any("evidence/applications" in error for error in violations(self.root)))

    def test_applicant_specific_packet_is_denied_regardless_of_extension(self):
        self.write("hire_package/casey-barton/applications/company/answers.md", "private application answers")
        self.assertTrue(any("hire_package/casey-barton/applications" in error for error in violations(self.root)))

    def test_receipt_copied_into_renamed_export_path_is_denied(self):
        self.write("manifests/company_intelligence/export.json", json.dumps({
            "schema": "glaciereq.external-application-receipt.v1",
            "provider_acknowledgement": True,
            "application_state": "APPLICATION_RECEIVED",
        }))
        self.assertTrue(any("export.json" in error for error in violations(self.root)))

    def test_nested_repackaged_provider_state_is_denied(self):
        self.write("artifacts/pages-site/index.json", json.dumps({
            "company": "Example", "opaque": [{"receipt_observation": {"source_type": "screenshot"}}],
        }))
        self.assertTrue(any("index.json" in error for error in violations(self.root)))

    def test_private_receipt_detection_does_not_reject_generic_technical_schema(self):
        self.write("evidence/architecture/proof.json", json.dumps({
            "schema": "glaciereq.architecture-proof.v1", "receipt_sha256": "a" * 64,
            "status": "PASS",
        }))
        self.assertEqual(violations(self.root), [])


if __name__ == "__main__":
    unittest.main()
