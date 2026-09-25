---
type: regex
target: trace
pattern: '"file_path":"[^"]*\.claude/settings\.json"(?:,"(?:old_string|replace_all)":(?:"(?:[^"\\]|\\.)*"|true|false))*,"(?:content|new_string)":"(?:[^"\\]|\\.)*?\\"Bash\([^)"\\]*[^ )"\\]\*\)\\"'
match: not_contains
---
