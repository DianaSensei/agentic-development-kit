#!/usr/bin/env python3
"""hooks/edit-gates.sh, checkpoint half: a gated workflow's code edit waits for its Checkpoint,
unless the change has since moved to a path that has none.

Run: python3 -m unittest discover -s hooks/tests
"""

import json
import os
import subprocess
import tempfile
import unittest

HOOKS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
PLUGIN = os.path.abspath(os.path.join(HOOKS, ".."))


def tool_use(name, **inp):
    return {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": name, "input": inp}]}}


def skill(name):
    return tool_use("Skill", skill=f"adk-adlc:{name}")


CHECKPOINT = tool_use("AskUserQuestion", questions=[{
    "question": "Proceed with this fix?", "header": "Checkpoint", "multiSelect": False,
    "options": [{"label": "Proceed", "description": "-"}, {"label": "Revise", "description": "-"}]}])


class CheckpointGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.project = self.tmp.name
        self.config({"mode": {"checkpoint_gate": "block", "skill_gate": "off"}})

    def tearDown(self):
        self.tmp.cleanup()

    def config(self, cfg):
        os.makedirs(os.path.join(self.project, ".claude"), exist_ok=True)
        with open(os.path.join(self.project, ".claude", "quality-check.config.json"), "w") as f:
            json.dump(cfg, f)

    def edit(self, *events, path="src/shop/orders.py"):
        transcript = os.path.join(self.project, "t.jsonl")
        with open(transcript, "w") as f:
            f.write(json.dumps({"type": "user", "message": {"role": "user", "content": "go"}}) + "\n")
            for e in events:
                f.write(json.dumps(e, separators=(",", ":")) + "\n")
        env = dict(os.environ, CLAUDE_PROJECT_DIR=self.project, CLAUDE_PLUGIN_ROOT=PLUGIN)
        env.pop("QUALITY_CHECK_MODE", None)
        payload = {"session_id": "s", "transcript_path": transcript, "tool_name": "Edit",
                   "tool_input": {"file_path": os.path.join(self.project, path)}}
        out = subprocess.run(["bash", os.path.join(HOOKS, "edit-gates.sh")], input=json.dumps(payload),
                             capture_output=True, text=True, env=env, timeout=30)
        return "deny" if '"permissionDecision":"deny"' in out.stdout.replace(" ", "") else "allow"

    def test_a_gated_workflow_waits_for_its_checkpoint(self):
        self.assertEqual(self.edit(skill("feature-development")), "deny")
        self.assertEqual(self.edit(skill("feature-development"), CHECKPOINT), "allow")

    def test_no_workflow_no_gate(self):
        self.assertEqual(self.edit(), "allow")

    def test_moving_to_the_users_own_plan_ends_the_gated_scope(self):
        self.assertEqual(self.edit(skill("feature-development"), skill("directed-change")), "allow")

    def test_moving_to_the_quick_path_ends_the_gated_scope(self):
        self.assertEqual(self.edit(skill("bug-fix"), skill("quick-change")), "allow")

    def test_a_gated_workflow_started_after_the_plan_still_waits(self):
        self.assertEqual(self.edit(skill("directed-change"), skill("refactor")), "deny")

    def test_documentation_is_never_gated(self):
        self.assertEqual(self.edit(skill("feature-development"), path="docs/plans/x.md"), "allow")

    def test_the_ungated_list_is_the_projects_to_set(self):
        self.config({"mode": {"checkpoint_gate": "block", "skill_gate": "off"},
                     "checkpoint_gate": {"ungated": ["quick-change"]}})
        self.assertEqual(self.edit(skill("feature-development"), skill("directed-change")), "deny")


if __name__ == "__main__":
    unittest.main()
