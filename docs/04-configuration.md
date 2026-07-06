# 04 — Configuration reference

The authoritative reference for the three per-instance config surfaces:

- **`.env`** — fleet hosts, branch defaults, the dep-guard, deploy/health, the dashboard URL, the
  repos-file pointer, and tokens.
- **`evolve.repos.yaml`** — the registry of repos this instance manages.
- **Tokens** — how to obtain/generate each and where each lives.

For the ordered setup that uses all of this, see [`03-installation.md`](./03-installation.md). For
the charter and adapter (their own files), see [`05-the-charter.md`](./05-the-charter.md) and
[`06-target-adapters.md`](./06-target-adapters.md).

---

## `.env`

Copy `.env.example` to `.env` (gitignored) on each machine that needs it. The dashboard loads `.env`
from the repo root on startup (`dashboard/server.py`); the Claude Code skills/engine read these keys
at runtime instead of hardcoding any project's specifics.

Every key below comes from `.env.example`. "Machine(s)" tells you where each value must be present.

### Product identity

| Key | What it does | Machine(s) | Example / default |
|---|---|---|---|
| `EVOLVE_PRODUCT_NAME` | The product this instance maintains; surfaced in dashboards/logs. The charter names + describes it. | admin, brain | `YourProduct` |
| `EVOLVE_CHARTER_PATH` | Path to the charter file — the vision authority every agent judges against. | admin, brain | _(blank)_ = `CHARTER.md` (repo root) |

### Fleet hosts — the four machines

Logical names → real SSH hosts. May be VMs, containers, or boxes; any OS.

| Key | What it does | Machine(s) | Example / default |
|---|---|---|---|
| `EVOLVE_ADMIN_HOST` | Host running `/evolve-pm` + the dashboard (holds the decide-token). | admin, brain | `evolve-admin` |
| `EVOLVE_BRAIN_HOST` | Host running `/loop` + `/evolve` (the agent swarm). | admin, brain | `evolve-brain` |
| `EVOLVE_TEST_HOST` | Host where candidate changes deploy + validate. | admin, brain | `evolve-test` |
| `EVOLVE_UAT_HOST` | Host where you do gate-3 verification. | admin, brain | `evolve-uat` |

### Repos file

| Key | What it does | Machine(s) | Example / default |
|---|---|---|---|
| `EVOLVE_REPOS_FILE` | Path to the repo registry. Loaded by `engine/repos.py`; the dashboard repo-switcher and the per-pass multi-repo intake read it. | admin, brain | `evolve.repos.yaml` |
| `EVOLVE_INTAKE_DEFAULT` | Default issue-intake mode for repos that don't set their own. `auto` = process every open issue; `manual` = process ONLY issues a human admits in the dashboard. Per-repo override via the registry `intake:` field. | admin, brain | `auto` |
| `EVOLVE_TARGET_REPO_PATH` | The PRIMARY repo's local working path (single-repo fallback when no registry file is present; with a registry, each repo's `path` is used). | brain | `~/repos/your-project` |
| `GITHUB_REPO` | Single-repo fallback used ONLY when `evolve.repos.yaml` is absent (see `engine/repos.py`). | admin, brain | _(empty)_ — e.g. `your-org/your-repo` |
| `EVOLVE_OPERATOR_GH` | Comma-separated GitHub logins treated as the operator — their issues skip vision-fit and are never auto-rejected at triage. Empty = no one. | brain | _(empty)_ — e.g. `your-github-username` |

### Branch defaults

Instance-wide defaults a registry entry may override per repo via `branch_model`.

| Key | What it does | Machine(s) | Example / default |
|---|---|---|---|
| `EVOLVE_STAGING_BRANCH` | Where approved work merges (the staging branch). | admin, brain | `release` |
| `EVOLVE_WORLD_BRANCH` | The published branch (operator-owned promotion). | admin, brain | `main` |

### Dependency guard (OPTIONAL, pluggable)

