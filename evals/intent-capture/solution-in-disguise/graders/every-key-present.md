---
type: regex
target: { source: file, path: docs/intents/checkout-card-hangs.md }
pattern: '^(?=-{3}\n)(?=[\s\S]*?\ntitle: \S)(?=[\s\S]*?\ntype: (?:feature|bug|refactor|unknown)\n)(?=[\s\S]*?\noriginator: [^\n]*Lan)(?=[\s\S]*?\ncreated: \d{4}-\d{2}-\d{2}\n)(?=[\s\S]*?\nupdated: \d{4}-\d{2}-\d{2}\n)(?=[\s\S]*?\nplan:)(?=[\s\S]*?\nchangelog:)(?=[\s\S]*?\nsuperseded_by:)'
---
