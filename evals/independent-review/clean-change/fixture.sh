#!/usr/bin/env bash
# A repo with an accepted intent and a chosen plan on main, and a branch that
# implements it. Only the branch's change differs between the two review cases.
set -euo pipefail
# The project opted into the kit, as project-setup leaves it - without that the
# kit's session reminders stay silent (hooks/common.sh project_opted_in).
mkdir -p .claude && printf '{"enabledPlugins":{"agentic-development-kit@agentic-development-kit":true}}\n' > .claude/settings.json
git init -q -b main
export GIT_AUTHOR_NAME=eval GIT_AUTHOR_EMAIL=eval@example.com GIT_COMMITTER_NAME=eval GIT_COMMITTER_EMAIL=eval@example.com
mkdir -p src/checkout tests docs/intents docs/plans
cat > CLAUDE.md <<'MD'
# Demo shop
Python backend. Checkout lives in src/checkout. Every behavior change ships with a pytest test in tests/.
MD
touch src/__init__.py src/checkout/__init__.py tests/__init__.py
cat > src/checkout/gateway.py <<'PY'
def charge(card, amount, timeout):
    """Charge the card through the payment provider. Raises TimeoutError when
    the provider gives no answer within `timeout` seconds."""
    raise NotImplementedError("provider client lives outside this demo")
PY
cat > src/checkout/payment.py <<'PY'
from src.checkout import gateway


def charge(order, card):
    result = gateway.charge(card, order.amount, timeout=30)
    order.status = "paid"
    return result
PY
cat > docs/intents/checkout-card-payment-hangs.md <<'MD'
---
title: Checkout hangs on card payment
status: in-progress
type: bug
originator: Lan
created: 2026-09-20
updated: 2026-09-22
plan: docs/plans/checkout-card-payment-hangs.md
changelog:
superseded_by:
---

# Checkout hangs on card payment

## Problem
Customers paying by card see checkout spin with no result when the gateway is slow.

## Evidence
- Support: 14 emails in September describing a spinning checkout.

## Desired outcome
A card payment always ends within 10 seconds with either success or a clear failure the customer can retry.

## Success signal
No order stays in `pending` longer than 10s after charge() is called.

## Non-goals
- No automatic retry of charges: a retried charge can bill the customer twice.

## Affected systems
| System / area | Why it is affected | Source |
|---|---|---|
| src/checkout/payment.py | charge() waits up to 30s and has no failure path | src/checkout/payment.py |

## Constraints
none stated

## Originator's idea (non-binding)
Add retries.

## Open questions
- none

## Decision log
- 2026-09-20 - created as proposed by Lan
- 2026-09-21 - accepted by Minh - retries rejected, fail fast instead
- 2026-09-22 - in-progress, plan chosen
MD
cat > docs/plans/checkout-card-payment-hangs.md <<'MD'
Intent: docs/intents/checkout-card-payment-hangs.md

# Feature: Fail fast on slow card payments

## Chosen: Bounded timeout with explicit failure

### AC-001: Slow gateway
Given the gateway does not answer within 10 seconds
When charge() is called
Then it raises PaymentTimeout and the order status is "payment_failed"

### AC-002: Successful charge
Given the gateway answers within 10 seconds with success
When charge() is called
Then the order status is "paid"
MD
git add -A && git commit -qm "Checkout: intent and plan for slow card payments"
git checkout -qb fix/checkout-card-payment-hangs
# The change under review: what the plan asked for, with a test per AC.
cat > src/checkout/payment.py <<'PY'
from src.checkout import gateway

TIMEOUT_SECONDS = 10


class PaymentTimeout(Exception):
    """The gateway gave no answer in time. The charge is not retried."""


def charge(order, card):
    try:
        result = gateway.charge(card, order.amount, timeout=TIMEOUT_SECONDS)
    except TimeoutError as exc:
        order.status = "payment_failed"
        raise PaymentTimeout(f"no answer from the gateway within {TIMEOUT_SECONDS}s") from exc
    order.status = "paid"
    return result
PY
cat > tests/test_payment.py <<'PY'
from types import SimpleNamespace
from unittest import mock

import pytest

from src.checkout import payment


def test_slow_gateway_fails_fast_without_retry():
    order = SimpleNamespace(amount=100, status="pending")
    with mock.patch.object(payment.gateway, "charge", side_effect=TimeoutError) as gateway_charge:
        with pytest.raises(payment.PaymentTimeout):
            payment.charge(order, card="4242")
    assert order.status == "payment_failed"
    gateway_charge.assert_called_once_with("4242", 100, timeout=10)


def test_successful_charge_marks_order_paid():
    order = SimpleNamespace(amount=100, status="pending")
    with mock.patch.object(payment.gateway, "charge", return_value="ok"):
        assert payment.charge(order, card="4242") == "ok"
    assert order.status == "paid"
PY
git add -A && git commit -qm "Fail fast on slow card payments"
# Runs get no shell (see evals/README.md), so hand over the diff the way CI does.
git diff main...HEAD > review.diff
