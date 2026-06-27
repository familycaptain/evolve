# Operations & Troubleshooting

This is the practical day-to-day guide: how to read what the loop is doing, what to do in
each run state, how things resume after a restart, what to back up, how to update, and how
to fix the handful of things that commonly go wrong.

It assumes you have read [The Gates, the Agents & the Flow](09-gates-and-the-flow.md) (the
gate semantics and run phases) and [Architecture & the Fleet](02-architecture.md) (the
four machines and the two-token split). For starting the loop in the first place, see
[Running Evolve](07-running.md).

> Paths below use the engine's conventions: per-item run state lives under
> `$EVOLVE_STATE_DIR/<n>/` (default `~/.evolve/runs`) on the brain machine; the offline outbox
> and the cost ledger live under `~/.evolve/`. The reference deployment's example product is "the example platform"
> — substitute your own.

---

## 1. Run states & what to do

A run's `phase` (see [§5 of chapter 09](09-gates-and-the-flow.md#5-the-run-lifecycle--phases))
tells you exactly what state it's in and who it's waiting on.

| State | What it means | What *you* do |
|---|---|---|
| **Waiting at a gate** (`gate1` / `gate2` / `verify`, with no decision yet) | The swarm is done with this segment and has **parked** the item on you. The loop is *not* blocked — it's working other items. | **Decide it.** Review the packet in the dashboard (your PM helps), then Approve / Change / Reject. The item is correctly idle until you act — it is not stuck. |
| **Building** (`build`, or `new` actively running) | An agent segment is in progress (implementing, validating, running the spec phase). | **Let it run.** Watch the live agent feed in the dashboard. Don't intervene mid-segment. |
| **Stranded mid-build** (`new` or `build` with **no** pending decision and no agent active) | A pass was interrupted *during* the segment — the session ended or hit a usage limit mid-work, so the item froze (e.g. a run stuck at "building" after the build pass died mid-implement). | **Nothing** — the loop self-heals. The next pass detects it (`evolve_runs.py stranded` returns exactly the `new`/`build` dirs) and **resumes it from its files** (see §2). If it never moves, see §6. |
| **Rejected** (`rejected`) | You rejected it at a gate (or triage rejected junk). Terminal. The worktree is torn down. | Nothing. To revisit, re-file the issue. |
| **Parked** (`parked`) | Prioritize set it aside as the long tail (below the surface threshold). Terminal until re-surfaced. | Nothing required. It's recorded, not lost. |
| **Done** (`done`) | Verified working; the GitHub issue is closed. Terminal. | Nothing. The loop closed it. |

The key distinction: **a phase `gate1`/`gate2`/`verify` with no decision is *parked on
you*, not stranded** — the loop must never "resume" those (it would duplicate a gate). Only
`new`/`build` without a live agent is genuinely stranded mid-segment.

---

## 2. Resuming — the "resumes from files" guarantee

The loop is non-blocking and **stateless between passes**: each pass re-hydrates everything
it needs from the per-item files. The conversation carried between passes is a *cache*, not
the source of truth — the files are.

This means **stopping and restarting the loop loses nothing.** When you restart it (a fresh
`/loop` session, after a stop, a crash, or a usage-limit pause):

1. The next pass first scans for a **decided gate** to act on (a single dashboard call
   returns every item with a live decision).
2. Then for an item **stranded mid-segment** — only the `new`/`build` run dirs — and
   **resumes it from its files**: a `new` item re-runs the funnel/spec phase from its saved
   artifacts; a `build` item re-locates (or re-cuts) the worktree and re-runs implement →
   isolation check → dep-guard → validate → Gate 2. *It does not re-ground or re-spec* — it
   continues with all prior decisions intact.
3. Then a **new open issue** not yet seen.
4. If nothing is ready, the pass ends and the loop idles until the next pass.

So the recovery procedure after any interruption is simply: **restart the loop.** It picks
up exactly where it left off. (For a clean low-token reset on a long session, you can
`/clear` then re-invoke `/loop` between passes — the loop rebuilds state from files; nothing
is lost.)

---

## 3. The offline outbox — brain ↔ dashboard resilience

The brain machine reports run status, agent activity, and gate packets to the dashboard
over HTTP. The dashboard machine is **not always up** — you restart it to test changes, and
it can be briefly unreachable. Evolve is built to never lose a report (or crash) over that.

From `engine/platform_bridge.py`: every status/gate/event write is *resilient*. If the
dashboard is reachable, it posts. If the dashboard is **unreachable at the connection
level** (down/restarting — distinct from an HTTP 4xx/5xx, which is a real error that won't
heal on retry), the write is **buffered to an offline outbox** (`~/.evolve/outbox.jsonl`,
configurable via `EVOLVE_OUTBOX`) and the loop keeps going.

