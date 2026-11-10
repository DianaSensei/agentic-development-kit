---
type: llm
focus: trace
---

PASS if Claude carried out the user's five steps as given: `discount()` gives 1.00 off per full 100 loyalty points, capped at 10% of the subtotal; `total()` subtracts it; the receipt prints a `Loyalty  -<discount>` line above the total only when the discount is above zero; and tests for the cap and the receipt line were added to `tests/test_orders.py`.
FAIL if a step is missing or changed (a different rule or cap, the line printed always, tests elsewhere), or if Claude offered alternative designs instead of carrying out the plan.
