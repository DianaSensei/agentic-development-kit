#!/usr/bin/env python3
"""hooks/lane-guard.sh: a unit-implementer writes only inside its unit's files, in its own worktree.

Run: python3 -m unittest discover -s hooks/tests
"""

import json
import os
import subprocess
import tempfile
import unittest

HOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lane-guard.sh")
AGENT = "adk-adlc:unit-implementer"


class LaneGuardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.lead = os.path.realpath(self.tmp.name)
        git = ["git", "-C", self.lead, "-c", "user.email=t@example.com", "-c", "user.name=t"]
        subprocess.run(["git", "init", "-q", self.lead], check=True)
        for f in ["src/shop/orders.py", "src/shop/dashboard.py", "tests/test_orders.py"]:
            self.write(self.lead, f, "x = 1\n")
        subprocess.run(git + ["add", "-A"], check=True)
        subprocess.run(git + ["commit", "-qm", "init"], check=True)
        self.wt = os.path.join(self.lead, ".claude", "worktrees", "agent-u2")
        subprocess.run(git + ["worktree", "add", "-q", "-b", "u2", self.wt], check=True)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, root, rel, text):
        path = os.path.join(root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(text)

    def lane(self, *paths, line=None):
        """The unit's dispatch prompt, as its own transcript records it - where the guard reads the lane."""
        sub = os.path.join(self.lead, "transcripts", "s", "subagents")
        os.makedirs(sub, exist_ok=True)
        lane = line if line is not None else "lane: " + json.dumps(list(paths))
        prompt = "unit:\n  id: U2\n  files: [...]\n" + lane + "\nbase_commit: abc\nticket: {...}\n"
        with open(os.path.join(sub, "agent-a1.jsonl"), "w") as f:
            f.write(json.dumps({"type": "user", "isSidechain": True, "agentId": "a1",
                                "message": {"role": "user", "content": prompt}}) + "\n")
            f.write(json.dumps({"type": "user", "message": {"role": "user", "content": "lane: [\"everything/\"]"}}) + "\n")

    def run_hook(self, file_path, agent=AGENT, mode=None, cwd=None, tool="Edit"):
        if mode:
            self.write(self.lead, ".claude/quality-check.config.json", json.dumps({"mode": {"lane_guard": mode}}))
        env = dict(os.environ, CLAUDE_PROJECT_DIR=self.lead)
        env.pop("QUALITY_CHECK_MODE", None)
        payload = {"session_id": "s", "hook_event_name": "PreToolUse", "tool_name": tool,
                   "transcript_path": os.path.join(self.lead, "transcripts", "s.jsonl"),
                   "cwd": cwd or self.wt, "tool_input": {"file_path": file_path}}
        if agent:
            payload.update(agent_id="a1", agent_type=agent)
        out = subprocess.run(["bash", HOOK], input=json.dumps(payload), capture_output=True, text=True,
                             env=env, timeout=30)
        if not out.stdout.strip():
            return "allow", ""
        o = json.loads(out.stdout)
        if o.get("hookSpecificOutput", {}).get("permissionDecision") == "deny":
            return "deny", o["hookSpecificOutput"]["permissionDecisionReason"]
        return "warn", o.get("systemMessage", "")

    def test_a_write_inside_the_lane_passes(self):
        self.lane("src/shop/orders.py")
        self.assertEqual(self.run_hook(os.path.join(self.wt, "src/shop/orders.py")), ("allow", ""))

    def test_a_directory_entry_covers_new_files_under_it(self):
        self.lane("scripts/")
        self.assertEqual(self.run_hook(os.path.join(self.wt, "scripts/backfill/run.py")), ("allow", ""))

    def test_a_write_outside_the_lane_is_denied_with_the_way_out(self):
        self.lane("src/shop/orders.py")
        decision, reason = self.run_hook(os.path.join(self.wt, "src/shop/dashboard.py"))
        self.assertEqual(decision, "deny")
        self.assertIn("`src/shop/dashboard.py` is outside this unit's files (`src/shop/orders.py`)", reason)
        self.assertIn("outside_files_needed", reason)
        self.assertIn("plan_mismatch", reason)

    def test_a_relative_path_is_resolved_against_the_worktree(self):
        self.lane("src/shop/orders.py")
        self.assertEqual(self.run_hook("src/shop/dashboard.py")[0], "deny")
        self.assertEqual(self.run_hook("src/shop/orders.py")[0], "allow")

    def test_the_leads_copy_is_off_limits(self):
        self.lane("src/shop/orders.py")
        decision, reason = self.run_hook(os.path.join(self.lead, "src/shop/orders.py"))
        self.assertEqual(decision, "deny")
        self.assertIn("lead agent's working tree", reason)

    def test_the_lane_is_the_first_lane_line_of_the_units_own_prompt(self):
        # A later message saying otherwise does not widen it.
        self.lane("src/shop/orders.py")
        self.assertEqual(self.run_hook(os.path.join(self.wt, "everything/x.py"))[0], "deny")

    def test_a_markdown_formatted_lane_line_still_counts(self):
        self.lane(line='- **lane**: ["src/shop/orders.py"]')
        self.assertEqual(self.run_hook(os.path.join(self.wt, "src/shop/orders.py"))[0], "allow")
        self.assertEqual(self.run_hook(os.path.join(self.wt, "src/shop/dashboard.py"))[0], "deny")

    def test_an_unreadable_lane_warns_once_and_lets_the_edit_through(self):
        # No transcript where the guard looks: it cannot tell, so it does not block the unit's work.
        decision, msg = self.run_hook(os.path.join(self.wt, "src/shop/orders.py"))
        self.assertEqual(decision, "warn")
        self.assertIn("Could not read this unit's lane", msg)
        self.assertEqual(self.run_hook(os.path.join(self.wt, "src/shop/orders.py")), ("allow", ""))
        # The lead's tree is still off limits.
        self.assertEqual(self.run_hook(os.path.join(self.lead, "src/shop/orders.py"))[0], "deny")

    def test_other_callers_are_never_touched(self):
        # The lead itself (no agent_type), and any other agent, even with no lane anywhere.
        self.assertEqual(self.run_hook(os.path.join(self.lead, "src/shop/orders.py"), agent=None, cwd=self.lead)[0], "allow")
        self.assertEqual(self.run_hook(os.path.join(self.wt, "x.py"), agent="adk-adlc:bulk-reader")[0], "allow")

    def test_paths_outside_both_trees_are_left_alone(self):
        self.lane("src/shop/orders.py")
        with tempfile.TemporaryDirectory() as scratch:
            self.assertEqual(self.run_hook(os.path.join(scratch, "notes.md"))[0], "allow")

    def test_warn_and_off(self):
        self.lane("src/shop/orders.py")
        outside = os.path.join(self.wt, "src/shop/dashboard.py")
        decision, msg = self.run_hook(outside, mode="warn")
        self.assertEqual(decision, "warn")
        self.assertIn("outside this unit's files", msg)
        self.assertEqual(self.run_hook(outside, mode="off"), ("allow", ""))

    def test_notebooks_are_guarded_too(self):
        self.lane("src/shop/orders.py")
        env = dict(os.environ, CLAUDE_PROJECT_DIR=self.lead)
        payload = {"agent_type": AGENT, "agent_id": "a1", "session_id": "s", "cwd": self.wt,
                   "transcript_path": os.path.join(self.lead, "transcripts", "s.jsonl"), "tool_name": "NotebookEdit",
                   "tool_input": {"notebook_path": os.path.join(self.wt, "nb/analysis.ipynb")}}
        out = subprocess.run(["bash", HOOK], input=json.dumps(payload), capture_output=True, text=True, env=env)
        self.assertIn('"deny"', out.stdout)


if __name__ == "__main__":
    unittest.main()
