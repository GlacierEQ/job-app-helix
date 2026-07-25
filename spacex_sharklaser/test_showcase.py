#!/usr/bin/env python3
"""Real-path tests for SpaceX shark-laser showcase generator."""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import generate_showcase  # noqa: E402

LEGAL = re.compile(
    r"1FDV|FEDERAL-WARFARE|SUPERLUMINAL|cathedrals_cases_distill",
    re.I,
)
EMPLOY = re.compile(
    r"employed at SpaceX|SpaceX employee|I worked at SpaceX|flight heritage at SpaceX",
    re.I,
)


class SpaceXShowcaseTests(unittest.TestCase):
    def test_generate_main(self) -> None:
        self.assertEqual(generate_showcase.main(), 0)
        self.assertTrue((ROOT / "SPACEX_SHARKLASER_SHOWCASE.md").is_file())
        self.assertTrue((ROOT / "A_TO_Z_CAMPAIGN.md").is_file())

    def test_showcase_anchors(self) -> None:
        generate_showcase.main()
        t = (ROOT / "SPACEX_SHARKLASER_SHOWCASE.md").read_text()
        self.assertGreater(len(t), 1500)
        for a in (
            "AKOS",
            "pro-code",
            "SpaceX",
            "spacex-thermal-protection",
            "spacex-orbital-mechanics",
            "spacex-telemetry",
            "shark-laser",
            "special-projects",
            "Bottleneck",
        ):
            self.assertIn(a, t, a)
        # second helix sample
        self.assertTrue(
            "spacex-launch-sequencer" in t or "spacex-ground-network" in t
        )
        self.assertIsNone(LEGAL.search(t))
        self.assertIsNone(EMPLOY.search(t))
        self.assertIn("Not claiming", t)

    def test_az_orchestration(self) -> None:
        generate_showcase.main()
        t = (ROOT / "A_TO_Z_CAMPAIGN.md").read_text()
        self.assertIn("AZOP", t)
        self.assertIn("token-saver", t)
        self.assertIn("jobapp_whole", t)
        self.assertTrue("explore" in t.lower() or "MICROWAVE" in t)
        self.assertIn("MICROWAVE", t)
        self.assertIn("SPACEX_SHARKLASER_SHOWCASE", t)

    def test_no_legal_in_outputs(self) -> None:
        generate_showcase.main()
        for name in ("SPACEX_SHARKLASER_SHOWCASE.md", "A_TO_Z_CAMPAIGN.md"):
            self.assertIsNone(LEGAL.search((ROOT / name).read_text()), name)


if __name__ == "__main__":
    unittest.main(verbosity=2)
