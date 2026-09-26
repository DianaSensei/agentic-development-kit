#!/usr/bin/env python3
"""ci/common.sh, the helpers the review and maintain runners share.

Run: python3 -m unittest discover -s ci/tests
"""

import json
import os
import subprocess
import tempfile
import unittest

COMMON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "common.sh")
CLEAN = {k: v for k, v in os.environ.items()
         if not k.startswith(("OTEL_", "CLAUDE_CODE_", "ANTHROPIC_", "ADK_"))}


def bash(script, **env):
    p = subprocess.run(["bash", "-c", f'. "{COMMON}"; {script}'], env=dict(CLEAN, **env),
                       capture_output=True, text=True, timeout=30)
    return p.returncode, p.stdout.strip()


class CredentialTests(unittest.TestCase):
    def test_none(self):
        self.assertEqual(bash("adk_has_claude_credential")[0], 1)

    def test_each_kind(self):
        for var in ("ANTHROPIC_API_KEY", "CLAUDE_CODE_OAUTH_TOKEN", "CLAUDE_CODE_USE_BEDROCK"):
            self.assertEqual(bash("adk_has_claude_credential", **{var: "x"})[0], 0, var)
        self.assertEqual(bash("adk_has_claude_credential", ADK_CLAUDE_AUTH="preconfigured")[0], 0)


class TelemetryTests(unittest.TestCase):
    SHOW = "adk_telemetry review; env | grep -E '^(OTEL_|CLAUDE_CODE_)' | sort"

    def env_after(self, **env):
        return dict(line.split("=", 1) for line in bash(self.SHOW, **env)[1].splitlines())

    def test_off_without_a_collector(self):
        self.assertEqual(self.env_after(), {})

    def test_on_with_a_collector(self):
        e = self.env_after(OTEL_EXPORTER_OTLP_ENDPOINT="https://otel.test", ADK_PROVIDER="gitlab",
                           ADK_PROJECT="shop/orders api", ADK_CHANGE_ID="7")
        self.assertEqual(e["CLAUDE_CODE_ENABLE_TELEMETRY"], "1")
        self.assertEqual(e["OTEL_TRACES_EXPORTER"], "otlp")
        self.assertEqual(e["OTEL_EXPORTER_OTLP_PROTOCOL"], "http/protobuf")
        self.assertEqual(e["OTEL_RESOURCE_ATTRIBUTES"],
                         "adk.run=review,adk.provider=gitlab,adk.project=shop%2Forders%20api,adk.change=7")
        self.assertNotIn("OTEL_LOG_TOOL_CONTENT", e)

    def test_settings_already_made_win(self):
        e = self.env_after(OTEL_EXPORTER_OTLP_ENDPOINT="https://otel.test", OTEL_EXPORTER_OTLP_PROTOCOL="grpc",
                           OTEL_TRACES_EXPORTER="none", OTEL_RESOURCE_ATTRIBUTES="team=payments")
        self.assertEqual(e["OTEL_EXPORTER_OTLP_PROTOCOL"], "grpc")
        self.assertEqual(e["OTEL_TRACES_EXPORTER"], "none")
        self.assertEqual(e["OTEL_RESOURCE_ATTRIBUTES"], "team=payments,adk.run=review")


class TranscriptTests(unittest.TestCase):
    def test_result_and_stats(self):
        d = tempfile.mkdtemp()
        t = os.path.join(d, "transcript.jsonl")
        with open(t, "w") as f:
            f.write('{"type":"system","subtype":"init"}\nnot json\n')
            f.write(json.dumps({"type": "result", "subtype": "success", "total_cost_usd": 0.4159,
                                "num_turns": 14, "duration_ms": 185000,
                                "structured_output": {"blocking": 2}}) + "\n")
        out = os.path.join(d, "result.json")
        self.assertEqual(bash(f'adk_run_result "{t}" "{out}"')[0], 0)
        self.assertEqual(json.load(open(out))["structured_output"], {"blocking": 2})
        self.assertEqual(bash(f'adk_run_stats "{out}"')[1], "$0.42 · 14 turns · 3m 5s")

    def test_no_result(self):
        d = tempfile.mkdtemp()
        t = os.path.join(d, "transcript.jsonl")
        with open(t, "w") as f:
            f.write('{"type":"system"}\n')
        self.assertEqual(bash(f'adk_run_result "{t}" "{d}/r.json"')[0], 1)


if __name__ == "__main__":
    unittest.main()
