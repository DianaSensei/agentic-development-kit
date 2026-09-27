#!/usr/bin/env python3
"""skills/feature-development/scripts/check_tickets.py: tickets precise enough to hand down.

Run: python3 -m unittest discover -s skills/feature-development/scripts/tests
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "check_tickets.py")


def ticket(tid="task-1", **overrides):
    t = {
        "id": tid,
        "task": "Show the order count on the dashboard",
        "files": ["src/shop/dashboard.py", "tests/test_dashboard.py"],
        "depends_on": [],
        "interface": ["shop.dashboard.render(conn, customer_id) -> dict with keys name, order_count"],
        "follow_pattern": [{"what": "one query per call, row by primary key", "at": "src/shop/dashboard.py:3"}],
        "tests": ["Given a customer with 3 orders, 1 cancelled, when render runs, then order_count is 2"],
        "must_not": ["change cancel_order"],
        "done_when": "python3 -m unittest discover -s tests -t . passes",
        "stop_if": ["render does not already read the customers row"],
    }
    t.update(overrides)
    return t


class CheckTickets(unittest.TestCase):
    def run_script(self, data, raw=None):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            f.write(raw if raw is not None else json.dumps(data))
        try:
            r = subprocess.run([sys.executable, SCRIPT, f.name], capture_output=True, text=True)
        finally:
            os.unlink(f.name)
        return r.returncode, r.stdout

    def test_a_complete_ticket_is_tight(self):
        code, out = self.run_script({"tickets": [ticket()]})
        self.assertEqual(code, 0, out)
        self.assertIn("tier: task-1 tight", out)
        self.assertIn("OK: 1 ticket(s), all tight", out)

    def test_a_ticket_without_a_pattern_or_tests_is_loose(self):
        code, out = self.run_script({"tickets": [ticket(follow_pattern=[], tests=[])]})
        self.assertEqual(code, 1)
        self.assertIn("tier: task-1 loose - missing follow_pattern, tests", out)

    def test_a_stated_reason_stands_in_for_an_empty_interface_or_pattern(self):
        t = ticket(interface=[], no_interface_reason="an index adds no callable surface",
                   follow_pattern=[], no_pattern_reason="the first index in this schema")
        code, out = self.run_script({"tickets": [t]})
        self.assertEqual(code, 0, out)

    def test_a_pattern_must_point_at_a_line(self):
        code, out = self.run_script({"tickets": [ticket(follow_pattern=[{"what": "the transaction", "at": "src/shop/orders.py"}])]})
        self.assertEqual(code, 1)
        self.assertIn("has no path:line", out)
        self.assertIn("tier: task-1 loose", out)

    def test_tests_must_say_when_and_then(self):
        code, out = self.run_script({"tickets": [ticket(tests=["test the count"])]})
        self.assertEqual(code, 1)
        self.assertIn("not written as Given/When/Then", out)
        obj = {"given": "no orders", "when": "render runs", "then": "order_count is 0"}
        self.assertEqual(self.run_script({"tickets": [ticket(tests=[obj])]})[0], 0)

    def test_done_when_is_required_for_tight(self):
        t = ticket()
        del t["done_when"]
        code, out = self.run_script({"tickets": [t]})
        self.assertEqual(code, 1)
        self.assertIn("missing done_when", out)

    def test_dependencies_must_name_tickets(self):
        code, out = self.run_script({"tickets": [ticket(), ticket("task-2", depends_on=["task-9"])]})
        self.assertEqual(code, 1)
        self.assertIn("task-2: depends_on 'task-9', which is not a ticket", out)

    def test_ids_are_unique_and_required_fields_present(self):
        t = ticket(files=[])
        code, out = self.run_script({"tickets": [t, ticket()]})
        self.assertIn("task-1: files missing", out)
        self.assertIn("two tickets share an id", out)

    def test_each_ticket_is_graded_on_its_own(self):
        code, out = self.run_script({"tickets": [ticket(), ticket("task-2", tests=[])]})
        self.assertIn("tier: task-1 tight", out)
        self.assertIn("tier: task-2 loose - missing tests", out)

    def test_reads_a_json_block_inside_text(self):
        raw = "Tickets for proposal-2:\n```json\n" + json.dumps({"tickets": [ticket()]}) + "\n```"
        self.assertEqual(self.run_script(None, raw=raw)[0], 0)


if __name__ == "__main__":
    unittest.main()
