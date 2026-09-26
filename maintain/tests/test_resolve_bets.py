#!/usr/bin/env python3
"""resolve-bets.py, and maintain/run.sh judging a bet end to end.

Run: python3 -m unittest discover -s maintain/tests
The end-to-end test needs git and PyYAML; it uses a local bare repository as
`origin` and codehost's fake MCP server, so no account, token or model.
"""

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.abspath(os.path.join(HERE, "..", ".."))
spec = importlib.util.spec_from_file_location("resolve_bets", os.path.join(KIT, "maintain", "resolve-bets.py"))
rb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rb)

import datetime  # noqa: E402

INTENT = """---
title: Checkout hangs on card payment
status: {status}
type: bug
originator: Lan
created: 2026-08-01
updated: {updated}
plan:
changelog: docs/postmortems/checkout-hangs.md
superseded_by:
signal_band: {band}
resolution: {resolution}
---

# Checkout hangs on card payment

## Problem
x

## Evidence
- none yet

## Desired outcome
x

## Success signal
p95 checkout under 10s

## Non-goals
- none stated

## Affected systems
| System / area | Why it is affected | Source |
|---|---|---|
| checkout | x | originator said |

## Constraints
none stated

## Originator's idea (non-binding)
none

## Open questions
- none

## Decision log
- 2026-08-01 - created as proposed by Lan
- 2026-09-01 - done
"""

BANDS = {
    "checkout-p95": {"name": "checkout-p95", "status": "ok", "value": 4200.0, "min": None, "max": 10000},
    "error-rate": {"name": "error-rate", "status": "breach", "value": 7.5, "min": None, "max": 2},
    "broken": {"name": "broken", "status": "error", "reason": "stdout is not a single number",
               "value": None, "min": None, "max": 1},
}
TODAY = datetime.date(2026, 9, 26)


def intent(status="done", updated="2026-09-01", band="checkout-p95", resolution=""):
    return INTENT.format(status=status, updated=updated, band=band, resolution=resolution)


class JudgeTests(unittest.TestCase):
    def judge(self, text):
        return rb.judge("x.md", text, BANDS, TODAY, 14)

    def test_band_in_range_is_met(self):
        action, verdict, detail = self.judge(intent())
        self.assertEqual((action, verdict), ("resolve", "met"))
        self.assertIn("`checkout-p95` = 4200 (band <= 10000)", detail)

    def test_breach_is_not_met(self):
        self.assertEqual(self.judge(intent(band="error-rate"))[:2], ("resolve", "not-met"))

    def test_too_recent_waits(self):
        action, _, detail = self.judge(intent(updated="2026-09-20"))
        self.assertEqual(action, "waiting")
        self.assertIn("2026-10-04", detail)

    def test_broken_or_missing_band_stays_open(self):
        self.assertEqual(self.judge(intent(band="broken"))[0], "open")
        self.assertEqual(self.judge(intent(band="nope"))[0], "open")

    def test_not_done_no_band_or_already_resolved_is_skipped(self):
        for text in (intent(status="in-progress"), intent(band=""), intent(resolution="met")):
            self.assertEqual(self.judge(text)[0], "skip")

    def test_resolve_edits_only_two_keys_and_the_log(self):
        before = intent()
        after = rb.resolve(before, "not-met", "`x` = 1 (band <= 0)", TODAY, "https://ci/run/1")
        self.assertIn("\nresolution: not-met\n", after)
        self.assertIn("\nupdated: 2026-09-26\n", after)
        self.assertTrue(after.endswith(
            "- 2026-09-26 - bet resolved as not met: `x` = 1 (band <= 0) - maintain loop, https://ci/run/1\n"))
        changed = [(a, b) for a, b in zip(before.splitlines(), after.splitlines()) if a != b]
        self.assertEqual(len(changed), 2)

    def test_older_intent_without_the_keys_gets_them(self):
        old = intent().replace("signal_band: checkout-p95\nresolution: \n", "")
        self.assertEqual(self.judge(old)[0], "skip")  # no signal_band: nothing to judge
        added = rb.set_keys(old, {"resolution": "met"})
        self.assertIn("\nresolution: met\n---\n", added)


