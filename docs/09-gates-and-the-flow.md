# The Gates, the Agents & the Flow

This chapter is the conceptual heart of the manual: **who does what, in what order, and
where *you* are in the loop.** It covers the three human gates and what each one is
actually asking you, the reproduce-first opening of Gate 1, the full agent roster, the
end-to-end pipeline, and the run lifecycle.

For the authoritative picture — the Mermaid diagram of the whole swarm — open
[`sdlc.md`](sdlc.md). This chapter is the prose companion to that diagram. For the
machinery that makes the gates real (the four-machine fleet, the two-token split), see
[Architecture & the Fleet](02-architecture.md). For *operating* the gates day to day
(states, resuming, troubleshooting), see [Operations & Troubleshooting](10-operations-and-troubleshooting.md).

> Throughout, the example product is **"the example platform"** (in the reference
> deployment, a self-hosted household app platform). Substitute your own.

---

## 1. The three gates

Evolve does the labor; **you make three judgment calls per change, and only those three.**
A requester files one GitHub issue, you make three decisions, and the swarm does everything
in between — live in front of you the whole time. Each gate is a different question.

### Gate 1 — approve the *intent / approach* (before the build)

Gate 1 happens **before any product code is written.** By the time it reaches you, the
swarm has reproduced the issue, grounded itself in the real code, designed an approach,
written a spec with bound tests, sketched the code footprint, and run four independent
reviewers — and the Lead has synthesized all of that into a single recommendation. The
question you are answering is:

> *Is this the right thing to build, and is the approach sound?*

You are approving **the plan**, not the result. The packet shows you the Lead's
recommendation (`current` → `after`, and `why`), the proposed spec, the **planned code
changes** (the Code Scout's read-only sketch — which files, add/modify/**rewrite**, where
new logic lands), any open decisions the design left for a human, and every reviewer's full
findings.

### Gate 2 — approve the *result* (the validated change)

Gate 2 happens **after the build.** The implement agent has written the code (and a bound
test) inside an isolated worktree, the change has been validated on the test machine, and
the dependency-rule guard has run. The question is:

> *Did the change actually do it, and is the diff acceptable?*

The packet carries the **full diff**, the **validation result** (the bound test's outcome
plus a live-acceptance run), the dependency-check result, and the **after-evidence on the
GitHub issue**. After-evidence is **mandatory** — symmetric with the Gate-1 reproduce
before-evidence — and takes the form the change calls for: a **screenshot** for a UI change,
or the **captured proof** (API response / stdout / test transcript via an issue comment) for
a backend / CLI / library change. The build **fails closed**: a change reaches a *green* Gate 2
only if the agent actually changed code, included a runnable bound test that passed on the test
machine, **and posted the after-evidence to the issue** — a green verdict with no posted
evidence is treated as incomplete, not a pass. A failed, empty, untested, or unevidenced build
lands at Gate 2 with a `change` recommendation that names the reason — a broken or unproven
build can never arrive looking approvable.

### Gate 3 — *verify* it works live (then it closes)

**Merge is not done.** A Gate-2 approve auto-merges a *candidate* to the staging branch and
deploys it to the **UAT machine** (a separate, mock-data host that tracks the staging
branch). The question is:

> *Does it really work when I use it for real?*

You — with your PM — test the live change on the UAT host. Only when you confirm it works
does Evolve **close the GitHub issue.** The issue stays *open* until you verify; a closed
issue therefore means a human confirmed the fix, not merely that code merged. This is
"closing the loop." (Verifying on a dedicated mock-data UAT host means you never disturb a
production deployment to confirm a fix.)

### What Approve / Change / Reject do at each gate

Every gate offers the same three verbs, but they mean something gate-specific:

| | **Approve** | **Change** ("change this") | **Reject** |
|---|---|---|---|
| **Gate 1** | Build it. The item enters the build phase: implement → tests → validate → Gate 2. | Bounce back to the spec phase with your note (the design re-frames, the spec is reworked, re-review), then re-push Gate 1. | Drop the item; the run is marked rejected. |
| **Gate 2** | Auto-merge to the staging branch and deploy to UAT for verification (→ Gate 3). | Bounce back to **implement** with your note; re-validate, re-push Gate 2. | Tear down the worktree; the run is rejected. |
| **Gate 3** (relabeled **✓ Works / Still-broken / Abandon**) | "✓ Works" → close the GitHub issue; the run is done. | "Still-broken" → resume the *same* conversation with your failure note. The agents judge the **depth** of the fix: a localized code bug re-implements → Gate 2; a wrong *approach* re-designs, **rewrites the spec**, re-reviews → Gate 1. | "Abandon" → drop it **without** closing the issue as resolved. |

