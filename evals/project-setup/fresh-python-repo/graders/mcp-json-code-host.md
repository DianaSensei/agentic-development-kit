---
type: regex
target: { source: file, path: .mcp.json }
pattern: 'api\.githubcopilot\.com/mcp[\s\S]*\$\{GITHUB_PAT\}|\$\{GITHUB_PAT\}[\s\S]*api\.githubcopilot\.com/mcp'
---
