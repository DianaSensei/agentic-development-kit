#!/usr/bin/env bash
# The shop, and an accepted intent: show each customer's order count on the dashboard - the hot path.
set -euo pipefail
bash "$(dirname "$0")/../_shop/base.sh" "$1"
cd "$1"
cat > docs/intents/order-count.md <<'EOF'
---
title: Customers cannot see how many orders they have placed
status: accepted
type: feature
originator: Mai (product)
created: 2026-09-27
updated: 2026-09-27
plan:
changelog:
superseded_by:
signal_band:
resolution:
---

# Customers cannot see how many orders they have placed

## Problem
Customers ask support how many orders they have placed with us; the dashboard does not say.

## Evidence
- support tickets: about 40 a week ask for an order count

## Desired outcome
The dashboard header shows the customer's current number of orders. Cancelled orders do not count.

## Success signal
Order-count tickets drop to near zero within a month.

## Non-goals
- Order history pages, filters or per-period counts.

## Affected systems
| System / area | Why it is affected | Source |
|---|---|---|
| dashboard header | shows the count | originator said |
| orders | the count comes from them | not yet checked |

## Constraints
- The dashboard must stay within its latency budget.
- The count must be exact and current right after every order is placed or cancelled - no staleness window.
- Schema changes are fine: an index, or a new column or table, if the design needs one.

## Originator's idea (non-binding)
none

## Open questions
- none

## Decision log
- 2026-09-27 - created as accepted by Mai (product)
EOF
git add -A && git commit -qm "intent: order count"
