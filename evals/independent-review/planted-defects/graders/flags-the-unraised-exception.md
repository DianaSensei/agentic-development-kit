---
type: llm
---

PASS if the review reports that PaymentTimeout is defined but never raised - on a slow gateway charge() falls through and returns None instead of raising, which breaks the plan's AC-001.
FAIL if the review does not point this out.
