#!/usr/bin/env bash
# A function whose validation and pricing are interleaved, and a profile whose Code
# style keeps a long function whole when its flow reads straight through. The kit's
# decomposition heuristic (SLAP) would split place_order into helpers; the profile
# wins over it, so the refactor proposed at the Checkpoint untangles the flow inside
# the one function. A headless run stops at that Checkpoint and edits nothing in src/.
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
cat > src/shop/checkout.py <<'PY'
TAX = {"VN": 0.10, "SG": 0.09}


def place_order(lines, country, coupon_rate=0.0):
    if not lines:
        raise ValueError("empty order")
    subtotal = 0.0
    for sku, price, qty in lines:
        if qty <= 0:
            raise ValueError(f"bad quantity for {sku}")
        subtotal += price * qty
    if country not in TAX:
        raise ValueError(f"no tax rule for {country}")
    if coupon_rate:
        if not 0 < coupon_rate < 1:
            raise ValueError("bad coupon rate")
        subtotal = subtotal * (1 - coupon_rate)
    tax = subtotal * TAX[country]
    total = round(subtotal + tax, 2)
    if total > 10000:
        raise ValueError("needs manual approval")
    return {"subtotal": round(subtotal, 2), "tax": round(tax, 2), "total": total}
PY
cat > tests/test_checkout.py <<'PY'
import pytest

from src.shop.checkout import place_order


def test_total_with_tax_and_coupon():
    assert place_order([("a", 50.0, 2)], "VN", 0.10) == {"subtotal": 90.0, "tax": 9.0, "total": 99.0}


def test_rejects_unknown_country():
    with pytest.raises(ValueError, match="no tax rule"):
        place_order([("a", 1.0, 1)], "XX")
PY
git add -A && git -c user.email=eval@example.com -c user.name=eval commit -qm "Checkout"
mkdir -p profile
cat > profile/profile.md <<'MD'
# How I work
<!-- A project's CLAUDE.md, REVIEW.md and checks override anything here. -->

## Code style _(statement; 2026-11)_
- Least change: the smallest edit that reaches the goal, in the file's existing style.
- Keep a long function whole when its flow reads straight through; split out a function only when the code is reused or I ask.

## Refactor _(statement; 2026-11)_
- Order the steps from least impact to most; each step builds and passes on its own.
MD
