#!/usr/bin/env python3
"""codehost.py against the fake MCP server, for each provider.

Run: python3 -m unittest discover -s codehost/tests
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
CODEHOST = os.path.join(HERE, "..", "codehost.py")
FAKE = os.path.join(HERE, "fake_server.py")
sys.path.insert(0, os.path.join(HERE, ".."))
import codehost  # noqa: E402

DIFF = """diff --git a/app/orders.py b/app/orders.py
index 1111111..2222222 100644
--- a/app/orders.py
+++ b/app/orders.py
@@ -10,4 +10,5 @@ def total(items):
     subtotal = sum(i.price for i in items)
-    return subtotal
+    tax = subtotal * RATE
+    return subtotal + tax
     # end
diff --git a/app/new.py b/app/new.py
new file mode 100644
index 0000000..3333333
--- /dev/null
+++ b/app/new.py
@@ -0,0 +1,2 @@
+def f():
+    return 1
"""

FINDINGS = [
    {"path": "app/orders.py", "line": 12, "severity": "blocking", "body": "`RATE` is never defined."},
    {"path": "app/orders.py", "line": 10, "severity": "question", "body": "Should this round?"},
    {"path": "app/new.py", "line": 2, "severity": "suggestion", "body": "Name the constant."},
    {"path": "app/orders.py", "line": 40, "severity": "suggestion", "body": "Outside the diff."},
    {"path": "app/orders.py", "line": 11, "severity": "blocking", "side": "old", "body": "Removed line."},
    {"path": "x.py", "line": 1, "severity": "nit", "body": "Not a severity - dropped."},
]


class Env:
    def __init__(self, provider, **extra):
        self.dir = tempfile.mkdtemp()
        self.state = os.path.join(self.dir, "state.json")
        self.log = os.path.join(self.dir, "calls.jsonl")
        self.env = dict(os.environ)
        self.env.update({
            "ADK_PROVIDER": provider,
            "ADK_PROJECT": "acme/shop" if provider == "github" else "42",
            "ADK_CODEHOST_TOKEN": "t0ken",
            "ADK_CODEHOST_URL": "https://gitlab.test/api/v4" if provider == "gitlab" else "",
            "ADK_CODEHOST_SERVER": json.dumps([sys.executable, FAKE]),
            "FAKE_PROVIDER": provider, "FAKE_STATE": self.state, "FAKE_LOG": self.log,
        })
        self.env.update(extra)

    def file(self, name, content):
        path = os.path.join(self.dir, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content if isinstance(content, str) else json.dumps(content))
        return path

    def run(self, *args):
        p = subprocess.run([sys.executable, CODEHOST, *args], env=self.env, capture_output=True, text=True, timeout=60)
        return p.returncode, p.stdout, p.stderr

    def calls(self):
        if not os.path.exists(self.log):
            return []
        with open(self.log, encoding="utf-8") as f:
            return [json.loads(line) for line in f]

    def state_json(self):
        with open(self.state, encoding="utf-8") as f:
            return json.load(f)

    def review(self, findings=FINDINGS, summary="## Independent review\n\n**1 blocking**"):
        result = self.file("result.json", {"blocking": 1, "suggestions": 1, "questions": 1,
                                            "summary_markdown": summary, "findings": findings})
        diff = self.file("review.diff", DIFF)
        return self.run("publish-review", "--change", "7", "--result", result, "--diff", diff,
                        "--head-sha", "abcdef1234567")


class DiffTests(unittest.TestCase):
    def test_lines(self):
        m = codehost.parse_diff(DIFF)
        self.assertEqual(m["app/orders.py"]["new"], {10: 10, 11: None, 12: None, 13: 12})
        self.assertEqual(m["app/orders.py"]["old"], {11})
        self.assertEqual(m["app/new.py"]["new"], {1: None, 2: None})
        self.assertEqual(m["app/new.py"]["old_path"], "app/new.py")

    def test_locate(self):
        m = codehost.parse_diff(DIFF)
        self.assertEqual(codehost.locate({"path": "app/orders.py", "line": 10}, m)[0]["old_line"], 10)
        self.assertIsNone(codehost.locate({"path": "app/orders.py", "line": 40}, m)[0])
        self.assertIsNone(codehost.locate({"path": "nope.py", "line": 1}, m)[0])
        self.assertEqual(codehost.locate({"path": "app/orders.py", "line": 11, "side": "old"}, m)[0]["side"], "old")

    def test_expand(self):
        env = {"A": "x"}
        self.assertEqual(codehost.expand("${A}-${B:-d}-{tools}", env, ["t1", "t2"]), "x-d-t1,t2")
        with self.assertRaises(codehost.CodeHostError):
            codehost.expand("${B}", env, [])


class GitHubTests(unittest.TestCase):
    def test_first_review_inline_and_summary(self):
        e = Env("github", ADK_CODEHOST_BOT_LOGIN="github-actions[bot]")
        code, out, err = e.review()
        self.assertEqual(code, 0, err)
        report = json.loads(out)
        self.assertEqual(report["findings"], 5)          # the "nit" is dropped
        self.assertEqual(report["inline"], 4)
        self.assertEqual(report["not_inline"], 1)        # line 40 is outside the diff
        self.assertEqual(report["summary"], "created")
        s = e.state_json()
        review = s["reviews"][0]
        self.assertEqual(review["state"], "COMMENTED")
        sides = {(c["path"], c["line"], c["side"]) for c in review["comments"]}
        self.assertIn(("app/orders.py", 11, "LEFT"), sides)
        self.assertIn(("app/orders.py", 12, "RIGHT"), sides)
        self.assertTrue(all(c["body"].startswith("**") for c in review["comments"]))
        comment = s["comments"][0]["body"]
        self.assertTrue(comment.startswith(codehost.REVIEW_MARKER))
        self.assertIn("`app/orders.py:40` - line not in the diff", comment)
        self.assertIn("commit abcdef1", comment)

    def test_rereview_updates_summary_and_skips_inline(self):
        e = Env("github", ADK_CODEHOST_BOT_LOGIN="github-actions[bot]")
        self.assertEqual(e.review()[0], 0)
        code, out, err = e.review(summary="## Independent review\n\nsecond pass")
        self.assertEqual(code, 0, err)
        report = json.loads(out)
        self.assertEqual(report["summary"], "updated")
        self.assertEqual(report["inline"], 0)
        s = e.state_json()
        self.assertEqual(len(s["comments"]), 1)
        self.assertIn("second pass", s["comments"][0]["body"])
        self.assertEqual(len(s["reviews"]), 1)           # no stranded pending review
        self.assertFalse([c for c in e.calls() if c["error"]])

    def test_without_bot_login_rereview_degrades(self):
        e = Env("github")
        self.assertEqual(e.review()[0], 0)
        code, out, err = e.review()
        self.assertEqual(code, 0, err)
        report = json.loads(out)
        self.assertEqual(report["inline"], 0)
        self.assertEqual(report["not_inline"], 5)
        self.assertEqual(len(e.state_json()["comments"]), 1)

    def test_rejected_line_is_reported_not_fatal(self):
        e = Env("github", ADK_CODEHOST_BOT_LOGIN="github-actions[bot]", FAKE_REJECT_PATHS="app/new.py")
        code, out, err = e.review()
        self.assertEqual(code, 0, err)
        report = json.loads(out)
        self.assertEqual(report["inline"], 3)
        self.assertEqual(report["not_inline"], 2)
        self.assertIn("Line could not be resolved", e.state_json()["comments"][0]["body"])

    def test_human_marker_comment_is_not_overwritten(self):
        e = Env("github", ADK_CODEHOST_BOT_LOGIN="github-actions[bot]", FAKE_VIEWER="alice")
        body = e.file("b.md", "quoted")
        e.run("upsert-comment", "--change", "7", "--marker", codehost.REVIEW_MARKER, "--body-file", body)
        e.env["FAKE_VIEWER"] = "github-actions[bot]"
        self.assertEqual(e.run("upsert-comment", "--change", "7", "--marker", codehost.REVIEW_MARKER,
                               "--body-file", body)[1].strip(), "created")

    def test_ensure_change(self):
        e = Env("github")
        body = e.file("b.md", "triage")
        code, out, _ = e.run("ensure-change", "--head", "maintain/q", "--base", "main", "--title", "T", "--body-file", body)
        self.assertEqual((code, out.strip()), (0, "opened https://github.test/pull/1"))
        code, out, _ = e.run("ensure-change", "--head", "maintain/q", "--base", "main", "--title", "T", "--body-file", body)
        self.assertEqual((code, out.strip()), (0, "existing https://github.test/pull/1"))


class GitLabTests(unittest.TestCase):
    def test_inline_positions_and_summary(self):
        e = Env("gitlab")
        code, out, err = e.review()
        self.assertEqual(code, 0, err)
        report = json.loads(out)
        self.assertEqual((report["inline"], report["not_inline"], report["summary"]), (4, 1, "created"))
        threads = {(t["position"]["new_path"], t["position"].get("new_line"), t["position"].get("old_line"))
                   for t in e.state_json()["threads"]}
        self.assertIn(("app/orders.py", 10, 10), threads)    # unchanged line: both numbers
        self.assertIn(("app/orders.py", 12, None), threads)  # added line: new only
        self.assertIn(("app/orders.py", None, 11), threads)  # deleted line: old only

    def test_rereview_updates_note(self):
        e = Env("gitlab")
        e.review()
        code, out, err = e.review(summary="second")
        self.assertEqual(code, 0, err)
        notes = e.state_json()["notes"]
        self.assertEqual(len(notes), 1)
        self.assertIn("second", notes[0]["body"])

    def test_ensure_change(self):
        e = Env("gitlab")
        body = e.file("b.md", "triage")
        args = ("ensure-change", "--head", "maintain/q", "--base", "main", "--title", "T", "--body-file", body)
        self.assertEqual(e.run(*args)[1].strip(), "opened https://gitlab.test/mr/1")
        self.assertEqual(e.run(*args)[1].strip(), "existing https://gitlab.test/mr/1")

    def test_every_call_matches_the_real_schema(self):
        e = Env("gitlab")
        e.review()
        self.assertFalse([c for c in e.calls() if c["error"]])


class ErrorTests(unittest.TestCase):
    def test_bad_provider(self):
        e = Env("github")
        e.env["ADK_PROVIDER"] = "svn"
        code, _, err = e.run("upsert-comment", "--change", "1", "--marker", "m", "--body-file", "/dev/null")
        self.assertEqual(code, 2)
        self.assertIn("ADK_PROVIDER", err)

    def test_server_that_cannot_start(self):
        e = Env("github")
        e.env["ADK_CODEHOST_SERVER"] = json.dumps(["/nonexistent/server"])
        code, _, err = e.run("upsert-comment", "--change", "1", "--marker", "m", "--body-file", "/dev/null")
        self.assertEqual(code, 2)
        self.assertIn("cannot start", err)

    def test_missing_token(self):
        e = Env("gitlab")
        e.env.pop("ADK_CODEHOST_SERVER")
        e.env["ADK_CODEHOST_TOKEN"] = ""
        code, _, err = e.run("upsert-comment", "--change", "1", "--marker", "m", "--body-file", "/dev/null")
        self.assertEqual(code, 2)
        self.assertIn("ADK_CODEHOST_TOKEN is not set", err)


class ProfileTests(unittest.TestCase):
    def test_profiles_name_only_real_tools(self):
        for provider in codehost.PROVIDERS:
            profile = codehost.load_profile(provider)
            with open(os.path.join(HERE, "..", "providers", f"{provider}.tools.json"), encoding="utf-8") as f:
                real = {t["name"] for t in json.load(f)}
            self.assertEqual(set(profile["tools"]), real, provider)

    def test_code_calls_only_profile_tools(self):
        with open(CODEHOST, encoding="utf-8") as f:
            src = f.read()
        classes = {"github": src.split("class GitHub:")[1].split("class GitLab:")[0],
                   "gitlab": src.split("class GitLab:")[1].split("PROVIDERS =")[0]}
        import re
        for provider, body in classes.items():
            used = set(re.findall(r'call(?:_json)?\("([a-z_]+)"', body))
            self.assertTrue(used)
            self.assertLessEqual(used, set(codehost.load_profile(provider)["tools"]), provider)


if __name__ == "__main__":
    unittest.main()
