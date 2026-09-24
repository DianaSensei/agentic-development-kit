---
type: llm
focus: trace
---

PASS if the fix direction Claude proposes bounds the retries - a maximum number of attempts or an overall deadline, after which it gives up with an error - rather than only adding a delay or backoff.
FAIL if the proposed fix is only a longer delay, jitter or exponential backoff with no limit, or if Claude proposes no fix direction at all.
