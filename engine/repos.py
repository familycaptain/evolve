"""The repo registry — the COLLECTION of repos this Evolve instance watches.

Reads `$EVOLVE_REPOS_FILE` (default `evolve.repos.yaml`): a YAML list of entries, each
`{name, type, path, clone_path?, branch_model?, spec_roots?, token_env?}`. This is the single
source of truth for *which* repos Evolve manages and each one's per-repo config — consumed by
the dashboard's repo-switcher, the change-poller, and spec/dep resolution.

Falls back to a single entry from `$GITHUB_REPO` when the registry file is absent (or PyYAML
isn't installed), so single-repo setups still work.
"""
from __future__ import annotations

import os


def _registry_path() -> str:
    """The registry file. A relative $EVOLVE_REPOS_FILE is tried against CWD first, then the repo root
    (the parent of this engine/ package) — so the registry loads regardless of which dir a caller runs
    from (the loop's one-liners, the dashboard, the adapter dispatcher all differ)."""
    p = os.path.expanduser(os.getenv("EVOLVE_REPOS_FILE", "evolve.repos.yaml"))
    if os.path.isabs(p) or os.path.exists(p):
        return p
    root_rel = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), p)
    return root_rel if os.path.exists(root_rel) else p


def load_repos() -> list[dict]:
    """The configured repo collection (a list of entry dicts). Empty if nothing is configured."""
    path = _registry_path()
    if os.path.exists(path):
        try:
            import yaml  # PyYAML (see dashboard/requirements.txt)
            with open(path, encoding="utf-8") as fh:
                data = yaml.safe_load(fh) or []
            if isinstance(data, list):
                return [r for r in data if isinstance(r, dict) and r.get("name")]
        except ImportError:
            pass   # PyYAML absent → fall back to the single-repo env below
        except Exception:
            pass
    repo = (os.getenv("GITHUB_REPO") or "").strip()
    return [{"name": repo, "type": "platform"}] if repo else []


def primary_repo() -> str:
    """The first/primary repo name — what single-repo tooling uses until the multi-repo poller lands."""
    repos = load_repos()
    return repos[0]["name"] if repos else (os.getenv("GITHUB_REPO") or "")


def repo_config(name: str) -> dict:
    """The full registry entry for a repo name, or {} if not configured."""
    for r in load_repos():
        if r.get("name") == name:
            return r
    return {}


def repo_intake(name: str) -> str:
    """Intake mode for a repo: 'auto' (consider every open issue) or 'manual' (consider ONLY
    issues a human has admitted via the dashboard). Resolution: the entry's `intake:` field,
    else $EVOLVE_INTAKE_DEFAULT, else 'auto'. Anything but 'manual' normalizes to 'auto'."""
    mode = str(repo_config(name).get("intake")
               or os.getenv("EVOLVE_INTAKE_DEFAULT") or "auto").strip().lower()
    return "manual" if mode == "manual" else "auto"


# --- per-repo resolvers (the multi-repo seam) --------------------------------
# Every field a non-platform repo needs to build/deploy differently is resolved here, so the
# rest of the engine reads ONE place. All default so a single-platform setup behaves as before.

def repo_slug(name: str) -> str:
    """A filesystem/run-id-safe slug for a repo name ('your-org/your-app' → 'your-app'). Used to
    namespace run ids + state dirs so two repos that each have an issue #5 never collide."""
    base = (name or "").split("/")[-1]
    return "".join(c if c.isalnum() or c in "-_." else "-" for c in base).strip("-") or "repo"


def repo_type(name: str) -> str:
    """platform | app | model | companion (default 'platform')."""
    return (repo_config(name).get("type") or "platform").strip().lower()


def repo_path(name: str) -> str:
    """The local checkout path for a repo (where the loop edits its code). Falls back to '.'
    (the platform-in-place default) when the entry has no `path`."""
    return os.path.expanduser(repo_config(name).get("path") or ".")


def repo_branches(name: str) -> tuple[str, str]:
    """(staging, world) for a repo, parsed from `branch_model: <staging>-><world>`, falling back
    to $EVOLVE_STAGING_BRANCH / $EVOLVE_WORLD_BRANCH, then release/main."""
    bm = str(repo_config(name).get("branch_model") or "").strip()
    if "->" in bm:
        staging, world = (p.strip() for p in bm.split("->", 1))
        if staging and world:
            return staging, world
    return (os.getenv("EVOLVE_STAGING_BRANCH") or "release",
            os.getenv("EVOLVE_WORLD_BRANCH") or "main")


def repo_spec_roots(name: str) -> list[str]:
    """The repo-relative globs where THIS repo's specs live (the entry's `spec_roots`), with a
    type-aware default: platform → ['apps/*/specs','specs'], everything else → ['specs']."""
    roots = repo_config(name).get("spec_roots")
    if isinstance(roots, list) and roots:
        return [str(r) for r in roots]
    return ["apps/*/specs", "specs"] if repo_type(name) == "platform" else ["specs"]


def repo_token_env(name: str) -> str:
    """The env var holding this repo's GitHub token (entry `token_env`, default GITHUB_TOKEN) —
    so a repo in a DIFFERENT GitHub account authenticates with its own PAT."""
    return (repo_config(name).get("token_env") or "GITHUB_TOKEN").strip()


def repo_host(name: str) -> str | None:
    """For an app/model repo: the name of the PLATFORM repo it deploys INTO. Resolution:
      1. the entry's explicit `host:` field (the flexible, unambiguous way — an app can name ANY
         platform repo as its parent, and different apps can have different parents);
      2. else, ONLY when exactly one `type: platform` entry exists, that lone platform (a safe
         convenience for the common single-platform case);
      3. else None (ambiguous — `host:` is required).
    Returns None for a platform/companion repo (they don't clone into a host)."""
    if repo_type(name) in ("platform", "companion"):
        return None
    explicit = (repo_config(name).get("host") or "").strip()
    if explicit:
        return explicit
    platforms = [r["name"] for r in load_repos() if (r.get("type") or "").strip().lower() == "platform"]
    return platforms[0] if len(platforms) == 1 else None


def resolve_clone_target(name: str) -> str | None:
    """Absolute path an app/model repo deploys INTO: <host repo's path>/<clone_path>
    (e.g. ~/repos/your-platform/apps/foo). None if not an app/model, or if `clone_path`
    is missing, or the host can't be resolved (operator must set `host:`)."""
    if repo_type(name) in ("platform", "companion"):
        return None
    clone_path = (repo_config(name).get("clone_path") or "").strip()
    host = repo_host(name)
    if not clone_path or not host:
        return None
    return os.path.join(repo_path(host), clone_path)
