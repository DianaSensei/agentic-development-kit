---
type: regex
pattern: '\b(?:no|without|lacks?|missing|zero)\s+(?:[\w`-]+\s+){0,2}tests?\b|\buntested\b|\bnot tested\b|\btests?\b[^.\n]{0,30}\b(?:missing|absent)\b'
flags: i
match: not_contains
---
