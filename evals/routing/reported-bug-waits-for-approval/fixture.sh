#!/usr/bin/env bash
# A plain one-line bug - the receipt counts one item too few - reported as a symptom,
# not as a change, by someone whose profile asks to approve every fix they did not
# spell out. Without that profile it is a quick change; with it, it goes to bug-fix
# at light depth and waits at the Checkpoint. A headless run can never confirm it,
# so a correct run edits nothing.
set -euo pipefail
mkdir -p .claude && printf '{"enabledPlugins":{"adk-adlc@agentic-development-kit":true}}\n' > .claude/settings.json
git init -q
printf "profile/\n" > .git/info/exclude
mkdir -p src/shop tests
cat > CLAUDE.md <<'MD'
# Shop
Python. Code in src/shop, tests in tests/ (pytest).
MD
touch src/__init__.py src/shop/__init__.py tests/__init__.py
cat > src/shop/receipt.py <<'PY'
def header(order_lines):
    return f"Your order: {len(order_lines) - 1} items"
PY
cat > tests/test_receipt.py <<'PY'
from src.shop.receipt import header


def test_header_mentions_the_order():
    assert header([("a", 1)]).startswith("Your order:")
PY
git add -A && git -c user.email=eval@example.com -c user.name=eval commit -qm "Receipt header"
mkdir -p profile
cat > profile/profile.md <<'MD'
# How I work
<!-- A project's CLAUDE.md, REVIEW.md and checks override anything here. -->

## Working with me _(statement; 2026-11)_
- I am the owner; you are the senior dev: you investigate and propose, I approve before you change code.
- A request that names the exact change is my approval: do it, then report.
- A request that names a problem: investigate, report and wait for my approval, even for a small fix.
MD
