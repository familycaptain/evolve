# Target adapter

A **target adapter** teaches Evolve how to deploy and validate *your* project. The engine calls a
small set of operations; your adapter implements them for your stack. The Skipper instance's adapter
lives in `adapters/skipper/` (gitignored — per-instance, like `.env` and `CHARTER.md`).

> **About the `.py` files in this directory.** These are a **real reference adapter — the Skipper
> instance's, scrubbed of secrets and personal data** (names, locations, credentials, and
> infrastructure hostnames replaced with neutral placeholders). They show how the engine's
> deploy / validate / seed / scaffold operations are implemented for a concrete product. They
> **illustrate the pattern** — they import that product's own modules (`apps.*`, `app_platform.*`,
> the Skipper web app) and are **not meant to run inside `evolve/`**; copy the shape into your own
> `adapters/<your-project>/`. Connection details come from environment variables
> (`$EVOLVE_TEST_HOST`, `$EVOLVE_BRAIN_HOST`, `$EVOLVE_TARGET_REPO_PATH`, `$EVOLVE_DEPLOY_CMD`,
> `$EVOLVE_HEALTH_PATH`, `$GITHUB_REPO`, …), never hardcoded.

## How the binding works
An adapter is a directory under `adapters/` containing an **`adapter.yaml`** that maps each engine
operation to a shell command — see [`adapter.yaml`](./adapter.yaml) in this directory. Set
**`EVOLVE_ADAPTER`** in `.env` to your adapter's directory name. The engine never calls your scripts
directly; it goes through one stable entrypoint:

```
python3 scripts/evolve_adapter.py <op> key=value ...
```

which resolves `$EVOLVE_ADAPTER`, substitutes the `key=value` args into your `{placeholder}`s, and runs
the command on evolve-brain (your command does any ssh into the target host). Output + exit code pass
straight through to the calling agent.

## Operations
- **`deploy host=<host> ref=<branch|sha>`** — check out `ref` on `host` and bring the product up; print
  `{"ok":true,"healthy":true,"sha":"…"}` and exit 0/non-zero.
- **`health host=<host>`** — exit 0 if the product is up.
- **`acceptance host=<host> spec=<id|file>`** — drive the product as a user; print `{"passed":…,"evidence":[…]}`.
- **`seed host=<host>`** — *(optional)* load fixtures / mock data.
- **`scaffold unit=<name>`** — *(optional)* scaffold a new unit of work.

Implement only the ops you need — an undefined op is a clean error, not a crash. **Tiered acceptance:**
a project with no live UI can implement `acceptance` as a unit-test run.

## What each example file shows
- `box2_live.py` — the **deploy + health** lifecycle on the test host (`skipper update`, non-interactive).
- `box2_fixture.py` — snapshot/restore a reproducible DB baseline before each acceptance run.
- `box2_acceptance.py` — the reusable **acceptance** spine: a logged-in browser session whose
  `send_chat` returns hard evidence (the answer **and** the tool-calls that fired).
- `box2_no_reload_acceptance.py` — a full **bound test** for one issue, with an oracle + negative control.
- `box2_drive.py` — a stdlib "hands" CLI for an agent to drive one chat turn at a time over SSH.
- `ui_harness.py` — a hardened Playwright harness for driving the web UI like a user.
- `box2_cancel_onboarding.py`, `box2_diag_chatturns.py`, `box2_sim_nudge.py` — small in-container
  diagnostics/setup helpers used while validating.
- `seed_mock_data.py` — the **seed** operation: realistic mock household data for a fresh box/demo.
- `new_app.py` — the **scaffold** operation: generate a new drop-in app package.

## Built into the engine (NOT the adapter)
Posting evidence to a GitHub issue is the **engine's** job, not yours: the reproduce + validate
steps call `github_connector.attach_image_to_issue(n, path, caption)`, which uploads the screenshot
to **catbox.moe** and comments it inline on the issue (it renders even on a private repo), and
`github_connector.create_issue(...)` to file an incidental issue. Your adapter only needs to
produce the screenshot (the UI driver in `acceptance`); the engine handles getting it onto GitHub.

**Privacy note:** `catbox.moe` is an external, public, anonymous image host — a posted screenshot leaves
your network and gets a permanent public URL (which is *why* it renders inline even on a private repo).
That's only safe if your `acceptance` step screenshots **non-sensitive / mock data**. If it would
capture real user data, don't rely on it. Point `EVOLVE_IMAGE_UPLOAD_CMD` at your own uploader to keep evidence private — catbox is just the default.
