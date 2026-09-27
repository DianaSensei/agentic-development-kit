#!/usr/bin/env bash
set -euo pipefail
# A project whose logging convention lives only in a checker, not in CLAUDE.md:
# the hook (hooks/check-conventions.sh) is what tells Claude about it, right after
# the edit that breaks it.
mkdir -p .claude src/app tools
printf '{"enabledPlugins":{"adk-adlc@agentic-development-kit":true}}\n' > .claude/settings.json
cat > .claude/quality-check.config.json <<'JSON'
{
  "mode": {"convention_checks": "warn"},
  "checks": [
    {"name": "app-logging", "match": "^src/.*\\.py$", "run": "python3 tools/check_logging.py {file}"}
  ]
}
JSON
cat > CLAUDE.md <<'MD'
# Pricing service
Python 3, standard library only. Code lives in src/app/.
MD
cat > src/app/__init__.py <<'PY'
PY
cat > src/app/log.py <<'PY'
"""The service's logging: structured, with the request id attached."""
import logging


def get_logger(name):
    return logging.getLogger(f"pricing.{name}")
PY
cat > src/app/pricing.py <<'PY'
def subtotal(items):
    return sum(price * qty for price, qty in items)
PY
cat > tools/check_logging.py <<'PY'
"""Service code logs through app.log.get_logger, so every line carries the request id.

Fails on print() and on importing the standard logging module directly (only
src/app/log.py may).
"""
import re
import sys

path = sys.argv[1]
if path.replace("\\", "/").endswith("src/app/log.py"):
    sys.exit(0)
problems = []
for n, line in enumerate(open(path, encoding="utf-8"), 1):
    if re.search(r"\bprint\(", line):
        problems.append(f"{path}:{n}: print() - log with app.log.get_logger(__name__) instead")
    if re.match(r"\s*(import logging\b|from logging import)", line):
        problems.append(f"{path}:{n}: imports logging directly - use `from app.log import get_logger`")
print("\n".join(problems))
sys.exit(1 if problems else 0)
PY
git init -q && git add -A && git -c user.email=eval@example.com -c user.name=eval commit -qm "Pricing service"
