---
name: evolve-reproduce
description: >
  Evolve spec phase — empirical reproduction on the test host, run after the security screen clears and BEFORE
  grounding/design. Deploys the current staging branch to the test host, drives the project's real interface
  (UI / CLI / API / library, per the charter) to reproduce the REPORTED symptom, captures what the user/caller
  observes (a screenshot, or stdout/response/test output), and posts it to the issue. Proves/disproves the issue
  is real and names the actual user-facing surface so grounding targets the right code. Done by the
  orchestrator (it drives the test host).
---

# Reproduce (gate-1 empirical reproduction)

Play the **reproduce** agent. Canonical instructions: `agents/prompts/reproduce.md`.

You run **after** `evolve-security-screen` returns `clear` and **before** `evolve-grounding`. You
observe what the USER/CALLER sees first — then grounding goes and finds the code that produces *that*.
This kills the "read code → misattribute the symptom → check the wrong code → wrongly conclude
no-issue" failure.

**🚫 NEVER run a browser / Playwright / any test on the brain (`$EVOLVE_BRAIN_HOST`); NEVER install
tooling there.** Everything runs on the **test host** (`$EVOLVE_TEST_HOST`) over SSH — it has Playwright +
Chromium; write any script and `ssh`/`scp` it there to run. "Missing" tooling on the brain is expected —
it lives on the test host; do NOT install it locally.

**Drive the project's REAL interface, per the charter's project-kind — not a hardcoded Playwright run.**
A web app → the browser UI (e.g. Playwright + a screenshot); a CLI → invoke the command (capture stdout
+ exit code); an API → hit the endpoint (capture the response body + status); a library → call its
public API / run the failing case. Capture the evidence in the surface's native form.

## Run it (orchestrator, shared conversation — it drives the test host, like validate)
0. **Ensure the test host is PREPARED — run the codified bootstrap, never improvise.** The test host
   must be a known, ready state (platform + all apps cloned from git, built, mock data seeded, the mock
   login user present). Run **`python3 scripts/evolve_adapter.py prepare host=$EVOLVE_TEST_HOST`** if the
   adapter defines `prepare` (it stands the host up from scratch — even from an empty `~/repos`, and
   creates the codified **QA login account**). **Drive login THROUGH the adapter's harness/`acceptance`
   op — it logs in as the QA account `prepare` created. Do NOT hand-roll a login, mint ad-hoc users, or
   guess a username/password.** If auth fails, the host isn't prepared — run `prepare`, don't improvise.
   **The test host has the product's background/scheduled AI work DISABLED by default** (autonomous
   agents / scheduled jobs / background processors are off so they don't burn API spend on mock data —
   only what's actively driven is on). If the issue you're reproducing IS one of those background
   features, enable **only** the specific one for the repro, then **turn it back OFF** afterward — never
   leave background AI work enabled on the test host.
1. Deploy the current pre-fix state, **no fix applied**. For a **platform** item, deploy its staging branch
   (`python3 scripts/evolve_adapter.py deploy host=$EVOLVE_TEST_HOST ref=$EVOLVE_STAGING_BRANCH`). For an
   **app/model** item, install the app under test at its **baseline** branch so you can reproduce against
   its current code: `python3 scripts/evolve_adapter.py deploy host=$EVOLVE_TEST_HOST ref=<app baseline> repo=<repo>`
   (this clones it into the host's `apps/<id>`). `prepare` set up the platform + seed; the app under test
   is installed here — sibling apps are NOT installed (one broken app shouldn't block your test).
2. Reproduce the reported symptom on the **exact surface** the issue names (a button/screen/refresh for
   a UI; a flag/command for a CLI; an endpoint for an API) via the surface's real driver — the target
   adapter's UI harness + Playwright for a UI, or the real command/endpoint/call otherwise — follow the
   issue's steps literally; honor any `repro_constraints` from the security screen.
3. Capture the actual symptom in its native form — **if it involves a UI in any way, a screenshot (most
   compelling); if it's non-visual (a backend/CLI/API/library symptom, even in a project that HAS a UI),
   stdout+exit / a terminal snippet / response / test output. Always capture something — never skip
   evidence because the change isn't visual.** **Look at it**; then post it to the issue via the engine's built-in
   `github_connector` — `attach_image_to_issue` for an image, `post_comment` for fenced text output
   (caption `gate-1 repro: …`).

Produce `REPRODUCE_OUT` (`agents/registry.py`): `reproduced` (`yes`/`no`/`inconclusive`),
`evidence` (catbox URLs), `observed`, `surface` (the precise real surface, for grounding), `notes`.
Save as `reproduce.json`.

- `reproduced=yes` → continue: `evolve-grounding` grounds in the code behind `surface`, then the rest
  of the spec phase.
- `reproduced=no`/`inconclusive` → **first-class outcome, do NOT invent a fix.** Orchestrator pushes a
  Gate-1 packet ("could not reproduce" + evidence) for the operator; `phase=gate1`, END.

NEVER conclude "already works" from reading code — only the captured observation (the screenshot for a
UI, the stdout/response/test result otherwise) decides.
