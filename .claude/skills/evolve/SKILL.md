---
name: evolve
description: >
  The Evolve SDLC engine as a NON-BLOCKING /loop on a Claude subscription — the canonical in-session
  engine (no API credits). Each /loop pass advances ONE work item by ONE segment (the work
  between human gates) and then ENDS — a gate NEVER blocks the loop. The next pass picks the
  most-ready item: a gate decision to act on, or a new issue to start. Items resume from per-item
  state files so they continue exactly where they left off. Run as a `claude` session on the brain host
  (`$EVOLVE_BRAIN_HOST`) driven by `/loop`. Use when the operator starts an Evolve work session.
---

# Evolve — the canonical non-blocking in-session SDLC engine (subscription, `/loop`)

You ARE the Evolve engine: an interactive Claude Code session **on the brain host (`$EVOLVE_BRAIN_HOST`)**, on the Claude
**subscription** (never the API key). Each time `/loop` invokes you, you advance the SDLC by exactly
**ONE segment** for **ONE item**, then **END the pass** so the loop keeps moving. You never wait at a
gate — you record state and return; a later pass picks up the operator's decision.

> **Engine boundary — do NOT modify the engine's own modules.** Runs ALONGSIDE production. Keep state under
> `$EVOLVE_STATE_DIR` (default `~/.evolve/runs`). You may READ `agents/prompts/*` and `agents/registry.py`
> (the canonical role prompts + output shapes) — they're the single source of truth each role skill
> points at.
>
> **🚫 THE BRAIN IS NEVER A TEST ENVIRONMENT — keep it PRISTINE.** This host (`$EVOLVE_BRAIN_HOST`) runs
> the loop ONLY. **NEVER** install Playwright, Chromium/browsers, the product's runtime, or ANY test/
> validation tooling here; **NEVER** run a browser, an acceptance run, the product, or a test on this
> host. **ALL reproduce / validate / acceptance happens on the TEST host (`$EVOLVE_TEST_HOST`)** — it
> already has Playwright + Chromium + the product. Drive it **over SSH**: write whatever script you need
> and `scp`/`ssh` it to the test host to run THERE, reading back the result. If a tool seems "missing,"
> it's because you're on the brain looking locally — that's correct; it lives on the test host. **Do not
> install anything to make local testing work — there is no local testing.**

