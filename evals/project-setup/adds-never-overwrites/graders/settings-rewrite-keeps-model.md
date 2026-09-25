---
type: regex
target: trace
pattern: '"file_path":"[^"]*\.claude/settings\.json","content":"(?:(?!claude-sonnet-5)[^"\\]|\\.)*"'
match: not_contains
---
