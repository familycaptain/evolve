---
name: evolve-validate
description: >
  Evolve build — validate a change on the test host TWO ways: (A) run its bound tests, and (B) drive the
  LIVE product through its real interface as a real user/caller (UI clicks + chat for a web app; the
  command for a CLI; the endpoint for an API; the public API for a library) and judge on captured
  evidence (the actual tool-calls / responses / stdout). Honest by construction: no bound test AND/OR a
  failed acceptance scenario is NOT green. Done by the orchestrator after implement.
---

# Validate (on the test host)

Play the **Validate** agent. Canonical instructions: read `agents/prompts/validate.md`.
**🚫 NEVER test on the brain. NEVER install Playwright/Chromium/browsers/test tooling on `$EVOLVE_BRAIN_HOST`
— keep it pristine.** The browser tooling already lives on the **test host** (`$EVOLVE_TEST_HOST`); drive it
**over SSH** — write any script you need and `ssh`/`scp` it to the test host to run THERE. If Playwright/
a browser looks "missing," that's because you're on the brain; it lives on the test host. Do NOT install
anything to make local testing work — there is no local testing.

The brain host (`$EVOLVE_BRAIN_HOST`) never validates itself — everything here runs on the test host
(`$EVOLVE_TEST_HOST`), which runs the live deployed product.

