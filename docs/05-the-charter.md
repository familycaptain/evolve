# 05 · Writing your charter

> Part of the Evolve operator manual. Siblings: [README.md](../README.md),
> [01-overview](01-overview.md), [02-architecture](02-architecture.md),
> [03-installation](03-installation.md), [04-configuration](04-configuration.md),
> [06-target-adapters](06-target-adapters.md), [07-running](07-running.md),
> [08-the-dashboard](08-the-dashboard.md), [09-gates-and-the-flow](09-gates-and-the-flow.md),
> [10-operations-and-troubleshooting](10-operations-and-troubleshooting.md), [sdlc.md](sdlc.md).

The charter is the single most important thing you write. Everything else in Evolve is generic
machinery; the charter is the one file that makes a generic engine behave like *your* project's
engine. If you do nothing else carefully, do this carefully.

---

## 1. What the charter is

The charter (`CHARTER.md` at the repo root) is the **vision authority** — the human-owned, top-level
statement of what your product *is* and *isn't*. It is the document every reasoning agent returns to
when it has to decide whether a proposed feature belongs.

Two rules govern it:

- **Only a human edits this file.** The autonomous loop never writes to `CHARTER.md`. Agents may
  *propose* a charter change (the **vision-fit** agent can return a `needs-charter-change` verdict —
  see `agents/registry.py`, `VISION_OUT`), but the product never silently expands what it is. A
  charter change is always a human decision, made by editing the file by hand.
- **When in doubt, a feature is off-charter.** Protecting focus *is* the point. The charter is the
  thing that lets Evolve decline good-but-off-vision work without you in the loop.

`CHARTER.md` is per-instance (like `.env` and your target adapter). The repo ships two companion
files instead:

- **`CHARTER.example.md`** — the blank template. Copy it to `CHARTER.md` and fill in every section.
- **`CHARTER.skipper-example.md`** — a complete, real, filled-in charter (Skipper's, the first
  project Evolve was proven against). Read it as a worked example of how each section reads when it's
  done well.

---

## 2. How agents use it — section-scoped grounding (the context economy)

Evolve does **not** paste the whole charter into every agent. That would waste tokens and dilute each
agent's focus — the instruction that matters gets buried. Instead the charter is *addressable by
section*, and each agent declares only the sections it needs. This is the "context economy" idea:
inject the right guidance just-in-time, never bloat the prompt.

The mechanics live in two files:

**`agents/charter.py`** parses `CHARTER.md` into its `## ` (level-2) sections and exposes them by a
small set of stable **grounding keys**. The key→header mapping is the `_KEYS` table:

| grounding key | matches a `## ` header containing… |
|---------------|-------------------------------------|
| `thesis`      | `thesis` |
| `is`          | `*is*` |
| `project-kind`| `project kind` |
| `surfaces`    | `cross-surface` |
| `non-goals`   | `non-goals` |
| `scope`       | `scope` |
| `autonomy`    | `autonomy` |
| `principles`  | `engineering principles` |
| `contracts`   | `external contract` |
| `stack`       | `stack` |

`grounding(keys)` then assembles *only* the requested sections, in charter order, under a header that
tells the agent these are the vision authority to judge against — not material to invent from.

**`agents/registry.py`** is where each agent declares its needs, via the `charter_keys=[…]` field on
its `AgentSpec`. The wiring as it stands today:

| agent | `charter_keys` | why it needs them |
|-------|----------------|-------------------|
| `vision-fit` | `thesis`, `non-goals`, `scope` | judges a feature against the north star, the explicit non-goals, and what belongs |
| `security-screen` | `non-goals` | classifies a raw issue's intent against what the product refuses to do |
| `security` | `non-goals` | reviews a change for things the product must never do |
| `interop` | `contracts` | knows which out-of-tree consumers must not break |
| `architecture` | `is`, `surfaces`, `principles`, `contracts`, `stack` | the broadest grounding: identity, parity, non-functional rules, contracts, and the stack/layout |
| `ux` | `project-kind`, `surfaces` | whether there's a GUI surface at all, then cross-surface consistency |
| `prioritize` | `thesis` | scores a proposal against the north star |
| `spec-author` | `thesis`, `surfaces`, `principles` | writes behavior that honors parity + the non-functional bar |
| `spec-audit` | `surfaces` | critiques a spec for surface gaps |
| `design` | `scope`, `surfaces`, `principles`, `stack` | sets a system-level approach that fits scope, parity, principles, and stack |
| `code-scout` | `surfaces`, `principles` | sketches where code would land under those constraints |
| `lead` | `thesis`, `scope`, `principles` | owns the single Gate-1 recommendation |
| `implement` | `surfaces`, `principles` | writes code that honors parity + the non-functional rules |
| `code-audit` | `non-goals` | reads code for things the product must not do |
| `reproduce` | `project-kind`, `surfaces`, `stack` | learns what interface to drive (UI vs CLI/API/library) + how evidence is captured |
| `validate` | `project-kind`, `surfaces`, `stack` | learns the real interface to exercise + the native form of its evidence |
| `test-author` | `project-kind`, `surfaces`, `stack` | learns whether tests drive a UI, a CLI, an API, or a library |

