"""Lockheed multi-repo composition — leveled."""
from __future__ import annotations

import unittest

from pathutil import add_repo

add_repo("lockheed-evidence-binding-gateway")
add_repo("lockheed-dual-key-actuator-fence")
add_repo("lockheed-mission-thread-isolator")

from core import MissionThreadIsolator
from dual_key_fence import Decision, RefuseReason, build_stack
from evidence_gateway import EvidenceBindingGateway, EvidenceSnapshot, GateVerdict


class LockheedTriadLeveled(unittest.TestCase):
    def test_toctou_blocks_stale_evidence_before_actuate(self):
        gw = EvidenceBindingGateway()
        gw.put(EvidenceSnapshot("ev1", {"risk": 0.1, "action": "open_valve"}))
        bound = gw.bind("dec-1", "ev1", "open_valve")
        gw.put(EvidenceSnapshot("ev1", {"risk": 0.9, "action": "open_valve"}))
        v, reason = gw.authorize(bound)
        self.assertEqual(v, GateVerdict.REFUSE)
        self.assertIn(reason, ("EVIDENCE_MUTATED", "VERSION_DRIFT"))

    def test_fresh_evidence_plus_dual_key_executes_in_isolated_thread(self):
        gw = EvidenceBindingGateway()
        content = {"risk": 0.1, "action": "open_valve", "ok": True}
        gw.put(EvidenceSnapshot("ev2", content))
        bound = gw.bind("dec-2", "ev2", "open_valve")
        self.assertEqual(gw.authorize(bound)[0], GateVerdict.ALLOW)

        brain, issuer, muscle, audit = build_stack(
            "pol-triad",
            lambda i: (float(i.get("risk", 1)) < 0.5, "OK"),
            b"triad-secret",
        )
        decision = brain.decide(content, now=1000.0)
        self.assertEqual(decision.verdict, Decision.ALLOW)
        grant = issuer.issue(decision, now=1000.0)
        receipt = muscle.execute(decision, grant, content, lambda i: {"opened": True}, now=1001.0)
        self.assertEqual(receipt.outcome, "EXECUTED")
        self.assertTrue(audit.verify_chain())

        iso = MissionThreadIsolator()
        iso.open("mission-a", "tok-a")
        iso.open("mission-b", "tok-b")
        iso.write("mission-a", "tok-a", "receipt_fp", receipt.fingerprint())
        self.assertIsNone(iso.read("mission-b", "tok-b", "receipt_fp"))
        eid = iso.export("mission-a", "tok-a", "receipt_fp", now=1.0, single_use=True)
        iso.import_export("mission-b", "tok-b", eid, "peer_receipt", now=2.0)
        self.assertEqual(iso.read("mission-b", "tok-b", "peer_receipt"), receipt.fingerprint())

    def test_multi_evidence_bind_then_refuse_partial_mutation(self):
        gw = EvidenceBindingGateway()
        gw.put(EvidenceSnapshot("e1", {"a": 1}))
        gw.put(EvidenceSnapshot("e2", {"b": 2}))
        multi = gw.bind_many("d", "act", ["e1", "e2"])
        self.assertEqual(gw.authorize_multi(multi)[0], GateVerdict.ALLOW)
        gw.put(EvidenceSnapshot("e1", {"a": 9}))
        v, _r = gw.authorize_multi(multi)
        self.assertEqual(v, GateVerdict.REFUSE)

    def test_end_to_end_refuse_without_grant(self):
        brain, _issuer, muscle, _ = build_stack("p", lambda i: (True, "OK"), b"s")
        d = brain.decide({"ok": True}, now=1.0)
        r = muscle.execute(d, None, {"ok": True}, lambda i: 1, now=2.0)
        self.assertEqual(r.refuse_reason, RefuseReason.MISSING_GRANT.value)


if __name__ == "__main__":
    unittest.main()
