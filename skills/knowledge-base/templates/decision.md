---
title: Money is integer cents across services
type: decision
status: accepted
date: 2025-12-02
---

# Money is integer cents across services

- [context] A float rounding error in invoice totals reached customers; three services converted money differently
- [decision] Every service stores and sends money as integer cents with an ISO currency code
- [alternative] Decimal strings in APIs - lost: every consumer parses them differently
- [alternative] Per-service choice - lost: it is how the incident happened
- [consequence] Events carry amount_cents and currency; a float in a money field is a review blocker
- [source] ADR-014 in the platform repo; incident review 2025-11

## Relations
- affects [[Billing Service]]
- affects [[Orders Service]]
