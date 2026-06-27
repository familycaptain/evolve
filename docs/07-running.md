# Daily Operation

This is the day-to-day playbook: how you start Evolve, the rhythm you settle into, and how you
review and decide the gates that work parks at. It assumes you've already done
[Installation](03-installation.md) and [Configuration](04-configuration.md) — a filled-in `.env`,
your `evolve.repos.yaml`, your `CHARTER.md`, and a target adapter. For the concepts behind the
gates, see [Overview & Concepts](01-overview.md); for the machines and the security model, see
[Architecture & the Fleet](02-architecture.md).

The shape of a day: two long-lived Claude Code sessions are running (one on **evolve-admin**, one on
**evolve-brain**), plus the dashboard. The loop grinds away on its own; you glance at the dashboard
when something is **waiting on you**, decide it, and go back to whatever you were doing.

---

## 1. Starting the system

Three things run continuously. Bring them up in this order.

### a. The dashboard (on evolve-admin)

The dashboard is a small FastAPI web server. From the repo root on **evolve-admin**:

```
uvicorn dashboard.server:app --host 0.0.0.0 --port 8000
```

- The app object is `dashboard.server:app` and the default port is **8000**
  (`dashboard/server.py` reads `EVOLVE_DASHBOARD_PORT` / `PORT`, falling back to 8000). The bare command binds **localhost only** — use `--host 0.0.0.0` (above) so evolve-brain can reach it. If you set a different port, use the same one in `EVOLVE_SERVER_URL` so the brain and
  the PM reach it.
- It serves the operator console at `/` and the engine's REST contract under `/api/apps/evolve`.
- It reads the repo-root `.env` for its two tokens (`EVOLVE_DECIDE_TOKEN`, `EVOLVE_SERVICE_TOKEN`)
  and the SQLite store path (`EVOLVE_DASHBOARD_DB`, default `~/.evolve/dashboard.db`).

Open it in a browser at `EVOLVE_SERVER_URL` (e.g. `http://localhost:8000`). See
[The Dashboard](08-the-dashboard.md) for the full UI reference, including pasting your decide-token.

### b. The PM session (on evolve-admin)

In a Claude Code session on **evolve-admin**, invoke the PM skill:

```
/evolve-pm
```

This (re)establishes Claude as your **project manager** for Evolve — the human-side partner who
reads packets with you, answers questions against the live code, pushes back on thin evidence, and
operates a gate on your explicit say-so. evolve-admin is the **only** machine that holds the parent
decide-token, so this is the only session that can actually decide a gate. More on the role in
section 4 below.

### c. The loop (on evolve-brain)

In a Claude Code session on **evolve-brain**, logged into the Claude **subscription** (not an API
key), start the engine: Launch Claude Code with **`--dangerously-skip-permissions`** so the autonomous loop isn't interrupted by a permission prompt on every action (that's why the brain is a dedicated machine — see [03-installation](03-installation.md)).

```
/loop /evolve
```

`/evolve` is the engine skill; `/loop` drives it on a self-paced interval. Each pass advances
**exactly one** work item by **one** segment (the work between two human gates) and then ends — a
gate never blocks the loop. The brain reports every run, gate, and agent step to the dashboard via
`$EVOLVE_SERVER_URL` using the service token (which can push but can never decide).

> The brain runs on the **subscription** deliberately — that's what makes a continuously-running
> agent swarm affordable. It never uses the API key.

---

## 2. The daily rhythm

Once all three are up, you do very little moment to moment. The pattern is:

- **The loop runs continuously.** Each pass it picks the *most-ready* item: a gate you've just
  decided (act on it), an item stranded mid-segment (resume it from its state files), or a new
  GitHub issue (start it) — **intake is automatic**: each pass scans your repos' open issues via the GitHub token, so there is no separate poller or cron to set up. If nothing is ready, the pass just ends and the next one re-checks.
- **Items park at gates.** When a pass reaches a gate it writes the packet, flips the run to
  `waiting`, and ends. It does **not** wait, sleep, or poll for your decision. The loop moves on to
  other work.
- **You decide on your own time.** Periodically check the dashboard's **runs rail** for the
  **"⚠ waiting on you"** badge. Open the run, review the packet, decide. A *future* loop pass picks
  your decision up and continues that item exactly where it left off.

So the loop never blocks on you, and you never block the loop. An item can sit parked indefinitely;
meanwhile the swarm keeps advancing everything else. The gates are mandatory — nothing ships without
your three decisions (intent, result, verify) — but they're asynchronous.

A run resumes from per-item state files, so the brain session can be interrupted (usage limit,
restart, crash) and the next pass continues from where it stopped. If you ever need to confirm the
loop is actually alive, check for the session process on the brain, and watch the dashboard's live
activity tail tick.

---

## 3. How work enters

