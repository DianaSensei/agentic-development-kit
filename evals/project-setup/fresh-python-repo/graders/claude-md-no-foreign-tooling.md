---
type: regex
target: { source: file, path: CLAUDE.md }
pattern: '\b(?:npm|yarn|cargo|gradle|mvn)\b'
match: not_contains
---
