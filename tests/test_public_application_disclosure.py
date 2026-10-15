"""Regression: public evidence must not publish private application lifecycle records."""
import unittest
from pathlib import Path

from scripts.check_public_surface import check_application_disclosure


class PublicApplicationDisclosureTests(unittest.TestCase):
    def test_public_submission_receipt_is_rejected(self):
        paths = [Path("evidence/applications/supabase/receipt.json")]
        self.assertTrue(check_application_disclosure(paths))

    def test_public_portfolio_proof_is_allowed(self):
        paths = [Path("evidence/portfolio/verified-project.json")]
        self.assertEqual(check_application_disclosure(paths), [])

    def test_other_evidence_is_not_reclassified(self):
        paths = [Path("evidence/portfolio/claims.json")]
        self.assertEqual(check_application_disclosure(paths), [])
