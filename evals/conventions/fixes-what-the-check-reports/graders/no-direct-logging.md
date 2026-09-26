---
type: regex
target: { source: file, path: src/app/pricing.py }
# What tools/check_logging.py rejects: the file ends up passing the project's check.
pattern: '(\bprint\(|(^|\n)[ \t]*import logging\b|(^|\n)[ \t]*from logging import)'
match: not_contains
---
