# 06 · Writing a target adapter

> Part of the Evolve operator manual. Siblings: [README.md](../README.md),
> [01-overview](01-overview.md), [02-architecture](02-architecture.md),
> [03-installation](03-installation.md), [04-configuration](04-configuration.md),
> [05-the-charter](05-the-charter.md), [07-running](07-running.md),
> [08-the-dashboard](08-the-dashboard.md), [09-gates-and-the-flow](09-gates-and-the-flow.md),
> [10-operations-and-troubleshooting](10-operations-and-troubleshooting.md), [sdlc.md](sdlc.md).

The charter ([05-the-charter](05-the-charter.md)) teaches Evolve *what your product is*. The target
adapter teaches it *how to deploy and validate your product on the test host*. These are the two
pieces that are genuinely yours; everything else is generic.

---

## 1. What an adapter is

A **target adapter** is the one project-specific bit of automation in an Evolve instance. The engine
knows the *shape* of "deploy a branch, check it's up, drive it like a user, judge the evidence" — but
it can't know how *your* stack does those things. The adapter fills that in.

It lives in `adapters/<name>/` and is **gitignored, per-instance** — exactly like `.env` and
`CHARTER.md`. The repo's `.gitignore` carries:

```
# adapters/example/ documents the interface; the real one lives here, gitignored.
adapters/skipper/
```

