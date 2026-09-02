# Atlassian MCP - Self-hosted Jira + Confluence

Configuration for [mcp-atlassian](https://github.com/sooperset/mcp-atlassian),
run locally via `uvx`. Once connected, you can ask Claude Code things like: "find
tickets assigned to me", "summarize Confluence page X" without opening the
Jira/Confluence UI.

This configuration only applies to self-hosted Jira/Confluence (Server or Data
Center - an address that isn't a `*.atlassian.net` domain).

## Using Atlassian Cloud

Don't use the configuration in this directory. Atlassian provides an official MCP server
(Rovo) for Cloud, requiring no installation or token management:

```bash
claude mcp add atlassian-cloud --transport http https://mcp.atlassian.com/v1/mcp
```

If `claude mcp list` shows `! Needs authentication`, run `/mcp` inside Claude
Code, select this server, and choose Authenticate to log in via the browser.

---

## Installation

The official install and run instructions are at the
[sooperset/mcp-atlassian README](https://github.com/sooperset/mcp-atlassian#quick-start)
- refer to that page if the suggestions below become outdated. This repo defaults to
running via `uv`/`uvx` since it's the simplest option, requiring no Docker:

```bash
brew install uv
uvx --version
```

If you're not on macOS or don't have Homebrew, see the `uv` installation guide at
[docs.astral.sh/uv](https://docs.astral.sh/uv/getting-started/installation/).
`uvx mcp-atlassian` (used in the registration step below) always fetches the latest
release, no need to specify a version.

## Create a Personal Access Token

The exact UI navigation in Jira/Confluence can change between versions - refer to the
[official mcp-atlassian authentication docs](https://mcp-atlassian.soomiles.com/docs/authentication)
if the steps below don't match.

Do this separately for each product - Jira and Confluence use different tokens even
though they're part of the same suite: log in → avatar in the top-right corner →
**Profile** → **Personal Access Tokens** → **Create token**. Copy the token
immediately after creating it.

If you only use one of the two products, skip the token-creation step for the other one.

## Configure `.env`

```bash
cp .env.example .env
```

| Variable | Required | Note |
|---|---|---|
| `JIRA_URL` | If using Jira | e.g. `https://jira.yourcompany.com` |
| `JIRA_PERSONAL_TOKEN` | If using Jira | the token you just created |
| `CONFLUENCE_URL` | If using Confluence | Confluence address |
| `CONFLUENCE_PERSONAL_TOKEN` | If using Confluence | the token you just created |
| `READ_ONLY_MODE` | No, defaults to `true` | `true` disables every write/edit/delete tool - see the section at the end of this document |
| `JIRA_PROJECTS_FILTER` / `CONFLUENCE_SPACES_FILTER` | No | limits the project/space scope, comma-separated |

Any product you're not using can be left blank, the server will skip it automatically.

## Register with Claude Code

Determine the absolute path to this directory (`pwd` while inside it), then:

```bash
claude mcp add selfhost-atlassian --scope user -- uvx mcp-atlassian --env-file /path/mcp/selfhost-atlassian/.env
```

Unlike Grafana/Toolbox, this server reads the `.env` file directly via
`--env-file` - no need to pass the token into the command, just the exact
path to the file.

Confirm:

```bash
claude mcp list
```

A `✔ Connected` status next to `selfhost-atlassian` means it's done. On error,
check whether the URL is reachable and whether the token has expired or been revoked.

## Verify after connecting

- "Find Jira tickets assigned to me"
- "Summarize the Confluence page named X"
- "Any bugs created this week?"

With `READ_ONLY_MODE=true`, requests to create a new ticket or page will be
rejected - see below.

---

## Advanced configuration

**Registering via a config file instead of the CLI command** - since `--env-file`
only needs a path rather than direct values, this approach is safe at any scope, even
when shared via git:

```json
{
  "mcpServers": {
    "selfhost-atlassian": {
      "type": "stdio",
      "command": "uvx",
      "args": [
        "mcp-atlassian",
        "--env-file", "${CLAUDE_PROJECT_DIR}/mcp/selfhost-atlassian/.env"
      ]
    }
  }
}
```

Personal scope: paste into `~/.claude.json`, replacing `${CLAUDE_PROJECT_DIR}`
with the absolute path (this variable only has a value within a session tied
to a specific project). Sharing with the team: paste into `.mcp.json` at the
project root and commit it to git, keeping `${CLAUDE_PROJECT_DIR}` as-is - each
team member still needs to create their own `.env` file on their machine.

`.mcp.json` is only re-read when a new session is opened.

## Why read-only by default

`READ_ONLY_MODE=true` disables every create/edit/delete tool on the server side, not
just a description line asking Claude to avoid write operations. Even if a request to
create a ticket comes in, the server will reject it directly, regardless of the token's
actual permissions.

Only turn off read-only mode when you genuinely need Claude Code to create or edit
content. You can combine this with `JIRA_PROJECTS_FILTER` / `CONFLUENCE_SPACES_FILTER`
to limit the access scope, since an Atlassian Personal Access Token typically inherits
all the permissions of the account that created it, without auto-limiting by
project/space.
