# Overview & Concepts

Evolve is a **a Claude Code agent swarm that follows a gated SDLC to automatically code & test your project.** It is a swarm of specialized agents plus a small number of human decision gates that runs your
software delivery loop: it watches your repos' GitHub issues, reproduces and triages them,
writes specs, designs and implements changes, validates them on a test machine, and ships
them — pausing at the gates for the calls only you should make.

It runs **inside Claude Code**. The LLM is **Claude**; the only external integration is
**GitHub**.

## The core bet: you review, the swarm labors

The whole design rests on one trade. The agent swarm does the labor — reading code,
reproducing bugs, writing specs, implementing, validating, screenshotting. **You make
three judgment calls per change**, and only those three:

1. **Intent** (Gate 1) — *Is this the right thing to build, and is the approach sound?*
2. **Result** (Gate 2) — *Did the change actually do it, and is the diff acceptable?*
3. **Verify** (Gate 3) — *Does it really work when I use it for real?*

A requester files one GitHub issue. You make three decisions. The swarm does everything
in between — live in front of you the whole time. That is the bet: human attention is the
scarce resource, so spend it only at the gates.

## The mental model

```
issues in  →  the loop (agent swarm)  →  human gates  →  shipped
```

- **Issues come in** from GitHub (a teammate, a user, or a proactive QA/feature agent).
- **The loop** picks the most-ready item and advances it through the funnel and spec
  phase, narrating every agent's work to the dashboard.
- **At each gate** the item parks and waits for *you* — it never auto-decides.
- **Shipped** means an issue stays open until *you* verify the fix on a real machine; only
  then does Evolve close it. A closed issue means a human confirmed it works.

## Key concepts

- **The loop / `/loop /evolve`** — the engine itself, run as a Claude Code session. Each
  pass advances exactly **one** work item by **one** segment (the work between two human
  gates), then ends. A gate never blocks the loop; the next pass picks up whatever is most
  ready — a decision to act on, or a new issue to start. Items resume from per-item state
  files, so a pass can be interrupted and the next one continues exactly where it left off.

- **A run — `ev-N`** — one work item's whole life, identified by `ev-<issue#>` (e.g.
  `ev-42`). One issue is one run is one continuous conversation, for life: it is grounded
  once and resumed on every later pass, never restarted.

- **The agent swarm** — ~21 single-responsibility role agents (a triage agent, a security
  screen, a reproduce agent, grounding/design/spec-author/spec-audit, four reviewers —
  security, architecture, interop, UX — a lead, an implement agent, a validate agent, and
  more). Each has a curated prompt and a structured output contract. They are coordinated
  by the loop; the critics (spec-audit, the reviewers) fork into independent subagents for
  fresh eyes.

- **The three gates** — the human control surface. **Gate 1** approves *intent* (after a
  security screen, a live reproduction, and the spec phase). **Gate 2** approves the
  *result* (diff + tests + before/after screenshots). **Gate 3** *verifies* the change live
  on a real machine before the issue is closed. Each gate can also bounce an item back
  ("change this") or reject it.

- **The charter** — `CHARTER.md`, the one piece that is truly yours. It describes what your
  product *is* and *isn't*. It is the vision authority every agent judges against — what
  fits scope, what's off-vision, what your principles are. Everything else in Evolve is
  generic; the charter is where your product lives. See
  [The Charter](05-the-charter.md).

- **The repo collection** — `evolve.repos.yaml`, the list of repos this Evolve instance
  manages, each with its own path, branches, type, and spec roots. This is what lets one
  instance watch many repos. See [Configuration](04-configuration.md). *(Multi-repo is wired:
  issue intake scans every registered repo each pass, each honoring its own intake mode; the
  item carries its repo, run state is namespaced per repo, and the build/deploy is repo-aware —
  see [Configuration → The multi-repo model](04-configuration.md#the-multi-repo-model-types-host-and-deploy).)*

- **The target adapter** — the one project-specific bit of automation: how to deploy and
  test *your* project. It lives in `adapters/<name>/` (with `adapters/example/` as a
  scrubbed reference). The engine invokes it to deploy candidates to the test/UAT machines
  and to drive live validation. See [Target Adapters](06-target-adapters.md). *(The engine invokes it via `scripts/evolve_adapter.py <op>`, which runs the adapter's `adapter.yaml`.)*

- **The PM / `/evolve-pm`** — *you*, with an AI partner at the gates. The PM is a Claude
  Code session that reads each packet, restates the real decision in plain language,
  pushes back on thin or un-reproduced evidence, answers your questions against the live
  code, and **operates the gate on your explicit say-so**. `/chat-ev <n>` is its
  Gate-1 requirements-partner form; `/evolve-pm` rebuilds the role in a fresh session.
  The PM holds the **decide-token** — the agents never can.

- **The dashboard** — a local web server (on the admin machine) that shows every run with
  a live agent feed, the parked gates with their full packets, and the repo-switcher. It is
  where you watch the swarm and where you decide. See [The Dashboard](08-the-dashboard.md).

## What Evolve is NOT

- **Not unattended CI.** It is the opposite of fire-and-forget. The gates are mandatory;
  nothing ships without your three decisions. An item parks indefinitely until you act.
- **Not autonomous-without-gates.** The agent swarm can *do* the work and *propose*
  decisions, but it structurally **cannot decide its own gates** — that is enforced by a
  two-token split (see [Architecture](02-architecture.md)). The control is the point.
- **Not a hosted SaaS or a multi-LLM framework.** It runs inside **Claude Code**, with
  **Claude** as the LLM, and **GitHub** as the only external integration. There is no
  in-app issue tracker, no other provider, no cloud control plane — you clone it and run it
  on your own fleet.

## Next

- For how the pieces fit across the four-machine fleet and the security model that makes
  the gates real, read [Architecture & the Fleet](02-architecture.md).
- For a concrete, end-to-end walkthrough of one issue from filing to close, see the
  **Example workflow** in the project [README](../README.md).
