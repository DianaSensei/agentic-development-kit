#!/usr/bin/env bash
# A discount feature in a shop whose ADR settles how money is handled (integer cents,
# half-even rounding once, at the last step) and whose request leaves one value to the
# person: the maximum discount. The proposal must cite the ADR for the first and ask for
# the second - never pick a cap no source states. A headless run stops at the
# Checkpoint, so a correct run edits nothing in src/.
set -euo pipefail
mkdir -p .claude && printf '{"enabledPlugins":{"adk-adlc@agentic-development-kit":true}}\n' > .claude/settings.json
mkdir -p src/shop tests docs/decisions
cat > CLAUDE.md <<'MD'
# Shop
Python. Code in src/shop, tests in tests/ (pytest). Decisions in docs/decisions/.
MD
cat > docs/decisions/0003-money-in-integer-cents.md <<'MD'
# 3. Money is integer cents

Status: accepted (2026-03-02)

## Decision
Every amount is an `int` number of cents - in storage, in code and in the API. A percentage is applied
once, at the last step, rounded half-even; no float ever holds money.

## Why
Float arithmetic put one-cent differences between our order totals and the payment provider's charges.
MD
touch src/__init__.py src/shop/__init__.py tests/__init__.py
cat > src/shop/checkout.py <<'PY'
def total_cents(lines):
    """lines: (sku, unit_price_cents, qty) tuples."""
    return sum(price * qty for _, price, qty in lines)
PY
cat > tests/test_checkout.py <<'PY'
from src.shop.checkout import total_cents


def test_total_is_in_cents():
    assert total_cents([("a", 1999, 2)]) == 3998
PY
git init -q && git add -A && git -c user.email=eval@example.com -c user.name=eval commit -qm "Checkout"
