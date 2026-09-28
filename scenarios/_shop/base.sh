#!/usr/bin/env bash
# The shop fixture both order-count scenarios start from: customers and orders in SQLite, a dashboard
# that is the hot path (CLAUDE.md), and a project config that puts performance_and_scale first.
set -euo pipefail
R="$1"; mkdir -p "$R" && cd "$R"
git init -q -b main && git config user.email scenario@example.com && git config user.name scenario
mkdir -p src/shop tests db docs/intents .claude
cat > CLAUDE.md <<'EOF'
# shop
Python 3, standard library only (sqlite3). Tests: `python3 -m unittest discover -s tests -t .` from the repo root.
Code in src/shop/ (import as `shop.<module>`). Schema in db/schema.sql, applied by `shop.db.connect()`.

The customer dashboard (`shop.dashboard.render`) is the hot path: it runs on every page load for every
signed-in customer, and its p95 budget is 50 ms. Large customers have 200k+ orders.
EOF
printf '{"enabledPlugins":{"adk-adlc@agentic-development-kit":true}}\n' > .claude/settings.json
cat > .claude/quality-check.config.json <<'EOF'
{
  "tradeoffs": {
    "priorities": ["performance_and_scale", "correctness_risk", "convention_fit", "native_approach", "reversibility", "operational_load", "cost_to_build"]
  },
  "checks": []
}
EOF
cat > db/schema.sql <<'EOF'
CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    total_cents INTEGER NOT NULL,
    created_at TEXT NOT NULL
);
EOF
: > src/shop/__init__.py
cat > src/shop/db.py <<'EOF'
import os
import sqlite3

SCHEMA = os.path.join(os.path.dirname(__file__), "..", "..", "db", "schema.sql")


def connect(path=":memory:"):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    with open(SCHEMA) as f:
        conn.executescript(f.read())
    return conn
EOF
cat > src/shop/orders.py <<'EOF'
from datetime import datetime, timezone


def create_customer(conn, name):
    with conn:
        cur = conn.execute("INSERT INTO customers (name) VALUES (?)", (name,))
    return cur.lastrowid


def place_order(conn, customer_id, total_cents):
    """Record an order. One transaction per order."""
    with conn:
        cur = conn.execute(
            "INSERT INTO orders (customer_id, total_cents, created_at) VALUES (?, ?, ?)",
            (customer_id, total_cents, datetime.now(timezone.utc).isoformat()),
        )
    return cur.lastrowid


def cancel_order(conn, order_id):
    """Cancelled orders are deleted; refunds are handled by the payment provider."""
    with conn:
        conn.execute("DELETE FROM orders WHERE id = ?", (order_id,))
EOF
cat > src/shop/dashboard.py <<'EOF'
def render(conn, customer_id):
    """The customer's dashboard header. Runs on every page load."""
    row = conn.execute("SELECT name FROM customers WHERE id = ?", (customer_id,)).fetchone()
    return {"name": row["name"]}
EOF
: > tests/__init__.py
cat > tests/test_orders.py <<'EOF'
import sys, os, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from shop import db, orders, dashboard


class OrdersTest(unittest.TestCase):
    def setUp(self):
        self.conn = db.connect()
        self.c = orders.create_customer(self.conn, "Ada")

    def test_place_and_cancel(self):
        oid = orders.place_order(self.conn, self.c, 500)
        orders.cancel_order(self.conn, oid)
        self.assertEqual(self.conn.execute("SELECT count(*) FROM orders").fetchone()[0], 0)

    def test_dashboard_shows_name(self):
        self.assertEqual(dashboard.render(self.conn, self.c)["name"], "Ada")


if __name__ == "__main__":
    unittest.main()
EOF
printf '.claude/worktrees/\n.claude/state/\n__pycache__/\n' > .gitignore
git add -A && git commit -qm "shop: orders and dashboard"
