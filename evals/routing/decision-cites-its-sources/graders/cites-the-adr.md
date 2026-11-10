---
type: llm
focus: trace
---

PASS if the proposal Claude presents cites `docs/decisions/0003-money-in-integer-cents.md` (by its path) as the ground for computing the discount in integer cents with the percentage applied once, rounded half-even.
FAIL if it proposes float amounts or another rounding, or handles money that way without citing the ADR's path.
