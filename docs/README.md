# Evolve — Operator Manual

The complete guide to installing, configuring, and running Evolve. **New here?** Read
[01 — Overview](01-overview.md) first, then jump to [03 — Installation](03-installation.md) to set up
your fleet. The project [README](../README.md) has the 60-second version + the architecture diagram.

| # | Chapter | What it covers |
|---|---|---|
| 1 | [Overview & concepts](01-overview.md) | What Evolve is, the core bet, the mental model, the key terms |
| 2 | [Architecture & the fleet](02-architecture.md) | The four machines, the data flow, the two-token security model, the run lifecycle |
| 3 | [Installation & setup](03-installation.md) | Prerequisites + a step-by-step setup of the fleet, with a first-run checklist |
| 4 | [Configuration reference](04-configuration.md) | Every `.env` key, the `evolve.repos.yaml` registry schema, the multi-repo model (types, `host`, deploy), the tokens, where config lives |
| 5 | [Writing your charter](05-the-charter.md) | The vision authority — the one piece that's truly yours, and how agents use it |
| 6 | [Target adapters](06-target-adapters.md) | Teaching Evolve how to deploy + validate **your** project (the one project-specific bit) |
| 7 | [Daily operation](07-running.md) | Starting/stopping, the daily rhythm, the PM role, reviewing & deciding gates, publishing |
| 8 | [The dashboard](08-the-dashboard.md) | The admin-console UI reference (runs, gate review, repo-switcher, activity) |
| 9 | [Gates, the agents & the flow](09-gates-and-the-flow.md) | The three gates, the full agent roster, the pipeline, the run lifecycle |
| 10 | [Operations & troubleshooting](10-operations-and-troubleshooting.md) | Run states, recovery, the offline outbox, common problems & fixes, backups |
| — | [SDLC flow diagram](sdlc.md) | The Mermaid diagram of the whole agent-swarm + gates flow |

### The 60-second version
You run a **dashboard** + `/evolve-pm` on **evolve-admin** and `/loop /evolve` on **evolve-brain** (both
in Claude Code). The loop watches your repos' GitHub issues, and a swarm of agents reproduces, specs,
builds, and validates each change on **evolve-test** — parking at three human gates (**intent → result →
verify**) that you decide in the dashboard. You make the judgment calls; the swarm does the labor. The
only thing that's *yours* is the [charter](05-the-charter.md) (what your product is) and a
[target adapter](06-target-adapters.md) (how to deploy + test it).