(Agents with no `charter_keys` — `triage`, `grounding`, `review-packet` — do not consume the
charter directly; they work from the issue, the code, or the upstream agents' output.)

The practical consequence for you: **the sections below are not decoration. They are the literal
inputs to those agents.** A thin or hand-wavy `## Non-goals` section makes vision-fit and the
security screen weak; a vague `## Engineering principles` makes architecture and implement weak.

---

## 3. The header-keyword rule (load-bearing)

Because grounding matches *keywords inside the `## ` headers* (the `_KEYS` substrings above), **the
header text is load-bearing.** If you rename `## What it is *not* (non-goals)` to `## Things we
won't build`, the `non-goals` key stops matching and vision-fit silently loses that section.

The rule:

- Keep the **keyword** in each header — `thesis`, `is` (as `*is*`), `project kind`, `cross-surface`,
  `non-goals`, `scope`, `autonomy`, `engineering principles`, `external contract`, `stack`. You may
  reword *around* the keyword freely (`## Scope: what belongs here` is fine; `## What's in bounds` is
  not).
- The match is a case-insensitive substring on the header line, so capitalization and surrounding
  words don't matter — only that the keyword is present.
- Delete a section only if it genuinely doesn't apply, and say so explicitly rather than leaving it
  blank. A missing section means that key returns nothing and the agents reason without it.

When in doubt, diff your headers against the `_KEYS` table in `agents/charter.py` — that table is the
contract.

---

## 4. The sections — what each is for and how to write it well

The blank template (`CHARTER.example.md`) carries the first eight sections plus two recommended
ones; the worked example (`CHARTER.skipper-example.md`) fills them in. Write them concretely —
abstractions don't constrain agents.

### `## Thesis (one sentence)` — key `thesis`

One sentence: what the product is, for whom, and why it exists. The north star every agent returns
to. Used by `vision-fit`, `prioritize`, `spec-author`, and `lead`.

*Write it well:* force it into a single sentence. If you can't, the project isn't focused enough yet,
and every downstream judgment inherits that fuzziness. (Skipper's: "a self-hosted, agentic 'life OS'
for a household … reached by chat, voice, mobile, and a desktop UI over one shared agent.")

### `## What <Project> *is*` — key `is`

The core identity — the handful of things the product fundamentally does and stands for. This is what
vision-fit accepts a feature *toward*; a feature that advances none of these is probably off-charter.
Used by `architecture`.

*Write it well:* be concrete and specific, a short bulleted list of pillars, not adjectives. Keep the
literal `*is*` (with asterisks) in the header — that's the keyword.

### `## Project kind & primary interface(s)` — key `project-kind`

Declares what KIND of project this is, its primary interface(s), and how to build / run / test it —
the single section that tells the agents whether there's a browser UI to drive at all. A web app is
*one* possibility, never the assumption. Used by `reproduce`, `validate`, and `test-author` (the
three agents that exercise the change and capture evidence) and by `ux` (to decide GUI-vs-ergonomics).

*Write it well:* be concrete about the interface and the build/run/test commands — "headless Python
library; interface = its public API; tested with pytest" / "CLI; interface = the `mytool` command;
tested by invoking it and asserting stdout + exit code" / "web app; interface = the browser UI;
tested with unit + browser e2e." **State plainly whether there is a GUI surface at all.** This is
what makes reproduce/validate capture evidence in the surface's *native* form — a screenshot for a
UI, stdout+exit code for a CLI, a response body for an API, a failing→passing test for a library —
and it must stay consistent with what your target adapter (`adapter.yaml`) actually runs.

### `## Cross-surface parity & consistency` — key `surfaces`

If the product spans multiple surfaces (web, CLI, mobile, API, voice, a bot), list them and state the
parity doctrine: what must look/behave the same across them, and where they're allowed to differ.
Consumed by the most agents — `architecture`, `ux`, `spec-author`, `spec-audit`, `design`,
`code-scout`, `implement`.

*Write it well:* if you have one surface only, say so plainly — the agents will then stop reasoning
about parity. If you have several, make the doctrine actionable (Skipper's "every capability is
reachable from every surface, and behaves the same way" turns directly into spec-author asserting
which surfaces a behavior touches).

### `## What <Project> is *not* (non-goals)` — key `non-goals`

The explicit non-goals: what the product deliberately does NOT do and will reject features toward.
Used by `vision-fit`, `security-screen`, `security`, `code-audit` — i.e. both the vision gate *and*
the safety screens.

*Write it well:* be specific and a little ruthless. This is where focus is protected. Vague non-goals
("we won't do bad things") give the agents nothing to decline against; sharp ones ("not a SaaS or
cloud product — if a feature only works with a central backend, it's off-charter") let vision-fit
decline cleanly without you.

### `## Scope: what belongs` — key `scope`

What kinds of work belong inside the project versus outside it — the boundary the loop uses when it
triages an incoming issue. Used by `vision-fit`, `design`, `lead`.

*Write it well:* distinguish "a real change to this product" from "support / config / someone else's
repo." Give positive signals (what fits) *and* the off-charter list, and name the escape hatch for
borderline cases (Skipper routes those to `needs-charter-change` — a human decision, never a silent
yes).

### `## Autonomy guardrails (how far Evolve may go unattended)` — key `autonomy`

How much the autonomous loop may do on its own, and where it must stop and ask. The human gates
(intent / result / verify) are always present; this section bounds everything *between* them.

*Write it well:* state your risk tolerance in tiers (e.g. "may refactor freely within a module; must
gate any schema change, any new dependency, any outward-facing or destructive action"). Note: as of
this writing no agent declares `autonomy` in its `charter_keys` — the section documents your policy
and informs how you operate the gates ([09-gates-and-the-flow](09-gates-and-the-flow.md)) rather than
feeding an agent prompt directly. Write it anyway; it's the standing agreement you hold the loop to.

### `## Engineering principles (non-functional)` — key `principles`

The non-functional constraints every change must honor — the agents ground the architecture and
implement steps on this. Used by `architecture`, `spec-author`, `design`, `code-scout`, `lead`,
`implement`.

*Write it well:* cover at least your stack/languages/frameworks and the "don't invent files of type
X" guardrails, module-boundary / dependency-direction rules, your security & privacy stance,
performance expectations, and the testing bar — i.e. what "validated" *means* for you. Skipper's
section is a strong model: each principle is a rule with a concrete example ("a weather request must
not geocode the user's ZIP on every call").

### `## External contracts (consumers outside this repo)` — key `contracts`

Shared contracts — APIs, auth, protocols, schemas — that *other* repos or services depend on, and
which repos those are, so the interop/architecture agents know what they must not break. Used by
`interop` and `architecture`. Omit if you have none.

*Write it well:* name the consumer repos explicitly and the contract each one rides (Skipper names
`skipperbot-voice` and `skipperbot-mobile` and the auth/WebSocket relay they consume). A contract
change is then never treated as "internal-only."

### `## Stack & repository layout` — key `stack`

Where code, specs, and tests live (spec roots, app/module directories), the dependency-direction
rules, and the languages/frameworks in use — so agents place code correctly and resolve your specs.
Used by `architecture` and `design`.

*Write it well:* be explicit about the dependency direction (it must match what you configure as
`$EVOLVE_PLATFORM_PREFIXES` / `$EVOLVE_APP_GLOB` for the dep-guard — see
[04-configuration](04-configuration.md) and [06-target-adapters](06-target-adapters.md)). State the
guardrail in words ("the platform must never import an app; apps must never import each other") so the
architecture review can judge intent, then let the deterministic dep-check enforce it.

---

## 5. How to start

1. `cp CHARTER.example.md CHARTER.md`.
2. Fill in every section for your product. Keep each `## ` header's keyword (§3).
3. Read `CHARTER.skipper-example.md` alongside it as a complete worked example — match its concrete,
   ruthless style, not its content.
4. Set `EVOLVE_PRODUCT_NAME` in `.env` (it titles the assembled grounding block); if your charter
   lives somewhere other than `CHARTER.md`, set `EVOLVE_CHARTER_PATH` (both read by
   `agents/charter.py`). See [04-configuration](04-configuration.md).
5. Thereafter, treat `CHARTER.md` as a human-only file. When the loop surfaces a
   `needs-charter-change`, that's your cue to consider editing it — by hand, deliberately.

The charter is the contract between your judgment and the engine. Spend the time here; every gate you
*don't* have to babysit later is paid for in this file.
