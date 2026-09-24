---
type: llm
---

PASS if the reply explains that bug-fix is for behavior that is currently wrong (a defect to reproduce and fix) while refactor improves structure and must keep external behavior exactly the same.
FAIL if the reply gets that distinction wrong, starts working on a code change, or asks which code to change.
