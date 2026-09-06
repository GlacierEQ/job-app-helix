"""Palantir multi-repo composition — ledger + lineage."""
from __future__ import annotations

import unittest

from pathutil import add_repo

add_repo("palantir-ontology-writeback-ledger")
add_repo("palantir-action-lineage-graph")

from lineage import ActionKind, ActionNode, CommitStatus, LineageGraph
from writeback_ledger import (
    ApplyStatus,
    DiffOp,
    ObjectSnapshot,
    OntologyWritebackLedger,
    SignMode,
    WritebackDiff,
)


class PalantirStack(unittest.TestCase):
    def test_observe_lineage_then_writeback(self):
        g = LineageGraph()
        self.assertEqual(
            g.commit(ActionNode("obs", ActionKind.ROOT_OBSERVE, {"obj": "Aircraft:A-1"}, ()))[0],
            CommitStatus.COMMITTED,
        )
        self.assertEqual(
            g.commit(
                ActionNode(
                    "write",
                    ActionKind.SIDE_EFFECT,
                    {"field": "status"},
                    ("obs",),
                    attestation="sig:write",
                )
            )[0],
            CommitStatus.COMMITTED,
        )
        self.assertTrue(g.reaches("write", "obs"))

        led = OntologyWritebackLedger("onto-v3", SignMode.HUMAN_AGENT)
        base = ObjectSnapshot("Aircraft", "A-1", {"status": "ground"}, "onto-v3")
        led.upsert_base(base)
        d = WritebackDiff(
            diff_id="d1",
            base=base,
            ops=(DiffOp("status", "set", "airborne"),),
            proposed_by="agent:scout",
            authority="ops",
            mode=SignMode.HUMAN_AGENT,
            signatures=("human:ada", "agent:scout"),
            parent_ledger_hash=led.tip,
        )
        e = led.apply(d)
        self.assertEqual(e.status, ApplyStatus.APPLIED)

if __name__ == "__main__":
    unittest.main()
