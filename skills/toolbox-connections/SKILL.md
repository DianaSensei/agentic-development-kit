---
name: toolbox-connections
description: Manage this plugin's bundled toolbox MCP server (mcp/toolbox/) - full CRUD for database connections (PostgreSQL, MySQL, TiDB, Redis, MongoDB, or any other type Toolbox supports) and their tools. Create a connection/tool (checking for an existing target match first, and a read-only permission check for connections), read/list existing ones (secrets redacted), update values on an existing connection/tool, or delete either. Always applies a write through validate.sh's snapshot/check/restore flow. Use for any add/list/show/edit/update/remove request about a toolbox connection or tool. Do NOT use for a different third-party MCP server (`mcp-setup`) or for authoring toolbox/a new MCP server (`mcp-developer`).
metadata:
  domain: platform
  triggers: list toolbox connections, show connection, update connection, rotate password, edit connection, remove connection, add database connection, connect postgres, connect mysql, connect redis, connect mongodb, connect tidb, toolbox tool, edit toolbox tool, remove toolbox tool, database MCP setup
  role: specialist
  scope: implementation
  output-format: code
  related-skills: mcp-setup, mcp-developer, database-skill, redis-skill
---

# Toolbox Connections

Manages `mcp/toolbox/`'s connections/tools only (see Boundaries) - full CRUD on both.

## Step 1 - Orient

```bash
claude mcp list | grep '^plugin:agentic-development-kit:toolbox'
```

Its `--config-folder` value is the live connections directory. No such line = not enabled
here, stop. List it (`ls`, then per file `grep -E '^(host|port|database|user|address|uri):'`
for its target) before any operation below - every one needs to know what already exists,
and Create must check it for a duplicate.

## Step 2 - Connections

**Create** (template: `examples/new-{sql,redis,mongodb}-connection.yaml.example`):
1. Type if not stated: `AskUserQuestion` (header `Type`, Postgres/MySQL/Redis/Mongo, else
   "Other").
2. Non-secret fields (host/port/database/user, or `address` for Redis) in ONE batched
   `AskUserQuestion` (≤4 questions, `(Recommended)` defaults, header ≤12 chars - a hard
   schema limit).
3. Compare against Step 1's listing on `host:port`+`database`+`user` (or `address`+db-index
   / `uri`+`database`) - exact match → tell the user it already exists, stop.
4. Password/URI: plain message, never `AskUserQuestion` (no sensible default, and it's for
   secrets not choices - same as `mcp-setup`). Never echo it back.
5. Read-only permission: separate `AskUserQuestion` (header `Access`,
   `Read-only (Recommended)` / `Can write too`); if not read-only, explain why
   (`../../mcp/toolbox/README.md`) and get explicit confirmation regardless.
6. Unique name (infer, don't ask unless ambiguous) → write with literal values → derive the
   generic tools from the template.

**Read**: `cat` the file - redact any `password:`/credential-bearing `uri:` line, never
display a secret back.

**Update**: same field-collection pattern as Create (batched `AskUserQuestion` for
non-secret fields, plain message for password/URI) but edit the existing file. Re-run
Create.3's duplicate check if host/port/database/user changed.

**Delete**: remove the file.

Any write (Create/Update/Delete) → Step 4.

## Step 3 - Tools

**Create**: `examples/custom-tool.yaml.example` - point `source:` at an existing connection,
write the exact statement/parameters asked for.

**Read**: list a connection's tools (`grep -A1 '^kind: tool' <file>`), or show one tool's
full block.

**Update**: edit an existing tool's `description`/`statement`/`parameters` in place.

**Delete**: remove that `kind: tool` document (between its `---` separators) and drop its
name from any `kind: toolset` list referencing it.

Any write here → Step 4.

## Step 4 - Validate every write

```bash
../../mcp/toolbox/validate.sh snapshot <dir>   # before any change
# make the change
../../mcp/toolbox/validate.sh check <dir>
```

FAIL → `restore <dir>`, fix the printed error, retry. `toolbox` validates the whole folder as
one unit - one bad file breaks every connection, not just the one being changed. Read
operations don't touch this step.

## Step 5 - Reconnect required (after any write)

No auto-reload, no CLI reconnect command. Tell the user: open `/mcp` → `toolbox` → Reconnect
(or start a new session) - never claim the change is already live.

## Constraints

**MUST**: confirm read-only before a query-only connection · snapshot/check every write, no
exceptions · reject an exact-target duplicate before creating (2.Create.3) · state
reconnecting is required after any write · discover the connections-dir via `claude mcp
list`, never hardcode · batch `AskUserQuestion` fields per 2.Create.2's rules · redact
secrets when reading a connection back.

**MUST NOT**: ask for a password/URI via `AskUserQuestion`, or echo one back · assume write
access without being asked · write to the live directory without a preceding snapshot ·
leave a `check` failure unresolved.

## Boundaries

Only `mcp/toolbox/`'s own connections/tools. Other MCP servers → `mcp-setup`. Authoring
`toolbox`/a new MCP server → `mcp-developer`. Deep query/schema design → `database-skill`/
`redis-skill`.

## Reference

`mcp/toolbox/README.md`, `mcp/toolbox/validate.sh`, `mcp/toolbox/examples/*.yaml.example`.
