"""Engine test: the git workspace manager (engine/workspace.py).

Two kinds of check, both domain-agnostic:
  * pure path logic — id slugging (a "." / ".." in an id must never reach the
    filesystem), the specs-root / spec-relpath mapping, and worktree CONTAINMENT
    (a crafted relpath can't escape the worktree, incl. the sibling-prefix trick);
  * a real-local-git lifecycle proving a feature worktree is an ISOLATED checkout
    (writing in it doesn't touch the main checkout) and is cleaned up.

Hermetic: tmp dirs + a throwaway `git init` repo with filler content. No origin,
no network, no remote boxes. The repo content is a dummy README — nothing about
the project the engine evolves.

Run: python -m unittest engine.tests.test_workspace   (from the repo root)
"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from engine import workspace  # noqa: E402
from engine.workspace import Feature, GitError, WorkspaceManager  # noqa: E402

_HAS_GIT = shutil.which("git") is not None


class PurePathLogic(unittest.TestCase):
    def test_slug_strips_dots_and_traversal(self):
        for dirty in ("demo.thing.widget", "../escape", "a/b/c", "..", "x.y/../z"):
            s = workspace._slug(dirty)
            self.assertNotIn(".", s)
            self.assertNotIn("/", s)
            self.assertTrue(all(c.isalnum() or c in "-_" for c in s), s)

    def test_specs_root_and_spec_relpath_mapping(self):
        # app capability vs platform-wide capability
        self.assertEqual(workspace.specs_root_for("demo"), "apps/demo/specs")
        self.assertEqual(workspace.specs_root_for("platform"), "specs/platform")
        self.assertEqual(
            workspace.spec_relpath({"id": "demo", "kind": "capability"}),
            "apps/demo/specs/_capability.yaml")
        self.assertEqual(
            workspace.spec_relpath({"id": "demo.thing", "kind": "feature"}),
            "apps/demo/specs/thing/_feature.yaml")
        self.assertEqual(
            workspace.spec_relpath({"id": "demo.thing.widget", "kind": "specification"}),
            "apps/demo/specs/thing/widget.yaml")


class WorktreeContainment(unittest.TestCase):
    def _wm_and_feature(self, tmp):
        wt = os.path.join(tmp, "wt", "foo")
        os.makedirs(wt, exist_ok=True)
        wm = WorkspaceManager(os.path.join(tmp, "repo"), worktrees_dir=os.path.join(tmp, "wt"))
        return wm, Feature("demo.thing.widget", "feature/foo", wt)

    def test_normal_write_lands_inside_the_worktree(self):
        with tempfile.TemporaryDirectory() as tmp:
            wm, feat = self._wm_and_feature(tmp)
            rel = wm.write_file(feat, "sub/note.txt", "content")
            self.assertEqual(rel, "sub/note.txt")
            self.assertTrue(os.path.isfile(os.path.join(feat.path, "sub/note.txt")))

    def test_parent_traversal_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            wm, feat = self._wm_and_feature(tmp)
            with self.assertRaises(GitError):
                wm.write_file(feat, "../evil.txt", "x")

    def test_sibling_prefix_escape_is_rejected(self):
        # /wt/foo-evil startswith /wt/foo — the classic prefix bug. commonpath (not
        # startswith) must catch this.
        with tempfile.TemporaryDirectory() as tmp:
            wm, feat = self._wm_and_feature(tmp)
            with self.assertRaises(GitError):
                wm.write_file(feat, "../foo-evil/pwn.txt", "x")


def _git(d, *args):
    subprocess.run(["git", "-C", d, *args], check=True, capture_output=True, text=True)


def _init_repo(d):
    subprocess.run(["git", "init", "-q", d], check=True, capture_output=True)
    _git(d, "config", "user.email", "t@localhost")
    _git(d, "config", "user.name", "T")
    with open(os.path.join(d, "README.md"), "w", encoding="utf-8") as fh:
        fh.write("filler\n")
    _git(d, "add", "-A")
    _git(d, "commit", "-q", "-m", "init")
    _git(d, "branch", "-M", "main")
    _git(d, "branch", "release")


@unittest.skipUnless(_HAS_GIT, "git not available")
class WorktreeLifecycle(unittest.TestCase):
    def test_feature_worktree_is_isolated_and_cleaned_up(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = os.path.join(tmp, "repo")
            _init_repo(repo)
            wm = WorkspaceManager(repo, worktrees_dir=os.path.join(tmp, "wt"),
                                  release="release", main="main")

            feat = wm.start_feature("demo.thing.widget")
            self.assertTrue(os.path.isdir(feat.path))
            self.assertNotEqual(os.path.realpath(feat.path), os.path.realpath(repo))

            wm.write_file(feat, "sub/note.txt", "hello")
            wm.commit(feat, "add note")
            self.assertFalse(wm.is_dirty(feat))
            self.assertEqual(wm.changed_files(feat), ["sub/note.txt"])

            # isolation: the change lives in the worktree, NOT the main checkout
            self.assertFalse(os.path.exists(os.path.join(repo, "sub/note.txt")))

            wm.finish_feature(feat)
            self.assertFalse(os.path.exists(feat.path))


if __name__ == "__main__":
    unittest.main()