A "Change" at any gate carries your free-text note forward as authoritative guidance. At
Gate 3 the routing rule is precise: only a code-level bug *under an unchanged spec* skips
ahead to re-implement; if the fix changes the approach, the behavior contract, or a
load-bearing technical choice, it is a new plan and gets the full funnel again (Gate 1).
**The spec always describes what is actually built** — a change of approach rewrites the
spec; you never leave it documenting a way you no longer ship.

### The review-not-labor principle: one gate per deliverable, not per unit

This is the core bet, and it is written into the charter's *Autonomy* section and the
engine's `SKILL.md`: **the human gates are judgment points — approve the intent, verify the
result — never a per-task drip.**

A large or comprehensive issue that the agents decompose into many internal units (a *spec
tree*: a foundation plus N per-app migrations, a service plus its callers, and so on) is
**gated ONCE as one deliverable, not once per unit.** You approve the *approach* at Gate 1;
the engine then autonomously builds **and** validates the whole thing — each internal unit
still fully built and test-validated, no quality lost — and surfaces a **single** result
gate carrying the *complete* evidence. The decomposition and sequencing are the engine's
concern, not yours.

Flooding you with a gate per leaf — dozens of near-identical "approve this unit?"
touchpoints — would defeat the whole review-not-labor bet and is itself treated as a
defect. Comprehensive fixes are reviewed comprehensively and **once**.

---

## 2. Reproduce-first Gate 1

Gate 1 does **not** open by reading code. Reading code alone misattributes a UI symptom to
the wrong code path — the same on-screen element can be produced by more than one path
(a foreground flow vs. a background path), so a code-read can land on the wrong one and
wrongly conclude "no issue." So a surfaced item runs a fixed opening sequence **before any
code is read**:

