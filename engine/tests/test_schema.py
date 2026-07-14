"""Engine test: the C/F/S schema validator (engine/schema.py).

Domain-agnostic by construction — the fixtures are a synthetic
capability/feature/specification tree ("demo.thing.widget"), never anything about
the project the engine happens to be evolving (no web/DB/app-specific shapes).
Pure: no disk, no network, no git; Records are built in memory with paths derived
to match their ids so each test isolates one validation rule.

Run: python -m unittest engine.tests.test_schema   (from the repo root)
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from engine import schema  # noqa: E402

# A synthetic specs tree root + capability. Nothing is written to disk; these are
# just the strings path_derived_id() does relative arithmetic against.
ROOT = "/synthetic/specs/demo"
CAP = "demo"
REPO = "/synthetic/repo"


def _path_for(kind: str, rid: str) -> str:
    """The on-disk path an id *should* live at, so a well-formed record passes the
    id<->path rule by default (lets other rules be tested in isolation)."""
    parts = rid.split(".")
    if kind == "capability" or len(parts) == 1:
        return f"{ROOT}/_capability.yaml"
    if kind == "feature" or len(parts) == 2:
        return f"{ROOT}/{parts[1]}/_feature.yaml"
    return f"{ROOT}/{parts[1]}/{parts[2]}.yaml"


def rec(kind: str, rid: str, *, path: str | None = None, title: str = "T",
        state: str = "proposed", **raw) -> schema.Record:
    body = {"kind": kind, "id": rid, "title": title, "state": state, **raw}
    return schema.Record(kind=kind, id=rid, title=title,
                         path=path or _path_for(kind, rid), state=state, raw=body)


def parents():
    return [rec("capability", "demo"), rec("feature", "demo.thing")]


def spec(**over):
    body = dict(behavior="does a thing", tests=[{"path": "t/test_widget.py"}])
    body.update(over)
    return rec("specification", "demo.thing.widget", **body)


def check(records, **kw):
    return schema.validate(records, specs_root=ROOT, repo_root=REPO, capability=CAP, **kw)


def _has(msgs, needle):
    return any(needle in m for m in msgs)


class ValidCorpus(unittest.TestCase):
    def test_a_well_formed_corpus_passes_clean(self):
        rep = check(parents() + [spec()])
        self.assertTrue(rep.ok, rep)
        self.assertEqual(rep.errors, [])


class Errors(unittest.TestCase):
    def test_invalid_kind(self):
        rep = check([rec("gizmo", "demo.thing.widget", path=f"{ROOT}/x.yaml")])
        self.assertTrue(_has(rep.errors, "invalid kind 'gizmo'"))

    def test_missing_id(self):
        rep = check([rec("specification", "", path=f"{ROOT}/x.yaml")])
        self.assertTrue(_has(rep.errors, "missing id"))

    def test_duplicate_id(self):
        rep = check(parents() + [spec(), spec()])
        self.assertTrue(_has(rep.errors, "duplicate id 'demo.thing.widget'"))

    def test_id_depth_must_match_kind(self):
        rep = check(parents() + [rec("feature", "demo.thing.toodeep")])
        self.assertTrue(_has(rep.errors, "id depth != kind"))

    def test_id_must_match_path(self):
        wrong = rec("specification", "demo.thing.widget",
                    path=f"{ROOT}/thing/somethingelse.yaml", behavior="b")
        rep = check(parents() + [wrong])
        self.assertTrue(_has(rep.errors, "id != path-derived"))

    def test_invalid_state(self):
        rep = check(parents() + [spec(state="halfbaked")])
        self.assertTrue(_has(rep.errors, "invalid state 'halfbaked'"))

    def test_non_resting_state_rejected_on_main(self):
        # proposed is a valid file state, but only live/deprecated may sit on main.
        rep = check(parents() + [spec(state="proposed")], on_main=True, bootstrap=False)
        self.assertTrue(_has(rep.errors, "on main"))
        # ...and bootstrap suspends that invariant for hand-authored seeds.
        rep2 = check(parents() + [spec(state="proposed")], on_main=True, bootstrap=True)
        self.assertFalse(_has(rep2.errors, "on main"))

    def test_invalid_autonomy(self):
        rep = check(parents() + [spec(autonomy="whenever")])
        self.assertTrue(_has(rep.errors, "invalid autonomy 'whenever'"))

    def test_missing_parent(self):
        rep = check([spec()])  # no capability/feature above it
        self.assertTrue(_has(rep.errors, "parent 'demo.thing' not found"))

    def test_specification_requires_behavior(self):
        rep = check(parents() + [spec(behavior="")])
        self.assertTrue(_has(rep.errors, "has no `behavior`"))

    def test_verified_requires_bound_tests(self):
        rep = check(parents() + [spec(verified=True, tests=[])])
        self.assertTrue(_has(rep.errors, "marked verified but has no bound tests"))


class Warnings(unittest.TestCase):
    def test_missing_title_warns(self):
        rep = check(parents() + [spec(title="")])
        self.assertTrue(rep.ok, rep)                      # advisory only
        self.assertTrue(_has(rep.warnings, "missing title"))

    def test_untested_spec_warns(self):
        rep = check(parents() + [spec(tests=[])])
        self.assertTrue(rep.ok, rep)
        self.assertTrue(_has(rep.warnings, "untested variance"))

    def test_unresolved_link_warns(self):
        rep = check(parents() + [spec(links={"related": ["demo.thing.ghost"]})])
        self.assertTrue(rep.ok, rep)
        self.assertTrue(_has(rep.warnings, "links.related -> 'demo.thing.ghost' unresolved"))


class Checksum(unittest.TestCase):
    def test_checksum_is_content_addressed_and_order_stable(self):
        a = rec("specification", "demo.thing.widget", behavior="b", tests=[{"path": "t.py"}])
        # same content, keys inserted in a different order -> same checksum
        b = schema.Record(kind="specification", id="demo.thing.widget", title="T",
                          path=a.path, state="proposed",
                          raw={"tests": [{"path": "t.py"}], "behavior": "b",
                               "state": "proposed", "title": "T", "id": "demo.thing.widget",
                               "kind": "specification"})
        self.assertEqual(a.content_checksum(), b.content_checksum())
        # a semantic change moves the checksum
        c = rec("specification", "demo.thing.widget", behavior="b DIFFERENT",
                tests=[{"path": "t.py"}])
        self.assertNotEqual(a.content_checksum(), c.content_checksum())


if __name__ == "__main__":
    unittest.main()
