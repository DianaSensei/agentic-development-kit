#!/usr/bin/env python3
"""hooks/lane-check-bash.sh: a shell command that writes outside a unit's lane is caught after it runs.

Run: python3 -m unittest discover -s hooks/tests
"""

import json
import os
import subprocess
import tempfile
import unittest

HOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lane-check-bash.sh")
AGENT = "adk-adlc:unit-implementer"
ENV = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.com",
           GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.com")


class LaneCheckBashTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.lead = os.path.realpath(self.tmp.name)
        self.git(self.lead, "init", "-q")
        for f in ["src/shop/orders.py", "src/shop/dashboard.py", ".gitignore"]:
            self.write(self.lead, f, "__pycache__/\nbuild/\n" if f == ".gitignore" else "x = 1\n")
        self.git(self.lead, "add", "-A")
        self.git(self.lead, "commit", "-qm", "init")
        self.base = self.git(self.lead, "rev-parse", "HEAD").strip()
        self.wt = os.path.join(self.lead, ".claude", "worktrees", "agent-u2")
        self.git(self.lead, "worktree", "add", "-q", "-b", "u2", self.wt)
        self.prompt("src/shop/orders.py")

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, cwd, *args):
        return subprocess.run(["git", "-C", cwd, *args], check=True, capture_output=True, text=True, env=ENV).stdout

    def write(self, root, rel, text):
        path = os.path.join(root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(text)

    def prompt(self, *lane, base=None):
        sub = os.path.join(self.lead, "transcripts", "s", "subagents")
        os.makedirs(sub, exist_ok=True)
        text = f"unit: U2\nlane: {json.dumps(list(lane))}\nbase_commit: {base or self.base}\nticket: {{}}\n"
        with open(os.path.join(sub, "agent-a1.jsonl"), "w") as f:
            f.write(json.dumps({"type": "user", "message": {"role": "user", "content": text}}) + "\n")

    def run_hook(self, agent=AGENT, mode=None):
        if mode:
            self.write(self.lead, ".claude/quality-check.config.json", json.dumps({"mode": {"lane_guard": mode}}))
        env = dict(os.environ, CLAUDE_PROJECT_DIR=self.lead)
        env.pop("QUALITY_CHECK_MODE", None)
        payload = {"session_id": "s", "hook_event_name": "PostToolUse", "tool_name": "Bash", "cwd": self.wt,
                   "transcript_path": os.path.join(self.lead, "transcripts", "s.jsonl"),
                   "tool_input": {"command": "whatever"}, "agent_id": "a1", "agent_type": agent}
        out = subprocess.run(["bash", HOOK], input=json.dumps(payload), capture_output=True, text=True,
                             env=env, timeout=30)
        if not out.stdout.strip():
            return "quiet", ""
        o = json.loads(out.stdout)
        return ("block", o["reason"]) if o.get("decision") == "block" else ("warn", o.get("systemMessage", ""))

    def test_changes_inside_the_lane_are_quiet(self):
        self.write(self.wt, "src/shop/orders.py", "x = 2\n")
        self.assertEqual(self.run_hook(), ("quiet", ""))

    def test_a_sed_i_on_another_units_file_is_named(self):
        self.write(self.wt, "src/shop/dashboard.py", "x = 3\n")   # what `sed -i` would leave
        decision, reason = self.run_hook()
        self.assertEqual(decision, "block")
        self.assertIn("- `src/shop/dashboard.py`", reason)
        self.assertIn("git checkout --", reason)
        self.assertIn("outside_files_needed", reason)

    def test_a_new_file_outside_the_lane_is_named_and_ignored_output_is_not(self):
        self.write(self.wt, "src/shop/generated.py", "y = 1\n")
        self.write(self.wt, "build/out.bin", "z")                  # ignored: never counts
        self.write(self.wt, "src/shop/__pycache__/orders.pyc", "z")
        decision, reason = self.run_hook()
        self.assertEqual(decision, "block")
        self.assertIn("src/shop/generated.py", reason)
        self.assertNotIn("build/", reason)
        self.assertNotIn("__pycache__", reason)

    def test_a_commit_carrying_a_stray_file_is_caught(self):
        self.write(self.wt, "src/shop/orders.py", "x = 2\n")
        self.write(self.wt, "src/shop/dashboard.py", "x = 3\n")
        self.git(self.wt, "add", "-A")
        self.git(self.wt, "commit", "-qm", "U2")
        decision, reason = self.run_hook()
        self.assertEqual(decision, "block")
        self.assertIn("src/shop/dashboard.py", reason)
        self.assertNotIn("src/shop/orders.py", reason)

    def test_reported_once_per_set_of_stray_paths(self):
        self.write(self.wt, "src/shop/dashboard.py", "x = 3\n")
        self.assertEqual(self.run_hook()[0], "block")
        self.assertEqual(self.run_hook(), ("quiet", ""))
        self.write(self.wt, "src/shop/other.py", "o\n")            # a new stray: reported again
        self.assertEqual(self.run_hook()[0], "block")

    def test_other_callers_and_unknown_lanes_are_left_alone(self):
        self.write(self.wt, "src/shop/dashboard.py", "x = 3\n")
        self.assertEqual(self.run_hook(agent="adk-adlc:bulk-reader"), ("quiet", ""))
        self.prompt()                                               # empty lane: lane-guard warns, this stays quiet
        self.assertEqual(self.run_hook(), ("quiet", ""))

    def test_warn_mode(self):
        self.write(self.wt, "src/shop/dashboard.py", "x = 3\n")
        decision, msg = self.run_hook(mode="warn")
        self.assertEqual(decision, "warn")
        self.assertIn("src/shop/dashboard.py", msg)


if __name__ == "__main__":
    unittest.main()
