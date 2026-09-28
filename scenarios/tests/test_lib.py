#!/usr/bin/env python3
"""scenarios/lib.py: reading a run's transcript and judging it - checked on small synthetic runs.

Run: python3 -m unittest discover -s scenarios/tests
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from lib import Checks, Run, git  # noqa: E402


def assistant(msg, *calls):
    return {"type": "assistant", "message": {"id": msg, "content": [
        {"type": "tool_use", "id": cid, "name": name, "input": inp} for cid, name, inp in calls]}}


def result(cid, text, error=False):
    return {"type": "user", "message": {"content": [
        {"type": "tool_result", "tool_use_id": cid, "content": [{"type": "text", "text": text}], "is_error": error}]}}


class RunTests(unittest.TestCase):
    def write(self, events):
        f = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False)
        f.write("\n".join(json.dumps(e) for e in events) + "\nnot json\n")
        f.close()
        self.addCleanup(os.unlink, f.name)
        return Run(f.name)

    def test_dispatches_group_by_message_and_denials_are_marked(self):
        unit = {"subagent_type": "adk-adlc:unit-implementer", "prompt": "lane: [\"a\"]", "model": "sonnet"}
        run = self.write([
            assistant("m1", ("t1", "Agent", unit), ("t2", "Agent", unit)),
            result("t1", "[dispatch-gate] Not dispatching this unit yet", error=True),
            result("t2", "[dispatch-gate] Not dispatching this unit yet", error=True),
            assistant("m2", ("t3", "Agent", unit), ("t4", "Agent", unit), ("t5", "Agent", {"subagent_type": "Explore"})),
            result("t3", "Async agent launched successfully."),
            result("t4", "Async agent launched successfully."),
        ])
        units = run.dispatches("unit-implementer")
        self.assertEqual([d["denied"] for d in units], [True, True, False, False])
        self.assertEqual({d["msg"] for d in units if not d["denied"]}, {"m2"})

    def test_subagent_calls_are_not_the_leads(self):
        run = self.write([
            assistant("m1", ("t1", "Bash", {"command": "python3 check_conformance.py plan.md"})),
            dict(assistant("m2", ("t2", "Bash", {"command": "bash snapshot.sh take 2"})), parent_tool_use_id="x"),
        ])
        self.assertEqual(len(run.bash(r"check_conformance")), 1)
        self.assertEqual(run.bash(r"snapshot"), [])

    def test_reads_and_the_final_result(self):
        run = self.write([
            assistant("m1", ("t1", "Read", {"file_path": "/cache/skills/feature-development/references/parallel-units.md"})),
            {"type": "result", "result": "interim", "total_cost_usd": 0.5},
            {"type": "result", "result": "final report", "total_cost_usd": 1.25},
        ])
        self.assertTrue(run.read("feature-development/references/parallel-units.md"))
        self.assertFalse(run.read("tickets.md"))
        self.assertEqual((run.final_text(), run.cost()), ("final report", 1.25))


class ChecksTests(unittest.TestCase):
    def test_a_failed_must_fails_and_a_missed_expectation_does_not(self):
        c = Checks("x")
        c.must(True, "a")
        c.expect(False, "b")
        self.assertEqual(c.report(), 0)
        c.must(False, "c")
        self.assertEqual(c.report(), 1)

    def test_branch_and_leftovers(self):
        with tempfile.TemporaryDirectory() as repo:
            g = ["git", "-C", repo, "-c", "user.name=t", "-c", "user.email=t@example.com"]
            subprocess.run(["git", "init", "-q", repo], check=True)
            subprocess.run(g + ["commit", "-q", "--allow-empty", "-m", "a"], check=True)
            start = git(repo, "rev-parse", "HEAD")
            subprocess.run(g + ["update-ref", "refs/adk/waves/2", start], check=True)
            subprocess.run(g + ["commit", "-q", "--allow-empty", "-m", "b"], check=True)
            c = Checks("x")
            c.branch_untouched(repo, start)
            c.nothing_left_behind(repo)
            self.assertEqual([r[0] for r in c.rows], ["FAIL", "PASS", "FAIL"])


if __name__ == "__main__":
    unittest.main()
