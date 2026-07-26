"""Dashboard test: gate admission rules (dashboard/gate_rules.py).

Pins the VERIFY-GATE EVIDENCE INTERLOCK — an item may not be presented to the
operator as ready-to-verify unless its packet carries `validation.passed`.

The fixtures at the bottom are the REAL key sets observed live: two items that had
genuinely validated (allowed) and one that reached the verify gate with no validation
payload at all while its code was already merged (must be refused). That item is why
this rule exists, so it is encoded as a regression case rather than a paraphrase.

Pure: no FastAPI, no request, no database — which is precisely why the rule lives in
its own module.

Run: python -m unittest dashboard.tests.test_gate_rules   (from the repo root)
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from dashboard.gate_rules import VERIFY_GATE, verify_gate_refusal  # noqa: E402


def pkt(**over):
    """A verify-gate packet that SHOULD be admitted, minus any overrides."""
    body = {"work_item": {"title": "T"}, "gate": VERIFY_GATE,
            "validation": {"passed": True, "reason": "bound tests green + live exercise"}}
    body.update(over)
    return body


class VerifyGateRequiresEvidence(unittest.TestCase):
    def test_a_validated_packet_is_admitted(self):
        self.assertIsNone(verify_gate_refusal(VERIFY_GATE, pkt()))

    def test_missing_validation_is_refused(self):
        # THE observed failure: no validation key at all.
        p = pkt()
        del p["validation"]
        refusal = verify_gate_refusal(VERIFY_GATE, p)
        self.assertIsNotNone(refusal)
        self.assertIn("validation.passed", refusal)

    def test_validation_that_did_not_pass_is_refused(self):
        # A RED validation is a FAIL to report, never a gate to advance.
        self.assertIsNotNone(verify_gate_refusal(VERIFY_GATE, pkt(validation={"passed": False})))

    def test_empty_or_malformed_validation_is_refused(self):
        for bad in ({}, None, "passed", ["passed"], {"reason": "ran, sort of"}):
            with self.subTest(validation=bad):
                self.assertIsNotNone(verify_gate_refusal(VERIFY_GATE, pkt(validation=bad)))

    def test_a_missing_packet_cannot_open_the_verify_gate(self):
        self.assertIsNotNone(verify_gate_refusal(VERIFY_GATE, None))
        self.assertIsNotNone(verify_gate_refusal(VERIFY_GATE, {}))


class EarlierGatesAreUnaffected(unittest.TestCase):
    """Requirements/validation gates legitimately precede validation evidence — the
    interlock must not become a blanket "every gate needs validation" rule."""

    def test_earlier_gates_admit_without_validation(self):
        for gate in ("gate1", "gate2", "requirements", ""):
            with self.subTest(gate=gate):
                self.assertIsNone(verify_gate_refusal(gate, {"work_item": {"title": "T"}}))

    def test_no_gate_named_is_not_a_verify_push(self):
        self.assertIsNone(verify_gate_refusal(None, {"work_item": {"title": "T"}}))


class GateNameMatching(unittest.TestCase):
    def test_matching_tolerates_case_and_padding(self):
        # the gate name arrives from a JSON body; don't let " Gate3 " slip the interlock
        p = pkt()
        del p["validation"]
        for spelling in (VERIFY_GATE, VERIFY_GATE.upper(), f"  {VERIFY_GATE} ",
                         VERIFY_GATE.capitalize()):
            with self.subTest(gate=spelling):
                self.assertIsNotNone(verify_gate_refusal(spelling, p))


class ObservedPacketShapes(unittest.TestCase):
    """Real key sets seen on live verify-gate packets."""

    # Two items that had actually validated and merged.
    VALIDATED = [
        {"work_item": {}, "gate": VERIFY_GATE, "feature": {}, "recommendation": {},
         "validation": {"passed": True}, "deferred_issues": []},
        {"work_item": {}, "gate": VERIFY_GATE, "feature": {}, "recommendation": {},
         "validation": {"passed": True}, "agents": []},
    ]
    # The anomaly: merged code, presented for verification, no validation slot. Note it
    # also lacks `gate`/`feature` — assembled by a pass that skipped validate+merge.
    UNVALIDATED = {"work_item": {}, "recommendation": {}, "verify_steps": []}

    def test_the_validated_shapes_are_admitted(self):
        for i, p in enumerate(self.VALIDATED):
            with self.subTest(packet=i):
                self.assertIsNone(verify_gate_refusal(VERIFY_GATE, p))

    def test_the_unvalidated_shape_is_refused(self):
        self.assertIsNotNone(verify_gate_refusal(VERIFY_GATE, self.UNVALIDATED))


if __name__ == "__main__":
    unittest.main()
