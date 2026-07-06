#!/usr/bin/env python3
"""The adapter binding — the ONE stable seam between the engine and YOUR project's deploy/validate.

The engine never hardcodes how to deploy or test a project. Instead it calls:

    python3 scripts/evolve_adapter.py <op> [key=value ...]

This resolves the ACTIVE adapter (`$EVOLVE_ADAPTER`, a directory under `adapters/`), reads its
`adapter.yaml` — a map of operation -> shell command with `{placeholder}`s — substitutes the
`key=value` args, and runs the command on the brain (the command itself handles any ssh to the
target host). Output and exit code pass straight through, so the calling agent reads them directly.

Operations the engine uses (an adapter implements only the ones it needs):
  deploy      host=<host> ref=<branch|sha>   check out <ref> on <host>, bring the product up.
              CONTRACT: must leave the host at EXACTLY <ref> even from a dirty checkout (reset
              --hard + clean untracked + forced checkout) and must FAIL rather than bring the
              product up on stale code — a checkout abort that falls through to a restart makes
              validation test the wrong build. Echo the deployed sha in the JSON result.
                                             Should print JSON {"ok":..,"healthy":..,"sha":..}, exit 0/!=0.
  health      host=<host>                    exit 0 if the product is up on <host>.
  acceptance  host=<host> spec=<id|file>     drive the product as a user; print {"passed":..,"evidence":[..]}.
  seed        host=<host>                     (optional) load fixtures / mock data.
  scaffold    unit=<name>                     (optional) scaffold a new unit of work.

An op the active adapter doesn't define is a clean error, not a crash — so a project that only
needs `deploy`+`acceptance` simply omits the rest.
"""
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Load the repo-root .env so $EVOLVE_ADAPTER (and anything the adapter command references) is set.
_envf = os.path.join(ROOT, ".env")
if os.path.exists(_envf):
    for _line in open(_envf, encoding="utf-8"):
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            _v = _v.strip()
            if _v and _v[0] not in "'\"":
                _v = _v.split(" #", 1)[0].rstrip()   # unquoted inline comment
            os.environ.setdefault(_k.strip(), _v.strip('\"').strip("'"))


def _manifest() -> tuple[str, dict]:
    name = (os.getenv("EVOLVE_ADAPTER") or "").strip()
    if not name:
        sys.exit("EVOLVE_ADAPTER is not set — point it at an adapter directory under adapters/ "
                 "(e.g. `EVOLVE_ADAPTER=myproject` in .env). See adapters/example/.")
    path = os.path.join(ROOT, "adapters", name, "adapter.yaml")
    if not os.path.exists(path):
        sys.exit(f"adapter manifest not found: adapters/{name}/adapter.yaml (EVOLVE_ADAPTER={name}).")
    try:
        import yaml
    except ImportError:
        sys.exit("PyYAML is required to read the adapter manifest: pip install pyyaml")
    with open(path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    if not isinstance(data, dict):
        sys.exit(f"adapters/{name}/adapter.yaml must be a mapping of op -> command.")
    return name, data


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        sys.exit("usage: evolve_adapter.py <deploy|health|acceptance|seed|scaffold> [key=value ...]")
    op = sys.argv[1]
    args = dict(a.split("=", 1) for a in sys.argv[2:] if "=" in a)
    name, manifest = _manifest()

    # When a `repo=` arg is given, enrich the args with that repo's registry config so an adapter op
    # can deploy ANY repo type — a platform in place, or an app/model CLONED INTO its host platform.
    # These are available as {placeholders}; an op uses only what it needs.
    if args.get("repo"):
        try:
            sys.path.insert(0, ROOT)
            from engine import repos as _repos
            r = args["repo"]
            args.setdefault("repo_type", _repos.repo_type(r))
            args.setdefault("repo_path", _repos.repo_path(r))        # the repo's own checkout
            staging, world = _repos.repo_branches(r)
            args.setdefault("staging_branch", staging)
            args.setdefault("world_branch", world)
            host = _repos.repo_host(r)
            if host:
                args.setdefault("host_repo", host)
                args.setdefault("host_path", _repos.repo_path(host))
            clone_path = (_repos.repo_config(r).get("clone_path") or "").strip()
            if clone_path:
                args.setdefault("clone_path", clone_path)
            target = _repos.resolve_clone_target(r)
            if target:
                args.setdefault("clone_target", target)  # abs path: host_path/clone_path
        except Exception:
            pass  # registry optional — bare host=/ref= still work
    # The auto-enrich placeholders are OPTIONAL: default any unset one to "" so a recipe may reference
    # {repo_type}/{clone_target}/… even on a legacy call with no repo= (they're empty, so a shell
    # `if [ "{repo_type}" = app ]` branch simply falls through to the platform path) — without tripping
    # the missing-arg guard below.
    for _k in ("repo", "repo_type", "repo_path", "staging_branch", "world_branch",
               "host_repo", "host_path", "clone_path", "clone_target"):
        args.setdefault(_k, "")

    cmd_tpl = manifest.get(op)
    if not cmd_tpl:
        defined = ", ".join(k for k in manifest if isinstance(manifest[k], str)) or "(none)"
        sys.exit(f"adapter '{name}' does not implement '{op}'. Defined ops: {defined}.")

    missing = []
    def _sub(m: "re.Match") -> str:
        k = m.group(1)
        if k not in args:
            missing.append(k)
            return ""
        return args[k]
    cmd = re.sub(r"\{(\w+)\}", _sub, str(cmd_tpl))
    if missing:
        sys.exit(f"op '{op}' needs arg(s) {missing} — call it as `{op} {' '.join(k+'=...' for k in missing)}`.")

    # Run on the brain; the adapter command owns any ssh into the target host. Pass through I/O + code.
    sys.exit(subprocess.run(cmd, shell=True, cwd=ROOT).returncode)


if __name__ == "__main__":
    main()
