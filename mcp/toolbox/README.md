# Database MCP (arbitrary connections)

Configuration for Google's [MCP Toolbox](https://github.com/googleapis/mcp-toolbox) - a
locally-run binary that sits between Claude Code and your database(s). Once connected, you
can ask Claude Code directly: "list the tables in the primary database", "get the value of
key user:123 in Redis", instead of opening each database's own client.

This plugin is installed via the marketplace (`/plugin install`), not a repo clone - so
nothing here assumes you have a local checkout to edit. Configuration lives in two places
instead, both of which persist across plugin updates:

- **This plugin's settings** (`/plugin`) - for the 6 pre-built connections' host/port/user/
  password-style values.
- **`${CLAUDE_PLUGIN_DATA}/connections/`** - a private, writable directory Claude Code
  creates for this plugin (survives updates, deleted only if you uninstall the plugin) -
  for the connection files themselves, seeded automatically the first time this plugin runs,
  and where you add/edit/remove connections and custom tools afterward.

## Structure

```
mcp/toolbox/                          (inside the plugin's own install - read-only to you)
├── connections-defaults/             seeded once into ${CLAUDE_PLUGIN_DATA}/connections/
│   ├── postgres-primary.yaml
│   ├── postgres-analytics.yaml
│   ├── mysql.yaml
│   ├── tidb.yaml
│   ├── redis.yaml
│   └── mongodb.yaml
└── examples/                         reference templates, never loaded by Toolbox
    ├── new-sql-connection.yaml.example
    └── custom-tool.yaml.example

${CLAUDE_PLUGIN_DATA}/connections/    (your actual, writable, live config - not in the repo)
├── postgres-primary.yaml             ← seeded copy, edit/delete freely
├── ...
```

Every file Toolbox loads is independent - Toolbox merges all `*.yaml`/`*.yml` files in
`${CLAUDE_PLUGIN_DATA}/connections/` (`--config-folder`), but each connection's
`source`/`tool`/`toolset` blocks only reference names within its own file. This means:

