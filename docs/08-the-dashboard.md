# The Dashboard (Admin Console)

The dashboard is Evolve's **operator control surface**: a single-page web app where you watch the
swarm work in real time and where you decide the gates. It runs as a small FastAPI server on
**evolve-admin** and is backed by a SQLite store. The brain reports every run, gate, and agent step
to it; you review and decide there.

This page is a UI reference grounded in `dashboard/static/index.html` and `dashboard/server.py`.
For *how* you use it in the daily flow, see [Daily Operation](07-running.md); for the security model
behind the decide-token, see [Architecture & the Fleet](02-architecture.md).

---

## Launching it & the URL

Run the dashboard on **evolve-admin**, from the repo root.

**1. Install once (a virtualenv keeps it clean):**
```bash
python3 -m venv .venv
. .venv/bin/activate                       # Linux / macOS / Windows-WSL
pip install -r dashboard/requirements.txt  # fastapi, uvicorn, pyyaml
```

**2. Start it.** For a single-machine trial, localhost is fine:
```bash
uvicorn dashboard.server:app --port 8000
# → open http://localhost:8000
```
**But evolve-brain is a different machine** — for it to report runs/gates to the dashboard, bind to all
interfaces, not just localhost:
```bash
uvicorn dashboard.server:app --host 0.0.0.0 --port 8000
```
> The bare `uvicorn … --port 8000` binds **127.0.0.1 (localhost only)** — the brain can't reach it.
> `--host 0.0.0.0` exposes it on the network. The port also comes from `EVOLVE_DASHBOARD_PORT` / `PORT`
> (default `8000`); the SQLite store defaults to `~/.evolve/dashboard.db` (override `EVOLVE_DASHBOARD_DB`).
> The server loads `.env` from the repo root on startup, so do step 3 of installation first.

**3. Point the brain at it.** On **evolve-brain**, set `EVOLVE_SERVER_URL` in `.env` to the admin's
reachable address — e.g. `http://evolve-admin:8000` (or its IP) — and open the port in the firewall
between brain ↔ admin.

**4. Open + verify.** Browse to your `EVOLVE_SERVER_URL`; the SPA loads at `/`. A quick health check:
```bash
curl $EVOLVE_SERVER_URL/api/apps/evolve/repos   # should return your repo collection as JSON
```

### Keeping it running
A foreground `uvicorn` dies when the shell closes. For a long-lived dashboard:
- **Linux** — a systemd unit:
  ```ini
  [Unit]
  Description=Evolve dashboard
  [Service]
  WorkingDirectory=/home/<you>/repos/evolve
  ExecStart=/home/<you>/repos/evolve/.venv/bin/uvicorn dashboard.server:app --host 0.0.0.0 --port 8000
  Restart=always
  [Install]
  WantedBy=default.target
  ```
  Then `systemctl --user enable --now evolve-dashboard`.
- **Windows** — run inside **WSL** (required, see [03-installation](03-installation.md)) and use the
  systemd unit above, or a `tmux` session.
- **macOS** — a `launchd` plist, or a `tmux`/`screen` session.

---

## Pasting your decide-token

In the header there's a **decide token** field. Paste your `EVOLVE_DECIDE_TOKEN` there **once**:

- It's stored in the browser (`localStorage`) and sent as `Authorization: Bearer <token>` on every
  decision and on the archive / reverify actions.
- The little state indicator next to it reads **"no token"** (amber) until you paste one, then
  **"ready to decide ✓"** (green); once set, the field **masks** the token (shown as dots).
- *(It's a plain text field that masks via CSS, not a `type=password` field — deliberately, so
  macOS / iCloud password managers don't intercept the paste.)*
- **Until a token is set, the decision buttons are disabled** — you can read everything, but you
  can't decide. This is the operator's key; the service token the brain uses is rejected (403) at the
  decision endpoint, so the engine can push packets but never decide them.

The token lives only in your browser and evolve-admin's `.env`. GET endpoints (reading runs, gates,
events) need no auth at all; only mutations do.

