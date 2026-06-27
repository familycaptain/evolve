---
name: run-evolve-tests
description: >
  Run Evolve's offline test suite (the cfs-store, process-engine, and agent-framework
  unit tests). Use to confirm a code change keeps the substrate green before handing
  off to a gate — the deterministic half of a spec's bound tests.
allowed-tools: Bash(python3 -m unittest*)
---

# Run the Evolve test suite

Pure stdlib `unittest` — no installs, no DB, no network:

```bash
python3 -m unittest discover -s tests
```

- A spec's bound `unit` tests live under `tests/<feature>/` (e.g.
  `tests/cfs_store/`, `tests/process_engine/`).
- Exit code 0 / `OK` = green. `FAILED` lists the failing cases — report them as the
  variance signal (a red bound test means the spec is not satisfied, EVOLVE.md §3).
- The live Anthropic test is gated behind `EVOLVE_LIVE_TESTS=1` and is skipped by
  default (don't run it just to check the substrate).

For browser/UI acceptance (Playwright on the test host) a separate validate-on-the-test-host
skill will exist once the brain-host/test-host environment is built.