- **Don't need a connection?** Delete its file (or ask Claude Code to). Nothing else breaks.
- **Have a database not listed here?** Ask Claude Code to add it (e.g. "add a toolbox
  connection for my orders Postgres database"), or copy
  `examples/new-sql-connection.yaml.example` into `${CLAUDE_PLUGIN_DATA}/connections/`
  yourself, rename it, and fill in the placeholders - works for any SQL type Toolbox
  supports (postgres, mysql, tidb, mssql, sqlite, spanner, bigquery, ...), not just the six
  pre-built here. For a second Redis/MongoDB-shaped connection, duplicate the seeded
  `redis.yaml` / `mongodb.yaml` and rename every identifier inside.
- **Want a specific, hand-written tool** (a fixed query/aggregation with named parameters)
  instead of - or alongside - the generic `query_data`/`list_tables` pair? Copy
  `examples/custom-tool.yaml.example`, point it at an existing `source:` name, and write the
  exact statement/parameters you want. It becomes just another tool Claude Code can call, no
  different from the built-in ones.

Since `${CLAUDE_PLUGIN_DATA}/connections/` is private to your machine (not committed to git,
not shared with a team), it's fine to write real connection values directly into a file
there - no `${VAR}`/`.env` indirection needed for a connection you add yourself. The
pre-built six use `${VAR}` placeholders instead because their real values come from this
plugin's settings (below), not from editing the file.

The six pre-built connections are a starting point, not a fixed set - use as many, as few,
or as different a set of connections as you actually have.

Important note: the PostgreSQL, MySQL, and TiDB connections shipped here are read-only, with
no tool that writes/deletes/modifies tables. The reasoning and how this is enforced are
described at the end of this document - the same reasoning applies to any SQL connection you
add yourself.

## Install the binary

The official installation instructions, updated for the latest version, are at the
[MCP Toolbox introduction page](https://mcp-toolbox.dev/documentation/introduction/#installing-the-server)
and the [GitHub Releases page](https://github.com/googleapis/mcp-toolbox/releases)
- refer to these two pages if the suggestions below become outdated.

On macOS, the fastest way is via Homebrew (always fetches the latest version, no need to
download a specific version yourself):

```bash
brew install mcp-toolbox
```

This installs a binary named `toolbox`. Run `toolbox --version` to confirm. If you're not
using Homebrew, or on Linux/Windows, download the binary directly from the Releases page
above, choosing the right build for your OS.

You'll also need database connection info - request it from your system administrator.
For any SQL connection, request an account with read-only permissions, not an admin account.

## Configure the pre-built connections

Open this plugin's settings - `/plugin` in Claude Code, select `agentic-development-kit`,
Configure - and fill in whichever connections you're using:

| Setting group | Applies to |
|---|---|
| PostgreSQL (primary) | `postgres-primary.yaml` |
| PostgreSQL (analytics) | `postgres-analytics.yaml` |
| MySQL | `mysql.yaml` |
| TiDB | `tidb.yaml` (default port `4000`) |
| Redis | `redis.yaml` |
| MongoDB | `mongodb.yaml` |

Leave every field of a connection blank to skip it entirely - Toolbox simply won't connect
that one, without affecting the others. Password/token/URI fields are marked sensitive and
stored securely (Keychain on macOS), never written to a plain settings file.

You don't have to use this UI - `claude mcp get toolbox` also shows the underlying config if
you'd rather inspect or script it.

## Automatic setup - nothing else to run

This plugin ships a `.mcp.json` at its root declaring `toolbox` in stdio mode, so Claude Code
starts and connects it automatically whenever the plugin is enabled - no `claude mcp add`
step. A `SessionStart` hook also seeds `${CLAUDE_PLUGIN_DATA}/connections/` with the six
pre-built connection files the first time you use this plugin, so there's no file to copy by
hand. After filling in the settings above, just start (or restart) a session:

```bash
claude
```

Confirm it connected:

```bash
claude mcp list
```

A `✔ Connected` status next to `toolbox` means it's done. If you see `✘ Failed to connect`,
double check that the `toolbox` binary is on `PATH` (`toolbox --version`) - that's the most
common cause; the settings above only supply values, they don't install the binary.

## Verify after connecting

Try a few requests with Claude Code:
- "List the tables in the primary database"
- "Query the first 10 rows of the users table in the analytics database"
- "List the tables in the MySQL database"
- "List the tables in the TiDB database"
- "Get the value of key session:abc123 in Redis"
- "Find documents with status=active in MongoDB"

Mention the connection explicitly (primary/analytics/MySQL/TiDB/Redis/MongoDB, or whatever
name you gave a connection you added yourself) in your request, Claude Code will pick the
right tool accordingly.

---

## Advanced configuration

**Running it as a standalone HTTP server instead** - useful if you want to keep toolbox
running independently of any single Claude Code session (e.g. sharing one instance across
machines), instead of relying on the plugin's bundled stdio config:

```bash
toolbox --config-folder "$CLAUDE_PLUGIN_DATA/connections"
```

Seeing `Server ready to serve!` means it started successfully; keep the process running.
Then, in a different terminal, register it as its own server (this runs alongside, not
instead of, the plugin's bundled `toolbox` entry - give it a different name):

```bash
claude mcp add toolbox-http --scope user --transport http http://127.0.0.1:5000/mcp
```

**Limiting connection scope, e.g. only exposing Redis** - only relevant to the HTTP mode
above; add the toolset name to the end of the URL:

```bash
claude mcp add redis-only --scope user --transport http http://127.0.0.1:5000/mcp/redis-toolset
```

Each connection file defines its own toolset with a matching name (e.g. `redis-toolset`,
`postgres-primary-toolset`) - check the file for the exact name, or a custom one you added.

**TiDB and TLS** - for TiDB Cloud, Toolbox auto-enables TLS when `TIDB_HOST` matches the
`*.tidbcloud.com` pattern, no extra config needed. For a self-hosted TiDB cluster that
requires TLS, add `ssl: true` to the `tidb-source` block in your seeded `tidb.yaml`.

## Why PostgreSQL, MySQL, and TiDB are read-only

Toolbox doesn't inspect the content of SQL statements before executing them - whatever is
passed in gets run verbatim, as long as the connecting account has the permission to
execute it. The pre-built connection files deliberately don't define any write/delete/modify
tool, but this is only a protection layer at the configuration level, not a hard technical
limit. The same is true of any custom SQL tool you add via
`examples/custom-tool.yaml.example` - write the statement as read-only, but don't rely on it
alone.

The real protection layer is the database account you configure. This account should only
have SELECT permission - no INSERT/UPDATE/DELETE, doesn't own any tables, has no DDL
permission. In that case, even if a write statement is requested, the database will reject
it with a permission-denied error, regardless of the YAML config's content.

This repo doesn't create or modify that account's permissions - request a read-only account
from your database administrator, the same as the process for granting access to any other
read-only reporting tool.
