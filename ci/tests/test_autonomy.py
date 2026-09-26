#!/usr/bin/env python3
"""ci/autonomy.py: which reviewed changes may skip human approval.

Run: python3 -m unittest discover -s ci/tests
"""

import importlib.util
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("autonomy", os.path.join(HERE, "..", "autonomy.py"))
autonomy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(autonomy)


def diff(*files, lines=3):
    out = []
    for f in files:
        out += [f"diff --git a/{f} b/{f}", f"--- a/{f}", f"+++ b/{f}", "@@ -1,1 +1,1 @@"]
        out += ["+x"] * lines
    return "\n".join(out) + "\n"


CLEAN = {"blocking": 0, "suggestions": 2, "questions": 0}
DOCS = {"tiers": [{"name": "docs", "mode": "approve", "paths": ["docs/**", "**/*.md"],
                   "max_changed_lines": 100, "max_changed_files": 5}]}


class DecideTests(unittest.TestCase):
    def test_no_policy_is_off(self):
        d = autonomy.decide({}, diff("docs/a.md"), CLEAN)
        self.assertEqual((d["mode"], d["eligible"]), ("off", False))
        self.assertEqual(autonomy.note(d), "")

    def test_docs_change_is_eligible(self):
        d = autonomy.decide(DOCS, diff("docs/guide/setup.md", "README.md"), CLEAN)
        self.assertEqual((d["tier"], d["mode"], d["eligible"]), ("docs", "approve", True))
        self.assertIn("approved by the project's autonomy policy", autonomy.note(d))

    def test_report_mode_says_what_it_would_do(self):
        policy = {"tiers": [dict(DOCS["tiers"][0], mode="report")]}
        d = autonomy.decide(policy, diff("docs/a.md"), CLEAN)
        self.assertTrue(d["eligible"])
        self.assertIn("would have been approved without a person", autonomy.note(d))

    def test_code_outside_the_paths_needs_a_person(self):
        d = autonomy.decide(DOCS, diff("docs/a.md", "src/app.py"), CLEAN)
        self.assertFalse(d["eligible"])
        self.assertIn("`src/app.py`", autonomy.note(d))

    def test_limits(self):
        self.assertFalse(autonomy.decide(DOCS, diff("docs/a.md", lines=101), CLEAN)["eligible"])
        many = [f"docs/{i}.md" for i in range(6)]
        self.assertFalse(autonomy.decide(DOCS, diff(*many, lines=1), CLEAN)["eligible"])

    def test_review_findings_block(self):
        for result in ({"blocking": 1, "questions": 0}, {"blocking": 0, "questions": 1}, None, {}):
            d = autonomy.decide(DOCS, diff("docs/a.md"), result)
            self.assertFalse(d["eligible"], result)
            self.assertEqual(d["tier"], "docs")

    def test_steering_files_are_never_eligible_whatever_the_policy(self):
        everything = {"tiers": [{"name": "all", "mode": "approve", "paths": ["**"], "max_changed_lines": 10 ** 6}]}
        for f in (".claude/autonomy.json", "CLAUDE.md", "pkg/CLAUDE.md", "REVIEW.md", ".github/workflows/ci.yml",
                  ".gitlab-ci.yml", "docs/intents/x.md", ".mcp.json", "bands.yaml", ".github/CODEOWNERS"):
            d = autonomy.decide(everything, diff("src/a.py", f), CLEAN)
            self.assertFalse(d["eligible"], f)
            self.assertIn("steers the agent", autonomy.note(d))
        self.assertTrue(autonomy.decide(everything, diff("src/a.py"), CLEAN)["eligible"])

    def test_authors(self):
        deps = {"tiers": [{"name": "deps", "mode": "approve", "paths": ["package-lock.json", "package.json"],
                           "max_changed_lines": 500, "authors": ["dependabot[bot]"]}]}
        files = diff("package.json", "package-lock.json")
        self.assertTrue(autonomy.decide(deps, files, CLEAN, "dependabot[bot]")["eligible"])
        self.assertFalse(autonomy.decide(deps, files, CLEAN, "someone")["eligible"])
        self.assertFalse(autonomy.decide(deps, files, CLEAN, "")["eligible"])  # unknown author: closed

    def test_first_matching_tier_wins_and_off_tiers_are_ignored(self):
        policy = {"tiers": [{"name": "ignored", "mode": "off", "paths": ["**"], "max_changed_lines": 999},
                            {"name": "docs", "mode": "report", "paths": ["docs/**"], "max_changed_lines": 50}]}
        self.assertEqual(autonomy.decide(policy, diff("docs/a.md"), CLEAN)["tier"], "docs")

    def test_renames_count_both_paths(self):
        text = "diff --git a/src/old.py b/docs/new.md\nsimilarity index 100%\nrename from src/old.py\nrename to docs/new.md\n"
        self.assertFalse(autonomy.decide(DOCS, text, CLEAN)["eligible"])

    def test_empty_diff_matches_no_tier(self):
        d = autonomy.decide(DOCS, "", CLEAN)
        self.assertEqual((d["tier"], d["eligible"]), (None, False))

    def test_globs(self):
        g = autonomy.glob_re
        self.assertTrue(g("docs/**").match("docs/a/b.md"))
        self.assertTrue(g("**/*.md").match("README.md"))
        self.assertTrue(g("**/*.md").match("a/b/c.md"))
        self.assertFalse(g("docs/*.md").match("docs/a/b.md"))
        self.assertFalse(g("*.md").match("docs/a.md"))


if __name__ == "__main__":
    unittest.main()
