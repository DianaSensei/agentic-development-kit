#!/usr/bin/env python3
"""hooks/quick-change-scope.sh: a quick change that outgrew the quick path is sent back.

Run: python3 -m unittest discover -s hooks/tests
"""

import json
import os
import subprocess
import tempfile
import unittest

HOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "quick-change-scope.sh")


class QuickChangeScopeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.project = self.tmp.name
        git = ["git", "-C", self.project, "-c", "user.email=t@example.com", "-c", "user.name=t"]
        subprocess.run(["git", "init", "-q", self.project], check=True)
        for f in ["src/a.py", "src/b.py", "src/c.py", "src/d.py"]:
            self.write(f, "x = 1\n")
        subprocess.run(git + ["add", "-A"], check=True)
        subprocess.run(git + ["commit", "-qm", "init"], check=True)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, rel, text):
        path = os.path.join(self.project, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(text)

    def config(self, cfg):
        self.write(".claude/quality-check.config.json", json.dumps(cfg))

    def run_hook(self, mode=None):
        if mode:
            self.config({"mode": {"quick_change_scope": mode}})
        env = dict(os.environ, CLAUDE_PROJECT_DIR=self.project)
        env.pop("QUALITY_CHECK_MODE", None)
        out = subprocess.run(["bash", HOOK], input=json.dumps({"session_id": "s", "stop_hook_active": False}),
                             capture_output=True, text=True, env=env, timeout=60)
        msg = json.loads(out.stdout)["systemMessage"] if out.stdout.strip() else ""
        return out.returncode, msg + out.stderr

    def test_a_small_local_change_passes(self):
        self.write("src/a.py", "x = 2\n")
        self.assertEqual(self.run_hook(), (0, ""))

    def test_too_many_files(self):
        for f in ["src/a.py", "src/b.py", "src/c.py", "src/d.py"]:
            self.write(f, "x = 2\n")
        rc, msg = self.run_hook()
        self.assertEqual(rc, 0)
        self.assertIn("4 files changed (the quick path allows 3)", msg)
        self.assertIn("workflow-router", msg)

    def test_too_many_lines_counts_new_files_too(self):
        self.write("src/new.py", "y = 1\n" * 70)
        rc, msg = self.run_hook()
        self.assertIn("70 lines changed (the quick path allows 60)", msg)

    def test_sensitive_paths(self):
        for path in ["db/migrations/0002_add.sql", "src/auth/session.py", "src/payments.py",
                     ".github/workflows/ci.yml", "api/openapi.yaml", "package.json", "requirements-dev.txt"]:
            with self.subTest(path=path):
                self.tearDown()
                self.setUp()
                self.write(path, "a\n")
                self.assertIn(f"`{path}`", self.run_hook()[1])

    def test_an_ordinary_name_is_not_sensitive(self):
        self.write("src/author_list.py", "a\n")  # "author", not "auth/"
        self.assertEqual(self.run_hook()[1], "")

    def test_block_mode_sends_claude_back(self):
        self.write("src/payments.py", "a\n")
        rc, msg = self.run_hook(mode="block")
        self.assertEqual(rc, 2)
        self.assertIn("outgrew the quick path", msg)

    def test_reported_once_per_state_of_the_diff(self):
        self.write("src/payments.py", "a\n")
        self.assertIn("outgrew", self.run_hook()[1])
        self.assertEqual(self.run_hook()[1], "")
        self.write("src/payments.py", "b\n")
        self.assertIn("outgrew", self.run_hook()[1])

    def test_project_limits(self):
        self.config({"quick_change": {"max_files": 1, "max_lines": 1, "sensitive_paths": ["^docs/"]}})
        self.write("src/a.py", "x = 2\n")
        self.write("src/b.py", "x = 2\n")
        msg = self.run_hook()[1]
        self.assertIn("files changed (the quick path allows 1)", msg)
        self.tearDown()
        self.setUp()
        self.config({"quick_change": {"sensitive_paths": ["^docs/"]}})
        self.write("src/payments.py", "a\n")  # the default list is replaced, not extended
        self.assertNotIn("payments", self.run_hook()[1])

    def test_the_kits_own_state_does_not_count(self):
        self.write(".claude/state/reviewed", "abc\n")
        self.write("src/a.py", "x = 2\n")
        self.assertEqual(self.run_hook()[1], "")


if __name__ == "__main__":
    unittest.main()
