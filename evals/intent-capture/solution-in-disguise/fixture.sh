#!/usr/bin/env bash
set -euo pipefail
# The project opted into the kit, as project-setup leaves it - without that the
# kit's session reminders stay silent (hooks/common.sh project_opted_in).
mkdir -p .claude && printf '{"enabledPlugins":{"agentic-development-kit@agentic-development-kit":true}}\n' > .claude/settings.json
mkdir -p src/checkout
cat > CLAUDE.md <<'MD'
# Demo shop
Python backend. Checkout lives in src/checkout.
MD
cat > src/checkout/payment.py <<'PY'
from src.checkout import gateway


def charge(order, card):
    # calls the payment gateway; no retry, times out after 30s
    result = gateway.charge(card, order.amount, timeout=30)
    order.status = "paid"
    return result
PY
git init -q && git add -A && git -c user.email=eval@example.com -c user.name=eval commit -qm "Initial shop"
