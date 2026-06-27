---
name: cfs-validate
description: >
  Validate a Capability/Feature/Specification tree against the §4 loader rules
  before relying on it. Use after authoring or editing C/F/S YAML under an app's
  specs/ tree, or whenever an agent needs to confirm the corpus is well-formed.
allowed-tools: Bash(python3 -m schema*)
---

# Validate a C/F/S tree

Run the Evolve loader validation over a specs directory:

```bash
python3 -m schema <specs_dir>     # a path under the configured spec roots (`$EVOLVE_SPEC_ROOTS`)
```

## Interpreting the result

- **errors** → the corpus is malformed; it must be fixed before it can be projected
  or merged. Causes: id↔kind↔path mismatch, missing parent, duplicate id, bad state,
  a specification with no `behavior`, a `proposed` spec on `$EVOLVE_WORLD_BRANCH` (outside bootstrap).
- **warnings** → advisory, not blocking: `untested variance` (a spec with no bound
  tests — fine for a draft, must be resolved before `live`) and `implements path
  missing` (drift / not-yet-built code).

A clean tree prints `errors=0`. A reverse-engineered draft tree legitimately shows
`untested` warnings until its tests are written (EVOLVE.md §12).
