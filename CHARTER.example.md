# <Your Project> Charter — what it is and isn't

> **The vision authority.** This is the human-owned, top-level statement of what your product *is*.
> Evolve's **vision-fit** agent judges every proposed feature against this document (plus each
> Capability's own `scope`); the **design** agent generates proposals *from* it. It is the single most
> important file you write — it is what makes a generic Evolve behave like *your* project's engine.
>
> **Only a human changes this file.** Agents may *propose* a change, but your product never silently
> expands what it is. When in doubt, a feature is off-charter — protecting focus is the point.
>
> **How to use:** copy this file to `CHARTER.md` and fill in every section for your product. The `## `
> **headers are load-bearing** — the engine assembles each agent's grounding by matching keywords in
> these headers (`thesis`, `is`, `project kind`, `cross-surface`, `non-goals`, `scope`, `autonomy`,
> `engineering principles`). Keep those words in the headers even as you reword around them. Delete a
> section only if it truly doesn't apply (say so explicitly rather than leaving it blank).

## Thesis (one sentence)
<One sentence: what this product is, for whom, and why it exists. The single north star every agent
returns to. If you can't say it in a sentence, the project isn't focused enough yet.>

## What <Your Project> *is*
<The core identity — the handful of things this product fundamentally does and stands for. Concrete and
specific. This is what vision-fit accepts a feature *toward*. A feature that doesn't advance one of
these is probably off-charter.>

## Project kind & primary interface(s)
<Declare what KIND of project this is, what its primary interface(s) are, and how to build / run /
test it. This is what tells the agents whether there's a browser UI to drive at all — a web app is
ONE possibility, not the assumption. Be concrete, e.g.:
- "Headless Python library; interface = its public API (the exported functions/classes); built with
  `pip install -e .`, tested with `pytest`. No GUI surface — evidence is failing→passing tests."
- "CLI tool; interface = the `mytool` command + its flags; run by invoking it; tested by invoking it
  and asserting stdout + exit code. No GUI surface — evidence is captured stdout/exit code."
- "HTTP API service; interface = its REST endpoints; run with `uvicorn app:app`; tested with request
  assertions. Evidence is the response body + status code."
- "Web app; interface = the browser UI (plus a JSON API); run with `./deploy.sh`; tested with unit
  tests + browser e2e. Evidence is a screenshot of the rendered surface."
- "Firmware / data pipeline / desktop app — name the real interface and how it's exercised."
State whether there is a **GUI surface** at all (if not, say so plainly — the UX review then judges
interface ergonomics, not pixels, and the loop won't demand screenshots). This drives reproduce /
validate: they exercise the change through *this* interface and capture evidence in *its* native form
(a screenshot for a UI, stdout+exit code for a CLI, a response body for an API, a failing→passing test
for a library) — keep it consistent with what your target adapter (`adapter.yaml`) actually runs.>

## Cross-surface parity & consistency
<If your product spans multiple surfaces (web, CLI, mobile, API, voice, a bot…), list them and state
the parity doctrine — what must look and behave the same across them, and where they're allowed to
differ. If it's a single surface, say so plainly; the agents will stop reasoning about parity.>

## What <Your Project> is *not* (non-goals)
<The explicit non-goals — what this product deliberately does NOT do, and will reject features toward.
This is where focus is protected; be specific and a little ruthless. vision-fit treats drift here as a
reason to decline.>

## Scope: what belongs
<What kinds of work belong inside this project versus out of it — the boundary the loop uses when it
triages an incoming issue. Distinguish "a real change to this product" from "support / config / someone
else's repo."

## Autonomy guardrails (how far Evolve may go unattended)
<How much the autonomous loop may do on its own, and where it MUST stop and ask. The human gates
(intent / result / verify) are always present; this section bounds everything *between* them — e.g.
"may refactor freely within a module; must gate any schema change, any new dependency, any
outward-facing or destructive action." State your risk tolerance.>

## Engineering principles (non-functional)
<The non-functional constraints every change must honor — the agents ground the architecture, security,
and implement steps on this. Cover at least: your stack/languages/frameworks (and the "don't invent
files of type X" guardrails), module-boundary / dependency-direction rules, your security & privacy
stance, performance expectations, and the testing bar (what "validated" means here).>

<!-- RECOMMENDED ADDITIONAL SECTIONS (wired into agent grounding during engine setup):

## External contracts (consumers outside this repo)
<Shared contracts — APIs, auth, protocols, schemas — that OTHER repos or services depend on, and which
repos those are, so the interop/architecture agents know what they must not break. Omit if none.>

## Repository layout & stack
<Where code, specs, and tests live (spec roots, app/module directories), the dependency-direction
rules, and the languages/frameworks in use — so agents place code correctly and resolve your specs.>
-->