Evolve imposes **no** dependency model. To run a deterministic build-time dependency check, point
`EVOLVE_DEP_CHECK_CMD` at a checker — the engine runs it on the changed files during the build, and
**skips the step entirely when it's blank** (the default). A project with an unusual architecture points
it at its own script (any script taking `<worktree> <base_ref>`, printing JSON, exiting non-zero on a violation).

| Key | What it does | Machine(s) | Example / default |
|---|---|---|---|
| `EVOLVE_DEP_CHECK_CMD` | Command to run as the dependency guard. **Blank = no guard.** | brain | _(empty)_ — e.g. `python3 scripts/evolve_dep_check.py` |
| `EVOLVE_PLATFORM_PREFIXES` | *(only for the shipped layered checker)* core prefixes a unit may depend ON. | brain | `core` |
| `EVOLVE_APP_GLOB` | *(only for the shipped layered checker)* the unit directories that must not import each other. | brain | `apps/*` |

### Spec roots

| Key | What it does | Machine(s) | Example / default |
|---|---|---|---|
| `EVOLVE_SPEC_ROOTS` | Comma-separated repo-relative globs where the C/F/S specs live. **Advisory** — no engine code reads it; it is context for the agents (the prompts reference `$EVOLVE_SPEC_ROOTS`). The authoritative per-repo setting is `spec_roots:` in the registry. | brain | _(blank)_ = type-aware default (platform: `apps/*/specs,specs`; app/model: `specs`) |

### Deploy / health (simple-case adapter knobs)

The simple-case knobs for deploying + health-checking your product on a host. The pluggable target
adapter (see [`06-target-adapters.md`](./06-target-adapters.md)) formalizes this; these cover most
stacks, and an adapter's `adapter.yaml` may reference them; the binding itself is `scripts/evolve_adapter.py`.

| Key | What it does | Machine(s) | Example / default |
|---|---|---|---|
| `EVOLVE_ADAPTER` | **The adapter binding** — names the directory under `adapters/` whose `adapter.yaml` maps the engine ops (deploy / health / acceptance / seed / scaffold) to your commands, invoked via `scripts/evolve_adapter.py <op> …`. | brain | _(empty)_ — e.g. `myproject` → `adapters/myproject/adapter.yaml` |
| `EVOLVE_DEPLOY_CMD` | Command run on a host to deploy the checked-out branch. | brain | _(empty)_ — e.g. `./deploy.sh` |
| `EVOLVE_HEALTH_PATH` | Path polled to confirm the deploy is up. | brain | _(empty)_ — e.g. `/api/health` |

### Evidence images

| Key | What it does | Machine(s) | Example / default |
|---|---|---|---|
| `EVOLVE_IMAGE_UPLOAD_CMD` | Uploader the reproduce/validate agents run (image path as last arg; must print the resulting URL on stdout) before linking screenshots on the GitHub issue. Set your own to keep evidence private. | brain | _(blank)_ = catbox.moe (public, anonymous — fine only for non-sensitive/mock data) |

### Dashboard URL

| Key | What it does | Machine(s) | Example / default |
|---|---|---|---|
| `EVOLVE_SERVER_URL` | The dashboard URL the brain reports to + the PM reads. On the brain, set it to the admin machine's reachable URL. | admin, brain | `http://localhost:8000` |
| `EVOLVE_STATE_DIR` | Where the loop stores per-item run state. Set a distinct path to run more than one Evolve instance on one host. | brain | `~/.evolve/runs` |

### Advanced path overrides (all default under `~/.evolve/`)

| Key | What it does | Machine(s) | Example / default |
|---|---|---|---|
| `EVOLVE_OUTBOX` | The offline outbox file for queued dashboard posts. | brain | _(blank)_ = `~/.evolve/outbox.jsonl` |
| `EVOLVE_SPEC_INDEX_CACHE` | The triage dedup spec-index cache. | brain | _(blank)_ = `<EVOLVE_STATE_DIR>/spec_index_cache.json` |
| `EVOLVE_COST_DB` | The spend-ledger SQLite path (vestigial on the subscription path — no metered cost). | brain | _(blank)_ = `~/.evolve/costs.db` |

### Tokens & secrets

