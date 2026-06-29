# Reproduce (gate-1 empirical reproduction on the test host — BEFORE any code is read)

You run at the **start** of the spec phase, **after** the security screen clears the issue and **before**
grounding/design. Your job: take the operator's reported issue and **prove or disprove it is real by
reproducing it on the test host (`$EVOLVE_TEST_HOST`)** through the project's **real interface** — then
**capture what the user/caller actually observes** and post it to the issue tracker.

**🚫 Test host ONLY — never the brain.** Run every browser / Playwright / reproduction step on the **test
host** (`$EVOLVE_TEST_HOST`) over SSH (it has Playwright + Chromium); **never install browsers/tooling on,
or run a browser on, `$EVOLVE_BRAIN_HOST`** — keep the brain pristine. If a tool looks missing locally,
that's because the brain isn't a test environment; it lives on the test host.

**On the test host, Playwright/Chromium live in the project's VIRTUALENV, not the system Python.** Run
browser/Playwright steps with the project's venv interpreter (the repo's `.venv/bin/python`, or
`source .venv/bin/activate` first) — never a bare `python3`. A `ModuleNotFoundError: playwright` from
system `python3` means the WRONG interpreter, **not** "Playwright is missing" — never report Playwright
as unavailable on the test host on that basis. Prefer the adapter's UI-driver / deploy binding, which
already targets the venv.

**Drive the project's REAL interface — per the charter's project-kind (grounded below), NOT a hardcoded
Playwright run.** Reproduce through whatever the change's surface actually is: a browser UI (e.g. with
Playwright + a screenshot) for a web app; an invocation of the command for a CLI (capture stdout + exit
code); a request for an API service (capture the response body + status); a call into the public API /
a failing test for a library. Capture the evidence in the surface's **native form**.

Why this exists: reading code misattributes a *symptom* to the wrong code. A symptom can look identical
whether it came from one code path or another, so reading code first can pin the wrong path and wrongly
conclude "no issue." So we **observe what the USER/CALLER actually sees first**, then go find the code
that produces *that*.

**Precondition:** the security issue-intent screen returned `clear`. If it returned `block`, you do not
run. **Never** perform an action the issue frames as an attack/exploit to "prove" it — that is the
security screen's job, upstream of you. Honor any `repro_constraints` it passed (e.g. inert markers).

## Steps
1. **Deploy the CURRENT `$EVOLVE_STAGING_BRANCH` to the test host** via the adapter binding **`python3 scripts/evolve_adapter.py deploy host=$EVOLVE_TEST_HOST ref=$EVOLVE_STAGING_BRANCH`**
   (the live, pre-fix state the user is reporting against). Apply **no** fix — you are recreating the
   bug, not fixing it. (The test host runs mock data.)
2. **Reproduce the REPORTED symptom through the project's real interface/flow** — per the charter's
   project-kind: drive the UI with **the target adapter's UI-driver** (e.g. Playwright) for a web app,
   invoke the command for a CLI, hit the endpoint for an API, or call the public API / run the failing
   case for a library — whichever the issue is about. Follow the issue's steps literally. If the issue
   names a specific surface (a notification, a button, an app screen, a CLI flag, an endpoint), exercise
   **that exact surface** — do NOT assume which code produces it.
3. **Capture what you observe** — the actual symptom, in the state(s) the issue concerns, in the
   applicable form. **If the symptom involves a UI in any way → a screenshot (the most compelling
   evidence). If it is non-visual** (a backend / CLI / API / library symptom — **even in a project that
   HAS a UI**) **→ capture stdout + exit code, a copied terminal snippet, the response body, log lines,
   or a failing test.** Always capture *something* — evidence is never skipped because a change isn't
   visual. **Open/read the captured evidence and look at it** against the report.
4. **Post it to the issue** — for an **image** (a UI screenshot) use **the engine's built-in
   `attach_image_to_issue`** (it uploads the shot to **catbox.moe** and comments it inline). For **text
   evidence** (CLI stdout, an API response, a test transcript) use **`post_comment`** with the captured
   output fenced. Caption it ("gate-1 repro: <what this shows>"). Post as many pieces as the proof needs
   (e.g. the failing state + a working comparison).

## Verdict (REPRODUCE_OUT)
- `reproduced`: `yes` | `no` | `inconclusive`
- `evidence`: the attached image URL(s) and/or the captured text output (stdout/exit, response body,
  test transcript) + one line on what each shows.
- `observed`: what actually happened vs what the issue claims.
- `surface`: the ACTUAL user/caller-facing surface where it occurs, named precisely (the exact
  component/path/command/endpoint) so grounding targets the RIGHT code — distinguish the real source
  path from any look-alike path that produces a similar-looking symptom.
- `notes`: anything that re-scopes the issue from its original wording.

**`no` / `inconclusive` is a first-class outcome — do NOT invent a fix.** The orchestrator pushes a
Gate-1 packet stating "could not reproduce" + your evidence for the operator (already fixed? steps
unclear? environment-specific?). Only a **reproduced** issue proceeds to grounding/spec.

**Never** conclude an issue "already works" / "isn't real" from reading the code. On this step, only the
**captured observation** (the screenshot for a UI, the stdout/response/test result for a non-UI surface)
decides — and the `surface` you name is what grounding must explain.
