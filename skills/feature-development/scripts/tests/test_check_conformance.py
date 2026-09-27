#!/usr/bin/env python3
"""skills/feature-development/scripts/check_conformance.py: the change against its tickets.

Run: python3 -m unittest discover -s skills/feature-development/scripts/tests
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "check_conformance.py")
TICKETS = [
    {"id": "task-2", "task": "count", "files": ["src/shop/orders.py"],
     "interface": ["shop.orders.place_order(conn, customer_id, total_cents) - also increments order_count"]},
    {"id": "task-3", "task": "render", "files": ["src/shop/dashboard.py"],
     "interface": ["shop.dashboard.render(conn, customer_id) -> dict with `order_count`"]},
    {"id": "task-5", "task": "backfill", "files": ["scripts/"],
     "interface": ["`backfill(conn)` sets every customer's order_count", "a one-off, no callable surface"]},
]


class CheckConformance(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        self.git("init", "-q")
        self.write("src/shop/orders.py", "def place_order(conn, customer_id, total_cents):\n    pass\n")
        self.write("src/shop/dashboard.py", "def render(conn, customer_id):\n    return {}\n")
        self.write(".gitignore", "__pycache__/\n")
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

    def build_as_ticketed(self):
        self.write("src/shop/orders.py", "def place_order(conn, customer_id, total_cents):\n    order_count = 1\n")
        self.write("src/shop/dashboard.py", "def render(conn, customer_id):\n    return {'order_count': 0}\n")
        self.write("scripts/backfill_order_count.py", "def backfill(conn):\n    pass\n")

    def run_script(self, source=None):
        path = source or os.path.join(self.root, ".claude", "tickets.json")
        if source is None:
            self.write(".claude/tickets.json", json.dumps({"tickets": TICKETS}))
        r = subprocess.run([sys.executable, SCRIPT, path], capture_output=True, text=True, cwd=self.root)
        return r.returncode, r.stdout

    def test_a_change_built_as_ticketed_conforms(self):
        self.build_as_ticketed()
        self.write("docs/plans/order-count.md", "# plan\n")  # the workflow's own record, never a stray
        code, out = self.run_script()
        self.assertEqual(code, 0, out)
        self.assertIn("| task-3 | 1/1 | render | - |", out)
        self.assertIn("(not checkable: 1)", out)

    def test_a_file_no_ticket_names_is_a_stray(self):
        self.build_as_ticketed()
        self.write("src/shop/cache.py", "CACHE = {}\n")
        code, out = self.run_script()
        self.assertEqual(code, 1)
        self.assertIn("problem: src/shop/cache.py: changed, but in no ticket's files", out)

    def test_a_ticket_left_undone_is_named(self):
        self.build_as_ticketed()
        self.git("checkout", "--", "src/shop/dashboard.py")
        code, out = self.run_script()
        self.assertEqual(code, 1)
        self.assertIn("task-3: src/shop/dashboard.py is in its files but was not changed", out)

    def test_an_interface_renamed_on_the_way_is_caught(self):
        self.build_as_ticketed()
        self.write("src/shop/dashboard.py", "def render_header(conn, customer_id):\n    return {}\n")
        code, out = self.run_script()
        self.assertEqual(code, 1)
        self.assertIn("task-3: interface `render` does not appear in its files", out)

    def test_reads_the_tickets_from_the_plan(self):
        self.build_as_ticketed()
        plan = ("# Feature\n\n```json\n{\"not\": \"tickets\"}\n```\n\n## Tickets\n\n```json\n"
                + json.dumps({"tickets": TICKETS}) + "\n```\n")
        self.write("docs/plans/order-count.md", plan)
        code, out = self.run_script(os.path.join(self.root, "docs/plans/order-count.md"))
        self.assertEqual(code, 0, out)

    def test_base_can_be_a_snapshot(self):
        self.build_as_ticketed()
        self.git("add", "-A")
        self.git("-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "-qm", "built")
        self.write(".claude/tickets.json", json.dumps({"tickets": TICKETS}))
        r = subprocess.run([sys.executable, SCRIPT, "--base", "HEAD~1", ".claude/tickets.json"],
                           capture_output=True, text=True, cwd=self.root)
        self.assertEqual(r.returncode, 0, r.stdout)


if __name__ == "__main__":
    unittest.main()
