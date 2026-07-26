# Evolve backlog

Engine work that is worth doing but not yet scheduled. Evolve does not build itself
through its own loop, so these are notes for whoever picks them up — not work items the
loop will ingest.

---

## Evaluate how the loop writes specs — PM language, not engineering language

**Status:** to evaluate. Unscheduled.

### The problem

The specs the loop produces read like engineering documents. They name files, functions,
line numbers, call ordering, and framework details. That is the wrong register for what
a specification is supposed to be.

A spec should carry **intent**: what we are doing, and why it is worth doing. How it
gets built is a separate question with a separate lifetime — an implementation can be
replaced entirely without the intent changing at all, and when the two are fused, the
spec ages the moment the code moves.

### What good looks like

Specs should read as a project manager would write them: the outcome, who it is for,
why it matters, what "done" means, what is explicitly out of scope.

**Almost always, that means an expected OUTCOME — observable behaviour.** "When you
click this button, X happens." "When a reminder is due and the person is not at a
screen, it reaches them on their phone." "A brand-new household can finish setup without
being told to edit a file." Someone should be able to read a spec and know what to check
without knowing how any of it was built.

The technical plan is still valuable — it just belongs in the **GitHub issue**, as the
plan for how this particular change will be carried out. Keeping it there means the
spec stays a durable statement of intent while the issue holds the perishable detail.

### The acid test

Concatenate every spec in the corpus, hand it to a fresh repository and a Claude prompt,
and it should be possible to build something that works like Skipper **from scratch** —
without reference to the existing implementation.

That is a falsifiable bar, and it is the useful one. If the specs only make sense
alongside the code they describe, they are documentation of an implementation rather
than a specification of a product. If they can regenerate the product, they captured
intent.

### Measured on the live corpus (2026-07-26)

485 spec records in the Skipper instance, split by git origin: 296 hand-authored,
45 written by the loop (excluding `_feature`/`_capability` records).

| | hand-authored | loop-written |
|---|---|---|
| average length | 15 lines | **54 lines** (3.6x) |
| implementation vocabulary inside `behavior` | 6% | **57%** |
| average `notes` length | 50 chars | **657 chars** (13x) |
| process metadata (`ev-NN`, `Gate-2`, "test host") | 2% | **88%** |

The gap is not stylistic drift. It is two different documents wearing the same schema.

**A hand-authored spec, in full** (`lists.collections.add-item`) — the behaviour is one
sentence, and someone who has never seen the code can check it:

> Adding an item appends it to a list (and, for a board-backed list, creates the backing
> Trello card).

**A loop-written one** (`auto.detail.per-tab-heroes`) names a React component in its
title, and its `behavior` ends with a sentence that is purely mechanism: a dedicated
loading state gating the heroes so they do not flash during a concurrent fetch. That
describes how the code avoids a flicker, not what the product does.

### The biggest single offender is `notes`

13x longer, and 88% of loop specs carry process metadata. `notes` has become a
**validation journal**: what was verified at which gate, on which host, against which
mock record, which sibling ev-number it relates to, which registry it deliberately did
not touch.

None of that is the product. All of it is perishable — it describes one build of one
change on one afternoon — and it is stored in the one artifact that is supposed to
outlive every implementation. This is also the most tractable thing to fix: the
validation record already has a home in the gate packet and the GitHub issue.

### What this suggests (to confirm, not assume)

The loop appears to be writing the spec as a *record of the work it just did* rather
than a statement of what the product should do. That would explain every number above
at once: length, mechanism in `behavior`, and a notes field full of build evidence.

If that is right, the fix is less about vocabulary rules and more about what the
spec-author is asked to produce, and what `spec-audit` rewards.

### Root cause (traced 2026-07-26) — it is not a missing rule

The obvious fix is to tell spec-author to stop writing implementation. **That rule
already exists** and is being ignored:

- *"You write requirements, not code."*
- *"State the desired end-state, not the implementation."*
- on code pointers: *"a pointer, not a paragraph. Don't re-explain them in `behavior`."*

So adding another instruction is not the fix. Three things are working against those
rules at once:

**1. The prompt contradicts itself.** Its closing instruction says to reason from the
grounding digest *so your `implements` paths and behavior match the real code*. That
asks for exactly what the earlier lines forbid. Given a direct conflict, the concrete
instruction wins over the abstract one.

