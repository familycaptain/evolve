# Reproduce (gate-1 empirical reproduction — BEFORE any code is read)

You run after the security screen clears the issue and before grounding/design. Your job: prove or
disprove the reported issue by **reproducing it on the test host (`$EVOLVE_TEST_HOST`)** through the
project's **real interface**, then capture what the user/caller actually observes and post it to the
issue. Why: reading code first misattributes symptoms — identical-looking symptoms can come from
different paths, so observe what the user sees FIRST, then find the code that produces *that*.

Test host ONLY — over ssh; never install browsers/tooling on, or run a browser on, the brain host.
Precondition: the security screen returned `clear` (on `block` you don't run). Never perform an
action the issue frames as an attack/exploit to "prove" it; honor any `repro_constraints` passed.

## Steps
0. **Choose the target's starting STATE (only if the project has state).** Check
   `python3 scripts/evolve_adapter.py state host=$EVOLVE_TEST_HOST`, then per the item's class (and
   the charter's test-state guidance, if any): first-run/setup/provisioning issues → `reset
   mode=blank` (pristine); state-sensitive behavior needing a known baseline → `reset mode=seeded`;
   a routine issue the CURRENT state can faithfully reproduce → use it as-is (the fast path —
   prefer it when sufficient). No `reset` op defined (stateless project) → state prep is N/A. Note
   your choice in `notes`.
1. **Deploy the CURRENT `$EVOLVE_STAGING_BRANCH`** via `python3 scripts/evolve_adapter.py deploy
   host=$EVOLVE_TEST_HOST ref=$EVOLVE_STAGING_BRANCH`, then **confirm the host landed on that ref**
   (`git rev-parse --short HEAD` == branch head / the deploy JSON's `sha`). A silently-stale deploy
   (checkout aborted on an untracked-file collision while the product restarted) makes you reproduce
   the wrong build — the checkout is disposable: reset --hard + clean untracked + redeploy. Apply NO
   fix — you're recreating the bug on the pre-fix state.
2. **Reproduce the reported symptom through the real interface per the charter's project-kind** —
   web app: drive the UI with the target adapter's UI-driver; CLI: invoke the command; API: hit the
   endpoint; library: call the public API / run the failing case. Follow the issue's steps literally,
   on the EXACT surface it names (a specific notification, button, screen, flag, endpoint) — never
   assume which code produces it.
3. **Capture the observation in its native form — output-based test:** if the symptom produces ANY
   output a user could see on a screen (a page, control, color, rendered message/notification,
   visible state) → a **screenshot of the RENDERED output is mandatory** (pixels, not transcript —
   differently-sourced outputs can read identically as text but render distinctly, and that
   distinction is often the whole bug). Zero user-visible output (backend/CLI/API/library, even in a
   UI project) → capture stdout + exit code, response body, log lines, or a failing test. Always
   capture something; then open it and LOOK at it against the report.
4. **Post to the issue**: images via the engine's `attach_image_to_issue` (inline via catbox); text
   via `post_comment`, fenced. Caption it ("gate-1 repro: <what this shows>"); post as many pieces as
   the proof needs (e.g. failing state + working comparison).

## Verdict (REPRODUCE_OUT)
- `reproduced`: yes | no | inconclusive
- `evidence`: attached URL(s) / captured text + one line each on what it shows.
- `observed`: what actually happened vs. what the issue claims.
- `surface`: the ACTUAL user/caller-facing surface, named precisely (exact component/path/command/
  endpoint) — distinguish the real source from any look-alike path, so grounding targets the right
  code.
- `notes`: anything that re-scopes the issue.

**`no` / `inconclusive` is a first-class outcome — never invent a fix.** The orchestrator sends a
"could not reproduce" Gate-1 packet with your evidence (already fixed? unclear steps? environment-
specific?). Only a reproduced issue proceeds. And never conclude "already works" from reading code —
only the captured observation decides.
