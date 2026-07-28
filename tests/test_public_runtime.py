from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from helix.public_runtime import run_launch_campaign, run_pair


class PublicRuntimeTests(unittest.TestCase):
    def test_nominal_campaign_is_go(self) -> None:
        receipt = run_launch_campaign("nominal")
        self.assertEqual(receipt["initial_decision"], "GO")
        self.assertEqual(receipt["final_decision"], "GO")
        self.assertEqual(receipt["summary"]["pairs_run"], 3)
        self.assertEqual(len(receipt["proof_sha256"]), 64)

    def test_recoverable_campaign_closes_the_loop(self) -> None:
        receipt = run_launch_campaign("recoverable")
        self.assertEqual(receipt["initial_decision"], "NO-GO")
        self.assertEqual(receipt["final_decision"], "GO")
        self.assertGreaterEqual(receipt["summary"]["refinements"], 2)

    def test_terminal_campaign_fails_closed(self) -> None:
        receipt = run_launch_campaign("terminal")
        self.assertEqual(receipt["initial_decision"], "NO-GO")
        self.assertEqual(receipt["final_decision"], "NO-GO")
        self.assertTrue(receipt["final_reasons"])

    def test_single_pair_receipt(self) -> None:
        receipt = run_pair("flight", "nominal")
        self.assertTrue(receipt["pair"]["final_ok"])
        self.assertEqual(receipt["pair"]["pair"], "flight")

    def test_cli_writes_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "receipt.json"
            completed = subprocess.run(
                [sys.executable, "-m", "helix.public_runtime", "demo", "--scenario", "nominal", "--output", str(output)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(payload["final_decision"], "GO")


if __name__ == "__main__":
    unittest.main()
