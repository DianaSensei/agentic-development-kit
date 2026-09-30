---
title: Billing Service
type: system
tags: [payments]
verified: 2026-09-01
---

# Billing Service

- [purpose] Turns a placed order into an invoice with tax per line
- [owner] Payments team
- [interface] REST POST /invoices; publishes invoice.created on Kafka (billing.events)
- [data] Source of truth for invoices and credit notes
- [constraint] Totals are exact to the cent: integer cents end to end, never floats #money (source: incident 2025-11 rounding)
- [risk] Tax rules are loaded at startup; a rule change needs a restart

## Relations
- depends_on [[Tax Rules]]
- depends_on [[Orders Service]]
- owned_by [[Payments Team]]