A requester's only step is **filing a GitHub issue** on one of your managed repos (the ones listed
in `evolve.repos.yaml`). That's it — no in-app tracker, no special form. The loop scans the issues
across **every** registered repo each pass, and when it sees one it hasn't started, it opens a run.
The run id is namespaced per repo: `ev-<issue#>` for the primary platform repo (e.g. issue #42 →
`ev-42`), and `ev-<repo-slug>-<issue#>` for any other repo (so two repos that each have issue #5
don't collide). One issue is one run is one continuous conversation, for its whole life.

The issue stays **open** until *you* verify the fix at Gate 3; Evolve only closes it after a human
confirms it works. A closed issue means "verified working."

> *Intake scans all registered repos each pass (`engine/intake.all_admissible_issues()`), each
> honoring its own intake mode; companion repos are skipped. The item carries its repo, builds in
> that repo's own checkout/branch, and deploys via the adapter (a platform in place; an app/model
> cloned into its host platform). See [Configuration → The multi-repo model](04-configuration.md#the-multi-repo-model-types-host-and-deploy).*

---

## 4. The PM role (`/evolve-pm`)

`/evolve-pm` makes Claude your **project manager** on evolve-admin. It is **not** the autonomous
loop (that's the brain) — it's *your* side of the pipeline: the partner who brings you the calls
only you can make and helps you make them well. What it does for you, day to day:

- **Reads a gate item with you.** It pulls the live packet (read-only) and restates the *real*
  decision in plain language — the dashboard's terse "approve / option A / option B" buttons are
  low-context; the PM translates, recommends, and surfaces what the packet glosses over (a placement
  risk, a spec↔option mismatch, thin tests, a required user action, a cross-item conflict).
- **Holds the bar.** It pushes back — recommends *change* or *reject* — when validation is thin,
  un-reproduced, or a fix is half-done; it recommends *approve* when something is genuinely sound;
  it surfaces to you only the real forks and real failures.
- **Operates the gate on your say-so.** When you decide, it echoes the exact decision + note it will
  submit, gets your one-word go, then records it as *you* (the parent decide-token). You decide by
  talking to the PM, not by wrestling the gate UI.
- **Fixes bugs and hardens the engine**, designs new behavior *with* you (you are the design
  authority), keeps the fleet healthy, and reconciles messes.

Two rules the PM lives by, worth knowing as the operator:

- **Verify live state, never trust memory.** The loop is updating the dashboard DB and pushing
  branches at the same time the PM is. Before acting on any run/gate state or branch/merge state, the
  PM re-checks the source of truth (the live dashboard via `evolve_explain`, and `git` against the
  remote) — never its own remembered SHA, phase, or "already merged."
- **It decides a gate ONLY on your explicit, per-item instruction** — never autonomously, never to
  clear a backlog, never inferred from a passing "sounds good." (You *can* grant standing authority
  — "drive ev-42 through the gates, keep it moving" — and that's the one exception, still
  operator-granted.) The loop and its agents **cannot** decide gates at all: the parent decide-token
  lives only on evolve-admin.

If you lose the PM conversation, just run `/evolve-pm` again in a fresh session — the skill is
self-contained and rebuilds the role from scratch.

---

## 5. Reviewing & deciding a gate

There are **two ways** to review and decide a gate. They reach the same place (the decision is
recorded against the same run); pick by how much you need to think.

### a. In the dashboard console

Open the parked run in the dashboard. The gate-review panel shows the gate label, the lead's
recommendation, and the full readable packet (work item, decisions needed, spec, code-plan,
reviewers, validation, diff). Type an optional note, then click **Approve**, **Change**, or
**Reject** (at Gate 3 the buttons relabel to **✓ Works / Still-broken / Abandon**). This is the
fast path for a clear call. Full reference: [The Dashboard](08-the-dashboard.md).

### b. Through `/chat-ev <n>` (the Gate-1 requirements partner)

When an item reaches **Gate 1** and the decision isn't obvious — you want to pressure-test the
requirements before approving it to build — run, in your `/evolve-pm` session:

```
/chat-ev 42
```

This is the missing "chat it through with the agents" step. The PM:

1. **Fetches the live packet** for the item (read-only) and reads the digest itself.
2. **Orients you** — a tight plain-language brief of what the item *is*, what the agents propose to
   build, the lead's recommendation (and whether the PM agrees), each decision the agents flagged
   with the *real* tradeoff behind the terse labels, and what the packet underplays.
3. **Runs the revise loop** — back-and-forth for as long as you want, grounded in the actual code and
   your `CHARTER.md`, probing the ambiguities the spec left open, maintaining a running
   **requirements delta** so nothing is lost.
4. **Lands it on your say-so** — restates the decision crisply, echoes the exact note it will submit,
   and on your one-word go submits it for you.

`/chat-ev` is one item per conversation; switching ids re-fetches from scratch. It's a Gate-1
partner specifically — that's where requirements get clarified before a build commits.

### What Approve / Change / Reject mean

The three actions are the same at every gate; what they *route to* depends on the gate:

- **Approve** — proceed. At **Gate 1** this sends the item to build (your note becomes a build hint
  layered on the authoritative spec). At **Gate 2** it merges the change to your **staging branch**
  and moves the item to verify. At **Gate 3** ("✓ Works") it confirms the change works for real and
  the engine **closes the GitHub issue**.
- **Change** — bounce it back with revisions. At Gate 1, the spec phase re-runs on your note
  (write the note as an ordered list of requirement revisions the spec phase can act on). At Gate 2,
  the change is re-implemented. At Gate 3 ("Still-broken"), the *same* run resumes with your failure
  report as input — no new conversation — and the agents judge whether it's a localized bug
  (re-implement) or a wrong approach (re-spec). A `Change` should carry a note explaining what to
  change.
- **Reject** — stop this item. The worktree is torn down and the run is marked rejected. (Note: an
  *operator-authored* item is never auto-rejected upstream by triage — you remain the authority — but
  you can always reject it yourself at a gate.)

### The decide-token requirement

A decision is the one thing the brain can never do. Recording Approve / Change / Reject requires the
**parent decide-token** (`EVOLVE_DECIDE_TOKEN`):

- In the **dashboard**, you must paste your decide-token into the header field once (it's stored in
  the browser and sent as a Bearer header on every decision). Until you do, the decision buttons are
  **disabled**. The service token is rejected (403) at the decision endpoint — the engine can push a
  packet but can never decide it.
- Through **`/chat-ev` / `/evolve-pm`**, the PM submits with the same decide-token from
  evolve-admin's `.env`. If it isn't set, the decide helper refuses to act.

This two-token split is the core safety property (see [Architecture](02-architecture.md)).

---

## 6. Watching runs

While the swarm works, the dashboard narrates it live. Select any run to see:

- its **status, phase, current agent/node, and live spend**, and
- the **live activity tail** — each agent's steps as they happen (start/end lines, tool calls,
  emitted artifacts like the full spec, each reviewer's findings, the lead's recommendation, the
  build diff). Grouped by agent, it's the play-by-play of what the swarm is doing.

You read a run's *state* from the rail and the panel sub-header: the status chip (running / building
/ waiting / merged / rejected …), the `phase`, and which agent is active. The full UI is documented
in [The Dashboard](08-the-dashboard.md).

