#!/usr/bin/env bash
# Shared by ci/review.sh and maintain/run.sh - sourced, not run.

# adk_has_claude_credential - true when Claude Code can sign in on this job.
adk_has_claude_credential() {
  local v
  for v in ANTHROPIC_API_KEY CLAUDE_CODE_OAUTH_TOKEN ANTHROPIC_AUTH_TOKEN \
           CLAUDE_CODE_USE_BEDROCK CLAUDE_CODE_USE_VERTEX CLAUDE_CODE_USE_FOUNDRY; do
    [ -n "${!v:-}" ] && return 0
  done
  # A self-hosted runner where Claude Code is already signed in says so explicitly.
  [ "${ADK_CLAUDE_AUTH:-}" = "preconfigured" ]
}

# adk_telemetry <run> - when the CI provides an OTLP collector
# (OTEL_EXPORTER_OTLP_ENDPOINT, plus OTEL_EXPORTER_OTLP_HEADERS for its
# credential), export Claude Code's metrics, events and traces for this run,
# labelled so one run can be found among many: adk.run (review | maintain),
# adk.provider, adk.project, adk.change. Every OTEL_* variable already set wins.
# Tool parameters and content stay out unless the CI turns them on with
# OTEL_LOG_TOOL_DETAILS / OTEL_LOG_TOOL_CONTENT: a pull request's code is not
# the collector's to keep by default.
adk_telemetry() {
  [ -n "${OTEL_EXPORTER_OTLP_ENDPOINT:-}" ] || return 0
  export CLAUDE_CODE_ENABLE_TELEMETRY=1
  export CLAUDE_CODE_ENHANCED_TELEMETRY_BETA="${CLAUDE_CODE_ENHANCED_TELEMETRY_BETA:-1}"
  export OTEL_METRICS_EXPORTER="${OTEL_METRICS_EXPORTER:-otlp}"
  export OTEL_LOGS_EXPORTER="${OTEL_LOGS_EXPORTER:-otlp}"
  export OTEL_TRACES_EXPORTER="${OTEL_TRACES_EXPORTER:-otlp}"
  export OTEL_EXPORTER_OTLP_PROTOCOL="${OTEL_EXPORTER_OTLP_PROTOCOL:-http/protobuf}"
  # A CI run lives for minutes; the 60s default would lose the last minute of metrics.
  export OTEL_METRIC_EXPORT_INTERVAL="${OTEL_METRIC_EXPORT_INTERVAL:-5000}"
  local attrs
  attrs="$(python3 - "$1" <<'EOF'
import os, sys
from urllib.parse import quote
pairs = [("adk.run", sys.argv[1]), ("adk.provider", os.environ.get("ADK_PROVIDER", "")),
         ("adk.project", os.environ.get("ADK_PROJECT", "")), ("adk.change", os.environ.get("ADK_CHANGE_ID", ""))]
print(",".join(f"{k}={quote(v, safe='')}" for k, v in pairs if v))
EOF
)"
  export OTEL_RESOURCE_ATTRIBUTES="${OTEL_RESOURCE_ATTRIBUTES:+$OTEL_RESOURCE_ATTRIBUTES,}$attrs"
}

# adk_run_result <transcript.jsonl> <out.json> - the final result message of a
# `claude -p --output-format stream-json` transcript, written as JSON; false
# when the run produced none.
adk_run_result() {
  python3 - "$1" "$2" <<'EOF'
import json, sys
last = None
with open(sys.argv[1], errors="replace") as f:
    for line in f:
        try:
            msg = json.loads(line)
        except ValueError:
            continue
        if msg.get("type") == "result":
            last = msg
if last is None:
    sys.exit(1)
with open(sys.argv[2], "w") as f:
    json.dump(last, f)
EOF
}

# adk_run_stats <result.json> - "$0.42 · 14 turns · 3m 5s" for a summary line.
adk_run_stats() {
  python3 - "$1" <<'EOF'
import json, sys
r = json.load(open(sys.argv[1]))
parts = []
if r.get("total_cost_usd") is not None:
    parts.append(f"${r['total_cost_usd']:.2f}")
if r.get("num_turns") is not None:
    parts.append(f"{r['num_turns']} turns")
if r.get("duration_ms") is not None:
    s = int(r["duration_ms"] / 1000)
    parts.append(f"{s // 60}m {s % 60}s" if s >= 60 else f"{s}s")
print(" · ".join(parts))
EOF
}
