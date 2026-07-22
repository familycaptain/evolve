"""Dashboard test: gate decision lifecycle (dashboard/store.py::upsert_gate).

Pins the two OPPOSING properties of the decision-safety rule, which are easy to
break in each other's name:
  * an `approve` SURVIVES a same-gate re-push (a replayed/buffered push must never
    erase a verdict the operator believes they gave), and
  * a rework instruction (`change`/`reject`) is CONSUMED by the re-push that answers
    it — otherwise the decision lingers as 'decided' forever, polluting every later
    pending scan while the operator is never asked about the reworked packet.

Hermetic: a sqlite db in a tmpdir, no network, no server. The packets are synthetic
("demo.thing.widget") — nothing about the project any instance happens to evolve.

Run: python -m unittest dashboard.tests.test_gate_decisions   (from the repo root)
"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from dashboard import store as store_mod  # noqa: E402

IID = "ev-demo1"


def _packet(gate="gate1", title="Widget", note="v1"):
    return {"instance": IID, "gate": gate, "title": title,
            "work_item": {"title": title, "body": note}}


class GateDecisionLifecycle(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.store = store_mod.Store(os.path.join(self._tmp.name, "t.db"))

    def _push(self, gate="gate1", note="v1", **kw):
        self.store.upsert_gate(IID, gate=gate, title="Widget",
                               packet=_packet(gate, note=note), **kw)

    def _decide(self, decision):
        self.assertTrue(self.store.record_decision(IID, decision=decision, note="n",
                                                   decided_by="operator"))

    def test_approve_survives_a_same_gate_repush(self):
        # the safety property: a replayed push must not erase the operator's verdict
        self._push()
        self._decide("approve")
        self._push(note="replay")
        g = self.store.get_gate(IID)
        self.assertEqual(g["status"], "decided")
        self.assertEqual(g["decision"], "approve")

    def test_change_is_consumed_by_the_repush_that_answers_it(self):
        self._push()
        self._decide("change")
        self._push(note="reworked")          # the loop comes back with redone work
        g = self.store.get_gate(IID)
        self.assertEqual(g["status"], "waiting")
        self.assertIsNone(g["decision"])

    def test_reject_is_consumed_too(self):
        self._push()
        self._decide("reject")
        self._push(note="reworked")
        self.assertEqual(self.store.get_gate(IID)["status"], "waiting")

    def test_explicit_reset_clears_even_an_approve(self):
        self._push()
        self._decide("approve")
        self._push(reset=True)
        g = self.store.get_gate(IID)
        self.assertEqual(g["status"], "waiting")
        self.assertIsNone(g["decision"])

    def test_a_different_gate_kind_always_owes_a_fresh_decision(self):
        self._push(gate="gate1")
        self._decide("approve")
        self._push(gate="gate2")
        g = self.store.get_gate(IID)
        self.assertEqual(g["gate"], "gate2")
        self.assertEqual(g["status"], "waiting")
        self.assertIsNone(g["decision"])

    def test_a_preserved_decision_still_merges_the_incoming_packet(self):
        # decision-safety keeps the verdict, but must not throw away fresher metadata
        self._push(note="v1")
        self._decide("approve")
        self._push(note="v2")
        g = self.store.get_gate(IID)
        self.assertEqual(g["decision"], "approve")
        self.assertEqual(g["packet"]["work_item"]["body"], "v2")


if __name__ == "__main__":
    unittest.main()
