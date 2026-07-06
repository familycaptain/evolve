#!/usr/bin/env python3
"""OPTIONAL dependency guard — ONE pluggable build check, not a universal rule.

Evolve imposes NO dependency model on your project. This is a *reference* guard for the common
**layered / monorepo** shape: a "platform" (shared core) plus "units" (apps / plugins / modules),
where a unit may import the platform but the **platform must never import a unit** and **units must
not import each other's internals**. The unit namespace + platform prefixes are configured
(`$EVOLVE_APP_GLOB` / `$EVOLVE_PLATFORM_PREFIXES`).

It runs ONLY if you opt in — set `EVOLVE_DEP_CHECK_CMD` to point at it, and the engine runs whatever
that points at during the build (unset = no guard at all). A project with a different architecture
points `EVOLVE_DEP_CHECK_CMD` at its OWN checker instead — any script taking `<worktree> <base_ref>`,
printing JSON, exiting 0 (clean) / non-zero (violations) — or leaves it blank.

The Gate-1 architecture review already judges placement as *intent*; this deterministic check closes
the gap of *where the code actually landed* — it parses the imports of every CHANGED .py file and
fails if any crosses a configured boundary the wrong way.

  python3 scripts/evolve_dep_check.py [repo_or_worktree_dir] [base_ref]   # default: . , $EVOLVE_STAGING_BRANCH

Exit 0 = clean, 1 = violations. Prints JSON.
"""
import ast, json, os, subprocess, sys

REPO = sys.argv[1] if len(sys.argv) > 1 else "."
BASE = sys.argv[2] if len(sys.argv) > 2 else os.getenv("EVOLVE_STAGING_BRANCH", "release")

# Platform code (must never import a unit): the configured platform package prefixes + top-level modules.
_PLATFORM_PREFIXES = tuple(x.strip().rstrip("/") + "/" for x in os.getenv("EVOLVE_PLATFORM_PREFIXES", "core").split(",") if x.strip())

# The unit (app/module) directory + import namespace, from the configured glob ("apps/*" -> "apps").
# This is the ONE place the old `apps/`-specific concept lived; it is now config-driven.
_APP_DIR = (os.getenv("EVOLVE_APP_GLOB", "apps/*").split("/")[0].strip() or "apps")
_APP_NS = _APP_DIR   # the Python import namespace mirrors the unit directory name


def _changed_py():
    files = set()
    # BASE...HEAD (merge-base), not BASE..: two-dot blames this branch for commits that
    # landed on the base AFTER the feature was cut — the guard would fail a build for
    # imports someone else added. Matches workspace.changed_files.
    for args in (["diff", "--name-only", f"{BASE}...HEAD"], ["diff", "--name-only", "HEAD"],
                 ["diff", "--name-only", "--cached"]):
        out = subprocess.run(["git", "-C", REPO, *args], text=True, capture_output=True).stdout
        files.update(l.strip() for l in out.splitlines() if l.strip())
    return [f for f in files if f.endswith(".py") and os.path.exists(os.path.join(REPO, f))]


def _imports_from_src(src):
    try:
        tree = ast.parse(src)
    except Exception:
        return set()
    mods = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            mods.update(a.name for a in n.names)
        elif isinstance(n, ast.ImportFrom) and n.module and n.level == 0:
            mods.add(n.module)
    return mods


def _new_imports(rel):
    """Imports this change ADDED to the file (HEAD minus BASE) — so pre-existing baseline debt
    in a touched file isn't flagged, only what the change newly introduces."""
    try:
        head = _imports_from_src(open(os.path.join(REPO, rel)).read())
    except Exception:
        return set()
    r = subprocess.run(["git", "-C", REPO, "show", f"{BASE}:{rel}"], text=True, capture_output=True)
    base = _imports_from_src(r.stdout) if r.returncode == 0 else set()   # rc!=0 → new file
    return head - base


def _app_of(path):
    p = path.split("/")
    return p[1] if len(p) >= 2 and p[0] == _APP_DIR else None


def _is_platform(path):
    return path.startswith(_PLATFORM_PREFIXES) or "/" not in path


def _violation(path, mod):
    if not (mod == _APP_NS or mod.startswith(_APP_NS + ".")):
        return None
    target = mod.split(".")[1] if len(mod.split(".")) > 1 else "?"
    if _is_platform(path):
        return (f"PLATFORM `{path}` imports unit `{target}` (`{mod}`) — the platform must never "
                f"depend on a unit ({_APP_DIR}/). Move the shared code into a configured platform prefix.")
    src = _app_of(path)
    if src and target != src and target != "?":
        return (f"unit `{src}` (`{path}`) imports another unit `{target}` (`{mod}`) — units must not "
                f"depend on each other's internals. Put shared code in the platform.")
    return None


def main():
    findings = []
    for f in _changed_py():
        for mod in sorted(_new_imports(f)):
            v = _violation(f, mod)
            if v:
                findings.append({"file": f, "import": mod, "violation": v})
    print(json.dumps({"ok": not findings, "violations": findings}, indent=2))
    sys.exit(0 if not findings else 1)


if __name__ == "__main__":
    main()