class CheckerTests(unittest.TestCase):
    CHECK = os.path.join(KIT, "skills", "intent-capture", "scripts", "check-intent.sh")

    def check(self, text):
        d = tempfile.mkdtemp()
        p = os.path.join(d, "i.md")
        with open(p, "w") as f:
            f.write(text)
        r = subprocess.run(["bash", self.CHECK, p], capture_output=True, text=True)
        return r.returncode, r.stdout

    def test_resolved_intent_passes(self):
        self.assertEqual(self.check(intent(resolution="met"))[0], 0)

    def test_intent_without_the_new_keys_still_passes(self):
        old = intent().replace("signal_band: checkout-p95\nresolution: \n", "")
        self.assertEqual(self.check(old)[0], 0)

    def test_bad_resolutions_fail(self):
        self.assertIn("is not met or not-met", self.check(intent(resolution="yes"))[1])
        self.assertIn("status is not done", self.check(intent(status="in-progress", resolution="met"))[1])
        self.assertIn("without the signal_band", self.check(intent(band="", resolution="met"))[1])


@unittest.skipUnless(shutil.which("git"), "needs git")
class RunShTests(unittest.TestCase):
    def test_bet_resolved_and_published_without_claude(self):
        try:
            import yaml  # noqa: F401
        except ImportError:
            self.skipTest("needs PyYAML")
        tmp = tempfile.mkdtemp()
        origin, repo = os.path.join(tmp, "origin.git"), os.path.join(tmp, "repo")
        env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t",
                   GIT_COMMITTER_EMAIL="t@t")
        run = lambda *a, cwd=repo: subprocess.run(a, cwd=cwd, env=env, check=True, capture_output=True, text=True)
        run("git", "init", "-q", "--bare", "-b", "main", origin, cwd=tmp)
        run("git", "clone", "-q", origin, repo, cwd=tmp)
        os.makedirs(os.path.join(repo, "docs", "intents"))
        with open(os.path.join(repo, "docs", "intents", "checkout-hangs.md"), "w") as f:
            f.write(intent(updated="2026-01-01"))
        with open(os.path.join(repo, "bands.yaml"), "w") as f:
            f.write("bands:\n  - name: checkout-p95\n    command: echo 4200\n    max: 10000\n    tier: observe\n")
        run("git", "checkout", "-q", "-b", "main")
        run("git", "add", "-A")
        run("git", "commit", "-qm", "init")
        run("git", "push", "-q", "origin", "main")

        state, log = os.path.join(tmp, "state.json"), os.path.join(tmp, "calls.jsonl")
        renv = dict(env, ADK_PROVIDER="github", ADK_PROJECT="acme/shop", ADK_CODEHOST_TOKEN="t0ken",
                    ADK_DEFAULT_BRANCH="main", ADK_WORK_DIR=os.path.join(tmp, "work"),
                    ADK_CODEHOST_SERVER=json.dumps([sys.executable, os.path.join(KIT, "codehost", "tests", "fake_server.py")]),
                    FAKE_PROVIDER="github", FAKE_STATE=state, FAKE_LOG=log)
        for k in ("ANTHROPIC_API_KEY", "CLAUDE_CODE_OAUTH_TOKEN", "ANTHROPIC_AUTH_TOKEN", "ADK_CLAUDE_AUTH"):
            renv.pop(k, None)
        p = subprocess.run(["bash", os.path.join(KIT, "maintain", "run.sh")], cwd=repo, env=renv,
                           capture_output=True, text=True, timeout=120)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("resolved docs/intents/checkout-hangs.md met", p.stdout)

        published = run("git", "show", "maintain/proposed-intents:docs/intents/checkout-hangs.md", cwd=origin)
        self.assertIn("\nresolution: met\n", published.stdout)
        self.assertIn("bet resolved as met: `checkout-p95` = 4200 (band <= 10000)", published.stdout)
        with open(state) as f:
            prs = json.load(f)["prs"]
        self.assertEqual([(pr["head"], pr["base"]) for pr in prs], [("maintain/proposed-intents", "main")])

        # Judged once: a second run finds nothing left to resolve.
        p2 = subprocess.run(["bash", os.path.join(KIT, "maintain", "run.sh")], cwd=repo, env=renv,
                            capture_output=True, text=True, timeout=120)
        self.assertEqual(p2.returncode, 0, p2.stdout + p2.stderr)


if __name__ == "__main__":
    unittest.main()
