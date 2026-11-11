---
type: llm
---

PASS if the lock is released only by its owner: a unique token is stored and checked before deleting (for example in a Lua script), or a library that does so is used.
FAIL if any process can delete the key.
