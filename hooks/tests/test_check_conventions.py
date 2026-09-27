#!/usr/bin/env python3
"""hooks/check-conventions.sh: the project's checks, run on the file just written.

Run: python3 -m unittest discover -s hooks/tests
"""

import json
import os
import subprocess
import tempfile
import unittest

HOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "check-conventions.sh")


class CheckConventionsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.project = self.tmp.name
        os.makedirs(os.path.join(self.project, ".claude"))
        os.makedirs(os.path.join(self.project, "src"))

    def tearDown(self):
        self.tmp.cleanup()

    def config(self, checks, mode=None):
        cfg = {"checks": checks}
        if mode:
            cfg["mode"] = {"convention_checks": mode}
        with open(os.path.join(self.project, ".claude", "quality-check.config.json"), "w") as f:
            json.dump(cfg, f)

    def write(self, rel, text):
        path = os.path.join(self.project, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(text)
        return path

    def run_hook(self, path):
        env = dict(os.environ, CLAUDE_PROJECT_DIR=self.project)
        env.pop("QUALITY_CHECK_MODE", None)
        payload = {"tool_name": "Edit", "tool_input": {"file_path": path}, "session_id": "t"}
        out = subprocess.run(["bash", HOOK], input=json.dumps(payload), capture_output=True, text=True,
                             env=env, timeout=60)
        self.assertEqual(out.returncode, 0, out.stderr)
        return json.loads(out.stdout) if out.stdout.strip() else None

    NO_PRINT = {"name": "no-print", "match": r"^src/.*\.py$", "run": "! grep -n 'print(' {file}"}

    def test_no_project_config_runs_nothing(self):
        self.assertIsNone(self.run_hook(self.write("src/a.py", "print(1)\n")))

    def test_passing_check_is_silent(self):
        self.config([self.NO_PRINT])
        self.assertIsNone(self.run_hook(self.write("src/a.py", "import logging\n")))

    def test_failure_goes_back_to_claude_as_context(self):
        self.config([self.NO_PRINT])
        out = self.run_hook(self.write("src/a.py", "x = 1\nprint(x)\n"))
        ctx = out["hookSpecificOutput"]["additionalContext"]
        self.assertEqual(out["hookSpecificOutput"]["hookEventName"], "PostToolUse")
        self.assertIn("`src/a.py` fails the project's checks", ctx)
        self.assertIn("no-print", ctx)
        self.assertIn("2:print(x)", ctx)  # the checker's own output
        self.assertIn("never disable the check", ctx)

    def test_block_mode(self):
        self.config([self.NO_PRINT], mode="block")
        out = self.run_hook(self.write("src/a.py", "print(1)\n"))
        self.assertEqual(out["decision"], "block")
        self.assertIn("no-print", out["reason"])

    def test_off_mode(self):
        self.config([self.NO_PRINT], mode="off")
        self.assertIsNone(self.run_hook(self.write("src/a.py", "print(1)\n")))

    def test_match_limits_the_files(self):
        self.config([self.NO_PRINT])
        self.assertIsNone(self.run_hook(self.write("scripts/tool.py", "print(1)\n")))

    def test_missing_checker_is_skipped_not_failed(self):
        self.config([{"name": "absent", "run": "definitely-not-installed-xyz {file}"}])
        self.assertIsNone(self.run_hook(self.write("src/a.py", "print(1)\n")))
        self.config([{"name": "absent", "run": "definitely-not-installed-xyz {file}"}, self.NO_PRINT])
        ctx = self.run_hook(self.write("src/a.py", "print(1)\n"))["hookSpecificOutput"]["additionalContext"]
        self.assertIn("Skipped, not installed here: absent", ctx)

    def test_file_path_is_quoted(self):
        self.config([{"name": "exists", "run": "test -f {file} && ! grep -q TODO {file}"}])
        self.assertIsNone(self.run_hook(self.write("src/my file; rm -rf x.py", "ok\n")))
        out = self.run_hook(self.write("src/my file; rm -rf x.py", "TODO\n"))
        self.assertIn("exists", out["hookSpecificOutput"]["additionalContext"])

    def test_project_scope_checks_do_not_run_per_file(self):
        marker = os.path.join(self.project, "ran")
        self.config([{"name": "types", "scope": "project", "run": f"touch {marker}; false"}])
        self.assertIsNone(self.run_hook(self.write("src/a.py", "x\n")))
        self.assertFalse(os.path.exists(marker))

    def test_worktree_copy_is_matched_by_its_project_path(self):
        self.config([self.NO_PRINT])
        out = self.run_hook(self.write(".claude/worktrees/agent-1/src/a.py", "print(1)\n"))
        self.assertIn("`src/a.py` fails", out["hookSpecificOutput"]["additionalContext"])

    def test_timeout_is_reported(self):
        self.config([{"name": "slow", "run": "sleep 5", "timeout": 1}])
        out = self.run_hook(self.write("src/a.py", "x\n"))
        self.assertIn("did not finish in 1s", out["hookSpecificOutput"]["additionalContext"])

    def test_checker_reading_stdin_does_not_eat_the_next_check(self):
        self.config([{"name": "reads-stdin", "run": "cat > /dev/null"}, self.NO_PRINT])
        out = self.run_hook(self.write("src/a.py", "print(1)\n"))
        self.assertIn("no-print", out["hookSpecificOutput"]["additionalContext"])


if __name__ == "__main__":
    unittest.main()
