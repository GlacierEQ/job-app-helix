"""SpaceX multi-repo composition — leveled."""
from __future__ import annotations
import unittest
from pathutil import add_repo

add_repo("spacex-mission-thread-quorum")
add_repo("spacex-hold-reason-compiler")

from quorum import MissionThreadQuorum, SubsystemVote, Vote, Severity, StackState, DEFAULT_REQUIRED
from hold_compiler import HoldReasonCompiler, HoldResidual


class SpaceXStackLeveled(unittest.TestCase):
    def test_hold_compiles_from_quorum(self):
        q = MissionThreadQuorum()
        now = 100.0
        for sub in DEFAULT_REQUIRED:
            q.cast(SubsystemVote(sub, Vote.GO, Severity.LOW, "OK", now))
        q.cast(SubsystemVote("weather", Vote.NO_GO, Severity.HIGH, "WINDS", now))
        q.cast(SubsystemVote("conjunction", Vote.NO_GO, Severity.CRITICAL, "TCA", now))
        r = q.evaluate(now + 5)
        self.assertEqual(r.state, StackState.HOLD)

        residuals = [
            HoldResidual(sub, code, detail, "CRITICAL" if code == "TCA" else "HIGH")
            for sub, code, detail in q.residuals_for_hold(now + 5)
        ]
        # residuals_for_hold returns (sub, code, detail)
        residuals = []
        for sub, code, detail in q.residuals_for_hold(now + 5):
            residuals.append(HoldResidual(sub, code, detail, "HIGH"))
        brief = HoldReasonCompiler().compile(residuals)
        self.assertIn("HOLD", brief.headline)
        self.assertGreaterEqual(len(brief.machine_codes), 1)
        self.assertEqual(len(brief.fingerprint), 64)
        self.assertEqual(brief.machine["state"], "HOLD")

    def test_go_when_all_live(self):
        q = MissionThreadQuorum()
        now = 50.0
        for sub in DEFAULT_REQUIRED:
            q.cast(SubsystemVote(sub, Vote.GO, Severity.LOW, "OK", now))
        r = q.evaluate(now + 1)
        self.assertEqual(r.state, StackState.GO)
        brief = HoldReasonCompiler().compile([])
        self.assertEqual(brief.headline, "NO_HOLD")

    def test_supersession_clears_hold(self):
        q = MissionThreadQuorum()
        now = 50.0
        for sub in DEFAULT_REQUIRED:
            q.cast(SubsystemVote(sub, Vote.GO, Severity.LOW, "OK", now))
        q.cast(SubsystemVote("weather", Vote.NO_GO, Severity.HIGH, "WINDS", now + 1))
        self.assertEqual(q.evaluate(now + 2).state, StackState.HOLD)
        q.cast(SubsystemVote("weather", Vote.GO, Severity.LOW, "CLEAR", now + 3))
        self.assertEqual(q.evaluate(now + 4).state, StackState.GO)


if __name__ == "__main__":
    unittest.main()
