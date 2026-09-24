---
type: regex
target: { source: file, path: docs/intents/checkout-card-hangs.md }
pattern: '\n(?:slug:|(?:plan|changelog|superseded_by):[ \t]*(?:null|~)[ \t]*\n)'
match: not_contains
---
