#!/usr/bin/env python3
"""skills/feature-development/scripts/check_proposals.py: the tradeoff rubric's mechanical half.

Run: python3 -m unittest discover -s skills/feature-development/scripts/tests
"""

import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "check_proposals.py")
DIMS = ["correctness_risk", "reversibility", "convention_fit", "native_approach",
        "operational_load", "performance_and_scale", "cost_to_build"]


def rated(**overrides):
    t = {d: {"rating": "good", "why": f"{d} is fine", "evidence": "src/app.py:10"} for d in DIMS}
    for d, rating in overrides.items():
        t[d] = dict(t[d], rating=rating)
    return t


def output():
    return {
        "priorities": [{"dimension": d, "source": "default"} for d in DIMS],
        "proposals": [
            {"id": "a", "title": "Add a column", "recommended": True,
             "deciding_dimensions": ["reversibility"], "costs": ["performance_and_scale"],
             "tradeoffs": rated(performance_and_scale="fair")},
            {"id": "b", "title": "Rewrite the table",
             "tradeoffs": rated(reversibility="poor")},
        ],
    }


class CheckProposals(unittest.TestCase):
    def run_script(self, data, *flags, raw=None):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            f.write(raw if raw is not None else json.dumps(data))
        try:
            r = subprocess.run([sys.executable, SCRIPT, *flags, f.name], capture_output=True, text=True)
        finally:
            os.unlink(f.name)
        return r.returncode, r.stdout

    def problems(self, data):
        code, out = self.run_script(data)
        return code, [l for l in out.splitlines() if l.startswith("problem:")]

    def test_a_complete_output_passes(self):
        code, out = self.run_script(output())
        self.assertEqual(code, 0, out)
        self.assertIn("OK: 2 proposal(s)", out)

    def test_a_skipped_dimension_is_named(self):
        data = output()
        del data["proposals"][1]["tradeoffs"]["operational_load"]
        code, probs = self.problems(data)
        self.assertEqual(code, 1)
        self.assertTrue(any("b: operational_load missing" in p for p in probs), probs)

    def test_a_rating_nobody_can_check_is_rejected(self):
        data = output()
        data["proposals"][0]["tradeoffs"]["correctness_risk"]["evidence"] = "it is well known"
        code, probs = self.problems(data)
        self.assertEqual(code, 1)
        self.assertTrue(any("a: correctness_risk evidence" in p for p in probs), probs)

    def test_every_evidence_form_is_accepted(self):
        data = output()
        forms = ["src/orders/service.py:42", "https://docs.djangoproject.com/en/5.0/topics/db/",
                 "requirement: AC-2", "measured: p95 180 ms", "doc: ADR-7",
                 "assumption: the table is small - confirm by SELECT count(*)"]
        for d, e in zip(DIMS, forms):
            data["proposals"][0]["tradeoffs"][d]["evidence"] = e
        self.assertEqual(self.run_script(data)[0], 0)

    def test_a_hidden_cost_is_caught(self):
        data = output()
        data["proposals"][0]["costs"] = []
        code, probs = self.problems(data)
        self.assertEqual(code, 1)
        self.assertTrue(any("better on performance_and_scale" in p for p in probs), probs)

    def test_recommending_against_the_top_differing_priority_needs_a_reason(self):
        data = output()
        data["proposals"][0]["recommended"] = False
        data["proposals"][1].update(recommended=True, deciding_dimensions=["performance_and_scale"],
                                    costs=["reversibility"])
        code, probs = self.problems(data)
        self.assertEqual(code, 1)
        self.assertTrue(any("reversibility - the top priority" in p for p in probs), probs)
        data["proposals"][1]["priority_override"] = "the person said speed matters more this quarter"
        code, out = self.run_script(data)
        self.assertEqual(code, 0, out)
        self.assertIn("note: b: recommended against the priority order", out)

    def test_the_priority_order_decides_which_difference_counts(self):
        # With performance first, b (good on it) is the right recommendation and a is not.
        data = output()
        order = ["performance_and_scale"] + [d for d in DIMS if d != "performance_and_scale"]
        data["priorities"] = [{"dimension": d, "source": "requirement: p95 under 200 ms"} for d in order]
        code, probs = self.problems(data)
        self.assertTrue(any("performance_and_scale - the top priority" in p for p in probs), probs)

    def test_an_assumption_does_not_decide(self):
        data = output()
        data["proposals"][1]["tradeoffs"]["reversibility"]["evidence"] = "assumption: nobody reads it - confirm by grep"
        code, out = self.run_script(data)
        self.assertIn("note: reversibility: the top priority where the proposals differ rests on an unknown", out)

    def test_poor_correctness_is_not_recommended_over_a_safer_option(self):
        data = output()
        data["proposals"][0]["tradeoffs"]["correctness_risk"]["rating"] = "poor"
        data["priorities"] = [{"dimension": d, "source": "project"} for d in
                              ["reversibility"] + [d for d in DIMS if d != "reversibility"]]
        data["proposals"][0]["costs"] = ["performance_and_scale", "correctness_risk"]
        code, probs = self.problems(data)
        self.assertTrue(any("poor on correctness_risk" in p for p in probs), probs)

    def test_one_proposal_must_name_what_it_beat(self):
        data = output()
        data["proposals"] = [data["proposals"][0]]
        code, probs = self.problems(data)
        self.assertEqual(code, 1)
        self.assertTrue(any("no alternatives_rejected" in p for p in probs), probs)
        data["proposals"][0]["alternatives_rejected"] = [
            {"approach": "rewrite the table", "loses_on": ["reversibility"], "evidence": "db/schema.sql:3"}]
        self.assertEqual(self.run_script(data)[0], 0)
        alone = copy.deepcopy(data)
        alone["proposals"][0].pop("alternatives_rejected")
        alone["proposals"][0]["no_alternative_reason"] = "the framework has one mechanism: doc: Django signals"
        self.assertEqual(self.run_script(alone)[0], 0)

    def test_priorities_must_be_complete_and_sourced(self):
        data = output()
        data["priorities"] = [{"dimension": "reversibility"}]
        code, probs = self.problems(data)
        self.assertTrue(any("priorities: missing" in p for p in probs), probs)
        self.assertTrue(any("needs its source" in p for p in probs), probs)

    def test_reads_a_json_block_inside_text(self):
        raw = "Here are the proposals.\n\n```json\n" + json.dumps(output()) + "\n```\n"
        self.assertEqual(self.run_script(None, raw=raw)[0], 0)

    def test_table_rows_follow_the_priority_order(self):
        data = output()
        order = ["cost_to_build"] + [d for d in DIMS if d != "cost_to_build"]
        data["priorities"] = [{"dimension": d, "source": "project"} for d in order]
        code, out = self.run_script(data, "--table")
        self.assertEqual(code, 0)
        rows = [l for l in out.splitlines() if l.startswith("| 1.") or l.startswith("| 2.")]
        self.assertIn("`cost_to_build`", rows[0])
        self.assertIn("Add a column ★", out)
        self.assertIn("❌ poor", out)
        self.assertIn("★ Recommended: Add a column - decided on reversibility; costs: performance_and_scale.", out)


if __name__ == "__main__":
    unittest.main()
