---
type: regex
target: trace
# .mcp.json is refused in a non-interactive run like .claude/, so grade the write attempt.
pattern: '"file_path":"[^"]*\.mcp\.json"(?:,"(?:old_string|replace_all)":(?:"(?:[^"\\]|\\.)*"|true|false))*,"(?:content|new_string)":"(?:[^"\\]|\\.)*?https://gitlab\.example\.com/api/v4/mcp'
---
