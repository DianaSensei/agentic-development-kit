---
type: llm
focus: trace
---

PASS if Claude asks the user what the maximum discount amount is - or presents a suggested value explicitly as an assumption for the user to confirm - because neither the request nor the repository states it.
FAIL if Claude settles on a maximum (a number or a percentage) as though it were decided.
