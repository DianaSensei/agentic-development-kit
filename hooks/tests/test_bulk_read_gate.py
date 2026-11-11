#!/usr/bin/env python3
"""hooks/bulk-read-gate.sh: the person's own switch turns the gate off in every project.

Run: python3 -m unittest discover -s hooks/tests
"""

import json
import os
import subprocess
import tempfile
import unittest

HOOKS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
PLUGIN = os.path.abspath(os.path.join(HOOKS, ".."))


class BulkReadGateSwitch(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.project = self.tmp.name
        os.makedirs(os.path.join(self.project, ".claude"))
        with open(os.path.join(self.project, ".claude", "quality-check.config.json"), "w") as f:
            json.dump({"mode": {"bulk_read_gate": "block"}, "bulk_read_gate": {"line_threshold": 10}}, f)
        self.big = os.path.join(self.project, "big.py")
        with open(self.big, "w") as f:
            f.write("x = 1\n" * 50)

    def tearDown(self):
        self.tmp.cleanup()

    def read(self, **env_extra):
        env = dict(os.environ, CLAUDE_PROJECT_DIR=self.project, CLAUDE_PLUGIN_ROOT=PLUGIN, **env_extra)
        env.pop("QUALITY_CHECK_MODE", None)
        if "ADK_BULK_READ_GATE" not in env_extra:
            env.pop("ADK_BULK_READ_GATE", None)
        payload = {"session_id": "s", "tool_name": "Read", "tool_input": {"file_path": self.big}}
        out = subprocess.run(["bash", os.path.join(HOOKS, "bulk-read-gate.sh")], input=json.dumps(payload),
                             capture_output=True, text=True, env=env, timeout=30)
        return "deny" if '"permissionDecision":"deny"' in out.stdout.replace(" ", "") else "allow"

    def test_a_whole_read_of_a_large_file_is_redirected(self):
        self.assertEqual(self.read(), "deny")

    def test_the_persons_switch_turns_it_off_over_the_project_setting(self):
        self.assertEqual(self.read(ADK_BULK_READ_GATE="off"), "allow")


if __name__ == "__main__":
    unittest.main()
