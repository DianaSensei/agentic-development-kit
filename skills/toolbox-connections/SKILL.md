---
name: toolbox-connections
description: Configure database connections and tools for this plugin's own bundled toolbox MCP server (mcp/toolbox/) - PostgreSQL, MySQL, TiDB, Redis, MongoDB, or any other type Toolbox supports. Checks whether a datasource of the requested type/name already exists before adding a duplicate, writes a new connection from the matching template (asking about read-only permissions first), derives the standard query/list-tables tools automatically, and writes a custom parameterized tool on request. Always applies changes through validate.sh's snapshot/check/restore flow, since toolbox fails its entire server over one bad file, not just the connection with the mistake. Use when the user asks to add/remove a toolbox database connection, or to add a custom toolbox tool/query. Do NOT use for connecting a different, unrelated third-party MCP server (use `mcp-setup`), or for authoring toolbox itself/a new MCP server from scratch (use `mcp-developer`).
metadata:
  domain: platform
  triggers: toolbox connection, add database connection, connect postgres, connect mysql, connect redis, connect mongodb, connect tidb, toolbox tool, custom toolbox query, database MCP setup, second mysql connection
  role: specialist
  scope: implementation
  output-format: code
  related-skills: mcp-setup, mcp-developer, database-skill, redis-skill
---

# Toolbox Connections

Configures `mcp/toolbox/`'s own database connections and tools - the MCP this plugin ships
and auto-connects. Not for any other MCP server (see Boundaries). There are no pre-built
connections - every connection, including the first one, is added the same way.

## Step 1 - Find the live state

```bash
claude mcp list | grep '^plugin:agentic-development-kit:toolbox'
```

The line's `--config-folder` value is the live connections directory. If there's no such
line, toolbox isn't enabled in this session - say so and stop; this skill configures an
already-connected server, it can't enable a disabled one.

`ls` that directory to see what's already configured (it's empty on a fresh install -
`toolbox` will show `✘ Failed to connect` / `"no YAML files found"` until at least one
connection exists, which is expected, not a bug).

## Step 2 - Figure out what's being asked

- A new connection (first one, another of a type you already have, or a type you don't have
  yet) → Step 3.
- Remove a connection → Step 4.
- A specific query/tool beyond the generic pair → Step 5 (can combine with Step 3 for a new
  connection, or attach to an existing one).

Check the directory listing from Step 1 for a connection that already matches what's being
asked, so you don't create a duplicate by accident.

## Step 3 - Add a connection

Follow the matching template in `../../mcp/toolbox/examples/`:
`new-sql-connection.yaml.example` (any SQL type - postgres, mysql, tidb, mssql, sqlite,
spanner, bigquery, ...), `new-redis-connection.yaml.example` (Redis - one named tool per
command exposed, no generic "run any command" tool), or
`new-mongodb-connection.yaml.example` (MongoDB - bound to one database/collection per tool,
delete the write tools if only read access is wanted).

1. Ask for the type and its connection values (host/port/database/user/password for SQL;
   address for Redis; uri/database/collection for MongoDB).
2. **Always ask about the account's permissions before wiring it up**: confirm it's read-only
   (SELECT-only, no INSERT/UPDATE/DELETE/DDL) unless the user explicitly wants write access.
   If they're not sure or say it isn't read-only, explain why this matters (see
   `../../mcp/toolbox/README.md`'s "Why the SQL templates default to read-only" section) and
   get their explicit confirmation either way before proceeding - don't silently assume.
3. Pick a short, unique name not already used by another source/tool/toolset in the live
   directory (`orders`, `mysql_secondary`, ...).
4. Write the file straight into the live connections directory with the LITERAL values (no
   `${VAR}`/`.env` needed - that directory is private to this machine, never committed or
   shared, so this is as safe as a personal-scope MCP entry in `~/.claude.json`).
5. The generic `<name>_query_data` / `<name>_list_tables` tools (or the Redis/MongoDB op set)
   come from the template - write them derived from it, don't invent a different shape.

Then go to Step 6.

## Step 4 - Remove a connection

Delete its file from the live connections directory. Run Step 6's `check` afterward - a
custom tool elsewhere that still points `source:` at the connection just removed will now
fail to validate, and that needs surfacing before it's left broken.

## Step 5 - A specific custom tool

Follow `../../mcp/toolbox/examples/custom-tool.yaml.example`: point `source:` at an existing
(or just-added) source name, and write `statement`/`parameters` (or the Mongo/Redis
equivalent) for exactly what the user described - a fixed query, not a redesign of their
schema. Then go to Step 6.

## Step 6 - Validate and apply, every time

```bash
../../mcp/toolbox/validate.sh snapshot <connections-dir>   # before ANY change
# make the change: write/edit/delete files
../../mcp/toolbox/validate.sh check <connections-dir>
```

`check` FAILS → `../../mcp/toolbox/validate.sh restore <connections-dir>`, read the exact
error it printed, fix the file, and repeat from the "make the change" step. `check` PASSES →
the config itself is good; move to Step 7.

Never skip this because a change "looks simple" - `toolbox` validates its whole
`--config-folder` as one unit, so a single typo anywhere breaks every connection, not just
the new one (this is exactly the bug `validate.sh` exists to catch before it reaches a live
session).

## Step 7 - Tell the user to reconnect

There is no way for Claude Code to force the already-running `toolbox` connection to pick up
a config change itself - `toolbox`'s advertised dynamic-reload didn't observably trigger in
testing under `--stdio`, and there's no `claude mcp reconnect`/`restart` command. Say plainly
that the change is saved and validated, but won't take effect until the user opens `/mcp`,
selects `toolbox`, and reconnects (or starts a new session). Never imply it's already live.

## Constraints

### MUST DO

- Confirm (or actively obtain) a read-only account before wiring up a connection meant only
  for querying.
- Run the Step 6 snapshot/check/restore flow around every change to the live connections
  directory, no exceptions.
- Check whether a connection of the requested type/name already exists before adding a
  duplicate.
- Tell the user explicitly that reconnecting (Step 7) is required - never claim a change is
  already live.
- Discover the connections-dir path via `claude mcp list` - never hardcode or guess it, it
  varies by install (marketplace vs `--plugin-dir`, plugin id, etc.).

### MUST NOT DO

- Never grant or assume write access to a connection without the user explicitly asking for
  it.
- Never write directly into the live connections directory without a preceding `snapshot`.
- Never leave a `check` failure unresolved - always restore and report the exact error.

## Boundaries

- Manages only `mcp/toolbox/`'s own connections and tools. A different, unrelated third-party
  MCP server is `mcp-setup`'s job.
- Doesn't author `toolbox` itself or a new MCP server from scratch - that's `mcp-developer`.
- Query/schema design beyond what the user explicitly asked for belongs to `database-skill`/
  `redis-skill`, not this skill - this wires up the connection and the tool shape, not
  broader data modeling.

## Knowledge Reference

`mcp/toolbox/README.md` (setup, structure, why read-only), `mcp/toolbox/validate.sh`
(snapshot/check/restore), `mcp/toolbox/examples/*.yaml.example` (connection/tool templates).
