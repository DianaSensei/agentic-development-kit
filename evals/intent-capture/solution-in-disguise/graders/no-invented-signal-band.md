---
type: regex
target: { source: file, path: docs/intents/checkout-card-hangs.md }
# The fixture has no bands.yaml, so no band can measure the signal: the key stays empty.
pattern: '\nsignal_band:[ \t]*\S'
match: not_contains
---
