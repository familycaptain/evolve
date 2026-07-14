"""Engine test: the C/F/S store (engine/store.py).

Covers the "edit-serialize" round-trip (a record -> its YAML file -> back, with
state and content preserved — the gate-relevant `state` must survive) and the
"boot-sync" projection integrity rule (a corpus with hard errors is REFUSED and
the existing projection is left untouched — a bad edit can't wipe good data).

Hermetic: a synthetic specs tree in a tmpdir + the in-memory / :memory: sqlite
backends the store already ships. No network, no git, no domain-specific shapes.

Run: python -m unittest engine.tests.test_store   (from the repo root)
"""
import os
import sys
import tempfile
import textwrap
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from engine import schema, store  # noqa: E402


def _write(root, rel, text):
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(textwrap.dedent(text).lstrip("\n"))
    return path


def _valid_tree(root):
    """A synthetic, well-formed capability/feature/specification corpus."""
    _write(root, "_capability.yaml", """
        kind: capability
        id: demo
        title: Demo
    """)
    _write(root, "thing/_feature.yaml", """
        kind: feature
        id: demo.thing
        title: Thing
    """)
    _write(root, "thing/widget.yaml", """
        kind: specification
        id: demo.thing.widget
        title: Widget
        state: implementing
        behavior: does a thing
        tests:
          - path: t/test_widget.py
    """)


class SerializeRoundTrip(unittest.TestCase):
    def test_serialize_is_deterministic_and_canonically_ordered(self):
        raw = {"title": "Widget", "kind": "specification", "id": "demo.thing.widget",
               "state": "implementing", "behavior": "does a thing"}
        out = store.serialize_record(raw)
        # canonical key order (kind, id, title, ... state ...) regardless of input order
        self.assertLess(out.index("kind:"), out.index("id:"))
        self.assertLess(out.index("id:"), out.index("title:"))
        self.assertEqual(out, store.serialize_record(dict(reversed(list(raw.items())))))

    def test_write_then_parse_preserves_state_and_content(self):
        with tempfile.TemporaryDirectory() as d:
            r = schema.Record(
                kind="specification", id="demo.thing.widget", title="Widget",
                path=os.path.join(d, "widget.yaml"), state="implementing",
                raw={"kind": "specification", "id": "demo.thing.widget", "title": "Widget",
                     "state": "implementing", "behavior": "does a thing"})
            before = r.content_checksum()
            store.write_record_file(r)
            back = schema.parse_file(r.path)
            # the gate-relevant state survives the file round-trip
            self.assertEqual(back.state, "implementing")
            self.assertEqual(back.behavior, "does a thing")
            self.assertEqual(back.content_checksum(), before)


class BootSyncProjection(unittest.TestCase):
    def test_projects_a_valid_corpus_into_both_backends(self):
        for backend in (store.InMemoryBackend(), store.SqliteBackend(":memory:")):
            with tempfile.TemporaryDirectory() as d:
                _valid_tree(d)
                st = store.Store(backend)
                rep = st.boot_sync(d, repo_root=d, capability="demo", bootstrap=True)
                self.assertTrue(rep.ok, rep)
                self.assertEqual(len(st.all()), 3)
                self.assertEqual([r["id"] for r in st.by_kind("specification")],
                                 ["demo.thing.widget"])
                self.assertEqual(st.tree(), {"demo": {"demo.thing": ["demo.thing.widget"]}})
                # projected checksum matches the record's own content checksum
                rec = schema.parse_file(os.path.join(d, "thing/widget.yaml"))
                self.assertEqual(st.get("demo.thing.widget")["checksum"],
                                 rec.content_checksum())

    def test_a_broken_corpus_is_refused_and_leaves_the_projection_untouched(self):
        with tempfile.TemporaryDirectory() as good, tempfile.TemporaryDirectory() as bad:
            st = store.Store(store.InMemoryBackend())
            _valid_tree(good)
            self.assertTrue(st.boot_sync(good, repo_root=good, capability="demo",
                                         bootstrap=True).ok)
            self.assertEqual(len(st.all()), 3)

            # a corpus with a hard error (spec with no behavior + a bad state)
            _write(bad, "_capability.yaml", "kind: capability\nid: demo\ntitle: Demo\n")
            _write(bad, "thing/_feature.yaml", "kind: feature\nid: demo.thing\ntitle: T\n")
            _write(bad, "thing/widget.yaml",
                   "kind: specification\nid: demo.thing.widget\ntitle: W\nstate: bogus\n")
            rep = st.boot_sync(bad, repo_root=bad, capability="demo", bootstrap=True)
            self.assertFalse(rep.ok)
            # the good projection is intact — the refused sync did NOT clear it
            self.assertEqual(len(st.all()), 3)
            self.assertEqual(st.get("demo.thing.widget")["state"], "implementing")


if __name__ == "__main__":
    unittest.main()
