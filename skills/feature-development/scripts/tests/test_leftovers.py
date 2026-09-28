#!/usr/bin/env python3
"""skills/feature-development/scripts/leftovers.sh: what a stopped run left, found and cleaned without losing work.

Run: python3 -m unittest discover -s skills/feature-development/scripts/tests
"""

import os
import subprocess
import tempfile
import unittest

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "leftovers.sh")
ENV = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.com",
           GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.com")


class Leftovers(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = os.path.realpath(self.tmp.name)
        self.git(self.repo, "init", "-q", "-b", "main")
        self.write(self.repo, "a.py", "a = 1\n")
        self.write(self.repo, ".gitignore", ".claude/worktrees/\n.claude/state/\n")
        self.git(self.repo, "add", "-A")
        self.git(self.repo, "commit", "-qm", "init")

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, cwd, *args):
        return subprocess.run(["git", "-C", cwd, *args], check=True, capture_output=True, text=True, env=ENV).stdout

    def write(self, root, rel, text):
        path = os.path.join(root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(text)

    def unit(self, name, base="HEAD"):
        wt = os.path.join(self.repo, ".claude", "worktrees", name)
        self.git(self.repo, "worktree", "add", "-q", "-b", f"worktree-{name}", wt, base)
        self.git(self.repo, "worktree", "lock", wt)      # as Claude Code leaves them
        return wt

    def run_script(self, *args):
        r = subprocess.run(["bash", SCRIPT, *args], cwd=self.repo, capture_output=True, text=True, env=ENV)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout

    def worktrees(self):
        return [l for l in self.git(self.repo, "worktree", "list").splitlines()[1:] if l.strip()]

    def test_nothing_left_behind(self):
        self.assertIn("Nothing left behind.", self.run_script("list"))

    def test_list_shows_each_unit_and_snapshot(self):
        wt = self.unit("agent-u1")
        self.write(wt, "b.py", "b\n")
        self.git(self.repo, "update-ref", "refs/adk/waves/2", "HEAD")
        out = self.run_script("list")
        self.assertIn("worktree .claude/worktrees/agent-u1  branch worktree-agent-u1  own commits 0  uncommitted 1", out)
        self.assertIn("snapshot refs/adk/waves/2", out)

    def test_clean_removes_what_holds_nothing_and_keeps_work(self):
        self.unit("agent-empty")
        busy = self.unit("agent-busy")
        self.write(busy, "b.py", "b\n")                  # a run may still be going here
        self.git(self.repo, "update-ref", "refs/adk/waves/2", "HEAD")
        out = self.run_script("clean")
        self.assertIn("removed .claude/worktrees/agent-empty and branch worktree-agent-empty", out)
        self.assertIn("kept .claude/worktrees/agent-busy", out)
        self.assertEqual(len(self.worktrees()), 1)
        self.assertIn("refs/adk/waves/2", self.git(self.repo, "for-each-ref", "refs/adk/"))  # a unit is left

    def test_clean_all_keeps_the_work_itself(self):
        dirty = self.unit("agent-dirty")
        self.write(dirty, "new.py", "n\n")
        committed = self.unit("agent-committed")
        self.write(committed, "c.py", "c\n")
        self.git(committed, "add", "-A")
        self.git(committed, "commit", "-qm", "WIP U3")
        self.git(self.repo, "update-ref", "refs/adk/waves/2", "HEAD")
        out = self.run_script("clean", "--all")
        self.assertEqual(self.worktrees(), [])
        patch = os.path.join(self.repo, ".claude", "state", "leftovers", "agent-dirty.patch")
        with open(patch) as f:
            self.assertIn("new.py", f.read())
        self.assertIn("kept branch worktree-agent-committed (1 commit(s) of its own)", out)
        self.assertIn("worktree-agent-committed", self.git(self.repo, "branch"))
        self.assertEqual(self.git(self.repo, "for-each-ref", "refs/adk/"), "")

    def test_a_commit_already_in_a_snapshot_is_not_the_units_own(self):
        self.write(self.repo, "a.py", "a = 2\n")
        snap = subprocess.run(["bash", os.path.join(os.path.dirname(SCRIPT), "snapshot.sh"), "take", "2"],
                              cwd=self.repo, capture_output=True, text=True, env=ENV, check=True).stdout.strip()
        self.unit("agent-u3", base=snap)
        self.assertIn("own commits 0", self.run_script("list"))

    def test_only_the_workflows_own_worktrees_are_touched(self):
        other = os.path.join(self.repo, "..", os.path.basename(self.repo) + "-feature")
        self.git(self.repo, "worktree", "add", "-q", "-b", "feature", other)
        try:
            self.run_script("clean", "--all")
            self.assertTrue(any("feature" in w for w in self.worktrees()))
        finally:
            self.git(self.repo, "worktree", "remove", "-f", other)


if __name__ == "__main__":
    unittest.main()
