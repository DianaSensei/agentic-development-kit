#!/usr/bin/env bash
# The shop, with the maintained-counter proposal chosen and its tickets written and checked (all tight):
# U1 alone in wave 1, U2/U3/U5 in wave 2, U4 in wave 3.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
bash "$HERE/../_shop/base.sh" "$1"
cd "$1"
printf -- '---\nstatus: in-progress\nplan: docs/plans/order-count.md\n---\n# Customers cannot see how many orders they have placed\n' > docs/intents/order-count.md
git add -A && git commit -qm "intent: order count"
mkdir -p docs/plans
{
cat <<'EOF'
Intent: docs/intents/order-count.md

# Feature: order count on the customer dashboard

## ✅ Chosen: maintained `order_count` counter on `customers`
`dashboard.render` reads a counter kept on the customer row, updated in the same transaction as each
order write - O(1) on the hot path. Existing databases get the column and the initial counts from
`scripts/backfill_order_count.py`.

### Acceptance Criteria
- AC-1: the dashboard's `order_count` equals the customer's current number of orders; cancelled orders do not count.
- AC-2: `place_order` increments and `cancel_order` decrements the counter atomically, in the existing transaction.
- AC-3: `render` runs one query and never touches `orders`.
- AC-4: `scripts/backfill_order_count.py <db_path>` adds the column if missing and sets every count from `orders`.

## Parallel units

| Unit | Task | Files | Depends on |
|---|---|---|---|
| U1 | `order_count` column in the schema | `db/schema.sql` | - |
| U2 | increment/decrement in `place_order`/`cancel_order` | `src/shop/orders.py` | U1 |
| U3 | `render` reads `order_count` | `src/shop/dashboard.py` | U1 |
| U4 | tests: counts, cancels, drift, no `orders` query | `tests/test_orders.py` | U2, U3 |
| U5 | backfill script and its tests | `scripts/backfill_order_count.py`, `tests/test_backfill_order_count.py` | U1 |

Waves: U1; then U2, U3, U5; then U4.

## Tickets

```json
EOF
cat "$HERE/tickets.json"
printf '\n```\n\nTiers (check_tickets.py): all tight.\n'
} > docs/plans/order-count.md
