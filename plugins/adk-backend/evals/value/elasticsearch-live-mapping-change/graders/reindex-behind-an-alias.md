---
type: llm
---

PASS if the answer creates a new index with the corrected mapping, reindexes into it, and switches an alias (or equivalent cut-over) before removing the old index.
FAIL if it changes the field type in place on the running index, or omits the cut-over.