- **Flush-first, FIFO.** At the *start* of every pass, the decided-gate scan calls the
  outbox flush before reading. Buffered writes are delivered **in order**, and the flush
  stops at the first connection error (the dashboard is still down) — keeping that write and
  the rest for next time. Each buffered write thus reconciles on the dashboard **exactly
  once, in order**, when it's back.
- **No-op when empty.** Flushing an empty outbox is free, so it runs every pass safely.
- A poison/HTTP-error line is dropped rather than blocking the queue forever.

The operational upshot: **a dashboard outage only pauses *gated-item advancement* for a
minute.** Decision reads return "no decisions visible" (handled gracefully — they yield an
empty list), new GitHub issues still flow in from GitHub and can be worked, and every report
buffered during the outage flushes the moment the dashboard returns. **Never stop the loop
because the dashboard is down.**

If you suspect a report is stuck after a restart (a run shows mid-segment on the dashboard
but the brain is actually done), force a flush:

```
python3 scripts/evolve_runs.py flush
```

It prints `{"buffered": N, "remaining": M, "sent": N-M}` — a no-op if the outbox is empty or
the dashboard is still down.

---

## 4. Reading state from the CLI

Two scripts let you inspect and (only on your machine) decide, from a terminal.

### Read-only inspection — `scripts/evolve_explain.py`

This GETs run + gate state from the dashboard and prints it in plain language. It is **read
only** — it never decides, resolves, or mutates anything.

```
python3 scripts/evolve_explain.py list          # all runs + which gates are WAITING ON YOU
python3 scripts/evolve_explain.py 13            # loose token -> resolves to the matching run id
python3 scripts/evolve_explain.py ev-42         # an exact run id: full packet digest
python3 scripts/evolve_explain.py ev-42 --events # also show recent activity events
python3 scripts/evolve_explain.py ev-42 --json   # the raw gate-packet JSON (everything)
```

The digest renders the Lead's recommendation, the proposed spec, the planned code changes,
the design's open decisions, each agent's full findings, the validation result, the spend,
and (for Gate 2) whether a diff is available. The GET endpoints need no auth; the service
token is sent as a Bearer if present and is never printed.

The loop itself reads state with `scripts/evolve_runs.py` (`list` is the human view above;
the loop uses `pending` / `stranded` / `decision <id>` internally).

### Deciding — `scripts/evolve_decide.py` (operator machine only)

Decisions go through a **separate** script that requires the **decide-token**:

```
python3 scripts/evolve_decide.py <id> approve "confirmed scope / answers to the decisions"
python3 scripts/evolve_decide.py <id> change  "ordered list of requirement revisions"
python3 scripts/evolve_decide.py <id> reject  "reason"
```

This is the whole security model: `evolve_decide.py` uses `EVOLVE_DECIDE_TOKEN`, a
**parent-role** token set in `.env` **only on your assistant machine.** It is *never* placed
on the brain machine / the autonomous loop, which holds only the **service** token. The
service token can *post* gates but **cannot decide them** — so **the engine cannot decide
its own gates.** Only you (via your assistant) can. The decision is recorded as the
operator. (See [Architecture](02-architecture.md) for the two-token split.)

---

## 5. Common problems & fixes

**The loop isn't finding new issues.**
- Confirm the loop session is actually running (`/loop` pointed at the `evolve` skill on
  the brain machine).
- Check `GITHUB_REPO` / the repo registry and the GitHub token in `.env` — list issues
  manually: `python3 -c "from engine import github_connector as g; print([(i['number'], i['title']) for i in g.list_open_issues()])"`.
- An issue already in `$EVOLVE_STATE_DIR/seen.json` or with an existing `$EVOLVE_STATE_DIR/<n>/` dir
  is *not* re-picked — that's by design (it already has a run). Intake scans **every** registered
  repo each pass (`engine/intake.all_admissible_issues()`), each honoring its own intake mode;
  companion repos are skipped, and a repo that errors (auth/network) is skipped without aborting the
  scan — so if one repo's issues aren't appearing, check **that** repo's token (`token_env`) and
  `intake` mode in the registry.

**A gate isn't appearing in the dashboard.**
- The gate push may be **buffered in the outbox** because the dashboard was down when it was
  pushed. Run `python3 scripts/evolve_runs.py flush` (§3), then refresh the dashboard.
- Confirm the brain's `EVOLVE_SERVER_URL` points at the running dashboard and
  `EVOLVE_SERVICE_TOKEN` is set (the brain authenticates with the service token).

