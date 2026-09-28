#!/usr/bin/env bash
# shop pricing, with an uncommitted change: discounted() and a hollow test that passes against
# broken code (it only checks the result is an int).
set -euo pipefail
R="$1"; mkdir -p "$R" && cd "$R"
git init -q -b main && git config user.email scenario@example.com && git config user.name scenario
mkdir -p src/shop tests .claude
cat > CLAUDE.md <<'EOF'
# shop
Python 3, standard library only. Tests: `python3 -m unittest discover -s tests -t .` from the repo root.
Code in src/shop/ (import as `shop.<module>`).
EOF
printf '{"enabledPlugins":{"adk-adlc@agentic-development-kit":true}}\n' > .claude/settings.json
printf '.claude/worktrees/\n.claude/state/\n__pycache__/\n' > .gitignore
: > src/shop/__init__.py
printf 'import os, sys\nsys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))\n' > tests/__init__.py
cat > src/shop/pricing.py <<'EOF'
def subtotal(prices):
    """Sum of item prices, in cents."""
    return sum(prices)
EOF
cat > tests/test_pricing.py <<'EOF'
import unittest

from shop.pricing import subtotal


class Subtotal(unittest.TestCase):
    def test_sums_prices(self):
        self.assertEqual(subtotal([100, 250]), 350)
EOF
git add -A && git commit -qm "shop: subtotal"
cat >> src/shop/pricing.py <<'EOF'


def discounted(total, is_member):
    """Members get 10 off an order of 100 or more (cents)."""
    if is_member and total >= 100:
        return total - 10
    return total
EOF
cat > tests/test_discount.py <<'EOF'
import unittest

from shop.pricing import discounted


class Discount(unittest.TestCase):
    def test_discounted_returns_a_number(self):
        self.assertIsInstance(discounted(150, True), int)
EOF
