#!/usr/bin/env python3
"""hooks/dispatch-gate.sh: a unit is handed down only after the rules are read, with what it needs.

Run: python3 -m unittest discover -s hooks/tests
"""

import json
import os
import subprocess
import tempfile
import unittest

HOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "dispatch-gate.sh")
GOOD_PROMPT = """unit:
  id: U2
  files: ["src/shop/orders.py"]
lane: ["src/shop/orders.py"]
ticket: {"id": "task-2", "interface": ["..."]}
plan_excerpt: ...
base_commit: 42ebe0d
"""


class DispatchGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.project = self.tmp.name
        self.transcript = os.path.join(self.project, "session.jsonl")
        self.record(read=None)

    def tearDown(self):
        self.tmp.cleanup()

    def record(self, read):
        lines = [{"type": "user", "message": {"role": "user", "content": "build it"}}]
        if read:
            lines.append({"type": "assistant", "message": {"role": "assistant", "content": [
                {"type": "tool_use", "name": "Read", "input": {"file_path": read}}]}})
        with open(self.transcript, "w") as f:
            f.write("\n".join(json.dumps(l) for l in lines) + "\n")

    def run_hook(self, prompt=GOOD_PROMPT, agent="adk-adlc:unit-implementer", mode=None):
        if mode:
            os.makedirs(os.path.join(self.project, ".claude"), exist_ok=True)
            with open(os.path.join(self.project, ".claude", "quality-check.config.json"), "w") as f:
                json.dump({"mode": {"dispatch_gate": mode}}, f)
        env = dict(os.environ, CLAUDE_PROJECT_DIR=self.project)
        env.pop("QUALITY_CHECK_MODE", None)
        payload = {"session_id": "s", "transcript_path": self.transcript, "tool_name": "Agent",
                   "tool_input": {"subagent_type": agent, "description": "U2", "prompt": prompt}}
        out = subprocess.run(["bash", HOOK], input=json.dumps(payload), capture_output=True, text=True,
                             env=env, timeout=30)
        if not out.stdout.strip():
            return "allow", ""
        o = json.loads(out.stdout)
        if o.get("hookSpecificOutput", {}).get("permissionDecision") == "deny":
            return "deny", o["hookSpecificOutput"]["permissionDecisionReason"]
        return "warn", o.get("systemMessage", "")

    def read_the_rules(self):
        self.record("/root/.claude/plugins/cache/m/adk-adlc/0.17.0/skills/feature-development/references/parallel-units.md")

    def test_a_prepared_dispatch_goes_out(self):
        self.read_the_rules()
        self.assertEqual(self.run_hook(), ("allow", ""))

    def test_dispatching_without_reading_the_rules_is_denied(self):
        # What a headless run did: no snapshot, no inline ticket, a commit on the user's branch.
        decision, reason = self.run_hook()
        self.assertEqual(decision, "deny")
        self.assertIn("references/parallel-units.md", reason)
        self.assertIn("never committing on the user's branch", reason)

    def test_the_lane_must_be_a_json_array_of_paths(self):
        self.read_the_rules()
        for bad in ["lane: src/shop/orders.py", "lane: []", ""]:
            prompt = GOOD_PROMPT.replace('lane: ["src/shop/orders.py"]', bad)
            decision, reason = self.run_hook(prompt)
            self.assertEqual(decision, "deny", bad)
            self.assertIn("`lane:` line", reason)
        self.assertEqual(self.run_hook(GOOD_PROMPT.replace("lane:", "**lane**:"))[0], "allow")

    def test_the_ticket_and_base_commit_are_required(self):
        self.read_the_rules()
        decision, reason = self.run_hook(GOOD_PROMPT.replace("ticket:", "notes:").replace("base_commit:", "base:"))
        self.assertEqual(decision, "deny")
        self.assertIn("`ticket:`", reason)
        self.assertIn("`base_commit:`", reason)

    def test_a_compare_builds_candidate_needs_no_ticket(self):
        self.read_the_rules()
        prompt = GOOD_PROMPT.replace("ticket:", "candidate:")
        self.assertEqual(self.run_hook(prompt), ("allow", ""))

    def test_other_agents_are_never_touched(self):
        self.assertEqual(self.run_hook(prompt="anything", agent="adk-adlc:solution-architect"), ("allow", ""))
        self.assertEqual(self.run_hook(prompt="anything", agent="Explore"), ("allow", ""))

    def test_warn_and_off(self):
        self.assertEqual(self.run_hook(mode="warn")[0], "warn")
        self.assertEqual(self.run_hook(mode="off"), ("allow", ""))


if __name__ == "__main__":
    unittest.main()
