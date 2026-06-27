---
name: evolve-prioritize
description: >
  Evolve funnel gate 3 — score/rank a surviving item; surface the top-N or park the long tail.
  Runs BEFORE the expensive spec phase (the attention valve). Invoked by `evolve`.
---

# Prioritize

Play the **Prioritize** agent. Canonical instructions: read `agents/prompts/prioritize.md`.

You run on the **raw issue** (no proposal yet) — so score on what you can actually judge:
- **impact / blast-radius** (how many of the surfaces the charter declares it touches; how core) — derive from the issue + a quick look at the code,
- **rough effort**, and **strategic fit** with the charter/thesis,
- plus any **DEMAND** signal you're *handed* (GitHub reactions, duplicate-cluster count). **Never
  invent reach** — if you weren't given demand data, say so and weight it as unknown.

Decision: `surface` (top-N / safety-critical → continue to the spec phase) | `park` (record + stop;
recoverable). Operator-authored items lean `surface` (they asked for it).

Emit JSON matching `PRIORITIZE_OUT` (`agents/registry.py`) to `$EVOLVE_STATE_DIR/<id>/prio.json`.