> **⚠ Exposure.** The dashboard's **GET** endpoints are unauthenticated by design — anyone who can reach
> the port can read every run, gate packet, diff, and event. And if you start the server with **both**
> tokens blank (the un-configured state), even mutations are accepted anonymously. So when you bind
> `--host 0.0.0.0`, keep it on a **trusted network** (or behind a reverse proxy with auth), set your
> tokens before exposing it, and don't put it on the public internet.

---

## The runs rail (left)

The left rail lists the runs in scope. Each row shows:

- **Title** (or the run id if untitled) and a **status chip** — colour-coded:
  - blue = `running` / `in_progress`
  - green = `done` / `merged` / `verified`
  - amber = `waiting`
  - red = `failed` / `error` / `rejected`
  - grey = `archived`
  A **done** run reads **`verified ✓`** (and its detail panel shows a *"GitHub issue closed"* marker);
  a run whose gate you've decided shows **`✓ approved`** until the loop acts on it (not "waiting").
- A pulsing **"⚠ waiting on you"** badge whenever that run has a gate parked for your decision. This
  is the at-a-glance signal that the run needs you.
- A meta line: the **run id** (`ev-<n>`, or `ev-<repo-slug>-<n>` for a non-primary repo), the
  **phase**, and the **current agent** (`@<agent>`).

At the top of the rail, an **active / archived** toggle switches the list between live runs and
archived ones. (There is no spend/cost readout: Evolve runs on the Claude Code **subscription**, not
the metered API, so there are no per-run token costs to show.)

Click a run to open it in the main panel.

---

## The repo-switcher (header)

A **repo** dropdown in the header scopes every view (rail, gates) to one repo from your
collection, or **all repos**. Its options come from `GET /api/apps/evolve/repos`, which reads your
`evolve.repos.yaml` registry (falling back to the single `GITHUB_REPO` if no registry is
configured). Switching repo clears the current selection and reloads the rail for that scope.

---

## The issue-intake panel (rail)

When you select **one** repo, an **issue intake** panel appears at the top of the rail showing that
repo's intake mode (`auto` or `manual` — see [Configuration → Issue intake](04-configuration.md#issue-intake-auto-vs-manual)):

- **auto** — every open issue is processed; the panel just states that.
- **manual** — the loop processes **only issues you admit**. A human reads the issue on GitHub first,
  then **Admit #** here (type the number → Admit); admitted issues show as pills you can revoke (✕).
  This is the safety control for public/untrusted repos: an un-admitted issue is never even read by an
  agent. Admitting requires the decide-token (it's an operator trust decision).

---

## The gate-review panel (main)

When you select a run that has a parked gate, the main panel leads with the **gate review**. It
renders the packet exactly as the brain pushed it, so you see the *actual* spec and reviews, not a
summary.

### The gate banner & label

A prominent amber banner names the gate and the item: **"⚠ Gate 1 · intent — waiting on you"** (or
**Gate 2 · result**, **Gate 3 · verify**). The label maps directly from the packet's gate:
`gate1 → intent`, `gate2 → result`, `gate3 → verify`.

### The lead recommendation

A **lead recommendation** section shows the lead agent's single call — an action pill colour-coded
**approve** (green), **change** (amber), or **reject** (red) — beside its rationale (the "why").
This is the swarm's recommendation; the decision is still yours.

### The readable packet

Below the recommendation, the panel renders each packet section that's present, in order:

- **Work item** — the GitHub issue: id/number, title, source, repo, author, etc., plus the full
  issue body.
- **Decisions needed** — the human forks the design flagged: each numbered question, its options,
  and the agents' recommended option. These are the choices you answer (in your decision note, or by
  talking them through in `/chat-ev`).
- **Spec tree** — when the design decomposed into a tree of capabilities / features / specs, the
  nested structure. (A single spec omits the tree.)
- **Code plan** — the read-only **code scout** sketch: which files would be added / modified /
  rewritten and where new logic lands, so you see the change's code footprint *before* approving —
  shown at Gate 1.
- **Agents** — "the team": each role's full structured output (spec-audit findings, each reviewer's
  concerns/conflicts, the lead's arbitration).
