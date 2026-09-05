---
name: toolbox-connections
description: Configure database connections and tools for this plugin's own bundled toolbox MCP server (mcp/toolbox/) - PostgreSQL, MySQL, TiDB, Redis, MongoDB, or any other type Toolbox supports. Checks for an existing match before adding a duplicate, writes a new connection from the matching template with a read-only permission check, derives the standard query/list-tables tools, and writes custom parameterized tools on request. Always applies changes through validate.sh's snapshot/check/restore flow. Use for adding/removing a toolbox connection or a custom toolbox tool/query. Do NOT use for a different third-party MCP server (`mcp-setup`) or for authoring toolbox/a new MCP server (`mcp-developer`).
metadata:
  domain: platform
  triggers: toolbox connection, add database connection, connect postgres, connect mysql, connect redis, connect mongodb, connect tidb, toolbox tool, custom toolbox query, database MCP setup, second mysql connection
  role: specialist
  scope: implementation
  output-format: code
  related-skills: mcp-setup, mcp-developer, database-skill, redis-skill
---

# Toolbox Connections

Manages `mcp/toolbox/`'s connections/tools only (see Boundaries). No pre-built connections -
every one, including the first, is added the same way.

## Step 1 - Orient

```bash
claude mcp list | grep '^plugin:agentic-development-kit:toolbox'
```

Its `--config-folder` value is the live connections directory - `ls` it. No such line = not
enabled here, stop. Empty = expected on a fresh install (`✘ Failed to connect` until a
connection exists). Check the listing for a match before adding a duplicate.

New connection → Step 2. Remove one → Step 3. Custom tool → Step 4.

## Step 2 - Add a connection

Template: `examples/new-sql-connection.yaml.example` (any SQL type), `new-redis-connection...`
(Redis, one tool per command), `new-mongodb-connection...` (per database/collection).

1. Type, if not already stated: one `AskUserQuestion` (header `Type`,
   Postgres/MySQL/Redis/Mongo, else "Other").
2. Non-secret fields (host/port/database/user, or just `address` for Redis) in ONE batched
   `AskUserQuestion` call (≤4 questions, never one call per field), each with a
   `(Recommended)` default - `localhost`, the type's standard port, a plausible db/user guess
   - and "Other" for the real value. Keep every `header` to 12 characters or less (it's a
   hard schema limit) - `Host`, `Port`, `Database`, `User`, not "Database name" (14 chars).
3. Password/URI: a plain message, never `AskUserQuestion` (no sensible default to offer, and
   it's for enumerable choices, not secrets - same rule as `mcp-setup`). Never echo it back.
4. Read-only permission: its own single-question `AskUserQuestion` (header `Access`,
   `Read-only (Recommended)` / `Can write too`). If not read-only, explain why it matters
   (`../../mcp/toolbox/README.md`) and get explicit confirmation either way.
5. Infer a unique connection name (don't ask unless genuinely ambiguous), write the file with
   literal values (safe - this directory is private, uncommitted), and derive the generic
   tools from the template rather than inventing a different shape.

Go to Step 5.

## Step 3 - Remove a connection

Delete its file. Step 5's `check` catches anything else that referenced it.

## Step 4 - A custom tool

`examples/custom-tool.yaml.example`: point `source:` at an existing/new connection, write the
exact statement/parameters asked for. Go to Step 5.

## Step 5 - Validate, always

```bash
../../mcp/toolbox/validate.sh snapshot <dir>   # before any change
# make the change
../../mcp/toolbox/validate.sh check <dir>
```

FAIL → `restore <dir>`, fix the printed error, retry. `toolbox` validates the whole folder as
one unit - one bad file breaks every connection, not just the new one.

## Step 6 - Reconnect required

No auto-reload, no CLI reconnect command. Tell the user: open `/mcp` → `toolbox` → Reconnect
(or start a new session) - never claim the change is already live.

## Constraints

**MUST**: confirm read-only before a query-only connection · snapshot/check every change, no
exceptions · check for an existing match before duplicating · state reconnecting is required
· discover the connections-dir via `claude mcp list`, never hardcode · batch non-secret
fields into as few `AskUserQuestion` calls as possible · keep every `AskUserQuestion`
`header` to ≤12 characters (a hard schema limit - a longer one is an invalid tool call, not
just a style issue).

**MUST NOT**: ask for a password/URI via `AskUserQuestion`, or echo one back · assume write
access without being asked · write to the live directory without a preceding snapshot ·
leave a `check` failure unresolved.

## Boundaries

Only `mcp/toolbox/`'s own connections/tools. Other MCP servers → `mcp-setup`. Authoring
`toolbox`/a new MCP server → `mcp-developer`. Deep query/schema design → `database-skill`/
`redis-skill`.

## Reference

`mcp/toolbox/README.md`, `mcp/toolbox/validate.sh`, `mcp/toolbox/examples/*.yaml.example`.