**A decision is rejected with `403`.**
- The token at the decision endpoint is wrong, missing, or lacks the admin/parent role. The
  most common cause is trying to decide with the **service token** (the brain's token) —
  that token is intentionally forbidden from deciding. Use `evolve_decide.py` with
  `EVOLVE_DECIDE_TOKEN` set in `.env` **on your operator machine**. If `EVOLVE_DECIDE_TOKEN`
  is unset, the script refuses up front and tells you to mint a parent-role token.

**The dashboard is unreachable.**
- Not fatal (§3). The loop degrades and keeps working new GitHub issues; reports buffer.
  Bring the dashboard back, then `flush`. Verify the URL/port and that the dashboard service
  is up.

**The repo-switcher is empty / repos don't load (PyYAML missing).**
- The repo registry (`evolve.repos.yaml`) is parsed with **PyYAML**. If PyYAML isn't
  installed, `engine/repos.py` silently falls back to the single repo from `$GITHUB_REPO` —
  so a multi-repo registry appears empty. Install the dashboard requirements (which include
  PyYAML) into the environment running the loop/dashboard: `pip install -r dashboard/requirements.txt`.

---

## 6. Backups

Two pieces of durable state are worth backing up:

- **The dashboard's SQLite database** (on the admin/dashboard machine) — the runs, gates,
  packets, and activity the dashboard serves. Back up the dashboard DB file (see
  [Installation](03-installation.md) / [The Dashboard](08-the-dashboard.md) for its path)
  while the dashboard is stopped, or use SQLite's online-backup.

- **The brain's run state — `$EVOLVE_STATE_DIR/`** (default `~/.evolve/runs`) — the per-item directories (`<n>/state.json`
  plus every artifact: triage, grounding, design, spec, reviews, lead, gate packets) and
  `seen.json`. This is the "resumes from files" source of truth; a backup here lets you
  restore in-flight items. The offline outbox (`~/.evolve/outbox.jsonl`) is transient — back
  it up only if you need to preserve un-flushed reports across a machine move.

- **The cost ledger — `~/.evolve/costs.db`** (or `$EVOLVE_COST_DB`) — month-to-date spend
  history (§7). Back it up if you want spend continuity.

---

## 7. Cost — the spend ledger

Evolve measures spend and can cap it. From `engine/cost.py`:

- Every agent invocation's cost (input/output tokens + USD) is recorded to a durable SQLite
  ledger (`~/.evolve/costs.db` by default, or `$EVOLVE_COST_DB`), tagged by agent, model,
  day, and run.
- A monthly budget acts as a **kill-switch**: once month-to-date spend reaches the cap, the
  engine refuses further agent calls and Evolve pauses until the next month or you raise the
  cap (`BudgetGuard.over_budget()`).
- **Per-run spend** is summed per `instance_id`, which is how the dashboard's mission-control
  view shows a live running cost per work item; `evolve_explain.py` prints it as `spend` in
  a run's digest when present.

Read the month-to-date report from the CLI:

```
python -m engine.cost
```

It prints the ledger path, a breakdown by agent and by model for the current month, the
call count, and the all-time total.

> The canonical subscription `/loop` engine runs on a Claude **subscription** rather than
> metered API credits, so its per-pass dollar cost may not register in this ledger; the
> ledger and budget kill-switch are the spend controls for the metered path. Check what your
> dashboard surfaces for your deployment.

---

## 8. Updating Evolve

Evolve is a cloned repo on each machine; update with `git`.

- **Brain and admin machines:** `git pull` in the engine repo on each. The brain runs the
  loop; the admin runs the dashboard. Pull both so the engine, the skills, and the dashboard
  stay in lockstep.
- **If the dashboard's requirements changed,** re-install them on the admin machine:
  `pip install -r dashboard/requirements.txt` (this is also where **PyYAML** comes from — see
  §5). Restart the dashboard service to pick up the new code.
- **Test / UAT machines** are deploy targets, not engine hosts — they receive *product*
  candidates via the configured deploy command, not engine updates. Update the engine only
  where the loop and dashboard run.

After updating, a running loop session will pick up skill/prompt changes on its next pass
(skills are read fresh); restart the dashboard service to apply dashboard changes.

---

## See also

- [Running Evolve](07-running.md) — starting and driving the loop.
- [The Gates, the Agents & the Flow](09-gates-and-the-flow.md) — gate semantics and run phases.
- [Architecture & the Fleet](02-architecture.md) — the four machines and the two-token split.
- [The Dashboard](08-the-dashboard.md) — the live view and where you decide.
- [Configuration](04-configuration.md) — `.env`, the repo registry, tokens, and paths.