Never commit real values (`.env` is gitignored). See [Tokens](#tokens) below for how to obtain each.

| Key | What it does | Machine(s) | Example / default |
|---|---|---|---|
| `GITHUB_TOKEN` | GitHub PAT for reading/writing Issues (+ Contents if Evolve pushes branches) on your managed repos. | admin, brain | _(empty)_ |
| `EVOLVE_DECIDE_TOKEN` | The **parent** token that authorizes gate decisions. The dashboard requires it on the decision endpoint. | **admin only** | _(empty)_ |
| `EVOLVE_SERVICE_TOKEN` | The engine token the brain uses to push runs/gates/events. Same value on both machines; rejected (403) at the decision endpoint. | admin **and** brain | _(empty)_ |

> **The two-token split is the core safety invariant.** The decide-token lives only on
> evolve-admin; the brain holds only the service token, so the autonomous loop can *propose* but can
> never *approve* its own gates.

### Dashboard-only keys (read by `dashboard/server.py`, not in `.env.example`)

These have working defaults and are optional; set them only if you need to override. They live on
**evolve-admin** (where the dashboard runs):

| Key | What it does | Default |
|---|---|---|
| `EVOLVE_DASHBOARD_BIND` | The network INTERFACE the dashboard's socket binds (an IP, not a machine name — distinct from the fleet-role `EVOLVE_ADMIN_HOST`). Binding a **non-loopback** address requires the auth tokens — token-less mode refuses to start off loopback. | `127.0.0.1` |
| `EVOLVE_DASHBOARD_PORT` (or `PORT`) | Port the dashboard binds. `EVOLVE_DASHBOARD_PORT` wins, then `PORT`. Note `uvicorn ... --port 8000` on the CLI overrides both. | `8000` |
| `EVOLVE_DASHBOARD_DB` | SQLite store path for runs/gates/events. | `~/.evolve/dashboard.db` |

---

## `evolve.repos.yaml`

The **registry**: the collection of repos this instance watches and manages. Copy
`evolve.repos.example.yaml` to `evolve.repos.yaml` (gitignored). It's a YAML **list** of entry
dicts, loaded by `engine/repos.py` via PyYAML. If the file is absent (or PyYAML isn't installed),
the engine **falls back to a single entry** built from `$GITHUB_REPO` (typed `platform`) — the
degenerate single-repo case (see [single-repo is just the degenerate case](#single-repo-is-just-the-degenerate-case)).

### Per-entry schema

| Field | Required | What it is |
|---|---|---|
| `name` | **yes** | `owner/repo` on GitHub — the issue source + push target. |
| `type` | **yes** | `platform` \| `app` \| `model` \| `companion` (see below). |
| `path` | **yes** | Local working path the engine checks out (its own checkout for an `app`/`model`). |
| `host` | `app`/`model` only | `owner/repo` of the **platform repo this clones INTO**. Resolves the clone target with `clone_path`. **Required when more than one `platform` is registered**; with exactly one platform it defaults to that platform; omitted for `platform`/`companion`. See [The `host` field](#the-host-field-in-depth). |
| `clone_path` | no | Where it deploys INTO its host (`apps/<id>` / `models/<id>`), **relative to the host's `path`**. Omit for `platform`/`companion`. |
| `branch_model` | no | `<staging>-><world>` — this repo's own staging→world branches. Default `release->main`. |
| `spec_roots` | no | Globs where this repo's specs live. Default `["specs"]` (platform: `["apps/*/specs", "specs"]`). |
| `token_env` | no | Env var holding this repo's token. Default `GITHUB_TOKEN`; override for a repo in another GitHub account (cross-account PAT). |
| `intake` | no | `auto` \| `manual` for this repo. Falls back to `$EVOLVE_INTAKE_DEFAULT`, then `auto`. See [Issue intake](#issue-intake-auto-vs-manual). |

> Loader note: `engine/repos.py` keeps only list items that are dicts **with a `name`** — entries
> missing `name` are silently dropped. `repo_config(name)` returns the full entry; `primary_repo()`
> returns the first (the back-compat anchor for the `ev-<n>` run id). The per-repo resolvers
> `repo_path`, `repo_branches`, `repo_spec_roots`, `repo_token_env`, `repo_type`, `repo_slug`,
> `repo_host`, and `resolve_clone_target` are all consumed by the engine, the GitHub connector, and
> the adapter binding.

### What each `type` means

- **`platform`** — the core repo; worked **in place** (no `clone_path`).
- **`app`** — clones into `apps/<id>`; deploy = the adapter + a restart. Apps may depend on the
  platform but must not import each other (the dep-guard).
- **`model`** — clones into `models/<id>`; deploy = the adapter + a restart.
- **`companion`** — its own service/repo (e.g. a voice or mobile client). Evolve specs + drafts it,
  but **you build/test it** — there's no validation harness for companions yet.

### Worked example

```yaml
# evolve.repos.yaml — the collection this instance manages.

- name: your-org/your-platform
  type: platform
  path: ~/repos/your-platform
  branch_model: release->main
  spec_roots: ["apps/*/specs", "specs/platform"]

- name: your-org/your-app-foo
  type: app
  path: ~/repos/your-app-foo
  clone_path: apps/foo
  branch_model: release->main
  spec_roots: ["specs"]

# A repo in a DIFFERENT GitHub account — give it its own token via token_env,
# and set THEIR_GITHUB_TOKEN in .env.
- name: another-org/their-app
  type: app
  path: ~/repos/their-app
  clone_path: apps/their-app
  token_env: THEIR_GITHUB_TOKEN

# A companion service — Evolve specs + drafts it; you build/test it.
- name: your-org/your-voice-client
  type: companion
  path: ~/repos/your-voice-client
  branch_model: release->main
```

---

## The multi-repo model (types, `host`, and deploy)

One Evolve instance can manage **many** repos from the single `evolve.repos.yaml` registry. This is
wired end to end: intake scans every registered repo each pass, run state is namespaced per repo, and
the build/deploy is repo-aware. This section explains the model.

### Repo types — what each means for build & deploy

| `type` | Where its code lives | How it builds | How it deploys |
|---|---|---|---|
| `platform` | Its own repo + checkout (`path`) | Built **in place** on its own staging branch | Deployed in place (the adapter checks out the branch on the target host + restarts). No `host`/`clone_path`. |
| `app` | Its **own** GitHub repo + checkout (`path`) | Built **in its own repo** on its own staging branch | The adapter **clones the built branch into its host platform** at `clone_path` (e.g. `apps/foo`) + restarts. Apps may depend on the platform but must not import each other (the dep-guard). |
| `model` | Its **own** GitHub repo + checkout (`path`) | Built **in its own repo** on its own staging branch | Same as `app`, cloned into the host at `models/<id>`. |
| `companion` | Its own service/repo (e.g. a voice or mobile client) | **Specced + drafted only** — Evolve writes specs and drafts changes, but **you build/test it** (no validation harness yet). Skipped by intake. | n/a (you ship it). |

### Every per-repo field (all consumed)

- **`path`** — the repo's own local checkout. For an `app`/`model` this is a *separate* clone from the
  platform; the build happens here on this repo's own branches. (`repo_path`)
- **`branch_model`** — `"<staging>-><world>"`, **this repo's own** staging→world branches (default
  `release->main`). Each repo promotes on its own branches. (`repo_branches`)
- **`spec_roots`** — glob(s) where this repo's C/F/S specs live (default `["specs"]`; a platform
  defaults to `["apps/*/specs", "specs"]`). (`repo_spec_roots`)
- **`token_env`** — the env var holding this repo's GitHub PAT (default `GITHUB_TOKEN`). A repo in a
  **different GitHub account** names its own var here and sets that var in `.env`; `github_connector`
  reads/writes that repo's issues with **its own** token. (`repo_token_env`)
- **`intake`** — `auto` or `manual` for this repo (falls back to `$EVOLVE_INTAKE_DEFAULT`). Intake
  honors each repo's mode independently. (`repo_intake`)
- **`host`** — (app/model) which platform repo this clones INTO. See below. (`repo_host`)
- **`clone_path`** — the path **inside the host** the built code is cloned to (`apps/<id>` /
  `models/<id>`), relative to the host's `path`. (used by `resolve_clone_target`)

### The `host` field in depth

An `app`/`model` repo lives in its **own** GitHub repo and **own** checkout (`path`), but it doesn't
run standalone — it **deploys by being cloned into a platform repo**. The `host` field names **which**
platform repo it clones into. This is the key new concept: it makes the deploy target **explicit and
unambiguous**, so different apps can target *different* platform repos.

**Clone-target resolution** (`resolve_clone_target`):

```
clone_target = <host repo's path> / <clone_path>
# e.g. host = your-org/your-platform (path ~/repos/your-platform), clone_path = apps/foo
#   →  ~/repos/your-platform/apps/foo
```

**How `host` is resolved** (`repo_host`):

1. The entry's explicit **`host:` field** — the flexible, unambiguous way; an app can name **any**
   registered platform.
2. Else, if **exactly one** `platform` is registered, that platform is used (the single-platform
   default — you don't have to write `host:` at all).
3. Else **required** — with two or more platforms and no `host:`, resolution returns `None` and the
   deploy can't proceed (you must name the host). This is the safety: an ambiguous target is never
   guessed.

**Worked example — two platforms, apps targeting different hosts:**

```yaml
# Two products, one Evolve instance.
- name: your-org/product-a
  type: platform
  path: ~/repos/product-a
  branch_model: release->main

- name: your-org/product-b
  type: platform
  path: ~/repos/product-b
  branch_model: release->main

# An app that ships into product-a:
- name: your-org/app-anime
  type: app
  path: ~/repos/app-anime
  host: your-org/product-a          # ← clones INTO product-a
  clone_path: apps/anime            # → ~/repos/product-a/apps/anime

# An app that ships into product-b:
- name: your-org/app-weather
  type: app
  path: ~/repos/app-weather
  host: your-org/product-b          # ← clones INTO product-b
  clone_path: apps/weather          # → ~/repos/product-b/apps/weather
```

Because two platforms are registered, **`host:` is required** on each app — that's how `app-anime`
goes to `product-a` and `app-weather` to `product-b` with no ambiguity.

**When you'd use `host`:**

- **Optional apps shipped from their own repos** — an app maintained (and issue-tracked) in its own
  repo, deployed into the one platform.
- **An app shared across two products** — register the app twice (or point it at the right host) so the
  same code ships into different platforms.
- **A monorepo-of-platforms** — several platform products managed by one Evolve instance, each with its
  own apps; `host` keeps every app's deploy target explicit.

### How an issue flows, per repo

1. **Intake scans all registered repos** each pass (`engine/intake.all_admissible_issues()`), each
   honoring its own `intake` mode; companion repos are skipped; a repo that errors is skipped, never
   aborting the scan.
2. The admitted item **carries its repo** — every downstream step knows which repo it belongs to.
3. **Run id is namespaced:** `ev-<n>` for the primary platform repo (back-compat), `ev-<repo-slug>-<n>`
   for any other repo — so two repos that each have issue #5 don't collide.
4. The build runs **in that repo's own checkout, on that repo's own staging branch**.
5. **Deploy via the adapter:** a `platform` item deploys in place; an `app`/`model` item is **cloned
   into its host platform** at `clone_path`, then restarted. The triage `belongs_to` signal **routes**
   a fix to whichever managed repo owns it and builds it there — it only punts to the operator if the
   owning repo isn't in the registry.
6. **Gates as normal** — the same human gates apply regardless of which repo the item came from.

> The actual app-into-host *deploy command* is realized in your `adapters/<name>/adapter.yaml`; the
> engine hands the adapter `clone_target` (and `host_repo`/`host_path`/`clone_path`/`staging_branch`/
> `world_branch`) — the adapter is the deploy seam **by design**, not a missing feature.
>
> **To actually turn on app/model builds**, follow the step-by-step operator runbook:
> [06-target-adapters → §8 Enabling app/model repo builds](./06-target-adapters.md#8-enabling-appmodel-repo-builds-multi-repo)
> (register with a `host`, clone the app repo on the brain, add the app deploy recipe, verify).

### Single-repo is just the degenerate case

If you register **one** `platform` entry (or no registry file at all, falling back to `$GITHUB_REPO`),
nothing above changes — there's nothing to disambiguate, so no `host` is needed, run ids are plain
`ev-<n>`, and the item builds + deploys in place. Multi-repo adds repos; it doesn't complicate the
single-repo path.

---

## Tokens

Three tokens drive the instance. Recap of how to obtain each and where it lives (see also
[`03-installation.md` step 2](./03-installation.md)):

| Token | How to get it | Where it lives |
|---|---|---|
| `GITHUB_TOKEN` | GitHub → Settings → Developer settings → Personal access tokens. Fine-grained, scoped to your registered repos, **Issues: Read & Write** (+ **Contents: Read & Write** if Evolve pushes branches). | admin **and** brain. A repo in another account uses its own PAT in the var named by that entry's `token_env`. |
| `EVOLVE_DECIDE_TOKEN` | A secret **you generate**: `openssl rand -hex 32` (or `python -c "import secrets; print(secrets.token_hex(32))"`). | **evolve-admin ONLY.** The brain must not have it — that's what stops the loop approving its own gates. |
| `EVOLVE_SERVICE_TOKEN` | Generate once, the same way. | **The SAME value on both** evolve-admin (the dashboard) and evolve-brain (the loop). It can push/report but is rejected (`403`) at the decision endpoint. |

How the dashboard enforces this (`dashboard/server.py`):

- The `Authorization: Bearer <token>` value resolves to a principal: `decide` (matches
  `EVOLVE_DECIDE_TOKEN`), `service` (matches `EVOLVE_SERVICE_TOKEN`), or rejected.
- **GET** endpoints need no auth. **Mutations** accept either token. The **decision** endpoint
  (`gates/{id}/decision`) plus `runs/{id}/archive` and `runs/{id}/reverify` require the **decide**
  token — a service token there is `403`.
- **Local dev:** if *both* tokens are unset, mutations are allowed — but if a service token *is*
  configured, it is **still** rejected at the decision endpoint. The engine can push but can never
  decide.

---

## Where config lives

Per-instance config is **gitignored** — your instance's specifics never land in the public engine
repo. Each has a tracked `*.example` template you copy:

| Per-instance file (gitignored) | Tracked template | Purpose |
|---|---|---|
| `.env` | `.env.example` | All runtime config + tokens (this page). |
| `evolve.repos.yaml` | `evolve.repos.example.yaml` | The repo registry (this page). |
| `CHARTER.md` | `CHARTER.example.md` (+ `CHARTER.skipper-example.md` as a filled-in reference) | The vision authority — see [`05-the-charter.md`](./05-the-charter.md). |
| `adapters/<name>/` | `adapters/example/` | Your deploy/validate adapter — see [`06-target-adapters.md`](./06-target-adapters.md). |

Also gitignored: local run/loop state (`.evolve/`, the `EVOLVE_STATE_DIR` tree — default `~/.evolve/runs`) and Python artifacts. The
`.gitignore` also explicitly excludes `evolve.config.yaml` (a future per-instance config surface) and
`adapters/skipper/` (the first customer's real adapter; `adapters/example/` is the tracked
neutral reference).


### Issue intake (auto vs manual)

Each repo has an **intake mode** — `auto` (default) or `manual` — set by the registry entry's `intake:` field, falling back to `$EVOLVE_INTAKE_DEFAULT`, then `auto`.

- **auto** — the loop considers every open issue (the autonomous "it watches your issues" behavior).
- **manual** — the loop considers **only issues a human has admitted** in the dashboard. A human reads the issue on GitHub first and clicks **Admit #**, so (1) a malicious / prompt-injection issue is never even read by an agent, and (2) a high-volume public repo can be worked selectively. **Recommended for any public or untrusted repo.** Admitting requires the decide-token (it's an operator trust decision); the allowlist lives in the dashboard, and the loop reads it via `engine/intake.admissible_issues()` (fail-closed: an unreachable dashboard admits nothing).
