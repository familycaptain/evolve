"""Gate admission rules — pure predicates, no web framework and no database.

Kept separate from `server.py` on purpose: the rules that decide whether a gate may
be opened are the integrity core of the pipeline, so they must be unit-testable
without standing up FastAPI or a request. `server.py` imports and enforces them.
"""

# The operator's verify-on-the-deliverable gate — the LAST gate, opened only after a
# change has been validated and merged.
VERIFY_GATE = "gate3"


def verify_gate_refusal(gate, packet) -> str | None:
    """Why this push must NOT be allowed to open the verify gate — or None if it may.

    The verify gate asserts "built, validation passed, merged — go confirm it on the
    deliverable." Opening it with an empty validation slot hands the operator an
    UNVALIDATED change as ready-to-verify, and since the queue holds one packet per
    item, it also destroys the evidence that validation never ran. Observed live: an
    item reached the verify gate with no validation payload and no validation
    artifact, and its code was already merged.

    A validation that did not run, or ran and did not pass, is a FAIL — it gets
    reported and pushed back, never advanced. So the packet must carry a truthy
    `validation.passed`.

    Only the verify gate is checked; earlier gates legitimately precede validation.
    """
    if (gate or "").strip().lower() != VERIFY_GATE:
        return None
    validation = (packet or {}).get("validation")
    if isinstance(validation, dict) and validation.get("passed"):
        return None
    return (f"{VERIFY_GATE} requires packet.validation.passed — refusing to open the "
            "operator's verify gate for an unvalidated change. A validation that did "
            "not run, or did not pass, is a FAIL: report it and push back instead of "
            "advancing.")
