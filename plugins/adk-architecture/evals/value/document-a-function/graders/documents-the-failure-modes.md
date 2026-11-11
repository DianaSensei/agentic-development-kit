---
type: llm
---

PASS if the doc comment documents both failure modes with their conditions - ValueError when qty is not positive, OutOfStock when not enough is available - and KeyError for an unknown sku is either documented or flagged.
FAIL if a raised error and its condition are missing.
