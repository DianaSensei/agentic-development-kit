#!/usr/bin/env python3
"""hooks/quality-gate.sh: unreviewed or untested code changes hold the turn.

Run: python3 -m unittest discover -s hooks/tests
"""

import json
import os
import shutil
import subprocess
import tempfile
import unittest

HOOKS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
PLUGIN = os.path.abspath(os.path.join(HOOKS, ".."))


def tool_use(name, **inp):
    return {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": name, "input": inp}]}}


class QualityGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.project = self.tmp.name
        git = ["git", "-C", self.project, "-c", "user.email=t@example.com", "-c", "user.name=t"]
        subprocess.run(["git", "init", "-q", self.project], check=True)
        os.makedirs(os.path.join(self.project, "src"))
        self.src = os.path.join(self.project, "src", "a.py")
        with open(self.src, "w") as f:
            f.write("x = 1\n")
        subprocess.run(git + ["add", "-A"], check=True)
        subprocess.run(git + ["commit", "-qm", "init"], check=True)
        with open(self.src, "w") as f:  # an uncommitted code change
            f.write("x = 2\n")
        self.config({"mode": {"quality_gate": "block"}})

    def tearDown(self):
        self.tmp.cleanup()

    def config(self, cfg):
        os.makedirs(os.path.join(self.project, ".claude"), exist_ok=True)
        with open(os.path.join(self.project, ".claude", "quality-check.config.json"), "w") as f:
            json.dump(cfg, f)
        shutil.rmtree(os.path.join(self.project, ".claude", "state"), ignore_errors=True)

    def gate(self, *events):
        transcript = os.path.join(self.project, "t.jsonl")
        with open(transcript, "w") as f:
            f.write(json.dumps({"type": "user", "message": {"role": "user", "content": "go"}}) + "\n")
            for e in events:
                f.write(json.dumps(e, separators=(",", ":")) + "\n")
        env = dict(os.environ, CLAUDE_PROJECT_DIR=self.project, CLAUDE_PLUGIN_ROOT=PLUGIN)
        env.pop("QUALITY_CHECK_MODE", None)
        payload = {"session_id": "s", "transcript_path": transcript, "stop_hook_active": False}
        out = subprocess.run(["bash", os.path.join(HOOKS, "quality-gate.sh")], input=json.dumps(payload),
                             capture_output=True, text=True, env=env, timeout=60)
        return out.returncode, out.stderr

    EDIT = tool_use("Edit", file_path="SRC", old_string="x = 1", new_string="x = 2")
    REVIEW = tool_use("Skill", skill="adk-adlc:code-review-skill")
    TESTS = tool_use("Bash", command="python3 -m pytest -q tests/", description="Run the tests")

    def edit(self):
        e = json.loads(json.dumps(self.EDIT))
        e["message"]["content"][0]["input"]["file_path"] = self.src
        return e

    def test_reviewed_and_tested_after_the_edit_passes(self):
        self.assertEqual(self.gate(self.edit(), self.TESTS, self.REVIEW)[0], 0)
        self.config({"mode": {"quality_gate": "block"}})
        self.assertEqual(self.gate(self.edit(), self.REVIEW, self.TESTS)[0], 0)

    def test_reviewed_but_not_tested_is_held(self):
        rc, err = self.gate(self.edit(), self.REVIEW)
        self.assertEqual(rc, 2)
        self.assertIn("changed after the last test run", err)
        self.assertIn("report the result as it", err)
        self.assertNotIn("have not been reviewed", err)

    def test_tests_before_the_last_edit_do_not_count(self):
        rc, err = self.gate(self.TESTS, self.edit(), self.REVIEW)
        self.assertEqual(rc, 2)
        self.assertIn("changed after the last test run", err)

    def test_tested_but_not_reviewed_is_held_for_the_review_only(self):
        rc, err = self.gate(self.edit(), self.TESTS)
        self.assertEqual(rc, 2)
        self.assertIn("have not been reviewed", err)
        self.assertNotIn("Run the tests after", err)

    def test_test_run_can_be_turned_off(self):
        self.config({"mode": {"quality_gate": "block"}, "quality_gate": {"require_test_run": False}})
        self.assertEqual(self.gate(self.edit(), self.REVIEW)[0], 0)

    def test_project_test_command(self):
        self.config({"mode": {"quality_gate": "block"}, "quality_gate": {"test_command": "make verify"}})
        self.assertEqual(self.gate(self.edit(), self.TESTS, self.REVIEW)[0], 2)
        self.config({"mode": {"quality_gate": "block"}, "quality_gate": {"test_command": "make verify"}})
        run = tool_use("Bash", description="Verify", command='make verify ARGS="-k \\"retry\\""')
        self.assertEqual(self.gate(self.edit(), run, self.REVIEW)[0], 0)

    def test_common_runners_are_recognised(self):
        for cmd in ["npm test", "npm run test -- --watch=false", "go test ./...", "cargo test",
                    "./mvnw -q verify", "./gradlew test", "pnpm test", "npx vitest run", "bundle exec rspec",
                    "cd api && python -m unittest discover -s tests"]:
            self.config({"mode": {"quality_gate": "block"}})
            self.assertEqual(self.gate(self.edit(), tool_use("Bash", command=cmd), self.REVIEW)[0], 0, cmd)

    def test_a_mention_of_tests_is_not_a_run(self):
        rc, _ = self.gate(self.edit(), tool_use("Read", file_path="tests/test_pytest.py"), self.REVIEW)
        self.assertEqual(rc, 2)


if __name__ == "__main__":
    unittest.main()
