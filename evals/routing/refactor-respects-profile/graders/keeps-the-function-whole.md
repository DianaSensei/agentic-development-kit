---
type: llm
focus: trace
---

PASS if the refactor Claude proposes keeps `place_order` as one function - regrouping, reordering or renaming inside it so the flow reads straight through - and does not propose splitting its steps into new helper functions (such as `validate_order` or `compute_total`) for structure alone.
FAIL if the proposal extracts `place_order`'s steps into separate functions, or if Claude edits `src/` before the Checkpoint is confirmed.
