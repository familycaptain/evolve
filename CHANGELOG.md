# Changelog

All notable changes to Evolve are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project aims to follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html) — see the `VERSION` file and the git tags.

## [Unreleased]

### Changed
- **Gate flow is now two operator gates + one automated gate.** Gate 2 (validate) is no longer an
  operator approval: on green test-host validation the loop **auto-approves it itself**
  (`decided_by=auto`), merges to the staging branch, pushes it, and opens Gate 3. The operator now makes
  exactly two judgment calls per change — **Gate 1 (requirements)** and **Gate 3 (verify / UAT)**.
- **Two-token rule reworded to a per-gate carve-out.** The loop's service token may auto-approve
  **Gate 2 only** — never a change/reject, and never Gate 1 or Gate 3. The operator's decide token still
  exclusively governs the two *final* approvals (requirements and UAT). The loop's auto-approval can only
  ever publish to the staging (`release`) branch; the `release → main` promotion to prod stays
  operator-owned, so nothing reaches production without the operator.
- **Dashboard rebuilt as a Kanban board.** The runs rail + detail panel are replaced by a six-column
  board — **New · Requirements · Build · Validate · UAT · Closed** — with each item a card in its stage's
  column. Cards reflow between columns automatically as their phase advances (live, on the existing poll).
  Clicking a card opens a full-screen, internally-scrolling **detail modal** (spec, decisions, validation,
  evidence, diff, live activity) carrying the approve/change/reject controls for the two operator gates.

### Added
- `scripts/evolve_runs.py autoapprove <id>` — records the Gate 2 auto-approval (service token).
- `engine/platform_bridge.py::decide()` and the server-side per-gate authorization
  (`dashboard/server.py::_require_decide_for_gate`) enforcing the Gate-2-only service carve-out.
