#!/usr/bin/env python3
"""skills/code-review-skill/scripts/mutate_changed.py: tests that pass against wrong code are found.

Run: python3 -m unittest discover -s skills/code-review-skill/scripts/tests
"""

import os
import subprocess
import sys
import tempfile
import unittest

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "mutate_changed.py")
TEST_CMD = f"{sys.executable} -m unittest discover -s tests -t ."


class MutateChanged(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        self.git("init", "-q")
        self.write("src/__init__.py", "")
        self.write("tests/__init__.py", "import os, sys\nsys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))\n")
        self.write("src/shop.py", "def total(items):\n    return sum(items)\n")
        self.write("tests/test_shop.py", "import unittest\nfrom shop import total\n\n\n"
                   "class T(unittest.TestCase):\n    def test_total(self):\n        self.assertEqual(total([1, 2]), 3)\n")
        self.git("add", "-A")
        self.git("-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "-qm", "init")

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, *args):
        subprocess.run(["git", "-C", self.root, *args], check=True, capture_output=True)

    def write(self, rel, text):
        path = os.path.join(self.root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(text)

    def run_script(self, *extra):
        r = subprocess.run([sys.executable, SCRIPT, "--test", TEST_CMD, *extra], cwd=self.root,
                           capture_output=True, text=True, timeout=300)
        return r.returncode, r.stdout

    def add_discount(self, test_body):
        self.write("src/shop.py", "def total(items):\n    return sum(items)\n\n\n"
                   "def discounted(price, is_member):\n"
                   "    if is_member and price >= 100:\n"
                   "        return price - 10\n"
                   "    return price\n")
        self.write("tests/test_discount.py", "import unittest\nfrom shop import discounted\n\n\n"
                   "class D(unittest.TestCase):\n" + test_body)

    def test_a_test_that_checks_the_behaviour_kills_every_mutant(self):
        self.add_discount("    def test_member_over_100(self):\n        self.assertEqual(discounted(100, True), 90)\n"
                          "    def test_member_under_100(self):\n        self.assertEqual(discounted(99, True), 99)\n"
                          "    def test_not_member(self):\n        self.assertEqual(discounted(100, False), 100)\n")
        code, out = self.run_script()
        self.assertEqual(code, 0, out)
        self.assertIn("survived.", out)
        self.assertIn(" 0 survived", out)

    def test_a_hollow_test_leaves_survivors_named_by_line(self):
        # Only checks that it runs: every mutant passes it.
        self.add_discount("    def test_runs(self):\n        self.assertIsNotNone(discounted(100, True))\n")
        code, out = self.run_script()
        self.assertEqual(code, 1, out)
        self.assertIn("survived: src/shop.py:6  and to or:", out)
        self.assertIn("survived: src/shop.py:7  - to +:", out)
        self.assertIn("add the test that catches it", out)

    def test_the_working_tree_is_never_touched(self):
        self.add_discount("    def test_runs(self):\n        self.assertIsNotNone(discounted(100, True))\n")
        path = os.path.join(self.root, "src/shop.py")
        with open(path) as f:
            before = f.read()
        self.run_script()
        with open(path) as f:
            self.assertEqual(f.read(), before)

    def test_only_changed_lines_of_source_files_are_mutated(self):
        self.add_discount("    def test_runs(self):\n        self.assertIsNotNone(discounted(100, True))\n")
        code, out = self.run_script()
        self.assertNotIn("src/shop.py:2 ", out)           # unchanged line
        self.assertNotIn("tests/", out.split("Mutants:")[1])  # test files are never mutated

    def test_a_folder_named_worktrees_is_copied_and_the_kits_own_is_not(self):
        self.write("src/worktrees/__init__.py", "")
        self.write("src/worktrees/pricing.py", "def discounted(price, is_member):\n"
                   "    if is_member and price >= 100:\n        return price - 10\n    return price\n")
        self.write(".claude/worktrees/agent-u1/marker", "a unit's worktree\n")
        self.write("tests/test_pricing.py", "import os, unittest\nfrom worktrees.pricing import discounted\n\n\n"
                   "class P(unittest.TestCase):\n"
                   "    def test_member_over_100(self):\n        self.assertEqual(discounted(100, True), 90)\n"
                   "    def test_member_under_100(self):\n        self.assertEqual(discounted(99, True), 99)\n"
                   "    def test_not_member(self):\n        self.assertEqual(discounted(100, False), 100)\n"
                   "    def test_units_are_not_copied(self):\n"
                   "        self.assertFalse(os.path.exists(os.path.join('.claude', 'worktrees')))\n")
        code, out = self.run_script()
        self.assertEqual(code, 0, out)

    def test_strings_and_comments_are_left_alone(self):
        self.write("src/shop.py", "def total(items):\n    return sum(items)\n\n\n"
                   "def label(x):\n    # compare x == 1 here\n    return 'x == 1 and true'\n")
        self.write("tests/test_label.py", "import unittest\nfrom shop import label\n\n\n"
                   "class L(unittest.TestCase):\n    def test_label(self):\n        self.assertEqual(label(1), 'x == 1 and true')\n")
        code, out = self.run_script()
        self.assertNotIn("== to !=", out)
        self.assertNotIn("and to or", out)

    def test_the_suite_must_pass_before_it_is_measured(self):
        self.write("src/shop.py", "def total(items):\n    return sum(items) + 1\n")
        code, out = self.run_script()
        self.assertEqual(code, 2)
        self.assertIn("fails on the unchanged code", out)

    def test_max_caps_the_runs(self):
        self.add_discount("    def test_runs(self):\n        self.assertIsNotNone(discounted(100, True))\n")
        code, out = self.run_script("--max", "2")
        self.assertIn("Mutants: 2 over 2 changed line(s)", out)

    def test_nothing_changed_is_nothing_to_do(self):
        code, out = self.run_script()
        self.assertEqual(code, 0)
        self.assertIn("nothing to mutate", out)


if __name__ == "__main__":
    unittest.main()
