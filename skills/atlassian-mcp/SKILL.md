---
name: atlassian-mcp
description: Integrates with Atlassian products to manage project tracking and documentation via MCP protocol. Use when querying Jira issues with JQL filters, creating and updating tickets with custom fields, searching or editing Confluence pages with CQL, managing sprints and backlogs, setting up MCP server authentication, syncing documentation, or debugging Atlassian API integrations.
metadata:
  domain: platform
  triggers: wiki, project management, worklog, log work, time tracking
  role: expert
  scope: implementation
  output-format: code
  related-skills: mcp-developer, mcp-setup, api-contract-skill, security-reviewer
---

# Atlassian MCP Expert

## Core Workflow

1. **Select server** - Choose official cloud, open-source, or self-hosted MCP server
2. **Authenticate** - Configure OAuth 2.1, API tokens, or PAT credentials
3. **Design queries** - Write JQL for Jira, CQL for Confluence; validate with `maxResults=1` before full execution
4. **Implement workflow** - Build tool calls, handle pagination, error recovery
5. **Verify permissions** - Confirm required scopes with a read-only probe before any write or bulk operation
6. **Deploy** - Configure IDE integration, test permissions, monitor rate limits

## Reference Guide

Load detailed guidance based on context:

| Topic | Reference | Load When |
|-------|-----------|-----------|
| Server Setup | `references/mcp-server-setup.md` | Installation, choosing servers, configuration |
| Jira Operations | `references/jira-queries.md` | JQL syntax, issue CRUD, sprints, boards, issue linking, worklogs/time tracking |
| Confluence Ops | `references/confluence-operations.md` | CQL search, page creation, spaces, comments |
| Authentication | `references/authentication-patterns.md` | OAuth 2.0, API tokens, permission scopes |
| Common Workflows | `references/common-workflows.md` | Issue triage, doc sync, sprint automation |

## Quick-Start Examples

### JQL Query Samples
```
# Open issues assigned to current user in a sprint
project = PROJ AND status = "In Progress" AND assignee = currentUser() ORDER BY priority DESC

# Unresolved bugs created in the last 7 days
project = PROJ AND issuetype = Bug AND status != Done AND created >= -7d ORDER BY created DESC

# Validate before bulk: test with maxResults=1 first
project = PROJ AND sprint in openSprints() AND status = Open ORDER BY created DESC
```

### CQL Query Samples
```
# Find pages updated in a specific space recently
space = "ENG" AND type = page AND lastModified >= "2024-01-01" ORDER BY lastModified DESC

# Search page text for a keyword
space = "ENG" AND type = page AND text ~ "deployment runbook"
```

### Minimal MCP Server Configuration
```json
{
  "mcpServers": {
    "atlassian": {
      "command": "uvx",
      "args": ["mcp-atlassian"],
      "env": {
        "JIRA_URL": "https://your-domain.atlassian.net",
        "JIRA_EMAIL": "user@example.com",
        "JIRA_API_TOKEN": "${JIRA_API_TOKEN}",
        "CONFLUENCE_URL": "https://your-domain.atlassian.net/wiki",
        "CONFLUENCE_EMAIL": "user@example.com",
        "CONFLUENCE_API_TOKEN": "${CONFLUENCE_API_TOKEN}"
      }
    }
  }
}
```
> **Note:** Always load `JIRA_API_TOKEN` and `CONFLUENCE_API_TOKEN` from environment variables or a secrets manager - never hardcode credentials.

## Constraints

- Probe a JQL/CQL query with `maxResults=1` before running it for real, and paginate large result sets
  (50-100/page).
- Confirm with the user before any write or bulk operation against production data.
- Log worklogs from actual measured session time (see `references/jira-queries.md`), never a fabricated
  or rounded-up estimate.
- Never hardcode API tokens/OAuth secrets, or expose issue data in logs and error messages.
- Never mix authentication methods in the same session.

## Output Templates

When implementing Atlassian MCP features, provide:
1. MCP server configuration (JSON/environment vars)
2. Query examples (JQL/CQL with explanations)
3. Tool call implementation with error handling
4. Authentication setup instructions
5. Brief explanation of permission requirements
