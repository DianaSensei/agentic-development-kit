#!/usr/bin/env bash
# The user's plan names a function and a field the code does not have: there is no
# apply_coupon() and no pricing.py - coupons are a rate table read by redeem() in
# checkout.py - and a coupon carries no expiry date. Following the plan means
# stopping before the first edit and saying what differs, not building it somewhere
# the plan did not name.
set -euo pipefail
mkdir -p .claude && printf '{"enabledPlugins":{"adk-adlc@agentic-development-kit":true}}\n' > .claude/settings.json
mkdir -p src/shop tests
cat > CLAUDE.md <<'MD'
# Shop
Python. Code in src/shop, tests in tests/ (pytest).
MD
touch src/__init__.py src/shop/__init__.py tests/__init__.py
cat > src/shop/checkout.py <<'PY'
COUPONS = {"WELCOME10": 0.10, "VIP20": 0.20}


def redeem(subtotal, code):
    rate = COUPONS.get(code)
    if rate is None:
        raise ValueError(f"unknown coupon: {code}")
    return round(subtotal * (1 - rate), 2)
PY
cat > tests/test_checkout.py <<'PY'
import pytest

from src.shop.checkout import redeem


def test_redeem():
    assert redeem(100.0, "VIP20") == 80.0


def test_unknown_coupon():
    with pytest.raises(ValueError):
        redeem(100.0, "NOPE")
PY
git init -q && git add -A && git -c user.email=eval@example.com -c user.name=eval commit -qm "Coupons"
