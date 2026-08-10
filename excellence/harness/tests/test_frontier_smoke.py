"""Smoke: frontier wave1c modules import and basic invariants."""
from __future__ import annotations
import unittest
from pathutil import add_repo

class FrontierSmoke(unittest.TestCase):
    def test_openai_budget(self):
        add_repo("openai-reasoning-budget-futures")
        from budget_futures import ReasoningBudgetLedger, SpendStatus
        led = ReasoningBudgetLedger()
        led.mint("f", 10)
        self.assertEqual(led.spend("f", 11).status, SpendStatus.REFUSED)

    def test_anthropic_transcript(self):
        add_repo("anthropic-constitutional-tool-transcript")
        from transcript import ConstitutionalTranscript, Policy, ToolCall, Verdict
        tx = ConstitutionalTranscript(Policy("p", frozenset({"bash"}), frozenset({"read"})))
        e = tx.decide(ToolCall("1", "bash", {}))
        self.assertEqual(e.verdict, Verdict.REFUSE)

    def test_nvidia_quorum(self):
        add_repo("nvidia-gradient-integrity-quorum")
        from gradient_quorum import GradientIntegrityQuorum, RankReport, Commit
        r = GradientIntegrityQuorum().evaluate({0: RankReport(0, 1.0, True)})
        self.assertEqual(r.decision, Commit.COMMIT)

    def test_xai_bus(self):
        add_repo("xai-actuation-receipt-bus")
        from receipt_bus import ActuationReceiptBus, Phase
        b = ActuationReceiptBus()
        b.intend("i", "cool")
        b.precheck("i", {"ok": True})
        b.actuate("i", lambda: {"done": True})
        self.assertEqual(b.complete("i", ("done",)).phase, Phase.COMPLETE)

if __name__ == "__main__":
    unittest.main()
