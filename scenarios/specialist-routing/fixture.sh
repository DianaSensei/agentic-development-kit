#!/usr/bin/env bash
# textkit (the waves fixture), with a code-writing project specialist - python-engineer - that the
# project routes through units, and U2 assigned to it.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
bash "$HERE/../waves-and-resume/fixture.sh" "$1"
cd "$1"
mkdir -p .claude/agents
cat > .claude/agents/python-engineer.md <<'EOF'
---
name: python-engineer
description: Use this agent to implement AND test Python modules in this project - standard library only, one test module per source module, unittest.
tools: Read, Write, Edit, Grep, Glob, Bash
---
You are this project's Python engineer. Write small pure functions with type hints and a one-line
docstring each; name tests `test_<behaviour>`; every public function gets at least one test for its
normal case and one for its edge case. Run the project's test command before reporting.
EOF
printf '{"dispatch_gate": {"route_through_units": ["python-engineer"]}}\n' > .claude/quality-check.config.json
git add -A && git commit -qm "project specialist: python-engineer"
python3 - <<'EOF'
p = "docs/plans/text-helpers.md"
s = open(p).read()
s = s.replace("| Unit | Task | Files | Depends on |\n|------|------|-------|------------|",
              "| Unit | Task | Files | Depends on | Assigned agent |\n|------|------|-------|------------|----------------|")
s = s.replace("`tests/test_wordfreq.py` | - |", "`tests/test_wordfreq.py` | - | - |")
s = s.replace("`tests/test_slug.py` | - |", "`tests/test_slug.py` | - | `python-engineer` (.claude/agents/python-engineer.md) |")
s = s.replace("`tests/test_report.py` | U1 |", "`tests/test_report.py` | U1 | - |")
open(p, "w").write(s)
EOF
