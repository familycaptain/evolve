# Skipper Charter — what Skipper is and isn't

> **Example — a real, filled-in charter (Skipper's).** `CHARTER.example.md` is the blank
> template; this shows what a complete one looks like. Copy the template to `CHARTER.md` for
> your own project.

> **The vision authority.** This is the human-owned, top-level statement of what
> Skipper *is*. Evolve's **vision-fit** agent judges every feature against this
> document **plus** the target Capability's `scope` field (EVOLVE.md §11); the
> **design** agent generates proposals *from* it. help.md/guide.md are inputs, not
> authority. Per-area boundaries live in each Capability's `scope`, not here.
>
> **Only a human changes this file.** The design agent may *propose* a change, but
> Skipper never silently expands what it is. When in doubt, a feature is
> off-charter — protecting the maintainer's focus is the point.

## Thesis (one sentence)

Skipper is a **self-hosted, agentic "life OS" for a household** — a private platform,
running on your own hardware, that helps a whole family run real life through domain
apps, reached by chat, voice, mobile, and a desktop UI over one shared agent.

## What Skipper *is*

- **A household assistant, for multiple people.** Family members have roles,
  per-person data, reminders, and focus. Not designed explicitly as a single-user tool, although it does contain tools that could be valuable for an individual. 
- **An app platform.** The core handles chat, memory, scheduling, notifications, the
  agent loop, and shared services; **app packages** (UI + tools + schema + migrations)
  add domain capabilities. Extensibility is drop-in-a-folder.
- **About running real life.** The domains are the stuff of a household: goals,
  reminders, schedules, lists/todo, recipes & meal planning, chores, auto
  maintenance, medical records, documents/journaling, weather, home upkeep, and the
  like.
- **Private and local-first.** No telemetry, no crash reports, no version pings — ever.
  Data lives in **your own Postgres**; the LLM is reached with **your own API key**;
  every other integration is one you explicitly configure. Self-hosted on hardware
  you control.
- **For every self-hoster, not one machine.** Built for the whole distributed user
  base: any OS, any deploy (Docker or native), any hardware (down to a Raspberry Pi),
  headless or attended. Never assume the operator's specific setup.
- **Agent-first and conversational.** Capabilities are reachable by natural language
  through the same agent, not buried in forms; voice, chat, Discord, mobile, and the
  web desktop all front the one agent.
- **Self-maintaining (Evolve).** Skipper improves its own codebase through the
  human-gated Evolve loop — this engine.

## Project kind & primary interface(s)

Skipper is a **multi-surface web application + agent platform** with a **GUI surface** —
so reproduce/validate DO drive a real browser UI and screenshot it. Concretely:

- **Kind:** a self-hosted server product (Python/FastAPI backend + a React web desktop
  UI), packaged as drop-in app folders, run under Docker (or native) on the operator's
  own hardware.
- **Primary interfaces:** the **browser web UI** *and* the **agent/tool layer** that
  fronts chat, voice, mobile, and Discord (every capability is an MCP tool). Both are
  first-class; there is a real GUI to exercise.
- **Build / run:** the target adapter deploys a branch to the test host and brings the
  stack up (`$EVOLVE_DEPLOY_CMD`, non-interactive); the app serves at `$EVOLVE_SERVER_URL`.
- **Test / evidence:** deterministic Python unit tests (`unittest`) for backend logic +
  **browser e2e** (Playwright via the adapter's UI harness) for UI behaviour; agentic
  acceptance scenarios for chat-intent. Because there's a GUI, **evidence is a screenshot
  of the rendered surface** (before/after), plus the captured chat `tool_calls` for the
  agent path.

## Cross-surface parity & consistency

Skipper is reached through several surfaces — **web desktop UI, chat, voice, mobile,
and Discord** — and they are not separate products. Two properties bind them:

- **Parity** — *every capability is reachable from every surface.* You should be able
  to do anything through chat that you can do in the UI, and vice versa.
- **Consistency** — *the same action behaves the same way on every surface.* If you
  learn to do something one way in web chat, voice should respond the same way.

Why this is load-bearing, not a nicety:

- **UI ⇒ chat parity forces complete tooling.** Chat is the agent calling tools, so
  "everything in the UI is also doable in chat" means **an MCP tool must exist for all
  functionality.** That tool coverage is what makes voice, Discord, and automation
  work too — they all ride the same tools. A UI action with no backing tool is a gap.
- **chat ⇒ UI affordance.** If something can be done in chat, it should also live in a
  UI somewhere — sometimes it's just faster to click a button than to type a request.
  A capability with no UI surface is a gap.
- **Mobile must be first-class.** In reality **most people reach Skipper from their
  phone.** If mobile is second-rate, the majority of the experience is diminished —
  mobile parity is not optional polish.
- **Voice must be first-class.** The whole point of voice is the hands-busy moment —
  walking through the house needing something *now*, when pulling out a phone and
  hunting for the right screen is slower than just speaking. Weak voice = a diminished
  experience for exactly the cases voice exists to serve.
- **Met expectations reduce friction.** Consistency across surfaces means a user's
  learned expectations hold everywhere. Divergence — doing X in web chat, then X in
  voice and getting something different — breaks trust and adds friction to every use.

**Implication for Evolve.** A feature isn't *complete* until it has surface parity:
spec-author should state which surfaces a behavior touches and ensure the backing
tool exists; a missing chat tool, a missing UI affordance, or an untested mobile/voice
path is a **variance/gap** to surface — and closing such gaps is squarely in scope.

## What Skipper is *not* (non-goals)

- **Not a SaaS or cloud product.** No hosted multi-tenant service, no phone-home, no
  account-on-our-servers. If a feature only makes sense with a central Skipper-run
  backend, it's off-charter.
- **Not surveillance or data extraction.** Nothing that sends household data anywhere
  the operator didn't explicitly choose.
- **Not a coding-agent gateway** — Skipper is not primarily a bridge from chat apps to
  dev agents.
- **Not a single-user general personal agent.** Multi-person household life is the focus.
- **Not a social network, marketplace, or public-facing site.** Skipper serves *one
  household*; features that publish to or transact with strangers are off-charter.
- **Not a replacement for professional judgment.** Apps like medical/auto/finance
  **organize and remind**; they do not give authoritative medical, legal, or
  financial *advice*. Stay on the side of record-keeping and logistics.
- **Not a walled garden.** MIT-licensed, forkable, hackable; never add lock-in.

## Scope: what belongs

A feature fits when it helps **a household run its real life** within an existing
Capability's `scope`, or proposes a coherent new household Capability. Good signals:

- It deepens a household domain Skipper already covers (a better recipe flow, an undo
  on a chore, an edit affordance on a saved record).
- It serves more than one family member, or a shared household concern.
- It works for a self-hoster who isn't the operator (no machine-specific assumptions).
- It keeps data local and respects the privacy stance.
- It closes a cross-surface gap — a UI action with no chat tool, a chat capability
  with no UI button, or a flow that's broken/missing on mobile or voice.

A feature is **off-charter** when it requires a central/cloud backend, publishes to
strangers, targets a single power-user workflow over family life, gives professional
advice, or expands Skipper into a different product category (a coding-agent gateway,
a trading bot, a social app). Borderline-but-interesting → `needs-charter-change`
(a human decision), never a silent yes.

## Autonomy guardrails (how far Evolve may go unattended)

The charter also bounds Evolve's own autonomy (EVOLVE.md §11):

- **App changes** can run more autonomously (still gated, but a bug fix or a small
  in-scope feature can flow through with lighter touch).
- **Net-new direction** (new Capabilities, charter-adjacent features) stays
  **lower-autonomy / always hard-gated** — this is where human judgment matters most.
- **Evolve-core changes** (the engine modifying itself) are the **most dangerous
  self-mod**: strictest gate, thorough box-2 run, a known-good release to roll back
  to. Never unattended.
- **The human owns the vision.** Evolve may propose, surface, and implement; it never
  redefines what Skipper *is*. That decision is always the maintainer's.
- **Gate the operator on the DELIVERABLE, not the agents' internal steps.** The human gates are
  judgment points — *approve the intent, verify the result* — never a per-task drip. A large or
  comprehensive issue that the agents decompose into many internal units (a spec tree: a foundation
  + N per-app migrations, a service + its callers, etc.) is **gated ONCE as one deliverable, not once
  per unit.** The operator approves the *approach* (Gate 1); the engine then **autonomously builds AND
  validates the WHOLE thing** — each internal unit still fully built + box-2-validated, no quality loss,
  but the **decomposition/sequencing is the engine's concern, not the operator's** — and surfaces a
  **single** result gate (Gate 2, then Gate 3) carrying the *complete* evidence (e.g. the lint clean
  platform-wide **and** every app's before/after light+dark screenshots). Flooding the operator with a
  gate per leaf — dozens of near-identical "approve this app's migration?" touchpoints — defeats the
  whole *review-not-labor* bet and is itself a defect. Comprehensive, one-shot fixes are reviewed
  comprehensively and **once**.

## Engineering principles (non-functional)

*How* Skipper is built, not just what it does. A spec or implementation is judged
against these too — violating one is a real concern even when the feature "works."
These are the operator's standing non-functional requirements; honor them by default.

- **Preconfigure once; don't recompute per request.** Resolve expensive or external
  lookups (geocoding, third-party data, anything slow) ONE time — at configuration
  time, in the Settings app — and cache the result. Never add a per-request external
  call when a preconfigured or cached value would do. *(A weather request must not
  geocode the user's ZIP on every call; the location is configured once and cached as
  city/region/coordinates.)*
- **Minimize external dependencies and calls.** Every outbound API call is latency, a
  failure mode, and a dependency to maintain. Prefer local/cached data; cache or batch
  what you must fetch; always define the offline/error path explicitly — never silently
  fall back to a wrong value.
- **Settings is the home for configuration.** Household/user constants (location,
  preferences, keys) live in the Settings app, resolved once and surfaced to the user —
  not hardcoded, not recomputed on demand.
- **Build for the distributed self-hoster.** Skipper runs on many machines (any OS,
  deploy, hardware, often headless) — design for all of them, never just one operator's
  box. No assumptions about a specific host, path, or always-on network.
- **Degrade gracefully and idempotently.** Define not-found / offline / invalid-input
  behavior explicitly; make operations safe to retry.
- **Make it observable — the operator must be able to SEE it working.** A behavior that
  works but leaves no trace can't be verified or trusted (a cache that never logs a hit; a
  background loop that logs only on failure). Anything that runs in the background, serves
  from a cache, takes a fallback, or acts without a direct user request must emit a signal
  *where the action happens* — at minimum a log line (cache hit vs live fetch, a refresh pass
  firing, a stale/fallback path taken, a background task's outcome). A plain log line usually
  suffices — don't build parallel telemetry. Every **spec** must state WHAT is observable and
  HOW the operator confirms it at Gate 3, and the **build** must actually emit it. "How will
  the operator know this is working?" is a question spec and build must both answer.
- **Guard the context window — inject just-in-time, never bloat the prompt.** Context is finite
  and attention-diluting: stuffing it *lowers* quality because the instruction that matters gets
  buried. Load a capability's tools, `guide.md`, and memory **on demand, scoped to relevance** —
  the router injects only matched categories, a guide rides *with* its tool, recall surfaces only
  relevant memories — with an explicit "ask for more" path (`request_tools`, `search_memories`).
  Never append a feature to the always-on prompt for convenience. But "lean" means *defer and
  scope*, not *omit*: a bloated prompt and a missing instruction are equally defects.
- **The LLM determines intent — NEVER string-match chat.** Don't infer what a user wants, or
  trigger behavior, by matching hardcoded words/phrases against their message
  (`if "stop onboarding" in text: ...`) — people say things hundreds of ways, so phrase-matching is
  brittle and **wrong** as an intent mechanism. Expose the capability as an **MCP tool** with a clear
  docstring and let the model decide when to call it; that's the point of the tool layer. *(The
  router's keyword routing is the lone sanctioned keyword use, and only to choose which tool schemas
  to OFFER the model — it never decides intent or invokes anything.)*
- **Code is the truth until a spec is `verified` — never rewrite working code to match an unverified
  spec.** Most of the corpus was bootstrapped from the code and is **unverified** (`verified: false`,
  `tests: []`): such a spec *describes* what the code does, it isn't a vetted contract. A spec earns
  authority only by becoming **`verified: true`** — set once it has a passing bound test and has
  cleared the gates (verified ⇒ MUST have a bound test; the loader errors otherwise). So a
  **verified** spec is the contract → converge the code to it; an **unverified** spec is a baseline →
  the **running code wins**: if they diverge, fix the SPEC to match the code, never the reverse. Code
  changes only ever satisfy a real reported bug or an approved feature — never a bare spec-vs-code
  mismatch. When unsure which way to reconcile, surface it to the operator; don't guess by editing code.

## External contracts (consumers outside this repo)

Skipper's companion clients live in their **own repos** and consume contracts the platform exposes —
Evolve must not break them:

- **skipperbot-voice** — the voice client; consumes the **auth + WebSocket relay** contracts.
- **skipperbot-mobile** — the mobile app; consumes the same **auth/WS** contracts (mobile is
  first-class — most usage is from the phone).
- **Discord** — the Discord surface fronts the same agent + tools.

These are **out-of-tree consumers**: a change to auth, the WS protocol, or the relay shape can silently
break them — it has (a WS-token regression once broke both voice and mobile at the same time). The
**interop** and **architecture** agents must flag any change to a shared contract and name the consumer
repos affected; a contract change is never "internal-only."

## Stack & repository layout

- **Stack:** Python + FastAPI (backend), React JSX (web). Do **not** introduce a different
  language/framework or invent `.ts` / `packages/`-style layouts — match the existing stack.
- **Layout:** the platform core lives under `app_platform/` + `data_layer/`; domain apps are drop-in
  packages under `apps/<id>/` (UI + tools + schema + migrations). Specs live under the configured spec
  roots; each app's tests co-locate with the app.
- **Dependency direction (one-directional, load-bearing):** apps may depend on the platform; the
  platform must **never** import an app; apps must **never** import each other. The dep-guard enforces
  this against the configured platform prefixes + app glob.

## Testing on the test host — thinking domains are OFF by default

Skipper runs **thinking domains**: autonomous, scheduled background reasoning processes (e.g. `pm`,
`goals`, `memory`, `document`, `self`, and a per-goal `g-<id>` domain), driven on a cadence by
`thinking_scheduler.py` and configured in the `thinking_domains` table. **On the test host these are
DISABLED by default** — only the `chat` domain (the interactive path acceptance drives) is on — so they
don't burn API spend reasoning over mock data nobody reads. `seed`/`prepare` re-enforce this on every
reseed, so a freshly-prepared test host always has only `chat` enabled.

So when a prompt says "the test host has the product's background AI work disabled," **for Skipper that
means these thinking domains.** If you are working on or testing a thinking-domain feature, enable
**only** the specific domain you need for the test — `data_layer.thinking_domains.update_domain('<name>',
enabled=True)`, run in the agent container on the test host — then **turn it back OFF** when done
(`enabled=False`). Never leave a thinking domain enabled on the test host.

## Building a NEW app (not just fixing existing code)

A *new* app is a different task from changing existing code, with a required path — follow it:

1. **Read `specs/APP_PACKAGES.md` first** — the platform's app contract (the manifest, a short
   globally-unique entity-type prefix, the `digest_record`-on-every-mutation rule, the `routes.py`
   bare-router convention, the `ui/index.js` launcher registry, the `__init__.py` / per-app schema /
   migrations layout). A new app MUST satisfy this contract; it's the source of truth, not guesswork.
2. **Scaffold FIRST — never hand-roll the package structure.** Run the **`scaffold`** op
   (`evolve_adapter.py scaffold unit="<App Name>"`, i.e. `scripts/new_app.py "<App Name>"`) to generate
   a contract-satisfying skeleton as a **sibling repo** `../skipperbot-app-<slug>/`. It is
   **non-interactive** (pass the display name as an arg). This wires the manifest, data layer (with
   `digest_record`), routes, UI registry, and `__init__.py` correctly so the app loads when dropped into
   `apps/<id>/`.
3. **Implement the app's behavior INSIDE that scaffold** — fill in `data.py`, `tools.py`, `routes.py`,
   the UI, the manifest's entity prefix + tool keywords, and migrations. Don't reinvent the layout the
   scaffold already got right; extend it.

Because a new app is its **own repo**, shipping it end-to-end also needs the multi-repo onboarding:
create the GitHub repo, add it to `evolve.repos.yaml` (`type: app`, `host: <platform>`,
`clone_path: apps/<id>`), and clone it on the brain + test host. Until those exist, a new-app build can
scaffold + implement locally but cannot deploy/validate as an installed app.
