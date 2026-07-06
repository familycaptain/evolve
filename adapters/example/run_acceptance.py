#!/usr/bin/env python3
"""Neutral `acceptance` skeleton — the shape the engine expects, for ANY project kind.

The adapter.yaml `acceptance` op runs this with the target host in $EVOLVE_TARGET_HOST
and the spec/scenario id as argv[1]. Contract: drive the product the way a real
user/caller would, judge the result, and print ONE JSON line:

    {"passed": true|false, "evidence": ["<what you checked and saw>", ...]}

exit 0 when it ran (pass OR fail is a valid run), non-zero only when the acceptance
itself could not execute (that reads as "could not validate" — a failure, never a skip).

Fill in ONE of the patterns below for your project kind (delete the rest):

  * Web app  — drive the real UI headlessly (e.g. Playwright over ssh on the test
    host), assert what the user would see, screenshot the rendered result to a file
    the validate agent can attach to the issue.
  * CLI      — invoke the real command (locally or over ssh), assert stdout + exit code.
  * API      — make the real request, assert status + response body.
  * Library  — run the public-API test scenario (a failing→passing test is evidence).
  * No live interface at all — running the project's own test suite here is a valid
    tiered implementation.

Keep REUSABLE helpers (login, waits, drivers) in a shared harness module in this
directory so every future acceptance compounds instead of re-deriving them.
"""
import json
import os
import subprocess
import sys


def main() -> int:
    host = os.getenv("EVOLVE_TARGET_HOST", "")
    spec = sys.argv[1] if len(sys.argv) > 1 else ""
    if not host:
        print(json.dumps({"passed": False,
                          "evidence": ["EVOLVE_TARGET_HOST not set — cannot reach the product"]}))
        return 2

    evidence: list[str] = []
    passed = False

    # --- EXAMPLE (CLI-flavoured; replace with your project's real interface) ----
    # r = subprocess.run(["ssh", host, "myproject --version"],
    #                    capture_output=True, text=True, timeout=60)
    # evidence.append(f"`myproject --version` -> exit {r.returncode}: {r.stdout.strip()[:200]}")
    # passed = r.returncode == 0
    # -----------------------------------------------------------------------------
    evidence.append(f"skeleton ran for spec {spec!r} against {host!r} — implement your checks")

    print(json.dumps({"passed": passed, "evidence": evidence}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
