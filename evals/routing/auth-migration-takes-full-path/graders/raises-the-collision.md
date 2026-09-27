---
type: regex
target: trace
# The decision a quick path would have skipped: existing accounts that collide once lowercased.
pattern: '(collid|collision|case-duplicate|dedup|duplicate (rows|accounts|emails|signups)|picking a winner|already exists? (with|in) (a |another )?(different )?case)'
flags: i
---
