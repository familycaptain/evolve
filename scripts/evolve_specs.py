#!/usr/bin/env python3
"""Validate EVERY specification corpus in a target repo, not one at a time.

`python3 -m engine.schema <root>` validates a single corpus. Nothing validated all of them, and
that gap hid real breakage for a long time: an orphaned spec (a feature directory with no
`_feature.yaml`) is a hard error that fails its WHOLE capability, so one missing file can take a
corpus out of the loader entirely — and nobody notices, because no one runs the validator against
that root by hand. A survey of one target product found five capabilities in exactly that state,
all from the same shape of mistake, plus records so broken the scanner skipped them silently.

Usage:
    scripts/evolve_specs.py [repo_path] [--quiet] [--warnings]

Exits non-zero if any corpus has an error, so it works as a pre-commit or CI gate.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.schema import (  # noqa: E402
    capability_from_root,
    corpus_roots,
    load_and_validate,
)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("repo", nargs="?", default=os.getcwd(),
                    help="target repo root (default: cwd)")
    ap.add_argument("--quiet", action="store_true",
                    help="only print corpora that have errors")
    ap.add_argument("--warnings", action="store_true",
                    help="also print warnings (off by default — they are advisory)")
    args = ap.parse_args()

    repo = os.path.abspath(args.repo)
    roots = corpus_roots(repo)
    if not roots:
        print(f"no specification corpora found under {repo}")
        return 0

    total_records = total_specs = total_errors = total_warnings = 0
    failed: list[str] = []

    for root in roots:
        rel = os.path.relpath(root, repo)
        cap = capability_from_root(root)
        try:
            records, rep = load_and_validate(root, repo_root=repo, capability=cap)
        except Exception as exc:  # a corpus that cannot even load is the loudest failure there is
            print(f"{rel:38s}  LOAD FAILED  {type(exc).__name__}: {str(exc)[:120]}")
            failed.append(rel)
            total_errors += 1
            continue

        specs = sum(1 for r in records if r.kind == "specification")
        total_records += len(records)
        total_specs += specs
        total_errors += len(rep.errors)
        total_warnings += len(rep.warnings)
        if not rep.ok:
            failed.append(rel)

        if rep.ok and args.quiet:
            continue
        status = "ok" if rep.ok else f"FAIL ({len(rep.errors)})"
        print(f"{rel:38s}  {len(records):5d} rec  {specs:5d} spec  {status}")
        for e in rep.errors:
            print(f"      ERROR  {e}")
        if args.warnings:
            for w in rep.warnings:
                print(f"      warn   {w}")

    print()
    print(f"{len(roots)} corpora · {total_records} records · {total_specs} specifications · "
          f"{total_errors} errors · {total_warnings} warnings")
    if failed:
        print(f"corpora with errors ({len(failed)}): {', '.join(failed)}")
        return 1
    print("every corpus validates.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
