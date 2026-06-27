"""Issue intake policy — which open issues the loop is allowed to CONSIDER.

Per-repo intake mode (registry `intake:` field → `$EVOLVE_INTAKE_DEFAULT` → `auto`):
  auto   — every open issue is considered (the default; the autonomous "it watches your issues" mode).
  manual — ONLY issues a human has ADMITTED via the dashboard are considered. The human reads the
           issue on GitHub first and opts its number in, so (a) a malicious / prompt-injection issue
           never reaches an agent at all, and (b) a high-volume public repo can be worked selectively.

The allowlist lives in the dashboard (admit via the admin UI); this module reads it over HTTP, so it
works whether the dashboard is local or on a separate admin host. Use from the loop:

    python3 -c "from engine import intake; [print(i['number'], i['title']) for i in intake.admissible_issues()]"
"""
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request

from engine import github_connector as _gh
from engine import repos as _repos


def _server() -> str:
    return (os.getenv("EVOLVE_SERVER_URL") or "http://localhost:8000").rstrip("/")


def admitted_numbers(repo: str) -> set[int]:
    """Issue numbers admitted for `repo` (from the dashboard allowlist). Empty set on any error —
    fail CLOSED for manual repos (an unreachable dashboard admits nothing, never everything)."""
    try:
        url = _server() + "/api/apps/evolve/admitted?repo=" + urllib.parse.quote(repo or "")
        with urllib.request.urlopen(url, timeout=15) as r:
            data = json.loads(r.read().decode())
        return {int(x) for x in (data.get("admitted") or [])}
    except Exception:
        return set()


def admissible_issues(repo: str) -> list[dict]:
    """Open issues the loop may consider for ONE repo, honoring its intake mode: all of them for
    `auto`, only admitted ones for `manual`. Each issue dict is tagged with `repo` and `source`."""
    issues = _gh.list_open_issues(repo=repo)
    if _repos.repo_intake(repo) != "auto":
        allow = admitted_numbers(repo)
        issues = [i for i in issues if int(i.get("number") or 0) in allow]
    for i in issues:
        i["repo"] = repo
        i["source"] = f"github:{repo}#{i.get('number')}"
    return issues


def all_admissible_issues() -> list[dict]:
    """Open, admissible issues across EVERY registered repo — the multi-repo intake scan the loop
    runs each pass. Companion repos are skipped (Evolve specs/drafts them; it doesn't build them).
    A repo that errors (auth/network) is skipped, never aborting the whole scan. Each issue carries
    its `repo` + `source` so the loop never confuses two repos' issue #5."""
    out: list[dict] = []
    for entry in _repos.load_repos():
        name = entry.get("name")
        if not name or _repos.repo_type(name) == "companion":
            continue
        try:
            out.extend(admissible_issues(name))
        except Exception as e:  # one bad repo must not blind the loop to the others
            print(f"# intake: skipped {name}: {str(e)[:120]}")
    return out


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        rows = admissible_issues(sys.argv[1])
    else:
        rows = all_admissible_issues()
    for i in rows:
        print(i.get("repo"), i.get("number"), i.get("title"))
