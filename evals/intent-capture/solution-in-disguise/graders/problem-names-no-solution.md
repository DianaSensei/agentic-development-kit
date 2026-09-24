---
type: regex
target: { source: file, path: docs/intents/checkout-card-hangs.md }
pattern: '^## Problem$(?:(?!^## )[\s\S])*retr'
flags: mi
match: not_contains
---
