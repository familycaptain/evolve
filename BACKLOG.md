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
