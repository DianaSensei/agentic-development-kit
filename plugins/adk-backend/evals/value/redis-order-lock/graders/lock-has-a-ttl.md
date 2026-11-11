---
type: llm
---

PASS if the lock is taken atomically with an expiry (SET NX with PX/EX, or Redisson with a lease time).
FAIL if the lock has no TTL, or sets the key and the expiry in two separate steps.
