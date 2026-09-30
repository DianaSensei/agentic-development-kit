---
title: invoice.created event contract
type: agreement
status: active
verified: 2026-07-20
---

# invoice.created event contract

- [term] Fields invoice_id, order_id, amount_cents, currency, issued_at are always present
- [term] New fields may be added; none is removed or renamed without 90 days' notice
- [term] At-least-once delivery; consumers dedupe on invoice_id
- [contact] Payments team: #payments; Finance data: #finance-data
- [source] Contract review 2026-07 between Payments and Finance data

## Relations
- party [[Payments Team]]
- party [[Finance Data Team]]
- governs [[Billing Service]]
