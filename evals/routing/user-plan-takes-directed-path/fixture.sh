#!/usr/bin/env bash
# The user brings the plan: a loyalty discount whose policy (1.00 off per full 100
# points, capped at 10% of the subtotal) they already decided, in five ordered steps.
# A change with a decision in it would stop at a Checkpoint; here the decision is
# theirs, so the run carries the plan out - no agents, no proposals, no Checkpoint.
set -euo pipefail
mkdir -p .claude && printf '{"enabledPlugins":{"adk-adlc@agentic-development-kit":true}}\n' > .claude/settings.json
mkdir -p src/shop tests
cat > CLAUDE.md <<'MD'
# Shop
Python. Code in src/shop, tests in tests/ (pytest).
MD
touch src/__init__.py src/shop/__init__.py tests/__init__.py
cat > src/shop/orders.py <<'PY'
from dataclasses import dataclass, field


@dataclass
class Line:
    sku: str
    price: float
    qty: int


@dataclass
class Order:
    lines: list = field(default_factory=list)

    def subtotal(self):
        return sum(l.price * l.qty for l in self.lines)

    def total(self):
        return round(self.subtotal(), 2)
PY
cat > src/shop/receipt.py <<'PY'
def render(order):
    out = [f"{l.sku} x{l.qty}  {l.price * l.qty:.2f}" for l in order.lines]
    out.append(f"Total  {order.total():.2f}")
    return "\n".join(out)
PY
cat > tests/test_orders.py <<'PY'
from src.shop.orders import Line, Order
from src.shop.receipt import render


def test_total():
    assert Order([Line("a", 10.0, 2)]).total() == 20.0


def test_receipt_ends_with_total():
    assert render(Order([Line("a", 10.0, 2)])).splitlines()[-1] == "Total  20.00"
PY
git init -q && git add -A && git -c user.email=eval@example.com -c user.name=eval commit -qm "Shop orders"
