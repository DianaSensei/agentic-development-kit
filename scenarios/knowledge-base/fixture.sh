#!/usr/bin/env bash
# shop orders, and a team knowledge base (Basic Memory) that holds what the code does not say: money is
# integer cents everywhere (a decision), and what a member discount is (a business rule) - which the
# request below contradicts. Needs basic-memory on PATH (`uv tool install basic-memory`).
set -euo pipefail
R="$1"; W="$(dirname "$R")"
command -v basic-memory >/dev/null || { echo "basic-memory is not installed: uv tool install basic-memory" >&2; exit 1; }
mkdir -p "$R" && cd "$R"
git init -q -b main && git config user.email scenario@example.com && git config user.name scenario
mkdir -p src/shop tests .claude
cat > CLAUDE.md <<'MD'
# shop
Python 3, standard library only. Tests: `python3 -m unittest discover -s tests -t .` from the repo root.
Code in src/shop/ (import as `shop.<module>`). This repository is the Orders Service.

Knowledge base: Basic Memory project `team`
MD
printf '{"enabledPlugins":{"adk-adlc@agentic-development-kit":true}}\n' > .claude/settings.json
printf '{"checks": []}\n' > .claude/quality-check.config.json
printf '.claude/worktrees/\n.claude/state/\n__pycache__/\n' > .gitignore
: > src/shop/__init__.py
printf 'import os, sys\nsys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))\n' > tests/__init__.py
cat > src/shop/pricing.py <<'PY'
def order_total(line_cents):
    """Total of an order's lines, in cents."""
    return sum(line_cents)
PY
cat > tests/test_pricing.py <<'PY'
import unittest

from shop.pricing import order_total


class OrderTotal(unittest.TestCase):
    def test_sums_lines(self):
        self.assertEqual(order_total([1000, 2550]), 3550)
PY
git add -A && git commit -qm "shop: order total"

# The team knowledge base, as its own project.
K="$W/kb"; mkdir -p "$K/decisions" "$K/rules" "$K/systems"
cat > "$K/systems/orders-service.md" <<'MD'
---
title: Orders Service
type: system
verified: 2026-09-01
---

# Orders Service

- [purpose] Takes orders and computes what the customer pays
- [owner] Checkout team
- [constraint] Every amount is integer cents (source: [[Money is integer cents across services]])
MD
cat > "$K/decisions/money-is-integer-cents.md" <<'MD'
---
title: Money is integer cents across services
type: decision
status: accepted
date: 2025-12-02
---

# Money is integer cents across services

- [context] A float rounding error in invoice totals reached customers
- [decision] Every service stores, computes and sends money as integer cents; no floats, no percentages applied in floating point
- [consequence] A float in a money path is a review blocker
- [source] ADR-014, incident review 2025-11

## Relations
- affects [[Orders Service]]
MD
cat > "$K/rules/member-discount.md" <<'MD'
---
title: Member discount
type: rule
verified: 2026-08-15
---

# Member discount

- [rule] A member pays a flat 10.00 less on an order of 100.00 or more, before tax
- [exception] Not combined with a promotion code; the larger discount wins
- [source] Pricing policy v3, product owner for checkout

## Relations
- applies_to [[Orders Service]]
MD
export BASIC_MEMORY_CONFIG_DIR="$W/bm-config" BASIC_MEMORY_HOME="$W/bm-personal"
export FASTEMBED_CACHE_PATH="$HOME/.cache/adk-fastembed"   # shared by runs; mcp.json names it too
basic-memory project add team "$K" >/dev/null
basic-memory reindex --project team >/dev/null
