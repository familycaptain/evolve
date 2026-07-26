# Writing specifications

How to write a specification record in this engine — for the `spec-author` agent, and for
anyone auditing or rewriting a corpus by hand.

## What a specification is

A statement of **how the product should behave, and why**, durable enough to outlive every
implementation of it.

The bar worth aiming at: concatenate every spec in a corpus, hand it to a fresh repository
and a capable engineer with no access to the current code, and they should be able to
build something that works like the product. That is only possible if specs describe the
product rather than the code.

## What it is not

- a description of how the code works
- a record of the work someone did
- a summary of a code-reading pass
- a build or verification log

## A spec names a trigger and a consequence

This is the whole thing. A specification is a requirement of the kind you could hand
someone to build against: **when this happens, that is the result.**

Two shapes work equally well — use whichever reads more naturally:

**BDD**

> GIVEN a household with no members added yet, WHEN the primary user opens the app for the
> first time, THEN the setup walkthrough starts on its own.

**Plain**

> When the primary user logs in for the very first time, the onboarding walkthrough starts
> automatically.

Both name a trigger and a consequence. Both can be checked by someone who has never seen
the code. Both survive a total rewrite of the internals.

## The failure to avoid: the tautology

> The onboarding walkthrough works.

This is not a specification. Of course it should work. It names no trigger and no
consequence, so there is nothing to build against and nothing to check — it glazes over
the actual behaviour instead of stating it.

Watch for the words that produce them: a feature that "works", "is supported", "is
available", "is handled", or "functions correctly". If you have written one, you have not
found the behaviour yet. Go back and ask: *what specifically happens, and when?*

## Three tests, in order

0. **Does it name a trigger and a consequence?** If you cannot point at the "when" and the
   "then", it is not a spec yet. A tautology passes the other two tests and still says
   nothing, which is why this one comes first.
1. **Could a completely different implementation satisfy this sentence?** If rewriting the
   internals would falsify it, you have written mechanism.
2. **Could someone who has never read the code verify it?** If not, it is not observable.

Tells that you have drifted into mechanism: naming an internal component, class, flag,
state variable, hook, table, call order, or framework detail.

## The technical-intent exception

Occasionally a technical constraint genuinely *is* the intent — "works with no internet
connection", "never requires a login", "survives a restart without losing state". When
that is the case, **the constraint itself is the spec**: state it plainly and stop. It does
not license describing how the constraint is met.

Treat this as rare. "But this constraint is really intent" is the excuse that keeps
engineering detail in specs where it does not belong. If a statement could be satisfied by
a different implementation without changing what a person experiences, it is plumbing.

## The fields

| field | holds |
|---|---|
| `behavior` | the trigger and consequence, 1–3 sentences. Cover the cases that materially differ — empty, error, permission denied, nothing configured — without padding. |
| `implements` | the code paths this governs. **The only field that should track the shape of the code.** |
| `tests` | bound acceptance tests, if they exist. Never invent them. |
| `notes` | **why this spec is the way it is** — rationale, and which choices were the operator's. Capped, and usually empty. |
| `issues` | bare tracker references only, e.g. `[117]`. Never descriptions. |

### On `notes`

It is not a record of work done: no verification narrative, no host or environment detail,
no restating a tracker item. Those are perishable — they describe one build on one
afternoon — and a spec outlives every implementation of it. Code paths belong in
`implements`; validation evidence belongs in the tracker.

Most specs need no notes at all. Leaving it empty is the normal case, not a gap.

## Grounding: the code is truth, but not the subject

Read the code to learn **what the product currently does**, then state that as behaviour.
Same source, opposite output — you are extracting the product from the code, not describing
the code.

Priority of sources when writing:

1. **The work item** — what was actually asked for.
2. **The charter** — what this product is and is not. A behaviour that conflicts with it is
   a finding, not something to write down and pass along.
3. **Existing specs** — if one already governs the area, you are amending a contract.
4. **The code** — a fallback for when the above do not settle it: nothing covers the area,
   or what does looks stale.

Where a spec and the code disagree, the code wins — the spec was written against an older
implementation. But do not silently encode a bug as intent: if the code does something that
looks wrong rather than merely undocumented, say so separately.

## Coverage

A corpus is usually thinner than the product. Expect to write more specs than you rewrite,
often several times more. Do not ration them — a behaviour someone could observe and would
care about deserves its own record.

Do not spec internal helpers with no observable effect, pure refactors, or anything visible
only to a developer reading the code.
