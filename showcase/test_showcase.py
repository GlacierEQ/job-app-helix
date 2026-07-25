#!/usr/bin/env python3
"""Real-path tests for the hireable showcase.

Drives generate_showcase.main() and reads SHOWCASE.md / README.md from disk.
No hard-coded success without opening the real entry artifacts.
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import generate_showcase  # noqa: E402


MUST_NAMES = ["AKOS", "pro-code", "Pro-", "xAI", "SpaceX", "Anthropic", "NVIDIA", "Notion"]
LEGAL_RE = re.compile(
    r"1FDV-23|FEDERAL-WARFARE|SUPERLUMINAL_CASE|DOCKETS|AspenGrove-KEKOA|"
    r"cathedrals_cases_distill|Family Court|Criminal Court|CSEA|Civil RICO|§1983",
    re.I,
)

# Per-company concrete exhibit that must appear as a real GitHub path/name
COMPANY_POINTERS = {
    "xAI": ["xai-colossus-cooling", "colossus-gateway"],
    "SpaceX": ["spacex-thermal-protection", "spacex-orbital-mechanics"],
    "Anthropic": ["AKOS", "pro-code", "Pro-comet-agent"],
    "NVIDIA": [
        "xai-colossus-energy",
        "xai-colossus-servers",
        "nvidia-gpu-health",
    ],
    "Notion": [
        "notion-workflow-intelligence",
        "notion-workspace-optimizer",
        "notion-mcp-empowerment-engine",
    ],
}


def _row_for(company: str, text: str) -> str:
    """Extract the markdown table row that starts with **Company**."""
    for line in text.splitlines():
        if line.strip().startswith(f"| **{company}**"):
            return line
    raise AssertionError(f"no table row for {company}")


class ShowcaseTests(unittest.TestCase):
    def test_generate_writes_showcase(self) -> None:
        rc = generate_showcase.main()
        self.assertEqual(rc, 0)
        path = ROOT / "SHOWCASE.md"
        self.assertTrue(path.is_file(), "SHOWCASE.md must exist after generate")
        text = path.read_text()
        self.assertGreater(len(text), 800, "showcase must be non-empty substantive content")
        for name in MUST_NAMES:
            self.assertIn(name, text, f"missing {name}")

    def test_readme_is_entry_path(self) -> None:
        readme = ROOT / "README.md"
        self.assertTrue(readme.is_file())
        body = readme.read_text()
        self.assertIn("SHOWCASE.md", body)
        self.assertIn("AKOS", body)

    def test_no_legal_case_leak(self) -> None:
        generate_showcase.main()
        text = (ROOT / "SHOWCASE.md").read_text()
        self.assertIsNone(LEGAL_RE.search(text), "legal/case docket content must not appear")
        self.assertNotIn("cathedrals_cases_distill", text)
        self.assertNotIn("cases_distill", text)

    def test_framework_cards_have_role_and_location(self) -> None:
        generate_showcase.main()
        text = (ROOT / "SHOWCASE.md").read_text()
        self.assertIn("Apex Knowledge OS", text)
        self.assertIn("pro-code", text)
        self.assertIn("https://github.com/GlacierEQ/AKOS", text)
        self.assertIn("https://github.com/GlacierEQ/pro-code", text)
        self.assertTrue(
            "xai-colossus-cooling" in text or "colossus-gateway" in text,
            "need a colossus/xAI motion sample",
        )
        self.assertIn("spacex-thermal-protection", text)

    def test_company_map_rows_have_concrete_pointers(self) -> None:
        """VP step 2: each company row points at real portfolio artifacts (not placeholders)."""
        generate_showcase.main()
        text = (ROOT / "SHOWCASE.md").read_text()
        for company, pointers in COMPANY_POINTERS.items():
            row = _row_for(company, text)
            self.assertIn("github.com/GlacierEQ", row, f"{company} row needs github pointer")
            hits = [p for p in pointers if p in row]
            self.assertTrue(
                len(hits) >= 1,
                f"{company} row missing concrete exhibit; want one of {pointers}; row={row}",
            )
            # ban vague filler that previously failed NVIDIA
            if company == "NVIDIA":
                self.assertIn("xai-colossus-energy", row)
                self.assertIn("xai-colossus-servers", row)
                self.assertNotIn("energy/servers pillars", row)
            if company == "Notion":
                self.assertNotIn("cathedrals", row.lower())
                self.assertNotIn("cases_distill", row)
                self.assertTrue(
                    any(n in row for n in ("notion-workflow", "notion-workspace", "notion-mcp")),
                    f"Notion row needs engineering notion-* repo; row={row}",
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
