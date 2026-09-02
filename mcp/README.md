# Common MCP Server

A collection of MCP configurations for connecting Claude Code to external systems: database,
Grafana, Jira/Confluence. Each directory under `mcp/` is an independent MCP server, not
dependent on the others.

MCP (Model Context Protocol) is a mechanism that lets Claude Code reach beyond the local
codebase — query a database, read a dashboard, interact with tickets — through MCP servers
that act as bridges to each specific system.

## List of MCP servers

| Directory | Function |
|---|---|
| [`mcp/toolbox/`](./toolbox/README.md) | Query PostgreSQL, MySQL, TiDB, Redis, MongoDB (read-only) |
| [`mcp/grafana/`](./grafana/README.md) | View dashboards, alerts, metrics on Grafana |
| [`mcp/selfhost-atlassian/`](./selfhost-atlassian/README.md) | Self-hosted Jira and Confluence. If you use Atlassian Cloud, this configuration isn't needed — see the note in the corresponding README |

## General setup process

1. Install the runtime tools needed for that MCP server (each README specifies which).
2. `cp .env.example .env`, fill in real values in `.env`. This file is not committed to
   git, so it's safe to put real values in it.
3. Register with Claude Code using the `claude mcp add ...` command — the full command is
   provided in each server's README.
4. Run `claude mcp list`, confirm the status shows `✔ Connected`.

Details for each step and how to handle common errors are in each MCP server's own README.
You can also ask Claude Code to carry out the whole process itself — for example, "set up
Grafana MCP for me" — and Claude Code will read the corresponding README and follow it.
