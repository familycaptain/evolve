# 03 — Installation & setup

This guide takes you from an empty set of machines to a running Evolve instance working your
repos' issues. Work through the steps in order; each one points to the deeper reference where it
exists.

- For *what* every config key means, see [`04-configuration.md`](./04-configuration.md).
- For the charter you'll author in step 5, see [`05-the-charter.md`](./05-the-charter.md).
- For the target adapter you'll add in step 6, see [`06-target-adapters.md`](./06-target-adapters.md).
- Once it's running, see [`07-running.md`](./07-running.md), [`08-the-dashboard.md`](./08-the-dashboard.md),
  and [`10-operations-and-troubleshooting.md`](./10-operations-and-troubleshooting.md).

---

## Prerequisites

### The fleet — four machines

Evolve runs across four logical machines (the **fleet**). They can be physical boxes, VMs, or
containers, on **any OS** (Windows / macOS / Linux), and they can be headless. What matters is the
role each plays, not the hardware:

| Logical name | What it runs | What it needs installed |
|---|---|---|
| **evolve-admin** | `/evolve-pm` + `/chat-ev` in Claude Code, **and** the dashboard web server | **Claude Code** + a Claude login; **Python 3** (for the dashboard); `git` |
| **evolve-brain** | `/loop` + `/evolve` in Claude Code (the agent swarm) | **Claude Code** + a Claude login; `git` |
| **evolve-test** | candidate deploy + automated acceptance | **your target project's own deploy/test tooling** |
| **evolve-uat** | release deploy for human gate-3 verification | **your target project's own deploy tooling** |

You can collapse these onto fewer physical hosts for a trial (even one machine with the four roles
as separate working dirs), but the **two-token safety split** (below) only has teeth when
evolve-admin and evolve-brain are genuinely separate `.env` files — the brain must never hold the
decide-token.

### Software & access checklist

- **Claude Code installed and logged in** on **evolve-admin** and **evolve-brain**. Evolve runs
  *inside* Claude Code — these two sessions are the engine.
- **On Windows hosts, WSL is required.** Install WSL with a Linux distro (`wsl --install`, then Ubuntu)
  and run **all** Evolve components inside it — Evolve assumes a Unix environment. Throughout this guide,
  "Windows" means "Windows under WSL," and you follow the **Linux / macOS** steps inside the WSL shell.
- **Python 3** on **evolve-admin** — the dashboard is a small FastAPI/uvicorn app
  (`dashboard/requirements.txt`: `fastapi`, `uvicorn`, `pyyaml`).
- **git + passwordless SSH** between the machines for deploys and remote drives:
  - **evolve-brain → evolve-test** and **evolve-brain → evolve-uat** (the brain cuts branches and
    deploys candidates/releases to those hosts).
  - **evolve-admin → evolve-brain** (the PM drives the brain for fleet operations).

  Set this up with SSH keys (`ssh-keygen` + `ssh-copy-id`) so no step ever prompts for a password —
  unattended deploys must be non-interactive.
