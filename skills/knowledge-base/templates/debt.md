---
title: Tax rules only load at startup
type: debt
status: open
verified: 2026-09-01
---

# Tax rules only load at startup

- [debt] Billing reads tax rules once at startup; there is no reload
- [impact] A tax change needs a coordinated restart; one was missed in 2026-03 and 40 invoices were wrong
- [cause] Rules were a constant file when the service was written
- [workaround] Restart every billing pod after a rules release (runbook: billing/restart-after-tax)
- [fix] Watch the rules table and swap an immutable rule set in place; about a week
- [source] Incident 2026-03 tax-rate change

## Relations
- in [[Billing Service]]