So the repo ships a **tracked, scrubbed reference adapter at `adapters/example/`** (a real Skipper
adapter with names, locations, credentials, and hostnames replaced by neutral placeholders), and the
live adapter for an instance lives in its own gitignored directory (`adapters/skipper/` for the
Skipper instance; `adapters/<your-project>/` for yours). You copy the *shape* of the example into
your own directory — you do not run the example files inside `evolve/` (they import the example
product's own modules; see §5).

All connection details come from environment variables, never hardcoded — `$EVOLVE_TARGET_REPO_PATH`,
`$EVOLVE_DEPLOY_CMD`, `$EVOLVE_HEALTH_PATH`, `$EVOLVE_TEST_HOST`, `$EVOLVE_BRAIN_HOST`,
`$GITHUB_REPO`, etc. (see [04-configuration](04-configuration.md)).

---

## 2. The operations the engine expects

An adapter is a directory under `adapters/` with an **`adapter.yaml`** that maps each operation to a shell command; the engine invokes them through one entrypoint — `python3 scripts/evolve_adapter.py <op> key=value …` (the binding, see §5). The operations:

| operation | required? | what it must do | Skipper example's approach |
|-----------|-----------|-----------------|----------------------------|
| `deploy host=<host> ref=<ref>` | yes | check out `ref` on `host`, bring the product up, return `{ok, healthy, sha}` | `git fetch` + `git checkout` then the deploy command from `$EVOLVE_DEPLOY_CMD` (`skipper update`, non-interactive), then wait until healthy |
| `health host=<host>` | yes | is the product up on `host`? | poll `$EVOLVE_HEALTH_PATH` (the status endpoint) until it reports `db_ok` |
| `acceptance host=<host> spec=<id\|file>` | yes | drive the product as a user and return `{passed, evidence}` | a logged-in Playwright UI driver + chat, judged on **captured tool-calls**, DB state, and screenshots |
| `seed host=<host>` | optional | load fixtures / mock data | `seed_mock_data` — realistic mock household data so a fresh box looks lived-in |
| `scaffold unit=<name>` | optional | scaffold a new unit of work | `new_app` — generate a new drop-in app package |

**`deploy` and `health` are the deploy half**; **`acceptance` is the validate half**. The optional
operations are conveniences: `seed` gives acceptance a known starting state, `scaffold` lets the
implement step stamp out a new module the way you would by hand. **Posting proof to the GitHub issue is built into the engine** (`github_connector.attach_image_to_issue` uploads the screenshot to catbox.moe and comments it inline) — NOT an adapter operation; your adapter only produces the screenshot in `acceptance`.

> The acceptance contract is **evidence-returning, not boolean.** It returns *what actually happened*
> (the answer **and** the tool-calls that fired, plus screenshots/DB rows) so the validate agent
> judges on captured reality rather than a self-reported pass. This is what makes validation honest
> by construction — see [09-gates-and-the-flow](09-gates-and-the-flow.md).

---

## 3. Tiered acceptance (design note)

`acceptance` is the operation that varies most by project type:

- A project with a **live UI** drives the real screens + chat as a user and judges on captured
  evidence (Skipper's approach — Playwright + chat + tool-call capture).
- A **CLI / library** project has no UI to drive. There, `acceptance` can be implemented as
  **unit-tests-only**: run the bound test suite on the test host and return its results as the
  evidence. The README states this directly: *"a project with no live UI can implement `acceptance`
  as unit-tests-only."*

This tiering is a **design note**, not yet a fully-wired feature: the Skipper reference implements the
rich UI-driven tier; the unit-tests-only tier is the documented path for non-UI projects but does not
yet ship a turnkey reference. If your project is a CLI or library, expect to write the thinner
`acceptance` yourself (run the suite, capture stdout/exit codes as evidence).

---

## 4. The reference adapter, file by file

Walk through `adapters/example/` (the real, scrubbed Skipper adapter). Each file maps to one of the
operations above. **These are illustrative** — they import the Skipper product's own modules
(`apps.*`, `app_platform.*`, `data_layer.*`, the Skipper web app) and are **not meant to run inside
`evolve/`**. Copy the shape into your own `adapters/<your-project>/`.

**Deploy + health**

- **`box2_live.py`** → `deploy` / `health`. The lifecycle controller that runs *on* the test host:
  `git fetch` + `git checkout -B <branch> origin/<branch>`, then the deploy primitive (`skipper
  update`, non-interactive via `SKIPPER_NO_FOLLOW=1`), then `wait_healthy()` polling the status URL.
  `reset` redeploys the baseline branch (`release`). The repo path comes from
  `$EVOLVE_TARGET_REPO_PATH`. Note it *calls the same command the operator runs by hand* — it never
  reinvents the deploy plumbing.

**Acceptance**

- **`box2_acceptance.py`** → the reusable `acceptance` spine. A `Session` wraps a logged-in Playwright
  page with high-level primitives (`open_app`, `click`, `fill`, `select`, `send_chat`). `send_chat`
  returns **hard evidence** — the assistant's answer *and* the tool-calls that fired (pulled from the
  chat-history API) — so judgments are grounded in what really happened. `run_scenario` executes a
  declarative scenario with per-step pass/fail.
- **`ui_harness.py`** → the hardened Playwright harness underneath acceptance: drives real screens
  like a user, hardened against React controlled inputs, flaky SPA navigation, and click-blocking
  modals; captures console errors and HTTP ≥ 400 and screenshots failures.
- **`box2_no_reload_acceptance.py`** → a complete **bound test for one issue** (ev-36), with an oracle
  *and* a negative control — the model for what a single spec's acceptance test looks like end to end.
- **`box2_fixture.py`** → snapshot/restore a reproducible DB baseline (`snapshot` / `reset` /
  `status`) so every acceptance run starts from identical state. (The test host is the disposable
  validator, so a full-DB reset is fine.)
- **`box2_drive.py`** → a stdlib-only "hands" CLI so an agent can drive one chat turn at a time over
  SSH (`signup`, `say`, `history`, `state`) — the brain stays in the agent, never in this file.

**Seed**

- **`seed_mock_data.py`** → the `seed` operation: realistic mock household data (~20 records per
  section) so a fresh box / demo looks fully lived-in. Run inside the product container.

**Scaffold**

- **`new_app.py`** → the `scaffold` operation: generate a new drop-in app package that satisfies the
  platform's app contract.

**Diagnostics / setup helpers** (used while validating, not part of the core contract):

- **`box2_cancel_onboarding.py`**, **`box2_diag_chatturns.py`**, **`box2_sim_nudge.py`** — small
  in-container helpers (force a state, inspect per-turn prompt sizes, simulate a proactive-nudge
  cycle). They illustrate the kind of state-setup an adapter accretes as you validate real issues.

---

## 5. The binding — how the engine invokes your adapter

The engine never calls your scripts directly. It goes through one stable entrypoint:

```
python3 scripts/evolve_adapter.py <op> key=value ...
```

`scripts/evolve_adapter.py` reads **`$EVOLVE_ADAPTER`** (the active adapter's directory name under
`adapters/`), loads that directory's **`adapter.yaml`** — a map of operation → shell command with
`{placeholder}`s — substitutes the `key=value` args, and runs the command on evolve-brain. Output and
exit code pass straight through to the calling agent; an op the manifest doesn't define is a clean
error, so you implement only what you need.

A manifest is a few lines (see [`adapters/example/adapter.yaml`](../adapters/example/adapter.yaml)):

```yaml
deploy: "ssh {host} 'cd ~/myproject && git fetch -q && git checkout -q {ref} && ./deploy.sh'"
health: "ssh {host} 'curl -fsS http://localhost:8000/health >/dev/null'"
acceptance: "python3 adapters/myproject/run_acceptance.py {host} {spec}"
```

To wire your project: set `EVOLVE_ADAPTER=<name>` in `.env`, create `adapters/<name>/adapter.yaml`, and
put any helper scripts it calls alongside it. The reproduce / validate / deploy steps in the skills
already call `evolve_adapter.py deploy|seed|acceptance …`, so once your manifest resolves those ops the
loop drives your project end to end.

---

## 6. The dependency guard (OPTIONAL, pluggable)

Evolve imposes **no** dependency model. *If* you want a deterministic check of where code landed, set
**`EVOLVE_DEP_CHECK_CMD`** to a checker — the engine runs it on the changed files during the build and
**skips it entirely when blank** (the default). A project with an unusual architecture points
`EVOLVE_DEP_CHECK_CMD` at its own script (anything taking `<worktree> <base_ref>`, printing JSON, exiting
non-zero on a violation) — this is how arbitrary dependency policies plug in.

The engine **ships one reference checker** — `scripts/evolve_dep_check.py` — for the common **layered /
monorepo** case (the rule a charter's `## Stack & repository layout` would describe). Opt in with
`EVOLVE_DEP_CHECK_CMD=python3 scripts/evolve_dep_check.py`. It parses the imports of every changed `.py`
file and fails if any crosses a boundary the wrong way: the core **must never import a unit**, and
**units must not import each other's internals**. Its boundaries are configured:

- `$EVOLVE_PLATFORM_PREFIXES` — the core package prefixes units may depend *on* (default `core`).
- `$EVOLVE_APP_GLOB` — the unit/app directory glob (default `apps/*`); units in it must not import
  each other.

It only flags imports a change **newly introduces** (HEAD minus the base ref), so pre-existing
baseline debt in a touched file isn't blamed on the change. Run it in the feature worktree before
Gate 2 (`python3 scripts/evolve_dep_check.py [repo_dir] [base_ref]`; exit 0 = clean, 1 =
violations).

The relationship: the **architecture review** judges placement *intent* before code is written, the
**adapter's acceptance** proves the change *behaves* correctly on the test host, and the **dep-check**
deterministically proves the change put code in the *right place*. All three are configured to your
project — the first two via the charter + adapter, the dep-check via `$EVOLVE_PLATFORM_PREFIXES` /
`$EVOLVE_APP_GLOB`. See [04-configuration](04-configuration.md) for setting all of these.

---

## 7. How to start

1. `mkdir -p adapters/<your-project>/` (it'll be gitignored if you reuse the `adapters/skipper/`
   ignore line, or add your own ignore entry).
2. Copy the *shape* of the relevant `adapters/example/` files — at minimum a `deploy`/`health` script
   and an `acceptance` script — and rewrite their bodies for your stack. Strip the Skipper-specific
   imports.
3. Set the connection env vars in `.env`: `$EVOLVE_TARGET_REPO_PATH`, `$EVOLVE_DEPLOY_CMD`,
   `$EVOLVE_HEALTH_PATH`, `$EVOLVE_TEST_HOST` (see [04-configuration](04-configuration.md)).
4. Set `$EVOLVE_PLATFORM_PREFIXES` / `$EVOLVE_APP_GLOB` to match your layout so the dep-guard knows
   your boundaries.
5. Verify by hand first: SSH to the test host and run your `deploy` then `acceptance` scripts. If you
   can deploy a branch and get evidence back, the engine can too.

## 8. Enabling app/model repo builds (multi-repo) — operator runbook

By default the loop builds your **platform** repo in place. To also have Evolve build an **app** (or
`model`) repo — one that lives in its **own** GitHub repo but ships by being cloned into the platform —
there are a few setup steps (the engine does the rest: it scans the app's issues, builds in
the app's own checkout on its own branch, and hands your adapter everything needed to deploy it).

> **Principle: the agents stand up the test host THEMSELVES — never hand-seed it.** Give the **test host
> read-only git access to all your repos** (a fine-grained read-only PAT in its git credential helper),
> and provide a **`prepare` adapter op** that stands up the **baseline from scratch** — clone the
> **platform** at its staging branch, build, seed mock data — even from an empty `~/repos` (see
> `adapters/skipper/prepare_test_host.py` for a registry-driven example). The **app under test is
> installed per-run by `deploy`** (reproduce installs its baseline, validate its feature branch), **not**
> all apps at once — one app with a broken migration would otherwise take the whole instance down. Three
> rules this enforces: the test host is always a known state the agents rebuilt; deployed app code is a
> **real `git clone`** (the commit is always visible — never an opaque copy); and the acceptance harness
> logs in as a **seeded mock user**, never a real person or an ad-hoc account.
>
> **Make the QA login account part of `seed`, not a separate step.** The harness needs a known login
> account. Create it *inside* your `seed` op (and therefore `prepare`, which seeds) — a deterministic
> account with a fixed password and full privileges. Then **any** reseed/reset re-establishes it, so an
> agent can never end up on a freshly-seeded box with no login and start guessing credentials. Don't
> rely on agents remembering to recreate it.
>
> **Disable your product's background/scheduled AI work on the test host (cost control).** The test host
> runs on mock data nobody reads — so any always-on background LLM work (autonomous agents, scheduled
> jobs, document processors, summarizers) just burns API spend on fakes, 24/7. Turn it **off by default
> in `seed`** (leave only what acceptance actually drives, e.g. an interactive request path). On a product
> with several always-on background workers this can quietly run to hundreds of dollars a month on the
> test box alone — so make `seed` leave the test host quiet.

### Step 1 — register the app repo with a `host`
In `evolve.repos.yaml`, the app entry must declare `type: app`, its own `path`, the `host` platform it
deploys into, and the `clone_path` inside that host:

```yaml
- name: your-org/your-app-foo
  type: app
  path: ~/repos/your-app-foo          # the app's OWN checkout on the brain
  host: your-org/your-platform        # which platform it clones INTO
  clone_path: apps/foo                # path inside the host  → clone_target = <host path>/apps/foo
  branch_model: release->main         # the app's own staging→world branches
  spec_roots: ["specs"]
  # token_env: FOO_TOKEN              # only if it's in a different GitHub account
```

### Step 2 — clone the app repo onto evolve-brain
The brain **builds** the app, so its checkout must exist locally at the `path` you declared, as a normal
git clone the loop can `git worktree add` from:

```bash
# on evolve-brain
git clone https://github.com/your-org/your-app-foo.git ~/repos/your-app-foo
```

(Repeat for each app/model repo. The platform repo you already cloned during install.)

### Step 3 — add an APP deploy recipe to your `adapter.yaml`
This is the one piece of real logic you write. When the engine invokes `deploy` for an app item it passes
`repo=<owner/repo>` and fills these placeholders from the registry, so **one `deploy` op can branch on the
repo type**:

| placeholder | meaning |
|---|---|
| `{repo_type}` | `platform` \| `app` \| `model` |
| `{ref}` | the feature branch / sha to deploy |
| `{repo_path}` | the repo's own checkout path (on the brain) |
| `{staging_branch}` / `{world_branch}` | that repo's branches |
| `{host_repo}` / `{host_path}` | (app/model) the platform it deploys into, and that platform's path |
| `{clone_path}` | e.g. `apps/foo` |
| `{clone_target}` | absolute path on the **host**: `<host_path>/<clone_path>` |

A deploy op that handles **both** a platform (in place) and an app (cloned into the host), then restarts:

```yaml
deploy: >
  ssh {host} 'set -e;
    if [ "{repo_type}" = platform ]; then
      cd {host_path} && git fetch -q --all && git checkout -q {ref} && ./deploy.sh;
    else
      # app/model: replace the app dir inside the host with the built branch, then restart the host
      rm -rf {clone_target} &&
      git clone -q -b {ref} https://github.com/{repo}.git {clone_target} &&
      cd {host_path} && ./deploy.sh;
    fi'
```

Notes:
- **The app must exist on the *test host* too** for the clone-in to work — i.e. the host platform is
  checked out on evolve-test, and the deploy clones the app branch into its `apps/<id>` there before
  restarting. (For a private app repo, the test host needs read access — a deploy key or token.)
- Adjust `./deploy.sh`, the remote URL, and the "replace the app dir" mechanics to your stack (some
  projects symlink, copy, or `pip install -e` the app instead of a raw clone). The point is: branch on
  `{repo_type}` and use `{clone_target}`.
- `acceptance`/`seed`/`health` usually don't need to change — they run against the host as a whole.

### Step 4 — verify by hand, then end-to-end
1. **By hand:** `python3 scripts/evolve_adapter.py deploy host=$EVOLVE_TEST_HOST ref=<some app branch> repo=your-org/your-app-foo` — confirm the app lands in `apps/foo` on the test host and the product comes back up healthy.
2. **End-to-end:** open a GitHub issue on `your-org/your-app-foo`. The loop will pick it up (its run id is `ev-<app-slug>-<n>`), build it in `~/repos/your-app-foo`, deploy it into the host via your recipe, and run it through the gates exactly like a platform issue.

If you skip steps 1–3, app issues still get **triaged and surfaced** (you'll see them on the dashboard),
but the build will fail at deploy because there's no recipe / clone — so wire all three before relying on
autonomous app builds. Companion repos (`type: companion`) are intentionally **not** built — Evolve
specs/drafts them and you build/test them yourself.