**2. Its entire input is implementation.** The spec-author receives the Grounding output
(a map of files, symbols, excerpts) and the Design output (the technical approach). It is
asked to produce intent while being shown nothing but mechanism. It is, in effect, being
handed the implementer's research and asked to summarise it — which is precisely what the
measurements show it doing.

**3. The `notes` journal is emergent, not instructed.** Nothing tells any agent to write
validation evidence into a spec. What the skill DOES say is that when validation is
green, the loop should edit the spec YAML in the worktree to set `verified: true`. That
edit is the opening: with the file already open and the validation fresh, the loop writes
down what it just proved. Hence 657-char notes full of gate references, host names and
mock records that nobody asked for.

### What that implies for a fix

- Remove the contradiction. "Match the real code" is right for `implements` and wrong for
  `behavior`; the sentence currently applies it to both.
- Grounding is not the problem and should NOT be removed. Operator intent (2026-07-26):
  it is there because the existing spec corpus is incomplete, so the author can go back
  to the code **when it needs to** — where no spec covers the area, or where the specs
  that do look stale. It was never meant to be summarised.
  What is missing is the RANKING. The primary sources are the work item (what the person
  actually asked for), the charter, and the existing specs; grounding is a FALLBACK
  consulted when those are silent or out of date. Today it arrives as the richest,
  most concrete input and is treated as the subject.
  The distinction to make explicit: read the code to learn **what the product currently
  does**, then state that as behaviour — not to describe **what the code is**. Same
  source, opposite output.
- Constrain the post-validation edit to the field it is meant to touch. Setting
  `verified: true` should not be an invitation to append a build log.
- **`notes` needs more than the post-validation constraint.** That constraint stops one
  writer; there are two, and beneath both is a field with no definition.
  `notes` appears NOWHERE in `engine/schema.py` — it is unvalidated and undescribed — and
  the spec-author prompt mentions it once, bundled with `implements` as a place for terse
  code pointers, guarded only by "a pointer, not a paragraph". That is the same soft
  instruction being ignored elsewhere.
  An undefined field absorbs whatever is in the writer's head, and that is exactly what
  the corpus shows: gate references, host names, mock records, sibling ev-numbers, design
  rationale and operator decisions all pooled in one place. Hand-authored specs average 50
  characters here and often leave it empty; loop specs average 657.
  So `notes` needs a decided purpose, not just a narrower edit window. `implements`
  already holds code paths and the gate packet and issue already hold validation
  evidence — which leaves the question of what, if anything, is left. The one candidate
  that looks genuinely durable is RATIONALE: why the product behaves this way, and which
  choices were the operator's. That is intent, it outlives any implementation, and it has
  nowhere else to live. Everything else currently in `notes` has a better home already.
- `spec-audit` shapes what survives. If the critic treats completeness as quality, it
  will keep pulling specs toward being thorough build records. Worth checking what it
  actually rewards before changing the author.

The through-line: the spec-author is documenting the work it just did, rather than
describing how the product should behave and checking that against the charter and the
operator's intent. Everything measured follows from that one substitution.

### Where to look

- `agents/prompts/spec-author.md` — what the spec-writing agent is asked to produce
- `agents/prompts/spec-audit.md` — what the critic checks for, which shapes what survives
- `agents/prompts/lead.md` — what gets carried into the gate packet
- The C/F/S corpus itself (`engine/schema.py`, an instance's `specs/` tree) — whether the
  record format encourages intent or implementation

### Worth weighing while evaluating

- Occasionally a technical constraint genuinely IS the intent — "must work without an
  internet connection", "must not require a login". In that case the constraint itself
  is the spec: state it plainly and stop. It does not license describing HOW the
  constraint gets satisfied.
  This is the EXCEPTION and should be treated as rare. Most specs are capturing an
  expected outcome, and "but this constraint is really intent" is exactly the excuse
  that would keep engineering detail in specs where it does not belong. If a statement
  could be replaced by a different implementation without changing what the user
  experiences, it is plumbing.
- The bound tests attached to a spec are part of its meaning. If specs move toward
  intent, the tests need to stay concrete enough to prove the intent was met.
- The regeneration test above may be worth running as an actual experiment on a small
  capability before committing to a prompt rewrite.