**Your TEST is yours to author; PRODUCT code is hands-off.** You MAY make the test robust — e.g. log
in **programmatically** (API auth + inject the token) when the login UI is racy under load and isn't
what's under test; that's fixing the TEST. You may NOT change application/product code or **redesign a
product subsystem** to pass — don't rewrite the product login because the theme test couldn't get past
it. A blocker that might be a **real product bug** → file an issue via the engine's built-in `github_connector`
even if you work around it in the test (never dismiss it as "just a test artifact"); a product that
genuinely doesn't work → `passed:
false` (blocked): file + name + push back. Product fixes/redesigns are separate items needing the
operator's **Gate-1**. "Validate a toggle" must never become "rebuild login."

## A) Bound tests (existing)
The target adapter's deploy/validate path: deploy the feature branch to the test host, run the
change's **bound tests** (unit via `unittest`, browser via Playwright), then reset to `$EVOLVE_STAGING_BRANCH`.

## B) LIVE acceptance — drive it like a user/caller (the real "does it actually work")
Bound tests are written by the *implement* agent and can be self-confirming. So ALSO exercise the
running product **through its real interface — per the charter's project-kind** (the browser UI + chat
for a web app; the command for a CLI; the endpoint for an API; the public API for a library) and judge
on **hard evidence** — the actual tool-calls / responses / stdout, not vibes. The target adapter's
deploy/validate/seed harness does the heavy lifting (drive it over ssh from the brain host). The steps
below describe the **web-UI** shape (the worked example); for a non-GUI project the same flow
runs against the adapter's `acceptance` op (which can simply run the project's real-interface tests) —
skip the UI-driver specifics:

0. **Ensure the test host is PREPARED first — run the codified bootstrap, don't improvise.** If the adapter
   defines `prepare`, run `python3 scripts/evolve_adapter.py prepare host=$EVOLVE_TEST_HOST` to stand the
   host up from scratch (platform built + seeded + the codified **QA login account** created).
   **Drive login THROUGH the adapter's harness/`acceptance` op — it logs in as the QA account `prepare`
   created. Never write your own login, mint ad-hoc users, or guess a username/password.** An auth
   failure means the host isn't prepared (run `prepare`), not that you need a new account.
   **The test host has the product's background/scheduled AI work DISABLED by default** (autonomous
   agents / scheduled jobs / background processors are off to avoid burning API spend on mock data —
   only what acceptance drives is on). If the change you're validating IS one of those background
   features, enable **only the specific one** you need for the test, then **turn it back OFF** when
   done — never leave background AI work enabled on the test host (it bleeds cost 24/7 on fakes).
1. **Deploy the change onto the live instance:** the adapter binding — `python3 scripts/evolve_adapter.py deploy host=$EVOLVE_TEST_HOST ref=<feature-branch>` —
   `git checkout` + the deploy command (`$EVOLVE_DEPLOY_CMD`, non-interactive) + waits until it's actually
   serving. (Code reset after via the adapter's reset.)
2. **Restore the data fixture (reproducible start):** the adapter binding — `python3 scripts/evolve_adapter.py seed host=$EVOLVE_TEST_HOST` — rolls the test host's
   DB back to a known baseline snapshot, so every run starts from an IDENTICAL state (the DB persists
   across deploys, so without this, data drifts run-to-run). Capture the baseline once with
   the adapter's snapshot step.
3. **Generate acceptance scenarios from the APPROVED spec/story** — a JSON list of scenarios, each a
   sequence of `steps`: UI actions (`open_app`, `click`, `fill`, `select`, `expect_ui`) and `chat`
   turns. **For chat, use VARIED phrasings** (how real users actually talk, not the literal wording)
   and assert the RIGHT outcome: `expect_tool` (which MCP tool must fire) + `expect_answer_contains`.
   This is what catches an intent path that string-matches instead of letting the LLM decide.
4. **Run it:** the adapter binding — `python3 scripts/evolve_adapter.py acceptance host=$EVOLVE_TEST_HOST spec=<file.json>` → returns a structured report
   with per-step pass/fail and the captured evidence (answer + `tool_calls` from the product's chat-history API).
5. **Judge** the report. Cap scenarios (~5–10 chat turns — bounded; the test host's agent spends API credits).

**Driving the real UI — use the hardened harness, not naive Playwright.** For UI steps prefer
the target adapter's UI harness (the `UI` class), which encodes the friction that makes naive automation
lie: React **controlled inputs** ignore `.fill()` → it sets the value via the native setter +
dispatches `input`/`change` so the form goes dirty and **Save un-disables**; **SPA nav is flaky** →
it clicks-and-waits-for-the-target with retries + overlay/Escape, not click+sleep; it finds a field
by the control after ANY element whose direct text matches the label; and it captures every console
error + **HTTP>=400** and screenshots failures to `/tmp/ui_*.png`. Host is `$EVOLVE_SERVER_URL` — point
it at the test host (`$EVOLVE_TEST_HOST`) for both the Gate-2 (feature branch) and Gate-3 pre-verify
(merged `$EVOLVE_STAGING_BRANCH`) passes.
(The operator's manual UAT box is *not* part of this automated loop.)
**Reusable scaffolding goes IN the harness, not a one-off.** If you build something future validations
will also need (a robust login, a wait/utility helper), add it to the target adapter's UI harness (the
`UI` class) so it compounds — don't bury it in this item's acceptance script to be re-derived next time.
E.g. robust auth is already the harness's programmatic `login()`; a `login_via_form()` drives the real
form only when login itself is under test.

**Behaviour is PROBABILISTIC — verify like it.** Re-run any scenario whose outcome can vary **N×
(≥3)**; a single green run is not proof (a real duplicate-write bug surfaced ~1 in 3). If a fix only
holds 2/3, it's **not** green — escalate. **Bug-scout:** if you trip over a bug **unrelated** to this
change (the change under test still works; this bug is independent), do NOT fix it and do NOT fail this
gate for it — **file it as its own issue via the engine's built-in `github_connector`** and keep going:
create an issue titled `<short title>` with body `<1-3 line desc + found while validating ev-<n>>` and
label `evolve-incidental` — note the # in your output.
(If instead the bug means the change UNDER TEST doesn't work → that's `passed:false`, not an incidental.)

**If it CAN be checked through the real interface, you MUST — a bound/unit test never substitutes.**
This doctrine is interface-shaped, per the charter's project-kind:

- **If the change involves a UI in any way** (a UI project, or any change to something a person sees or
  clicks — a UI file under `$EVOLVE_APP_GLOB` or web root, a new control, a visible state/behaviour):
  the live acceptance MUST exercise that exact thing **in the running UI** — click the real control,
  drive the real flow, and assert the rendered result the user would see (not just that a function
  returns the right value). A green unit/bound test for UI behaviour is **NOT sufficient**: a UI change
  validated only by unit tests is **NOT green**. For visual/appearance changes (themes, layout, states),
  additionally **capture before/after screenshots** (e.g. via `ui.shot(...)`) — always, not only on
  failure — and surface them so the operator can eyeball the actual look at verify.
- **If the change does NOT involve a UI** (a backend / CLI / API / library / pipeline change — **even
  inside a project that HAS a UI**, e.g. a backend-only bug): drive the project's real interface and
  judge on its captured output. Invoke the real command and assert stdout + exit code; hit the real
  endpoint and assert the response body + status; call the public API / run a failing→passing test.
  Capture that output as the evidence. A unit test that mocks away the real interface is **NOT
  sufficient** the same way a UI unit test isn't — exercise the thing the user/caller actually touches.

**Either way, evidence is posted to the GitHub issue — never skipped because the change isn't visual.**
Posting it is a REQUIRED output: your `evidence` field lists what you posted (catbox URL(s) and/or a
one-line description of each comment), and the loop will NOT push Gate 2 with an empty `evidence` — a
green verdict with no posted proof is treated as a FAIL, not a pass. Pair the after-evidence with the
gate-1 reproduce before-evidence so the issue shows the before→after the requester can verify.

Don't shrink scope to what's easy to assert; if the user/caller can observe it, prove it through the
real interface.

**Fail closed (either layer):**
- A change with **no bound test** → NOT green.
- **Validation that couldn't RUN is a FAIL, not a skip.** If the tests/acceptance can't execute —
  missing build/test tooling (e.g. no node to build the web bundle, no Playwright), or the test host
  target unavailable/occupied (e.g. uncommitted work you must not destroy) — emit `passed: false`
  with the blocker as the reason. Never proceed as if validated, never let a clean lint/dep-check/
  isolation result substitute, never hand it forward with a soft "verify later." Get the tool/target
  and re-run; flag the missing capability loudly.
- A change that touches the **real interface** with no live acceptance step that drives it → NOT green
  (a UI-affecting change with no live-UI step that clicks the real control; equally, a CLI/API/library
  change validated only by mocked unit tests with no real-interface invocation). Unit tests alone don't
  count for interface behaviour.
- Any **red** bound test, OR any **failed acceptance scenario** (wrong tool fired / answer or UI
  doesn't reflect the change) → NOT green; report it as the variance signal → back to implement.
- Only all-green (bound tests + acceptance) is green → Gate 2.

> The baseline fixture is captured once (the adapter's snapshot step) and restored per run (step 2);
> the acceptance scenarios are the agent's to author from the spec.

Emit `VALIDATE_OUT` (`agents/registry.py`) — `passed` + `failures` (include the failing
scenario's captured evidence). Save to `$EVOLVE_STATE_DIR/<id>/validate.json`.
