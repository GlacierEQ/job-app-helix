#!/usr/bin/env python3
"""Real-path tests for Musk-orbit hire pack."""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import generate_pack  # noqa: E402

LEGAL = re.compile(
    r"1FDV|FEDERAL-WARFARE|SUPERLUMINAL|cathedrals_cases_distill",
    re.I,
)


class PackTests(unittest.TestCase):
    def test_generate_pack(self) -> None:
        self.assertEqual(generate_pack.main(), 0)
        self.assertTrue((ROOT / "PACK_STAMP.md").is_file())

    def test_all_artifacts_exist_nonempty(self) -> None:
        generate_pack.main()
        for name in generate_pack.REQUIRED:
            p = ROOT / name
            self.assertTrue(p.is_file(), name)
            self.assertGreater(p.stat().st_size, 400, name)

    def test_no_legal_leak(self) -> None:
        generate_pack.main()
        for name in generate_pack.REQUIRED:
            text = (ROOT / name).read_text()
            self.assertIsNone(LEGAL.search(text), name)

    def test_resume_anchors_and_positioning(self) -> None:
        generate_pack.main()
        t = (ROOT / "RESUME_MUSK_ORBIT.md").read_text()
        for a in ("AKOS", "pro-code", "xAI", "SpaceX", "xai-colossus-cooling", "spacex-thermal-protection"):
            self.assertIn(a, t)
        self.assertTrue("all-domain" in t.lower() or "multi-domain" in t.lower())
        self.assertIn("OBJECTIVE", t)

    def test_assessment_has_tiers(self) -> None:
        generate_pack.main()
        t = (ROOT / "HONEST_SKILL_ASSESSMENT.md").read_text()
        for tier in ("Strength", "Gap", "Unknown"):
            self.assertIn(tier, t)
        # at least 3 skill areas marked with Strength tables
        self.assertGreaterEqual(t.count("**Strength**"), 3)
        self.assertNotIn("qualification score", t.lower())

    def test_linkedin_consistent(self) -> None:
        generate_pack.main()
        t = (ROOT / "LINKEDIN_BUILDOUT.md").read_text()
        self.assertIn("AKOS", t)
        self.assertIn("pro-code", t)
        self.assertIn("Headline", t)
        self.assertIn("About", t)

    def test_outreach_ranked_backdoor(self) -> None:
        generate_pack.main()
        t = (ROOT / "OUTREACH_BACKDOOR.md").read_text()
        self.assertTrue("back-door" in t.lower() or "Back-door" in t)
        self.assertIn("front-door", t.lower())
        self.assertIn("AKOS", t)
        self.assertIn("pro-code", t)
        # ranked list + draft
        self.assertIn("Rank", t)
        self.assertIn("Draft", t)
        self.assertTrue(
            "xai-colossus-cooling" in t or "spacex-thermal-protection" in t
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
