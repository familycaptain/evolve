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

### Where to look

- `agents/prompts/spec-author.md` — what the spec-writing agent is asked to produce
- `agents/prompts/spec-audit.md` — what the critic checks for, which shapes what survives
- `agents/prompts/lead.md` — what gets carried into the gate packet
- The C/F/S corpus itself (`engine/schema.py`, an instance's `specs/` tree) — whether the
  record format encourages intent or implementation

### Worth weighing while evaluating

- Some technical constraint IS intent ("must work without an internet connection",
  "must not require a login"). The line is not "no technical words" — it is whether the
  statement describes the product or the plumbing.
- The bound tests attached to a spec are part of its meaning. If specs move toward
  intent, the tests need to stay concrete enough to prove the intent was met.
- The regeneration test above may be worth running as an actual experiment on a small
  capability before committing to a prompt rewrite.
