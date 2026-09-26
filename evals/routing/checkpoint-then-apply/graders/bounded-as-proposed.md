---
type: llm
# The file itself, not the trace: a judge sees only the first and last 12
# messages of a trace, and the recorded history fills the first 12.
focus: { source: file, path: src/retry.py }
---

PASS if get_with_retry can no longer loop forever when every response is a 503: it stops after a maximum number of attempts or an overall time limit, and then fails clearly - raises an exception or returns an explicit error - as the proposal before the confirmation said.
FAIL if a server that always answers 503 can still keep it looping forever, or it gives up silently by returning the last 503 response as if it were a success.
