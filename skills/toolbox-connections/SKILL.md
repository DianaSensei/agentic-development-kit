---
name: toolbox-connections
description: Configure database connections and tools for this plugin's own bundled toolbox MCP server (mcp/toolbox/) - PostgreSQL, MySQL, TiDB, Redis, MongoDB, or any other SQL type Toolbox supports. Checks whether a datasource is already configured before adding a duplicate, sets up a new one (values via this plugin's settings for the six pre-built connections, or a hand-written connection file for anything else), derives the standard query/list-tables tools automatically, and writes a custom parameterized tool on request. Always applies changes through validate.sh's snapshot/check/restore flow, since toolbox fails its entire server over one bad file, not just the connection with the mistake. Use when the user asks to add/configure/remove a toolbox database connection, or to add a custom toolbox tool/query. Do NOT use for connecting a different, unrelated third-party MCP server (use `mcp-setup`), or for authoring toolbox itself/a new MCP server from scratch (use `mcp-developer`).
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
and auto-connects. Not for any other MCP server (see Boundaries).

## Step 1 - Find the live state

```bash
claude mcp list | grep '^plugin:agentic-development-kit:toolbox'
```

The line's `--config-folder` value is the live connections directory. If there's no such
line, toolbox isn't enabled in this session - say so and stop; this skill configures an
already-connected server, it can't enable a disabled one.

`ls` that directory. A pre-built connection's file (`postgres-primary.yaml`,
`postgres-analytics.yaml`, `mysql.yaml`, `tidb.yaml`, `redis.yaml`, `mongodb.yaml`) is present
if and only if it's already fully configured - `toolbox-seed.sh` never adds one until every
required value is filled in, and removes it the moment one is cleared (see
`../../hooks/toolbox-seed.sh`). So file presence is a reliable "is this already set up"
signal for the six; for anything else, it's whatever other files are already sitting there.

## Step 2 - Figure out what's being asked

- One of the six pre-built types, not yet present → Step 3a.
- One of the six already present, user wants ANOTHER of the same type (e.g. a second MySQL) →
  Step 3b - the six only cover one slot each.
- Any other SQL type Toolbox supports, or a type outside the six generally → Step 3b.
- Remove/disable a connection → Step 3c.
- A specific query/tool beyond the generic pair → Step 4 (can combine with 3a/3b for a new
  connection, or attach to an existing one).

## Step 3a - Configure a pre-built connection

Ask the user for the values that connection needs (host/port/database/user/password for a
SQL type; address for Redis; uri/database/collection for MongoDB - see
`.claude-plugin/plugin.json`'s `userConfig` block for the exact field list and descriptions).

**Always ask about the account's permissions before wiring it up**: confirm it's read-only
(SELECT-only, no INSERT/UPDATE/DELETE/DDL) unless the user explicitly wants write access. If
they're not sure or say it isn't read-only, explain why this matters (see
`../../mcp/toolbox/README.md`'s "Why PostgreSQL, MySQL, and TiDB are read-only" section) and
get their explicit confirmation either way before proceeding - don't silently assume.

Set the values non-interactively:

```bash
claude plugin list                              # find the exact "<id>@<marketplace>"
claude plugin install <id>@<marketplace> \
  --config postgres_primary_host=... \
  --config postgres_primary_password=... \
  ... \
  -y
```

This works for `sensitive: true` fields too (passwords, `mongodb_uri`) - Claude Code stores
them securely, the same path as the interactive Configure UI, never in plain `settings.json`.
Then go to Step 5.

## Step 3b - Add a connection outside the six

Follow `../../mcp/toolbox/examples/new-sql-connection.yaml.example` (SQL) or duplicate an
existing `redis.yaml`/`mongodb.yaml`-shaped file and rename every identifier (NoSQL):

1. Ask for the type, and its connection values - same read-only confirmation as Step 3a.
2. Pick a short, unique name not already used by another source/tool/toolset in the live
   directory (`orders`, `mysql_secondary`, ...).
3. Write the file straight into the live connections directory with the LITERAL values (no
   `${VAR}`/`.env` needed - that directory is private to this machine, never committed or
   shared, so this is as safe as a personal-scope MCP entry in `~/.claude.json`).
4. The generic `<name>_query_data` / `<name>_list_tables` tools (or the Redis/MongoDB op set)
   come from the template - write them derived from it, don't invent a different shape.

Then go to Step 5.

## Step 3c - Remove a connection

- One of the six: clear every one of its fields (`--config key=` with an empty value, or tell
  the user to clear them via `/plugin` → Configure). The next sync removes its file
  automatically - don't delete the file yourself for these, since a value might get refilled
  later and should reseed cleanly.
- Anything else: delete its file from the live connections directory directly.

Either way, run Step 5's `check` afterward - a custom tool elsewhere that still points
`source:` at the connection just removed will now fail to validate, and that needs surfacing
before it's left broken.

## Step 4 - A specific custom tool

Follow `../../mcp/toolbox/examples/custom-tool.yaml.example`: point `source:` at an existing
(or just-added) source name, and write `statement`/`parameters` (or the Mongo/Redis
equivalent) for exactly what the user described - a fixed query, not a redesign of their
schema. Then go to Step 5.

## Step 5 - Validate and apply, every time

```bash
../../mcp/toolbox/validate.sh snapshot <connections-dir>   # before ANY change
# make the change: write/edit/delete files, or run the --config command above
../../mcp/toolbox/validate.sh check <connections-dir>
```

`check` FAILS → `../../mcp/toolbox/validate.sh restore <connections-dir>`, read the exact
error it printed, fix the file, and repeat from the "make the change" step. `check` PASSES →
the config itself is good; move to Step 6.

Never skip this because a change "looks simple" - `toolbox` validates its whole
`--config-folder` as one unit, so a single typo anywhere breaks every connection, not just
the new one (this is exactly the bug `validate.sh` exists to catch before it reaches a live
session).

## Step 6 - Tell the user to reconnect

There is no way for Claude Code to force the already-running `toolbox` connection to pick up
a config change itself - `toolbox`'s advertised dynamic-reload didn't observably trigger in
testing under `--stdio`, and there's no `claude mcp reconnect`/`restart` command. Say plainly
that the change is saved and validated, but won't take effect until the user opens `/mcp`,
selects `toolbox`, and reconnects (or starts a new session). Never imply it's already live.

## Constraints

### MUST DO

- Confirm (or actively obtain) a read-only account before wiring up a connection meant only
  for querying.
- Run the Step 5 snapshot/check/restore flow around every change to the live connections
  directory, no exceptions.
- Check whether a connection of the requested type already exists before adding a duplicate.
- Tell the user explicitly that reconnecting (Step 6) is required - never claim a change is
  already live.
- Discover the plugin id and connections-dir path via `claude plugin list`/`claude mcp list`
  - never hardcode or guess them, they vary by install (marketplace vs `--plugin-dir`, etc.).

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
(snapshot/check/restore), `mcp/toolbox/examples/*.yaml.example` (connection/tool templates),
`.claude-plugin/plugin.json`'s `userConfig` (the six pre-built connections' exact fields),
`hooks/toolbox-seed.sh` (why a pre-built connection's file only exists once fully
configured).
