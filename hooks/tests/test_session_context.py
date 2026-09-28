#!/usr/bin/env python3
"""hooks/session-context.sh: the session starts knowing what an earlier stopped run left behind.

Run: python3 -m unittest discover -s hooks/tests
"""

import json
import os
import subprocess
import tempfile
import unittest

KIT = os.path.realpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
HOOK = os.path.join(KIT, "hooks", "session-context.sh")
ENV = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.com",
           GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.com")


class SessionContextLeftovers(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = os.path.realpath(self.tmp.name)
        self.git("init", "-q")
        os.makedirs(os.path.join(self.repo, ".claude"))
        with open(os.path.join(self.repo, ".claude", "quality-check.config.json"), "w") as f:
            json.dump({}, f)                                   # the project opted in
        self.git("add", "-A")
        self.git("commit", "-qm", "init")

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, *args):
        return subprocess.run(["git", "-C", self.repo, *args], check=True, capture_output=True, text=True, env=ENV).stdout

    def run_hook(self):
        env = dict(ENV, CLAUDE_PROJECT_DIR=self.repo, CLAUDE_PLUGIN_ROOT=KIT, HOME=self.repo)
        env.pop("QUALITY_CHECK_MODE", None)
        out = subprocess.run(["bash", HOOK], input=json.dumps({"session_id": "s", "hook_event_name": "SessionStart"}),
                             capture_output=True, text=True, env=env, timeout=30)
        return out.stdout

    def test_no_notice_when_nothing_is_left(self):
        self.assertNotIn("unit worktree", self.run_hook())

    def test_a_left_worktree_and_snapshot_are_announced_with_the_way_to_look(self):
        wt = os.path.join(self.repo, ".claude", "worktrees", "agent-u2")
        self.git("worktree", "add", "-q", "-b", "worktree-agent-u2", wt)
        self.git("update-ref", "refs/adk/waves/2", "HEAD")
        out = self.run_hook()
        self.assertIn("1 unit worktree(s) and 1 wave snapshot(s) from an earlier run", out)
        self.assertIn("feature-development/scripts/leftovers.sh list", out)
        self.assertIn("may belong to a run still going", out)


if __name__ == "__main__":
    unittest.main()
