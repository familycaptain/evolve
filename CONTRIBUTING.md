# Contributing to Evolve

Thanks for your interest! Evolve is a self-maintaining SDLC engine — a swarm of specialized agents
plus human decision gates — that you point at your own GitHub repos. It runs **inside Claude Code**
(not the Agent SDK), and the only external integration is **GitHub**. Contributions that keep it
**generic, safe, and project-type-agnostic** are very welcome.

## Ways to contribute

- **The engine** (`engine/`, `scripts/`) — the dashboard backend, the CLIs, the adapter binding, the
  repo registry, the GitHub connector. Pure Python, standard-library-leaning.
- **The agents** (`agents/prompts/*.md`, `agents/registry.py`) — the role prompts and the roster.
  This is prompt engineering: keep instructions interface-agnostic (a web UI is *one example*, never
  the assumption — see the project-kind charter section).
- **The skills** (`.claude/skills/*/SKILL.md`) — the operator- and loop-facing workflows.
- **Adapters** (`adapters/example/`) — reference adapters showing how to wire a project's
  deploy/validate. A turnkey non-web example (CLI or library) is especially wanted.
- **Docs** (`docs/`, `README.md`) — accuracy and honesty fixes, missing setup steps, clearer guides.

## Project layout

| Path | What it is |
|---|---|
| `engine/` | Python engine: dashboard store/server, GitHub connector, repo registry, cost, schema. |
| `agents/` | The role prompts (`prompts/`), the roster + output contracts (`registry.py`), charter grounding (`charter.py`). |
| `.claude/skills/` | The Claude Code skills that drive the loop + the PM. |
| `dashboard/` | FastAPI server + the single-page operator console. |
| `adapters/example/` | A reference target adapter (deploy/health/acceptance/seed/scaffold). |
| `docs/` | The operator manual (01–10) + the SDLC reference. |

## Local setup

```bash
git clone https://github.com/familycaptain/evolve.git
cd evolve
python3 -m venv .venv && . .venv/bin/activate
pip install -r dashboard/requirements.txt        # fastapi, uvicorn, pyyaml
```

Quick sanity checks before you open a PR:

```bash
# everything imports + the roster builds
python3 -c "import sys;sys.path.insert(0,'.');from agents import registry,charter;from engine import repos,github_connector;print('roster',len(registry.ROSTER))"
# the dashboard serves (smoke)
uvicorn dashboard.server:app --port 8000   # then curl http://localhost:8000/api/apps/evolve/repos
```

## Guidelines

- **Keep it generic.** No operator-, company-, or product-specifics in tracked files. Concrete
  examples are fine when clearly framed as examples (e.g. "the Skipper instance's …"), and the
  real worked example lives only in `CHARTER.skipper-example.md` / `adapters/skipper/` style files.
- **Never commit per-instance or secret files.** `.env`, `CHARTER.md`, `evolve.repos.yaml`, and
  `adapters/<your-project>/` are gitignored on purpose — they're yours, not the engine's. Use the
  `*.example` templates. Scan your diff for tokens, keys, hostnames, and personal data before pushing.
- **Don't weaken the two-token security model.** The brain holds only a service token and can *propose*
  decisions; only the operator (on evolve-admin) with the decide-token can *approve* a gate. Any change
  near `dashboard/server.py` auth, `engine/platform_bridge.py`, or the decide endpoints must preserve
  that the service token is rejected (403) at decision/archive/reverify.
- **Honor the design principles.** Inject the right context/tools just-in-time (don't bloat prompts);
  let the LLM determine intent (don't string-match chat to trigger behavior); a target project's
  deploy/test is the adapter's job, not hardcoded in the engine.
- **Match the surrounding code.** Mirror existing naming, comment density, and idiom; keep the engine
  standard-library-leaning.
- **Be honest in docs.** If something is designed-but-not-built (e.g. the multi-repo change-poller),
  say so. Don't describe aspirations as shipped features.

## Pull requests

1. Branch off `main`.
2. Make a focused change with a clear description of the problem and the fix.
3. Run the sanity checks above; for prompt/skill changes, explain how you validated the behavior.
4. Keep commits scoped and messages descriptive (what changed and *why*).
5. Confirm no secrets or per-instance data are in the diff.

## Reporting issues & security

- **Bugs / ideas:** open a GitHub issue with steps to reproduce (or the proposed change).
- **Security:** if you find a way to bypass the gate/token model or otherwise compromise an instance,
  please report it privately to the maintainers rather than opening a public issue.

## License

By contributing, you agree your contributions are licensed under the repository's
[MIT License](./LICENSE).
