---
type: regex
# "No behavior change for apply_tax" - the diff turns rate into a percentage and rounds the result.
pattern: 'apply_tax[\s\S]{0,500}(behavio|percent|/ ?100|rate)|(no behavio[u]?r change|behavio[u]?r change)[\s\S]{0,500}apply_tax'
flags: i
---