1. **Security screen first.** The `security-screen` agent (a forked subagent) reads **only
   the raw issue** — never the codebase — and classifies its *intent*. A good-faith
   fix/feature is `clear`; an issue whose *reproduction itself* would be the attack ("prove
   you can break into X / leak Y") is **blocked**. A blocked item never reaches the
   reproduce step — the reproduce agent must never become the weapon — and is flagged for
   you at Gate 1. This security interlock sits **upstream** of reproduction by design.

2. **Reproduce on the test host.** If the screen is `clear`, the `reproduce` agent deploys
   the current (pre-fix) staging branch to the **test machine**, drives the real UI/flow to
   recreate the **reported** symptom on its exact user-facing surface, **screenshots what
   the user sees**, and posts that screenshot to the GitHub issue itself (via an inline
   image that renders even on a private repo).

3. **"Could not reproduce" is a first-class outcome.** If the agent cannot reproduce the
   symptom (already fixed? steps unclear? environment-specific?), it does **not** invent a
   fix. It pushes a Gate-1 finding that says exactly that, with the evidence, and asks you
   to decide. A *reproduced* item, by contrast, carries its proven `surface` forward into
   grounding — so the spec phase anchors on the code behind **that** surface, not the one
   the issue's wording merely implies.

The screenshots **bracket the change on the issue itself**: the *before/repro* shot at Gate
1, and the *after/fix* shot at validation (Gate 2 / Gate 3). You judge the actual rendered
pixels, not the agents' code reasoning.

---

## 3. The agent roster

These are the agents in the engine's roster (`agents/registry.py`). Each is
single-responsibility: a curated prompt plus a structured output contract. The critics
(spec-audit and the four reviewers) **fork** into independent subagents for fresh eyes.

> The roster is *data* — an agent is added by adding a registry entry plus a prompt file;
> the engine picks it up with no other change. The list below is exactly what ships today.

### Intake & funnel — the cheap gates, before the expensive spec phase

| Agent | Its one job |
|---|---|
| **triage** | Classify a work item (bug vs. feature), reject junk (duplicate / malicious / invalid), link it to the spec corpus, and route the fix (`belongs_to`: this repo vs. an external package). |
| **security-screen** | Screen a raw issue's **intent** before reproduction — `clear` vs. `block` (malicious). Sees only the issue, never the code. |
| **reproduce** | Reproduce the reported issue on the test host and screenshot it to the GitHub issue — *before any code is read*. |
| **vision-fit** | Judge a feature against the charter plus the target Capability's scope — `fits` / `off-vision` / `needs-charter-change`. (Bugs and operator-authored items skip this.) |
| **prioritize** | Score a surviving item onto one ranked queue; **surface** the top-N or **park** the long tail. The attention valve that runs *before* the expensive spec phase. |

### Spec phase — the Lead's agentic inner loop

| Agent | Its one job |
|---|---|
| **grounding** | Scan the codebase **once** for the item and produce a reusable digest (files, key symbols, excerpts, conventions, the target Capability's existing specs) for the whole spec team — the one cold scan. |
| **design** | Set the system-level approach (how it should work) before the spec is written, decide the technical choices, and **size** it: one spec vs. a needs-tree decomposition. |
| **spec-author** | Turn the accepted intent + the design into one atomic specification record — a behavior plus bound acceptance tests (one per leaf when the design decomposed). |
| **spec-audit** | Critique a single spec for gaps, holes, and naive assumptions (cardinality, missing state, ambiguity, untestability…). *Forks* as a subagent for independence. |
| **code-scout** | Read-only: sketch **what** code would change for the approved approach — files/areas, add/modify/rewrite, where new logic lives, placement notes — **writing no code.** Gives you (and the architecture reviewer) the change's footprint before approval. |
| **security** (reviewer) | Review the proposal for vulnerabilities and supply-chain risk. |
| **architecture** (reviewer) | Review system fit: module boundaries and the one-directional dependency rule. It audits the **code-scout's planned placement** so a mis-placed shared dependency is caught at the gate. |
| **interop** (reviewer) | Detect spec-vs-spec conflicts — is the desired end state actually satisfiable alongside the existing contracts? |
| **ux** (reviewer) | Review UX/UI quality and cross-surface consistency. |
| **lead** | Arbitrate the author⇄auditor rounds, weigh the reviews, and own the **single** Gate-1 recommendation handed to you. |

### Build & result

| Agent | Its one job |
|---|---|
| **implement** | Write the code that converges the codebase to the approved spec — inside the feature worktree only, with its bound test. Fails closed (no code / no test / escaped workspace = not done). |
| **test-author** | Write or update a spec's bound acceptance tests. |
| **validate** | Run the spec's bound tests on the test host **and** drive the live product as a real user, judging on captured evidence (tool-calls, DB state, screenshots) — never vibes. |
| **review-packet** | Assemble the pre-digested Gate-2 review packet (summary, risk, test summary, recommendation). |

The roster also includes a **code-audit** agent (read code for logic bugs, edge cases,
security smells, dead code), used by the proactive QA / bug-discovery sweep that *feeds*
the intake lane rather than running inline in a single item's pipeline.

---

## 4. The full flow

A prose walk of one item from filing to close. (The diagram is in [`sdlc.md`](sdlc.md);
read it alongside this.)

1. **Intake.** Work enters from four lanes — two reactive (GitHub **issues** and **PRs**,
   pulled by one connector; there is no in-app tracker) and two proactive (a
   feature-proposer cadence, and a QA / bug-discovery sweep whose detectors emit
   bug/spec-gap items). All lanes feed **triage**.

2. **Funnel — cheap gates first.** Triage rejects junk and classifies bug vs. feature.
   Features pass through **vision-fit** (scope against the charter + Capability); bugs skip
   it. Then **prioritize** is the attention valve — the long tail is *parked* (recorded),
   only the top-N or safety-critical survive to the expensive spec phase. (Operator-authored
   items are never triage-rejected — the operator is the authority — but a triage flag is
   carried forward as a note for you to weigh at Gate 1.)

3. **Spec phase opens with reproduce-first.** For a surviving item: **security-screen** →
   **reproduce** (see §2). A `block` or a "couldn't reproduce" outcome short-circuits
   straight to a Gate-1 finding. A reproduced item carries its proven surface into
   **grounding** → **design** → **spec-author** → **code-scout** → forked **spec-audit**
   (bounded revise rounds) → four forked **reviewers** → **lead**.

4. **Gate 1 — approve intent.** The Lead hands you one recommendation plus the full packet.
   You Approve / Change / Reject (§1).

5. **Build.** On Approve, the engine serializes the spec to a feature branch, cuts an
   isolated worktree, runs **implement** (with the test author), runs the **isolation
   check** (the main checkout must stay clean) and the **dependency-rule guard**, then
   **validate** on the test host. A green validation marks the proved spec(s) `verified`.

6. **Gate 2 — approve result.** You get the diff, the validation, and the dep-check. Approve
   / Change / Reject.

7. **Merge & deploy to UAT.** On Approve, the engine auto-merges the feature → the staging
   branch and re-syncs files to the DB. The staging branch deploys to the **UAT machine**
   (via the configured deploy command).

8. **Gate 3 — verify live.** You (and your PM) test it on UAT. **✓ Works** closes the
   GitHub issue (done). **Still-broken** resumes the same conversation (localized fix →
   Gate 2, or new approach → Gate 1). **Abandon** drops it without closing.

The **per-change process ends at the staging branch, not the world branch.** Promotion of
the staging branch to the world/published branch is a separate, operator-owned **release
gate** — batched over many completed changes — and lives *outside* this per-change flow. The
world branch is branch-protected; nothing reaches it except that deliberate merge, so the
agents can never touch production directly.

> **A note on what's wired today.** Multi-repo is wired: issue intake scans **every** registered
> repo each pass (`engine/intake.all_admissible_issues()`), each honoring its own intake mode;
> the item carries its repo, run state is namespaced per repo (`ev-<n>` / `ev-<slug>-<n>`), and the
> build/deploy is repo-aware (a platform builds in place; an app/model builds in its own repo and is
> cloned into its host platform). The engine invokes the target adapter for deploy/validate through
> `scripts/evolve_adapter.py` (each adapter's `adapter.yaml`), threading the per-repo target into it.
> See [Target Adapters](06-target-adapters.md) and
> [Configuration → The multi-repo model](04-configuration.md#the-multi-repo-model-types-host-and-deploy).

---

## 5. The run lifecycle / phases

**One run = one resumable thread.** Each work item has exactly one run for its whole life,
identified by `ev-<issue#>` (e.g. `ev-42`). It is grounded once and **resumed** on every
later pass — never restarted. Its artifacts (triage, grounding, design, spec, reviews, the
lead recommendation, the gate packets) are persisted per item, so a pass can be interrupted
and the next one continues from the files exactly where it left off.

A run's `phase` field is the state machine the next pass routes on:

```
new  →  gate1  →  build  →  gate2  →  verify  →  done
                                                   (terminal)
              ↘ rejected            ↘ parked
                (terminal)            (terminal)
```

- **`new`** — created; running the funnel + spec phase.
- **`gate1`** — parked at Gate 1, awaiting your intent decision.
- **`build`** — approved at Gate 1; implementing + validating.
- **`gate2`** — parked at Gate 2, awaiting your result decision.
- **`verify`** — merged to staging and deployed to UAT; awaiting your live verification (Gate 3).
- **`done`** — verified working; the GitHub issue is closed. Terminal.
- **`rejected`** — rejected at a gate. Terminal.
- **`parked`** — set aside by prioritize (the long tail). Terminal until re-surfaced.

The phase is what lets the loop be non-blocking: a gate **parks** the item (phases `gate1`
/ `gate2` / `verify` with no decision are correctly waiting on *you*, never "stranded"),
and a later pass picks the decision up. A phase of `new` or `build` with no pending decision
means a pass was interrupted mid-segment — the loop *resumes it from files*. See
[Operations & Troubleshooting](10-operations-and-troubleshooting.md) for how that resume
works and what to do in each state.

---

## See also

- [`sdlc.md`](sdlc.md) — the authoritative Mermaid diagram + narrative of the swarm.
- [Overview & Concepts](01-overview.md) — the mental model and the core bet.
- [Architecture & the Fleet](02-architecture.md) — the four machines and the two-token split that makes the gates real.
- [The Charter](05-the-charter.md) — the vision authority the funnel agents judge against.
- [The Dashboard](08-the-dashboard.md) — where you watch the swarm and decide the gates.
- [Operations & Troubleshooting](10-operations-and-troubleshooting.md) — running, resuming, and fixing the loop.