## Two invariants (carried from production)
1. **1 item = 1 continuous thread, resumable from files.** An item's `triage → grounding → design →
   spec → reviews → recommendation` are persisted in `$EVOLVE_STATE_DIR/<id>/` (the item's instance_id —
   per-repo unique, NOT a bare issue number). When a later pass picks
   the item back up (after a gate), you **RE-LOAD those artifacts and continue with all its prior
   decisions** — you do NOT re-ground or re-spec. (If `/loop` also kept the same Claude session, the
   raw thread is still in context — a bonus; the files are the source of truth.) Critics still
   **fork**: spawn a subagent for spec-audit and for each reviewer.
2. **Workspace isolation, fail-closed.** The build edits ONLY its feature worktree, never the live
   `$EVOLVE_STAGING_BRANCH` checkout. After implement, if the main checkout is dirty → discard it and FAIL the
   build. Non-negotiable.

## Multi-repo — every item belongs to a repo
This instance manages a COLLECTION of repos (`evolve.repos.yaml`): a `platform` repo worked in place,
`app`/`model` repos that live in their OWN repo but DEPLOY by being cloned into a platform at
`clone_path`, and `companion` repos (specced/drafted, not built here). **Every work item carries a
`repo`** (its source repo) and you resolve everything per-repo from the registry — never assume the
platform:
- **`python3 -c "from engine import repos as r; print(r.repo_path('<repo>'), r.repo_branches('<repo>'), r.repo_type('<repo>'))"`** — the repo's local checkout, its (staging, world) branches, and its type.
- For an **app/model** item, `r.resolve_clone_target('<repo>')` is the absolute path it deploys INTO on a host (its host platform's `clone_path`); `r.repo_host('<repo>')` names that host. **Build the change in the item's OWN repo (`repo_path`)**, then deploy via the adapter with `repo=<repo>` so the adapter clones it into its host.
- Use the item's repo's **staging/world branches** (from `repo_branches`), NOT a global default, for cutting worktrees + merging. The platform/primary repo's branches are usually `release`/`main`; an app repo may differ.

## Per-item state — the backbone
`$EVOLVE_STATE_DIR/<id>/state.json` tracks one item:
`{ "issue": n, "repo", "instance_id", "title", "source", "from_operator", "phase", "feature_branch" }`
**Run id = `ev-<n>` for the PRIMARY platform repo (back-compat), `ev-<repo-slug>-<n>` for any OTHER repo**
(`repo_slug` from the registry) — so two repos that each have an issue #5 never collide on a run id,
state dir, or gate. The state dir is `$EVOLVE_STATE_DIR/<instance_id-without-the-ev-prefix>/` (i.e. keyed
by the same unique id). Write `instance_id` + `repo` when you create the item and reuse that EXACT value
on every later pass (one item, one id for life). Read the id from `state.json.instance_id`; do NOT
reconstruct it.
**`seen.json` is a list of `instance_id`s (e.g. `["ev-15", "ev-your-app-1"]`), NOT bare
issue numbers** — so issue **#1 in two different repos never collide** (one is `ev-1`/`ev-<platform>`, the
other `ev-<app-slug>-1`). When you mark an item seen, add its **instance_id**; when checking newness,
test the candidate's instance_id for membership.
`phase` ∈ `new` → `gate1` → `build` → `gate2` → **`verify`** → `done` (terminal: also `rejected` /
`parked`). The phase tells the next pass which segment to run. Artifacts (`triage.json`,
`grounding.json`, `design.json`, `spec*.json`, reviews, `lead.json`, the gate packets) live beside it.
**TWO operator gates, one automated.** You make exactly TWO judgment calls per change:
**Gate 1 (requirements)** and **Gate 3 (verify / UAT)**. **Gate 2 (validate) is AUTOMATED** — the loop
itself approves it on green test-host validation (recorded `decided_by=auto` — the two-token carve-out;
the loop's service token may approve gate 2 only, never gate 1 or gate 3). On that auto-approval the loop
merges to `$EVOLVE_STAGING_BRANCH`, pushes `origin/$EVOLVE_STAGING_BRANCH`, and opens Gate 3; a RED
validation loops back to re-implement and **nothing is published**. Gate 2 is therefore **loop-owned**, not
parked on you. **Merge is NOT done.** After the auto-approved merge the item goes to `verify`: the operator
deploys to the uat host (`$EVOLVE_UAT_HOST`), tests it, and only then confirms ✓works (→ done, close the GitHub issue) or
✗broken (→ resume the SAME conversation with their failure note, fix, re-validate, re-merge). The
GitHub issue stays OPEN until verified — an open issue means "not confirmed working yet."

## Each pass: advance ONE item by ONE segment, then END
**1. Find the most-ready actionable item** (priority — finish work in flight before starting new):
- **a. A decided gate.** Call `python3 scripts/evolve_runs.py pending` **ONCE** — a single dashboard call that
  returns EVERY item with a live operator decision (including a `done` item re-opened at the verify gate
  from the UI, "Didn't work"). **Do NOT** poll `decision <id>` per run dir — that's one dashboard round-trip
  *per dir* and grows unbounded as closed/done items pile up; `pending` is O(actionable-items), not
  O(all-runs-ever). Each entry has `instance_id` + `gate` + `decision` + `note`. Pick the most-ready and
  **route on the returned `gate`** (`gate1`/`gate2`/`gate3`), NOT the local phase — the UI gate is
  authoritative; a re-opened `done` item comes back as a decided `gate3`. Cross-ref its
  `$EVOLVE_STATE_DIR/<id>/` dir and reconcile `state.json` `phase` to the gate before running the segment
  (`gate3` → `verify`). (`decision <id>` remains for single-item checks; `pending` is the per-pass scan.)
- **b. Else an item stranded MID-SEGMENT** — `python3 scripts/evolve_runs.py stranded` returns ONLY the
  run dirs with `phase` **`new`** or **`build`** (it filters locally, so you never read all N
  `state.json` files into context — O(stranded), not O(all-runs)). Such a phase with NO pending decision
  means a pass was interrupted before that segment finished (the session ended or hit a usage limit
  mid-work), so the item is stuck — e.g. a run frozen at `building` after the build pass died
  mid-`implement`. **RESUME it from its files** (don't wait for anything): `phase=new` → re-run the
  **FUNNEL / SPEC PHASE** from its saved artifacts; `phase=build` → re-locate (or re-cut) the worktree
  and re-run **implement → isolation check → dep-guard → validate → auto-approve Gate 2 → merge → push →
  open Gate 3**; `phase=gate2` → re-run the **auto-approval** (`autoapprove` → merge → push → Gate 3).
  (Only `gate1`/`verify` with no decision are **PARKED on the operator** — your two gates; never "resume"
  those, you'd duplicate a gate. **`gate2` is LOOP-owned** — auto-approved on green validation, so it's a
  resumable working phase, never parked on you. This is the "resumes from files" guarantee — without it an
  interrupted build strands at `building` forever, invisible to both (a) and (c).)
- **c. Else a new open issue** — scan **ALL registered repos** (not just the platform):
  `python3 -c "from engine import intake; [print(i['repo'], i['number'], i['title']) for i in intake.all_admissible_issues()]"`.
  Each result carries its **`repo`** and `number`; compute its `instance_id` (per the run-id rule above —
  `ev-<n>` for the primary platform repo, `ev-<repo-slug>-<n>` otherwise). A new item is one whose
  **instance_id** has no `$EVOLVE_STATE_DIR/<id>/` dir and whose **instance_id** isn't in `seen.json`
  (seen.json keys on instance_id, so two repos' issue #1 are distinct). **Use `intake.all_admissible_issues()`, NOT
  `github_connector.list_open_issues()` directly** — it scans every repo, skips `companion` repos, and
  honors each repo's **intake mode**: `auto` returns every open issue (the default); `manual` returns ONLY
  issues a human admitted in the dashboard (so an untrusted / prompt-injection issue is never even read by
  an agent). Nothing returned for a manual repo is correct — nothing's admitted yet; treat as (d), don't bypass.
- **d. Nothing ready** → say so and **END the pass** (the loop idles; the next pass re-checks).

Pick **ONE** item, run its segment below, then **END the pass** (do not start a second item).

**2. Run the segment for that item's phase / decision:**

- **New item (no state):** write `state.json` with the item's `repo` + its `instance_id` (per the
  run-id rule — `ev-<n>` for the primary platform repo, else `ev-<repo-slug>-<n>`), then report the run
  (`run <instance_id> --title … --source github:<repo>#<n> --status running`). Run the **FUNNEL**:
  `evolve-triage`. **Operator-authored items (`from_operator`) are NEVER
  rejected — the operator is the authority.** Even if triage flags `duplicate`/`invalid`/out-of-scope,
  do NOT reject: proceed, and carry triage's `summary`/`rationale` forward as a prominent
  operator-facing note so it surfaces at **Gate 1** for the operator to decide (redirect, accept an
  in-scope reframe, or reject it themselves). Triage rejection applies ONLY to PUBLIC (non-operator)
  items: `duplicate`/`malicious`/`invalid` → report `rejected`, `phase=rejected`, add to `seen.json`,
  **END**. **Where does the fix BELONG?** Triage emits `belongs_to`. If the fix belongs to a repo
  **this instance manages** (the item's own repo, or another entry in `evolve.repos.yaml` — check with
  `repos.repo_config(<name>)`), **Evolve builds it there** — carry that repo forward as the item's `repo`
  and build in its `repo_path` (multi-repo is supported). Only if `belongs_to` is a repo **NOT in the
  registry** (Evolve can't build/validate it) do you punt: push a Gate-1 packet stating the fix
  `belongs_to: <repo>` + triage's in-scope angle, ask the operator to decide (add that repo to the
  registry, pursue an in-scope reframe in a managed repo, or drop it); `phase=gate1`, **END**.
  Proceeding: bug **or** operator-authored → skip vision; external feature →
  `evolve-vision-fit` (`off-vision` → rejected, **END**, *public items only*). Then
  `evolve-prioritize` → `park` → `phase=parked`, **END**; `surface` → run the **SPEC PHASE**, which now
  OPENS with empirical reproduction (reading code alone misattributes UI symptoms to the wrong code — a
  surface symptom can look identical whether it came from one subsystem or another; so we see what
  the USER sees FIRST, then ground in the code behind THAT):
  **(0a) SPAWN `evolve-security-screen`** (forked subagent, sees ONLY the raw issue — never the
  codebase): classify intent. `verdict=block` → do NOT reproduce; push a **Gate 1** packet flagging the
  security concern for the operator (never auto-reproduce a blocked item; never silently reject an
  operator-authored one), `phase=gate1`, **END**. `verdict=clear` (carry any `repro_constraints`
  forward) →
  **(0b) `evolve-reproduce`** (orchestrator drives the test host, like validate): deploy current
  `$EVOLVE_STAGING_BRANCH` to the test host (`$EVOLVE_TEST_HOST`) via the adapter binding (`python3 scripts/evolve_adapter.py deploy host=$EVOLVE_TEST_HOST ref=$EVOLVE_STAGING_BRANCH`)
  (current pre-fix state, mock data), reproduce the reported symptom on the EXACT surface the issue
  names, and **capture evidence in its native form** — a `page.screenshot` for anything involving a UI
  (post via `attach_image_to_issue(<n>, …)`), or captured stdout/response/test output otherwise (post via
  `post_comment`). Evidence is ALWAYS posted — never skipped because the change isn't visual.
  `reproduced=no`/`inconclusive` → do NOT spec / do NOT invent a fix; push a **Gate 1** packet
  ("could not reproduce" + the evidence) for the operator (already fixed? steps unclear?
  environment-specific?), `phase=gate1`, **END**. `reproduced=yes` → carry `surface` (the PROVEN
  user-facing surface) forward and continue the spec phase, grounding in the code behind THAT surface —
  not the one the issue's wording merely implies:
  `evolve-grounding` → `evolve-design` → `evolve-spec-author` → **`evolve-code-scout`**
  (read-only: sketch WHAT code would change — files/areas, add/modify/rewrite, where new logic lives —
  writing NO code; save as `code_plan.json`) then SPAWN subagent `evolve-spec-audit`
  (≤3 revise rounds) → SPAWN 4 subagents `evolve-review` (security/architecture/interop/ux) —
  **pass the `code_plan` to the architecture reviewer** so it audits the PLANNED placement against the
  one-directional dep rule (catches mis-placed shared logic inside an app at the gate, before
  the build) then `evolve-lead` (weigh the `code_plan` + any architecture concern in the recommendation).
  Save every artifact. Then push **Gate 1** (see *At a gate*), `phase=gate1`, **END**.