---

## 7. Pausing, stopping, and resuming the loop

The loop is just a Claude Code session on the brain — there's no daemon to manage.

- **Pause / stop:** stop the `/loop` session on the brain (end the session, or interrupt it between
  passes). In-flight items are safe: each item's progress lives in its per-item state files, not in
  the chat. A pass that was interrupted mid-segment leaves the item stranded, but recoverable.
- **Resume:** start a Claude Code session on the brain again and re-invoke `/loop /evolve`. The loop
  rebuilds state from files. Its first passes pick up: any gate you decided while it was down, then
  any item stranded mid-segment (it re-runs that segment from saved artifacts), then new issues.
  Nothing is lost — the files are the source of truth, the conversation is a disposable cache between
  passes.
- **A clean reset (operator-only):** between passes you can `/clear` then re-invoke `/loop /evolve`
  for a lossless, low-token restart (state rebuilds from files), or `/compact` to keep a summary. The
  loop can't do this to itself; it's your lever for long sessions.
- **Dashboard down ≠ loop down.** If the dashboard is unreachable (e.g. you're restarting it), the
  loop degrades rather than crashes: status/gate writes buffer on the brain and flush in order when
  the dashboard returns, and new GitHub issues can still be worked. Only *gated-item advancement*
  pauses briefly. Don't stop the loop because the dashboard blipped.

---

## 8. Publishing (staging → world)

Each per-change cycle ends at your **staging branch** (`EVOLVE_STAGING_BRANCH`, e.g. `release`) —
that's where an approved, verified change lands, and what **evolve-uat** tracks for your Gate-3
verification. Shipping to the world is a **separate, operator-owned** step you do deliberately:

- Promote the staging branch to your **world branch** (`EVOLVE_WORLD_BRANCH`, e.g. `main`) with a
  fast-forward push — `git push origin origin/<staging>:<world>` — on your say-so.

The engine never does this; the world-branch promotion is yours alone. The per-change gates verify
*correctness*; publishing is the act of *releasing* what's been verified.

---

## See also

- [The Dashboard](08-the-dashboard.md) — the admin console, panel by panel.
- [Gates & the Flow](09-gates-and-the-flow.md) — what each gate decides and how items route.
- [Operations & Troubleshooting](10-operations-and-troubleshooting.md) — when something's stuck.
- [Architecture & the Fleet](02-architecture.md) — the machines and the two-token security model.
- [The SDLC flow](sdlc.md) — the full agent-swarm + gates narrative.
