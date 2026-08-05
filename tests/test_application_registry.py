from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ApplicationRegistryTests(unittest.TestCase):
    def test_zero_omission_registry_gate(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "validate_application_registry.py")],
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
        self.assertEqual(result["helix_children_mapped"], 66)
        self.assertTrue(result["helix_children_exactly_once"])
        self.assertEqual(result["company_tracks"], 48)
        self.assertEqual(result["named_flagships"], 17)
        self.assertTrue(result["zero_direct_omission_gate"])


if __name__ == "__main__":
    unittest.main()