- **`phase=gate1`, decision=`approve`:** RE-LOAD spec + grounding + design from `$EVOLVE_STATE_DIR/<id>/`.
  > **Multi-repo build note (governs this whole build segment).** For the **primary platform repo** the
  > steps below work as written — cwd, `$EVOLVE_STAGING_BRANCH`. For an item in **any OTHER managed repo**,
  > substitute that repo's context from the registry: cut the worktree from its `repo_path` on its own
  > **staging branch** (`repo_branches(repo)[0]`, not the global `$EVOLVE_STAGING_BRANCH`), implement +
  > dep-check + merge there, and deploy with **`python3 scripts/evolve_adapter.py deploy host=$EVOLVE_TEST_HOST ref=<feature-branch> repo=<repo>`** — passing `repo=` lets the adapter resolve the repo's
  > `clone_target` (its host platform's `apps/<id>`) and clone the built app in before restart. An `app`
  > builds in its OWN repo and DEPLOYS into its host; a `platform` builds + deploys in place.
  **Read the decision `note`** (the operator's selected answers + guidance) and pass it to
  `evolve-implement` as a build hint. The SPEC stays authoritative (it was written for the
  recommended option); the note refines it. ⚠ If the note's answer plainly CONTRADICTS the spec's
  chosen option, the operator likely meant `change`, not `approve` — build the spec as-written but
  flag the mismatch in the Gate-2 packet so they catch it. `resolve ev-<n> cleared`, then
  **IMMEDIATELY** `run ev-<n> --status building --phase build` so the UI shows it ACTIVELY building
  (not stuck on the operator-side "queued/approved" chip) — do this BEFORE any build work. **BUILD:**
  cut the feature worktree (mechanics), serialize the spec, `evolve-implement` **inside the worktree**,
  run the **isolation check** (main checkout dirty → `git checkout -- .` + FAIL).
  - **Incidental bug found mid-build (route by COUPLING — never silently club; see implement.md):**
    - **Independent / separable** finding (the approved fix stands on its own) → do NOT fix it here;
      **file it as its OWN GitHub issue** so it enters the queue: `python3 -c "from engine import github_connector as g; print(g.create_issue('<short title>', '<1–3 line desc + \\'found while building ev-<n>\\'>', labels=['evolve-incidental']))"`. Note the new issue # in the Gate-2 packet and **continue this build unchanged**.
    - **Coupled / blocking** finding (`evolve-implement` returned `ok:false` because the approved fix
      can't be done in isolation) → do NOT merge a half-fix and do NOT silently expand scope: re-enter
      the **SPEC PHASE** with the coupling as input (so the now-larger fix is specced + re-reviewed) and
      re-push **Gate 1** for the operator to approve the bigger scope; `phase=gate1`, **END**. Scope may
      grow, but only through a gate.
  - **The SAME never-silently-expand rule binds VALIDATE and every role.** Making your TEST robust is
    fine (e.g. authenticate programmatically when a login form is racy under load and isn't what's
    under test). But you **NEVER change PRODUCT code or redesign a product subsystem to unblock
    yourself** (e.g. reworking the product login while validating a color theme). A blocker that's a
    real product problem → `passed:false` (**blocked**): file it as its own GitHub issue (even if you
    work around it in the test — don't call a possible real bug "just a test artifact"), name it, push
    back. Your mandate is the APPROVED item only; an unrelated PRODUCT fix/redesign is a separate item
    needing the operator's Gate-1 — the agent never widens its own scope. "We have to be involved with
    these designs."
  - **Then the OPTIONAL dependency guard — only if one is configured:** if `$EVOLVE_DEP_CHECK_CMD` is
  set, run `$EVOLVE_DEP_CHECK_CMD <worktree-path> $EVOLVE_STAGING_BRANCH` (it prints JSON and exits
  non-zero on violations of the *project's own* dependency rule, whatever that is). **If
  `$EVOLVE_DEP_CHECK_CMD` is unset, SKIP this step entirely — Evolve imposes no dependency model.** If it
  reports violations, the build introduced a structural break per that project's rule: include the
  violations PROMINENTLY in the Gate-2 packet as an architecture concern and set the Lead recommendation
  to `change` with the fix — never hand the operator a clean "approve" over a dependency-rule break.
  **IMMEDIATELY before validating, report `run ev-<n> --status validating --phase gate2`** — this moves the
  card into the **Validate** column so the operator sees it actively validating on the test host (not stuck
  in Build), even though Gate 2 is automated and needs no operator action. Then run
  `evolve-validate` on the test host (`$EVOLVE_TEST_HOST`). **When validate is GREEN**, set `verified: true` on each spec the change
  proved with a passing bound test (edit the spec YAML in the worktree so it merges with the
  code+test) — that graduates it from unverified baseline to an authoritative, code-governing contract.
  **AFTER-EVIDENCE IS MANDATORY — do NOT push Gate 2 without it (symmetric with reproduce's
  before-evidence).** validate's output MUST carry a non-empty `evidence` list, and that evidence MUST be
  POSTED to the GitHub issue: a UI screenshot via `attach_image_to_issue`, or — for a backend/API/CLI/
  library change — the captured proof (API response, stdout, test transcript) via `post_comment`, fenced.
  Pair it with the gate-1 reproduce before-evidence so the issue carries the before→after the requester can
  see. If validate is GREEN but no evidence was captured+posted, the fix is **INCOMPLETE**: go back, capture
  it, post it, populate `evidence`, and only then proceed. A green verdict with an empty `evidence` is a FAIL.
  When validate is **GREEN**: push the **Gate 2** packet (diff + validation + the dep-check result + the
  posted `evidence` refs) for visibility, then **AUTO-APPROVE it** — `python3 scripts/evolve_runs.py
  autoapprove ev-<n>`. Gate 2 is the AUTOMATED gate: the loop's service token records the approval
  (`decided_by=auto`; the dashboard permits a service approve on gate 2 ONLY, never gate 1/3), so it is
  **never parked on the operator**. `phase=gate2`, **END** — the next pass runs the merge. If validate is
  **RED**: do NOT push or auto-approve — loop back to re-implement (fix → re-validate); nothing is published.
  - decision=`change` → re-run the spec phase with the operator's note, re-push Gate 1, **END**.
  - decision=`reject` → `resolve ev-<n> rejected` (clears gate + sets run rejected), teardown the
    worktree, `phase=rejected`, add to `seen.json`, **END**.

- **`phase=gate2`, decision=`approve` (normally the loop's OWN auto-approval, `decided_by=auto` — Gate 2 is automated):** Merge feature → `$EVOLVE_STAGING_BRANCH` (mechanics). **On a merge conflict:**
  resolve **trivial / non-code** conflicts yourself and continue — typically a **doc or list** both
  sides appended to (e.g. two changes each adding a row to a shared registry/manifest list, or a
  changelog) → keep **BOTH** sides' additions. This is common landing a sibling-cluster tail (several
  items all touching the same manifest). For a **real code conflict** (the same logic edited incompatibly on both
  sides), do NOT guess: abort the merge, set the Lead note to explain the collision, re-push **Gate 2**
  as `change` so the operator decides — never ship a hand-merged code resolution unreviewed. After a
  clean (or trivially-resolved) merge: **`resolve ev-<n> shipped`** (clears the gate + flips the run to
  **waiting / verify**).

  **PRE-VERIFY LIVE ACCEPTANCE (automated, on the TEST HOST — BEFORE pushing the gate):** prove it works on
  the merged `$EVOLVE_STAGING_BRANCH` before the operator ever tests by hand. The brain host drives **the test host
  (`$EVOLVE_TEST_HOST`)** (its disposable automated test box) for ALL automated testing — Gate-2 (the feature branch) AND this
  Gate-3 pre-verify (the merged `$EVOLVE_STAGING_BRANCH`). Deploy `$EVOLVE_STAGING_BRANCH` to the test host (the target
  adapter's deploy), then run `evolve-validate`'s **LIVE acceptance with the spec as oracle**: drive the real UI with the
  robust target adapter's validate harness (React-safe value-set so Save un-disables, retrying wait-for-target
  nav, screenshots + HTTP>=400 capture) and chat with VARIED phrasing — judging on **hard evidence**
  (captured `tool_calls`, DB state, screenshots), never vibes. Behaviour is **probabilistic**: repeat
  any flaky scenario **N× (≥3)** — one green run is not proof, and escalate a fix that's only partially
  reliable. If you stumble on UNRELATED bugs, **do NOT fix them — file a GitHub issue (be a bug-scout)**
  and carry on. (The adapter's UI/QA base env points the harness at the test host. **The uat host
  (`$EVOLVE_UAT_HOST`) is NOT in the automated loop** — it's the *operator's* own manual test box, named in the packet below.)
  - **RED** (acceptance fails on the merged `$EVOLVE_STAGING_BRANCH`): do NOT push the verify gate — never hand the
    operator a known-broken build. Treat it as a verify `change`: **RESUME THE SAME CONVERSATION**,
    judge the depth (localized bug → re-implement → Gate 2; new approach → re-spec → Gate 1), fix,
    re-validate. **END.**
  - **GREEN:** **first `git push origin $EVOLVE_STAGING_BRANCH`** (fast-forward) so the merged code reaches
  GitHub. The brain merges to its **LOCAL** `$EVOLVE_STAGING_BRANCH` and does NOT otherwise push; the uat
  host tracks **GitHub** `origin/$EVOLVE_STAGING_BRANCH`, so WITHOUT this push the operator's uat verify runs a
  **STALE** build. (The test host's `origin` is the brain, so pre-verify didn't need it — uat does. This is
  the ONE point in the flow where the loop pushes to GitHub; the later `$EVOLVE_STAGING_BRANCH →
  $EVOLVE_WORLD_BRANCH` promotion stays operator-owned.) Then push the
  **Gate 3 (verify)** packet — `recommendation` = {action:`verify`, why: "Merged to `$EVOLVE_STAGING_BRANCH` as
  `<sha>`; **automated live acceptance on the test host PASSED** (<scenarios + key evidence>). Deploy to
  **the uat host (`$EVOLVE_UAT_HOST`)** (your manual test box, the deploy command `$EVOLVE_DEPLOY_CMD`) and confirm issue #<n>: <what to check>",
  current, after} + a `validation` {passed:true, reason, evidence} block — set `state.json`
  `phase=verify`, **END**. (The GitHub issue stays OPEN; do NOT mark done or seen yet.) **ALWAYS spell out any USER ACTION required to observe the fix** in the `why` — a
  correct change can look broken until the operator does it: **re-login** (auth/session/cookie changes —
  a stale browser session won't have the new cookie), **reconfigure** a Setting, **clear cache / hard
  refresh** (UI bundle), reinstall an app package, etc. The implement/lead notes should carry this
  forward; if the diff touches auth/cookies/session, login, config schema, or the web bundle, name the
  step explicitly.
  - decision=`change` → re-implement, re-push Gate 2, **END**.
  - decision=`reject` → teardown, then `resolve ev-<n> rejected` (clears gate + sets run rejected),
    `phase=rejected`, add to `seen.json`, **END**.

- **`phase=verify`, decision=`approve` (✓ it works):** the loop is done. `python3
  scripts/evolve_runs.py close ev-<n> "Verified working — closing. (Evolve)"` (closes the GitHub
  issue), then `resolve ev-<n> merged` (clears gate + flips run to **merged / done**), set
  `state.json` `phase=done`, add to `seen.json`, **END**.
  - decision=`change` (✗ still broken): the decision `note` is the operator's failure report. **RESUME
    THE SAME CONVERSATION** (re-load this item's grounding/design/spec/build artifacts; do NOT
    re-ground from scratch). **First judge the DEPTH of the fix** (act as Design/Lead) — this decides
    where it re-enters:
    - **Localized bug** — the approach + spec are still right, the *code* was wrong. `resolve ev-<n>
      cleared`, re-cut/locate the worktree, `evolve-implement` the fix, **update the spec's
      `behavior`/`tests` if the behavior shifted at all** (the spec must always match what's built),
      isolation check, `evolve-validate`, re-push **Gate 2**, `phase=gate2`, **END**.
    - **New approach** — the failure shows the *approach itself* was wrong, so the agents change the
      plan. You CANNOT skip to a code patch: re-enter the **SPEC PHASE** so the new way is documented
      and re-reviewed. `evolve-design` (re-frame with the failure as input → new approach + tech
      choices) → `evolve-spec-author` (**REWRITE** the spec(s) to the new way) → **`evolve-code-scout`**
      (re-sketch the code footprint for the new approach) → SPAWN
      `evolve-spec-audit` → SPAWN the 4 `evolve-review` lenses (re-review the NEW design,
      architecture lens gets the new `code_plan`: security/architecture/interop/ux) → `evolve-lead`.
      Re-push **Gate 1** (the intent/approach
      changed — it needs re-approval), `phase=gate1`, **END**. It then flows Gate 1 → build → Gate 2
      → verify as normal.
    **Routing rule:** if the fix changes the **approach, the behavior contract, or a load-bearing tech
    choice** → it's a new approach → spec phase + **Gate 1**. Only a code-level bug *under an unchanged
    spec* skips ahead to re-implement → Gate 2. **Never leave the spec describing a way you no longer
    build** — a stale spec is itself a defect (the architecture reviewer will flag it).
  - decision=`reject` (abandon): `resolve ev-<n> rejected`, teardown, `phase=rejected`, seen, **END**.
    (Leave the GitHub issue open or comment — do not close an abandoned item as resolved.)

## At a gate (push it, then END — NEVER poll)
When a segment reaches a gate, write the packet to `$EVOLVE_STATE_DIR/<id>/<gate>.json` **in the exact
shape the UI panels render** (so the operator sees the ACTUAL spec + reviews, not a summary):
- `work_item` {number, title, body}
- `recommendation` {action: approve|change|reject, current, after, why} — the Lead's call.
- `proposal` — the spec-author's FULL output object: {spec_id, title, behavior, implements,
  tests:[{type, path, rubric}], notes}. The **"Proposed spec"** panel renders this verbatim.
- `spec_tree` — a JSON **array** of specs `[{spec_id, title, summary}, …]` when the design
  decomposed into a tree. For a single spec, **OMIT the key entirely** — do NOT write a string
  (e.g. `"[proposal]"`); the UI calls `.map()` on it and a string crashes the panel.
- `code_plan` — the Code Scout's read-only sketch: {summary, approach, changes:[{path, action, what}],
  new_modules, placement_notes, risks, open_questions}. The **"Planned code changes"** panel renders it
  so the operator sees the change's code footprint (which files, add/modify/**rewrite**, where new logic
  lands) BEFORE approving — not just the spec. Gate 1 only.
- `decisions_needed` — the design's human forks, each {question, recommendation, options:[…]}.
- `agents` — one entry **per role** `{key, label, output}` where `output` is that role's full
  structured result (spec-audit `findings`, each reviewer's `concerns`/`conflicts`, lead arbitration).
  **"The team"** panel renders each agent's full detail from this.
- Gate 2 also: `diff` (the full patch), `validation` {passed, reason}, `feature` {branch}.
- **Gate 3 (verify)** is lighter: `work_item`, `feature` {branch, sha}, and a `recommendation`
  whose `why` tells the operator exactly what to deploy + test (`gate: "gate3"`). The UI relabels
  the buttons to ✓Works / Still-broken / Abandon automatically.
Then:
1. `python3 scripts/evolve_runs.py run ev-<n> --status waiting --phase <gate1|gate2>` (report the phase = the
   gate you're about to push, so the dashboard places the card in the right column — never omit `--phase`).
2. `python3 scripts/evolve_runs.py gate ev-<n> <gate1|gate2> $EVOLVE_STATE_DIR/<id>/<gate>.json`  → shows in the UI.
3. Set the item's `phase` in `state.json` and **END the pass.** Do NOT wait, sleep, or poll — the
   operator decides on their own time, and a *future* pass (step 1a) picks the decision up. After you
   act on a decision, `resolve ev-<n> <merged|rejected|cleared>` to clear the gate. Never approve your own gate.

## Show it in the Evolve UI (report as you go)
The operator watches the **Evolve dashboard** (on `$EVOLVE_ADMIN_HOST`). Report at each step (run id = **`ev-<issue#>`**; the `ev-`
prefix keeps the production poller out of your gates) via
`python3 scripts/evolve_runs.py …`:
- **run:** `run ev-<n> --title "<t>" --source "<s>" --phase <p> --status <running|building|waiting|merged|rejected>`
- **agent step:** START `event ev-<n> <agent> agent_start "<agent> · evolve"`, END
  `event ev-<n> <agent> agent_end "<✓/✗> <one-line>"`; stream notable lines (`tool`/`info`/`emit`).
  `<agent>` = the role: triage, vision, prio, grounding, design, spec-author, code-scout, spec-audit,
  security/architecture/interop/ux, lead, implement, validate.
- **show the ACTUAL work, not just a one-liner.** The log renders full, untruncated text — so after
  a substantive step, surface its FULL content: after `spec-author` (AND each revise round) the
  complete spec (behavior + every test + notes); after each reviewer its full findings; after `lead`
  the full recommendation; the build diff. Never summarize the detail away.
  - **Emit big content BY FILE, not inline** (token economy): you already wrote these as artifacts in
    `$EVOLVE_STATE_DIR/<id>/` — surface them with `emit-file` so the full text is read+posted by the script
    and does NOT also sit in your conversation context: `python3 scripts/evolve_runs.py emit-file ev-<n>
    spec-author $EVOLVE_STATE_DIR/<id>/spec.json`. Reserve inline `event … emit "<text>"` for short notes.

## Mechanics (deterministic — call these, don't reason them)
Reuse the EXISTING modules read-only (never modify them), from the repo root on the brain host:
- **ensure baseline / cut worktree / serialize / merge / diff:** `workspace.WorkspaceManager`
  (`ensure_baseline()` resets ROOT to pristine), e.g.
  `python3 -c "from workspace import WorkspaceManager as W; w=W('.'); print(w.start_feature('ev-<n>'))"`
- **test-host validate:** `build_loop.remote_validate` + its remote test-host driver.
- **canonical role instructions + schemas:** `agents/prompts/<role>.md` + the `*_OUT`
  shapes in `agents/registry.py`.

## Operating rules
- **Verify LIVE state — never act on remembered state.** Your memory of run phases, ev-ids, branch
  SHAs, what's merged, and gate decisions goes STALE: the operator (and their assistant) are editing the
  DB, deciding gates, and pushing branches **concurrently with you**. Before you act on any state,
  re-read the source of truth — run/gate state from its `$EVOLVE_STATE_DIR/<id>/` files + the live decided-gate
  scan, and **branch/merge state from git** (`git fetch` then check `origin/$EVOLVE_STAGING_BRANCH`, not your local
  checkout or your memory; your local `$EVOLVE_STAGING_BRANCH` can be behind origin — it self-syncs before each build,
  but re-check). A SHA or "this is already merged/approved" you remember from earlier in the session may
  no longer be true. Verify, don't remember.
- **Subscription, not API.** This session runs on the Claude subscription — that's the whole point.
- **One segment per pass, then END.** Never block; gates and "nothing ready" both just end the pass.
- **Token economy — the conversation is disposable between passes.** Files are truth (invariant #1): a
  pass re-hydrates everything it needs from `$EVOLVE_STATE_DIR/<id>/`, so the chat history carried between
  passes is a *cache, not the source*. Keep each pass lean: load ONLY what THIS segment needs, surface
  big artifacts with `emit-file` (not inline), and don't re-read items/artifacts you aren't acting on.
  - **Compaction is automatic** (`autoCompactEnabled` is on — pinned in `.claude/settings.json`); the
    model cannot self-trigger `/compact` and `/loop` has no per-iteration reset, so auto-compaction is
    the safety net. For a *hard, lossless* reset the **operator** can, between passes, run `/clear`
    then re-invoke `/loop` at this skill — the loop rebuilds state from files (nothing is lost), or
    `/compact` to keep a summary. This is the lowest-token way to run long sessions; it's an operator
    action, not something a pass does to itself.
- **Pace.** If you hit a usage limit, checkpoint `state.json` and end cleanly — the next pass resumes
  from files; nothing is lost.
- **Report honestly.** A step that fails surfaces + stops that item; never fake a green.
- **The Evolve dashboard being down is NOT fatal.** The operator restarts services to test changes (the
  deploy command `$EVOLVE_DEPLOY_CMD`).
  When the dashboard (on `$EVOLVE_ADMIN_HOST`) is unreachable: `decision` reads return no decisions (handled — `list_decided` yields `[]`),
  and every status/gate write **buffers to the brain host's outbox** and flushes in order when the dashboard is back.
  So a dashboard outage only pauses *gated-item advancement* for a minute — new GitHub issues still come from
  GitHub and can be worked (the brain host + test host need no dashboard until reporting, which buffers). **Never stop or
  crash the loop because the dashboard is down** — degrade, keep going, reconcile on a later pass.
  - **Flush-first every pass.** The decided-gate scan at the start of a pass (step 1a, `decision …`)
    now **drains the outbox before reading** (`list_decided` calls `_flush` first). This guarantees a
    report buffered while the dashboard was down goes out on the very next pass **even for a PARKED item whose
    own pass does no write** — e.g. a Gate-2 push buffered mid-deploy, where the item is then
    parked at Gate 2 and the loop goes idle. Without this, that report could strand until some *other*
    item happened to write. If you ever see a run stuck mid-segment on the dashboard after a restart while the brain
    host is actually done, force it: `python3 scripts/evolve_runs.py flush`.

## Launch
On the brain host (`$EVOLVE_BRAIN_HOST`): `cd <engine repo> && claude` (logged into the subscription), then drive with
`/loop` pointed at this skill — one segment per pass, gates handled out-of-band via the UI.
