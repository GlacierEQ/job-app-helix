#!/usr/bin/env python3
"""Real-path tests for job portfolio unified whole."""
from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import generate_whole  # noqa: E402

LEGAL = re.compile(
    r"1FDV|FEDERAL-WARFARE|SUPERLUMINAL|cathedrals_cases_distill",
    re.I,
)


class WholeTests(unittest.TestCase):
    def test_generate_main(self) -> None:
        self.assertEqual(generate_whole.main(), 0)
        self.assertTrue((ROOT / "WHOLE.md").is_file())
        self.assertTrue((ROOT / "REGISTRY.md").is_file())
        self.assertTrue((ROOT / "PASS_LOG.md").is_file())

    def test_whole_anchors_and_families(self) -> None:
        generate_whole.main()
        t = (ROOT / "WHOLE.md").read_text()
        self.assertGreater(len(t), 800)
        for a in ("AKOS", "pro-code", "Pro-", "xAI", "SpaceX", "Colossus"):
            self.assertIn(a, t)
        self.assertIn("xai-colossus-cooling", t)
        self.assertIn("spacex-thermal-protection", t)
        self.assertIn("github.com/GlacierEQ", t)

    def test_registry_core_rows(self) -> None:
        generate_whole.main()
        data = json.loads((ROOT / "registry.json").read_text())
        ids = {i["id"] for i in data["frameworks"] + data["exhibits"]}
        for need in ("AKOS", "pro-code", "xai-colossus-cooling", "spacex-thermal-protection", "Pro-comet-agent"):
            self.assertIn(need, ids)
        # each has status + role + pointer
        for it in data["frameworks"] + data["exhibits"]:
            self.assertIn(it["status"], ("integrated", "deferred", "blocked"))
            self.assertTrue(it.get("role"))
            self.assertTrue(it.get("pointer", "").startswith("https://github.com/GlacierEQ/"))
        # must have integrated core set
        integrated = {
            i["id"]
            for i in data["frameworks"] + data["exhibits"]
            if i["status"] == "integrated"
        }
        for need in ("AKOS", "pro-code", "xai-colossus-cooling", "spacex-thermal-protection", "Pro-comet-agent"):
            self.assertIn(need, integrated)
        # token_saver or mastermind
        self.assertTrue("token_saver" in integrated or "mastermind" in integrated)

    def test_registry_md_status_language(self) -> None:
        generate_whole.main()
        t = (ROOT / "REGISTRY.md").read_text()
        self.assertIn("integrated", t)
        # legend or composition may mention deferred status language
        self.assertTrue(
            "deferred" in t.lower() or "integrated" in t,
            "registry should discuss status language",
        )
        self.assertIn("AKOS", t)
        self.assertIn("pro-code", t)

    def test_pass_log_ordered_one_by_one(self) -> None:
        generate_whole.main()
        t = (ROOT / "PASS_LOG.md").read_text()
        self.assertIn("one by one", t.lower())
        self.assertIn("AKOS", t)
        self.assertIn("pro-code", t)
        self.assertIn("xai-colossus-cooling", t)
        self.assertIn("spacex-thermal-protection", t)
        self.assertIn("Pro-comet-agent", t)
        # pass numbers appear
        self.assertIn("| 1 |", t)
        data = json.loads((ROOT / "registry.json").read_text())
        integrated = [
            i for i in data["frameworks"] + data["exhibits"] if i["status"] == "integrated"
        ]
        self.assertGreaterEqual(len(integrated), 10)

    def test_no_legal(self) -> None:
        generate_whole.main()
        for name in ("WHOLE.md", "REGISTRY.md", "registry.json"):
            text = (ROOT / name).read_text()
            self.assertIsNone(LEGAL.search(text), name)

    def test_readme_entry(self) -> None:
        self.assertTrue((ROOT / "README.md").is_file())
        body = (ROOT / "README.md").read_text()
        self.assertIn("WHOLE.md", body)
        self.assertIn("REGISTRY.md", body)


if __name__ == "__main__":
    unittest.main(verbosity=2)
