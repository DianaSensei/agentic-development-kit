#!/usr/bin/env python3
"""skills/feature-development/scripts/snapshot.sh: a wave's base commit, off every branch.

Run: python3 -m unittest discover -s skills/feature-development/scripts/tests
"""

import os
import subprocess
import tempfile
import unittest

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "snapshot.sh")
ENV = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.com",
           GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.com")


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = self.tmp.name
        self.git("init", "-q", "-b", "main")
        self.write("src/a.py", "a = 1\n")
        self.write(".gitignore", "build/\n")
        self.git("add", "-A")
        self.git("commit", "-qm", "init")
        self.head = self.git("rev-parse", "HEAD").strip()

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, *args):
        return subprocess.run(["git", "-C", self.repo, *args], check=True, capture_output=True, text=True,
                              env=ENV).stdout

    def write(self, rel, text):
        path = os.path.join(self.repo, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(text)

    def snap(self, *args):
        return subprocess.run(["bash", SCRIPT, *args], cwd=self.repo, check=True, capture_output=True,
                              text=True, env=ENV).stdout.strip()

    def test_snapshot_holds_the_working_tree_and_leaves_branch_and_index_alone(self):
        self.write("src/a.py", "a = 2\n")            # modified, unstaged
        self.write("src/b.py", "b = 1\n")            # untracked
        self.write("src/c.py", "c = 1\n")
        self.git("add", "src/c.py")                   # staged by the user
        self.write("build/out.bin", "x")             # ignored
        status_before = self.git("status", "--porcelain")
        sha = self.snap("take", "1")
        self.assertEqual(self.git("show", f"{sha}:src/a.py"), "a = 2\n")
        self.assertEqual(self.git("show", f"{sha}:src/b.py"), "b = 1\n")
        self.assertEqual(self.git("show", f"{sha}:src/c.py"), "c = 1\n")
        self.assertNotIn("build/out.bin", self.git("ls-tree", "-r", "--name-only", sha))
        self.assertEqual(self.git("rev-parse", f"{sha}^").strip(), self.head)
        self.assertEqual(self.git("rev-parse", "HEAD").strip(), self.head)       # branch unmoved
        self.assertEqual(self.git("status", "--porcelain"), status_before)       # index untouched
        self.assertEqual(self.git("rev-parse", "refs/adk/waves/1").strip(), sha)

    def test_the_kits_worktrees_and_state_stay_out(self):
        self.write(".claude/worktrees/agent-x/src/z.py", "z\n")
        self.write(".claude/state/reviewed", "h\n")
        sha = self.snap("take", "1")
        names = self.git("ls-tree", "-r", "--name-only", sha)
        self.assertNotIn(".claude/worktrees", names)
        self.assertNotIn(".claude/state", names)

    def test_a_worktree_can_start_from_it_and_its_diff_applies_to_the_tree(self):
        self.write("src/a.py", "a = 2\n")
        sha = self.snap("take", "1")
        wt = os.path.join(self.repo, ".claude", "worktrees", "u3")
        self.git("worktree", "add", "-q", "-b", "u3", wt, sha)
        with open(os.path.join(wt, "src", "a.py"), "a") as f:
            f.write("a3 = 3\n")
        subprocess.run(["git", "-C", wt, "commit", "-qam", "u3"], check=True, env=ENV, capture_output=True)
        patch = self.git("diff", "--binary", sha, "u3")
        subprocess.run(["git", "-C", self.repo, "apply", "--check", "-"], input=patch, check=True, text=True)

    def test_drop_removes_every_wave_ref(self):
        self.snap("take", "1")
        self.write("src/a.py", "a = 3\n")
        self.snap("take", "2")
        self.snap("drop")
        self.assertEqual(self.git("for-each-ref", "refs/adk/"), "")


if __name__ == "__main__":
    unittest.main()
