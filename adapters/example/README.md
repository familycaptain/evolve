# Target adapter

A **target adapter** teaches Evolve how to deploy and validate *your* project. The engine calls a
small set of operations; your adapter implements them for your stack. Your real adapter lives in
`adapters/<your-project>/` (gitignored — per-instance, like `.env` and `CHARTER.md`); this directory
is the neutral template you copy from.

## How the binding works
An adapter is a directory under `adapters/` containing an **`adapter.yaml`** that maps each engine
operation to a shell command — see [`adapter.yaml`](./adapter.yaml). Set **`EVOLVE_ADAPTER`** in
`.env` to your adapter's directory name. The engine never calls your scripts directly; it goes
through one stable entrypoint:

```
python3 scripts/evolve_adapter.py <op> key=value ...
```

which resolves `$EVOLVE_ADAPTER`, substitutes the `key=value` args into your `{placeholder}`s, and
runs the command on the brain host (your command does any ssh into the target host). Output + exit
code pass straight through to the calling agent. Connection details come from environment variables
(`$EVOLVE_TEST_HOST`, `$EVOLVE_BRAIN_HOST`, `$EVOLVE_TARGET_REPO_PATH`, `$EVOLVE_DEPLOY_CMD`, ...),
never hardcoded.

## Operations
- **`deploy host=<host> ref=<branch|sha>`** — check out `ref` on `host` and bring the product up;
  print `{"ok":true,"healthy":true,"sha":"..."}` and exit 0/non-zero. Must leave the host at EXACTLY
  `ref` even from a dirty checkout, and fail loudly rather than restart on stale code (see the
  hardened recipe in `adapter.yaml`).
- **`health host=<host>`** — exit 0 if the product is up.
- **`acceptance host=<host> spec=<id|file>`** — drive the product as a user/caller would; print
  `{"passed":...,"evidence":[...]}`. Start from [`run_acceptance.py`](./run_acceptance.py), the
  neutral skeleton (it shows the contract for web / CLI / API / library project kinds).
- **`seed host=<host>`** — *(optional)* load fixtures / mock data so acceptance starts from a known
  state.
- **`scaffold unit=<name>`** — *(optional)* scaffold a new unit of work (an app/module skeleton for
  your product).

Implement only the ops you need — an undefined op is a clean error, not a crash. **Tiered
acceptance:** a project with no live UI can implement `acceptance` as a unit-test run.

## What a mature adapter grows into
Real adapters accrete reusable pieces as the engine validates more items. Worth building as shared
modules (not per-issue one-offs) when your project needs them:

- a **deploy/health lifecycle** script (bring the product up non-interactively, wait healthy);
- a **fixture snapshot/restore** so each acceptance run starts from a reproducible baseline;
- a hardened **UI/driver harness** (for a web product: programmatic login, console-error capture,
  screenshots-on-failure) that every acceptance scenario imports;
- per-issue **bound-test scenarios** with an oracle and a negative control;
- small **diagnostic helpers** for inspecting the product's state during validation.

Keep all of it inside your gitignored `adapters/<your-project>/` — it is product-specific by nature.

## Built into the engine (NOT the adapter)
Posting evidence to a GitHub issue is the **engine's** job: reproduce/validate call
`github_connector.attach_image_to_issue(n, path, caption)` — which uploads the screenshot and
comments it inline — and `github_connector.create_issue(...)` for incidental findings. Your adapter
only needs to *produce* the evidence (e.g. the screenshot from your `acceptance` driver).

**Privacy note:** the default image host (catbox.moe) is an external, public, anonymous service — a
posted screenshot leaves your network and gets a permanent public URL (which is *why* it renders
inline even on a private repo). That's only safe if your `acceptance` step screenshots
**non-sensitive / mock data**. If it would capture real user data, point `EVOLVE_IMAGE_UPLOAD_CMD`
at your own uploader — catbox is just the default.