- **Validation** — the result of validating on the test machine (`passed` + reason / evidence).
  Shown at Gate 2.
- **Diff** — the full unified patch, syntax-coloured (adds green, dels red, hunks purple), in a
  collapsible block. Shown at Gate 2.

Any packet field the panel doesn't have a dedicated renderer for is shown as collapsible
pretty-printed JSON, so nothing is hidden.

### The decision controls

At the bottom is **your decision** (relabelled **your verification** at Gate 3):

- **Per-decision controls** — each question the packet flagged renders as **selectable options**
  (radio buttons, with the agents' **recommended** option pre-selected and ★-badged) plus a **free-form
  note field per question**. Pick an option and jot a note on each — your answers are folded into the
  decision note the loop reads (no copy-pasting answers into one box).
- A **note** textarea for any overall context (required context for a *Change*).
- Three buttons: **✓ Approve**, **✎ Change**, **✕ Reject**. At **Gate 3** the approve button
  relabels to **✓ Verify** (Gate 3 is a verification, not an approval-to-build).
- **Disabled when no decide-token is set** — with a reminder to paste it in the header.

Clicking a button POSTs the decision (your per-decision answers + note) to the gate's decision endpoint
as a decide-token bearer. If the token is missing or wrong, the dashboard surfaces the 401/403. Once
recorded, the panel **stays on screen** showing your decision in past tense (**APPROVED** / change
requested / rejected) plus a **"what's next"** line (e.g. *"the loop runs the build segment next"*), and
the next loop pass on the brain acts on it — the run never goes blank or back to "waiting on you."

> Deciding here and deciding via `/chat-ev` / `/evolve-pm` are equivalent — both record against the
> same gate with the same decide-token. Use the console for a clear call; use `/chat-ev` when you
> want to pressure-test a Gate-1 item first (see [Daily Operation](07-running.md)).

---

## The live activity tail

Below the gate (or as the main content for a run with no parked gate) is the **live activity**
section — the run's event stream, polled continuously. Lines are grouped by agent, each with a
timestamp, and show the kind (tool / info / emit / agent_start / agent_end …) and the full,
untruncated message. This is where you watch the swarm narrate its work: the spec as it's written,
each reviewer's findings, the lead's call, the build diff. It auto-scrolls as new events arrive.

---

## Archive & reverify actions

Both require the decide-token:

- **Archive** — a button **in the run header** (next to the status chip) on any non-archived run;
  hides a finished or abandoned run from the active list (it moves to the **archived** toggle, which
  shows ONLY archived runs).
- **↻ Reverify** — beneath the activity tail; re-open a *done* run's Gate 3. Use it when an item was marked verified but later
  turns out to be broken: it sets the gate back to `waiting` (phase `verify`) **without** clobbering
  the existing packet, so the item comes back to your queue and the loop will re-engage it. Available
  on runs that are `done` / `verified` / `merged` or in the `verify` phase.

---

## The API contract (brief)

The SPA speaks a small REST contract under **`/api/apps/evolve`** — `runs`, `gates`,
`gates/{id}/decision`, `runs/{id}/events`, `runs/{id}/archive`, `runs/{id}/reverify`, `repos`, and the
issue-intake endpoints `admitted`, `admit`, `admit/revoke`. The same contract is what the engine CLIs
(`evolve_explain.py`, `evolve_decide.py`, the brain's bridge) call, which is why the PM and the
dashboard always agree on live state. GET endpoints are open; mutations need the service-or-decide
token, and the decide-only endpoints (decision, archive, reverify, **admit / admit/revoke**) reject the
service token outright. For the full contract and the two-token model, see
[Architecture & the Fleet](02-architecture.md).

---

## See also

- [Daily Operation](07-running.md) — starting the dashboard, the daily rhythm, deciding gates.
- [Gates & the Flow](09-gates-and-the-flow.md) — what each gate decides.
- [Architecture & the Fleet](02-architecture.md) — the REST contract and the two-token security model.
- [Configuration](04-configuration.md) — the dashboard's `.env` keys (port, DB path, tokens, URL).
