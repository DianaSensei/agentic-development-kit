#!/usr/bin/env bash
# A change that is small and plausible, described as doing three things it does
# not do. The code has no planted bug of its own: what the reviewer must catch
# is the distance between the description and the diff.
set -euo pipefail
mkdir -p .claude && printf '{"enabledPlugins":{"adk-adlc@agentic-development-kit":true}}\n' > .claude/settings.json
git init -q -b main
export GIT_AUTHOR_NAME=eval GIT_AUTHOR_EMAIL=eval@example.com GIT_COMMITTER_NAME=eval GIT_COMMITTER_EMAIL=eval@example.com
mkdir -p src/billing tests
cat > CLAUDE.md <<'MD'
# Billing
Python. Invoicing lives in src/billing. Every behavior change ships with a pytest test in tests/.
MD
touch src/__init__.py src/billing/__init__.py tests/__init__.py
cat > src/billing/invoice.py <<'PY'
def total(lines):
    """Sum of price * quantity over the invoice lines."""
    return sum(price * qty for price, qty in lines)


def apply_tax(amount, rate):
    """Amount with tax added; rate is a fraction, e.g. 0.08 for 8%."""
    return amount * (1 + rate)
PY
cat > tests/test_invoice.py <<'PY'
from src.billing.invoice import apply_tax, total


def test_total():
    assert total([(2.5, 2), (1.0, 3)]) == 8.0


def test_apply_tax():
    assert apply_tax(100, 0.08) == 108.0
PY
git add -A && git commit -qm "Billing: invoice totals and tax"
git checkout -qb billing/round-totals
cat > src/billing/invoice.py <<'PY'
import math


def total(lines):
    """Sum of price * quantity over the invoice lines, in cents precision."""
    raw = sum(price * qty for price, qty in lines)
    return math.floor(raw * 100) / 100


def apply_tax(amount, rate):
    """Amount with tax added; rate is a percentage, e.g. 8 for 8%."""
    return total([(amount * (1 + rate / 100), 1)])
PY
git commit -qam "Round invoice totals to cents"
cat > change.md <<'MD'
# Round invoice totals to cents; add tests

- Branch: billing/round-totals into main

## Description

Finance asked for invoice totals to be rounded to cents.

- `total()` now rounds to 2 decimals with banker's rounding (ROUND_HALF_EVEN), as finance specified.
- Adds tests for the rounding edge cases (half-cent values, negative credit lines).
- No behavior change for `apply_tax`.
MD
# Runs get no shell (see evals/README.md), so hand over the diff the way CI does.
git diff main...HEAD > review.diff