- **The target project's own deploy tooling** present on **evolve-test** and **evolve-uat** — i.e.
  whatever command brings *your* product up (this is what `EVOLVE_DEPLOY_CMD` invokes, and what the
  adapter's `deploy()` calls). Evolve does not replace your deploy mechanism; it drives it.
- **A GitHub token** — a Personal Access Token with **Issues: Read & Write** (plus **Contents:
  Read & Write** if Evolve pushes branches) on the repos you'll register. Detail in
  [`04-configuration.md` → Tokens](./04-configuration.md#tokens).

### Test & UAT host setup (easy to miss)

evolve-test and evolve-uat run **your product**, so beyond the deploy command they need everything your
deploy *and acceptance* actually touch. The pieces most often forgotten when standing up a new instance:

- **Your product's full runtime.** Whatever your deploy brings up must have its dependencies present —
  the database, services, containers, or daemons your product needs to run. (A real example: a test
  host that runs the app plus a Postgres container via Docker — so Docker + the images have to be
  installed there first.)
- **Your acceptance tooling, installed on the host.** The adapter's `acceptance` op runs *on this box*.
  If it drives a browser, install the browsers **and their OS libraries** — e.g. `playwright install
  --with-deps chromium`. If it runs a CLI, an API client, or a test suite, install that runner.
  **Evolve does not install your test tooling for you** — this is the single most commonly missed step.
  If you do not have test tooling, open this project in Claude Code and ask it to build tooling for
  you and give it your project repo code as a reference. 
- **Test credentials / fixtures the acceptance needs.** If acceptance logs in or calls an authed
  surface, put the test credential on the host **outside git** (e.g. a `~/.myproject_test_pw` file the
  adapter reads), never in the repo. Seed any baseline data via `evolve_adapter.py seed`.
- **Keep it isolated and disposable.** This box is deployed to and reset constantly; run it on
  **mock / non-production data** so a bad candidate can never reach anything real.

### evolve-brain needs your target repo(s) cloned

The brain doesn't just run Evolve — it **builds your project**. Clone each repo from your registry onto
evolve-brain at the path its entry declares (`path`). An `app`/`model` is its **own** checkout that
gets cloned into its `host` platform at `clone_path` on deploy. The loop cuts an **isolated git
worktree per work item**, as a sibling of that checkout (so a build never touches your main checkout) —
which means the checkout must be a normal git clone the brain can `git worktree add` from. The brain
also needs Python with the engine's deps (at minimum `pip install pyyaml`, for the registry + adapter
binding); a venv is cleanest.

> Building a **platform** repo works out of the box. To also build **app/model** repos (own repo →
> cloned into a host platform), there's a short setup — clone the app repos here + add an app deploy
> recipe to your adapter: see [06-target-adapters → §8 Enabling app/model repo builds](./06-target-adapters.md#8-enabling-appmodel-repo-builds-multi-repo).

### Setting up passwordless SSH (per OS)

Evolve's deploys run **non-interactively**, so the brain needs **key-based SSH** to evolve-test and
evolve-uat (and evolve-admin → evolve-brain). Generate a key on the *source* machine and put its public
key in the *target's* `~/.ssh/authorized_keys`. Use **no passphrase** (or an ssh-agent) so nothing ever
prompts.

**Linux / macOS** (run on the source machine, e.g. evolve-brain):
```bash
ssh-keygen -t ed25519                 # accept defaults; empty passphrase for unattended use
ssh-copy-id <user>@<evolve-test-host>
ssh-copy-id <user>@<evolve-uat-host>
ssh <user>@<evolve-test-host>         # must log in with NO password prompt
```

**Windows** — do it **inside WSL** (required). WSL is a Linux userland, so just follow the
**Linux / macOS** steps above (`ssh-keygen` + `ssh-copy-id`) in your WSL shell.

**Host aliases** — put the fleet in `~/.ssh/config` (works on every OS) so the logical names in `.env`
resolve and `ssh evolve-test` "just works":
```
Host evolve-test
    HostName 10.0.0.12
    User youruser
Host evolve-uat
    HostName 10.0.0.13
    User youruser
```
Then `EVOLVE_TEST_HOST=evolve-test` (etc.) is reachable from the brain on any platform.

### Cross-platform notes

Evolve assumes a **Unix environment**: Linux, macOS, or **Windows under WSL** (which is why WSL is
required on Windows — see Prerequisites). Inside any of those, the commands in this guide are identical,
so there is no separate Windows command set to learn — `cp`, `openssl rand -hex 32` (or the
`python -c "import secrets; print(secrets.token_hex(32))"` fallback if `openssl` isn't installed),
`uvicorn …`, etc. are the same everywhere. `~`-style config paths (e.g. `~/.evolve/dashboard.db`) are
resolved by Python's `expanduser`. Both **evolve-admin** (the dashboard + your PM session) and
**evolve-brain** (the agentic loop) issue Unix-style commands (`git`, `ssh`, `grep`, `python3`), so on
Windows both run inside WSL.

The **target hosts** (evolve-test / evolve-uat) run *your* product, so their OS and deploy tooling are
yours to choose — Evolve just SSHes in and runs your adapter's deploy command, whatever it is.

---

## Step-by-step

### 1. Clone the repo on evolve-admin and evolve-brain

Clone Evolve onto **both** human-facing machines (the test and uat machines run *your* product, not
Evolve itself):

```bash
git clone https://github.com/your-org/evolve.git
cd evolve
```

Everything project-specific you create below (`.env`, `evolve.repos.yaml`, `CHARTER.md`,
`adapters/<name>/`) is **gitignored** — you never commit your instance's config into the engine
repo. The tracked `*.example` files are the templates you copy.

### 2. Generate the two Evolve tokens and obtain a GitHub PAT

Evolve uses **three** tokens. Generate the two Evolve secrets yourself:

```bash
openssl rand -hex 32     # EVOLVE_DECIDE_TOKEN   (run once)
openssl rand -hex 32     # EVOLVE_SERVICE_TOKEN  (run once)
# or: python -c "import secrets; print(secrets.token_hex(32))"
```

- **`EVOLVE_DECIDE_TOKEN`** — the parent token that authorizes gate decisions.
- **`EVOLVE_SERVICE_TOKEN`** — the engine token the brain uses to push runs/gates/events.

Then create a **GitHub Personal Access Token** so Evolve can read issues and push branches. A
**fine-grained** token takes about a minute:

1. GitHub → **Settings** → **Developer settings** → **Personal access tokens** → **Fine-grained tokens**
   → **Generate new token**.
2. **Repository access** → *Only select repositories* → pick the repos listed in your `evolve.repos.yaml`.
3. **Permissions → Repository permissions:**
   - **Issues → Read and write** (read issues + post the before/after evidence comments).
   - **Contents → Read and write** (push feature branches + merge to your staging branch).
4. **Generate token** and copy the `github_pat_…` value — that is your **`GITHUB_TOKEN`**. GitHub shows
   it only once.

*(A classic token with the `repo` scope also works but grants more than needed.)* Keep all three values
handy for step 3. Reference: [`04-configuration.md` → Tokens](./04-configuration.md#tokens).

### 3. Create `.env` on each machine — mind which keys go where

Copy the template and fill it in:

```bash
cp .env.example .env
```

The same file structure lives on **evolve-admin** and **evolve-brain**, but the **token rows
differ** — this difference is the safety property, not an oversight:

| Key | evolve-admin | evolve-brain |
|---|---|---|
| `EVOLVE_DECIDE_TOKEN` | **yes** (only here) | **no** — leave blank |
| `EVOLVE_SERVICE_TOKEN` | yes (same value as brain) | yes (same value as admin) |
| `GITHUB_TOKEN` | yes | yes |
| `EVOLVE_SERVER_URL` | `http://localhost:8000` (it *is* the dashboard) | the dashboard's URL on admin, e.g. `http://evolve-admin:8000` |
| fleet hosts, branch defaults, dep-guard, deploy/health | same on both | same on both |

The **decide-token lives ONLY on evolve-admin**. The brain holding only the service token is
exactly what stops the autonomous loop from approving its own gates — the dashboard returns `403`
if a service token hits the decision endpoint.

Point the brain at the dashboard with `EVOLVE_SERVER_URL` (on the brain, set it to the admin
machine's reachable URL; on admin itself it can stay `http://localhost:8000`).

See [`04-configuration.md`](./04-configuration.md#env) for the full key-by-key reference.

### 4. Create `evolve.repos.yaml` — the repo collection

This registry is what makes one Evolve instance manage *many* repos. Copy the example and list
yours:

```bash
cp evolve.repos.example.yaml evolve.repos.yaml
```

Each entry carries its own `name`, `type`, `path`, optional `host` (the platform an `app`/`model`
clones into — required when more than one platform is registered), `clone_path`, `branch_model`,
`spec_roots`, `token_env`, and `intake`. It's loaded by `engine/repos.py` (PyYAML); if the file is
absent it falls back to a single repo from `$GITHUB_REPO`. Full schema:
[`04-configuration.md` → `evolve.repos.yaml`](./04-configuration.md#evolverepos-yaml). Keep this
file consistent on **both** admin and brain.

### 5. Create `CHARTER.md` from the template

The charter is the **vision authority** every agent judges proposals against — the one piece that
is truly yours. Copy the template and fill in every load-bearing section:

```bash
cp CHARTER.example.md CHARTER.md
```

A filled-in real example ships as `CHARTER.skipper-example.md` for reference. Authoring guidance and
the meaning of each section is in [`05-the-charter.md`](./05-the-charter.md). Keep `CHARTER.md`
consistent on both admin and brain.

If you need help with creating a charter for your existing project, simply point Claude Code
at your project and the `CHARTER.skipper-example.md` example and have it build something to
get you started. 

### 6. Add a target adapter under `adapters/<name>/`

The adapter teaches Evolve how to **deploy and validate your specific project** on the test/uat
hosts — the one piece of project-specific automation. Create `adapters/<your-project>/` and
implement the operations the engine expects (`deploy`, `health`, `acceptance`, optional `seed` /
`scaffold`). A neutral reference skeleton lives in `adapters/example/`. See
[`06-target-adapters.md`](./06-target-adapters.md) for the interface.

> Bind your adapter by setting `EVOLVE_ADAPTER=<your-adapter-dir>` in `.env`. The engine invokes it
> through one entrypoint — `python3 scripts/evolve_adapter.py <op> key=value ...` — which resolves
> `$EVOLVE_ADAPTER` to `adapters/<name>/adapter.yaml`. Model your adapter on `adapters/example/` and
> read connection details from env vars, never hardcode them.

### 7. On evolve-admin: install deps and start the dashboard

The dashboard is the operator's control surface (runs, gates, repo-switcher, two-token auth). Install
its deps and start it on **evolve-admin**:

```bash
pip install -r dashboard/requirements.txt
uvicorn dashboard.server:app --host 0.0.0.0 --port 8000
```

The ASGI app object is `dashboard.server:app` (confirmed in `dashboard/server.py`). The port can also
come from the environment: the server reads `EVOLVE_DASHBOARD_PORT`, then `PORT`, defaulting to
`8000`. The SQLite store path defaults to `~/.evolve/dashboard.db` (override with
`EVOLVE_DASHBOARD_DB`). The server loads `.env` from the repo root on startup, so make sure step 3
is done first.

> For a long-lived deployment, run uvicorn under a process manager (systemd, a `tmux`/`screen`
> session, etc.) rather than a foreground shell. See
> [`08-the-dashboard.md`](./08-the-dashboard.md).

### 8. Start the two Claude Code sessions

- On **evolve-admin**, open Claude Code in the repo and run **`/evolve-pm`** — this establishes your
  PM role (review packets, decide gates on your say-so, drive items through, keep the fleet healthy).
  `/chat-ev <n>` is your gate-1 requirements partner from within that session.
- On **evolve-brain**, open Claude Code in the repo and run **`/loop /evolve`** — this is the
  non-blocking engine loop. Each pass advances one work item by one segment and ends (a gate never
  blocks the loop); it reports runs/gates/events to the dashboard via `$EVOLVE_SERVER_URL`.

> **Run the brain autonomously.** Evolve's whole point is the brain working unattended, so launch Claude
> Code on **evolve-brain** with **`claude --dangerously-skip-permissions`** — otherwise the loop stops to
> ask permission for every tool / file / command. That flag is exactly *why* the brain should be a
> **dedicated, isolated machine** (the reason the fleet exists): it lets the agent act freely on that box.
> On **evolve-admin**, where you're present to decide gates, you can run Claude normally.

See [`07-running.md`](./07-running.md) for what each session does day to day, and
[`09-gates-and-the-flow.md`](./09-gates-and-the-flow.md) for the gate flow.

---

## First-run verification checklist

Walk these in order; each confirms one layer is wired:

- [ ] **Dashboard loads.** Browse to `EVOLVE_SERVER_URL` (e.g. `http://evolve-admin:8000`) from your
      workstation. The root returns the SPA (or, if the static SPA is absent, a JSON
      `{"detail": "Evolve dashboard — SPA pending"}` — the API is still up).
- [ ] **Repo-switcher lists your repos.** `GET /api/apps/evolve/repos` (or the switcher in the UI)
      returns the entries from `evolve.repos.yaml`. If it shows only one repo (or none), the registry
      file isn't being found — check `EVOLVE_REPOS_FILE` and that PyYAML is installed.
- [ ] **Auth split is correct.** A decision call with the **service** token must be rejected with
      `403` ("a service token cannot decide a gate"); only the **decide** token (admin) is accepted.
      This proves the brain can't approve its own gates.
- [ ] **The brain reaches the dashboard.** Start `/loop /evolve` on evolve-brain and confirm a run
      appears in the dashboard — i.e. the service token + `EVOLVE_SERVER_URL` from the brain are
      correct.
- [ ] **A test issue produces a run.** File a small GitHub issue on one of your registered repos.
      On the next loop pass the brain should pick it up and open a run (`ev-<n>`); watch it appear in
      the dashboard with a live event feed.
- [ ] **A gate parks for you.** Let that run reach **Gate 1**; confirm it appears in the dashboard
      awaiting your decision, and that approving it (with the decide-token, from `/evolve-pm` or the
      UI) advances it.
- [ ] **Deploys reach test/uat.** Confirm the brain can SSH to evolve-test and run your deploy
      command non-interactively (no password prompt), and that the health check passes.

If any step fails, [`10-operations-and-troubleshooting.md`](./10-operations-and-troubleshooting.md)
has the common causes.
