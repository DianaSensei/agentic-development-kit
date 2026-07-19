# Grafana MCP

Configuration for the [official Grafana server](https://github.com/grafana/mcp-grafana),
run locally via `uvx`, no Docker or dedicated server required. Once connected, you can ask
Claude Code things like: "list existing dashboards", "which alerts are active", "what's
service X's CPU usage over the last hour" without opening the Grafana UI.

## Installation

The official install and run instructions are in the
[grafana/mcp-grafana README](https://github.com/grafana/mcp-grafana#quick-start)
— refer to that page if the suggestions below become outdated. This repo defaults to
running via `uv`/`uvx` since it's the simplest option, requiring no Docker:

```bash
brew install uv
uvx --version
```

If you're not on macOS or don't have Homebrew, see the `uv` installation guide at
[docs.astral.sh/uv](https://docs.astral.sh/uv/getting-started/installation/).
`uvx mcp-grafana` (used in the registration step below) always fetches the latest release,
no need to specify a version.

## Create a Service Account token

The exact UI navigation in Grafana can change between versions — refer to the
[official Service Accounts documentation](https://grafana.com/docs/grafana/latest/administration/service-accounts/)
if the steps below don't match what you see.

Go to Grafana → **Administration** → **Service accounts** → **Add service
account**, give it any name (e.g. `mcp-claude-code`). Choose the **Viewer** role
if you only need to read data — a safer permission level. Choose Editor/Admin if you need
Claude Code to create or edit dashboards.

Open the newly created service account, choose **Add service account token**, and copy the
token right away — it's only shown once.

## Configure `.env`

```bash
cp .env.example .env
```

| Variable | Required | Note |
|---|---|---|
| `GRAFANA_URL` | Yes | `http://localhost:3000` (self-hosted) or `https://<instance>.grafana.net` (Cloud) |
| `GRAFANA_SERVICE_ACCOUNT_TOKEN` | Yes | the token you just created |
| `GRAFANA_ORG_ID` | Only for multi-org instances | the org's numeric ID |

## Register with Claude Code

```bash
set -a && source .env && set +a
claude mcp add grafana --scope user \
  --env GRAFANA_URL="$GRAFANA_URL" \
  --env GRAFANA_SERVICE_ACCOUNT_TOKEN="$GRAFANA_SERVICE_ACCOUNT_TOKEN" \
  -- uvx mcp-grafana
```

The first two lines load values from `.env` into the shell, the last line registers the
server and grabs the token directly from it — no need to type it manually. `--scope user`
applies to every project on this machine; if you use multiple machines, you'll need to
repeat these steps on each one since `.env` doesn't sync automatically.

Confirm:

```bash
claude mcp list
```

A `✔ Connected` status next to `grafana` means it's done. If you see
`✘ Failed to connect`, check whether `GRAFANA_URL` is reachable and whether the token has
been revoked.

## Verify after connecting

- "List the dashboards on Grafana"
- "Which alerts are active?"
- "What's the checkout service's CPU over the last hour?"

---

## Advanced configuration

**Registering via a config file instead of the CLI command** — personal scope, edit
`~/.claude.json`. This file is not committed to git so it's safe to put the real token
directly in it:

```json
{
  "mcpServers": {
    "grafana": {
      "type": "stdio",
      "command": "uvx",
      "args": ["mcp-grafana"],
      "env": {
        "GRAFANA_URL": "http://localhost:3000",
        "GRAFANA_SERVICE_ACCOUNT_TOKEN": "<token from .env>"
      }
    }
  }
}
```

To share with the team, create `.mcp.json` at the project root and commit it to git. Do NOT
put the real token in this file — use the `${VARIABLE_NAME}` syntax, each team member
declares their own value on their machine:

```json
{
  "mcpServers": {
    "grafana": {
      "type": "stdio",
      "command": "uvx",
      "args": ["mcp-grafana"],
      "env": {
        "GRAFANA_URL": "${GRAFANA_URL}",
        "GRAFANA_SERVICE_ACCOUNT_TOKEN": "${GRAFANA_SERVICE_ACCOUNT_TOKEN}"
      }
    }
  }
}
```

Note clearly in the project's README/CLAUDE.md that each team member needs to run
`set -a && source mcp/grafana/.env && set +a` before opening Claude Code.
`.mcp.json` is only re-read when a new session is opened.

**Other run methods** — Docker, or running as a shared HTTP server for multiple users, see
the [upstream README](https://github.com/grafana/mcp-grafana#usage).
The `uvx` approach above is the simplest for a single user, so it's used as the default here.

**Read-only limitation** — Grafana MCP has no dedicated read-only switch in its
configuration; access depends entirely on the Service Account's role. To ensure Claude Code
can't edit dashboards or write annotations, create the Service Account with the Viewer role,
and don't grant Editor/Admin unless you genuinely need write-capable tools.
