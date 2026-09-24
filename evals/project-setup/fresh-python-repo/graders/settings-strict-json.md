---
type: regex
target: trace
pattern: '"file_path":"[^"]*\.claude/settings\.json","content":"(?:[^"\\]|\\.)*?,(?:\\n|\\t|\s)*[}\]]'
match: not_contains
---
