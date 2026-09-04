# Database MCP (arbitrary connections)

Configuration for Google's [MCP Toolbox](https://github.com/googleapis/mcp-toolbox) - a
locally-run binary that sits between Claude Code and your database(s). Once connected, you
can ask Claude Code directly: "list the tables in the primary database", "get the value of
key user:123 in Redis", instead of opening each database's own client.

## Structure

```
mcp/toolbox/
├── connections/   # loaded by Toolbox - one file per connection, each self-contained
│   ├── postgres-primary.yaml
│   ├── postgres-analytics.yaml
│   ├── mysql.yaml
│   ├── tidb.yaml
│   ├── redis.yaml
│   └── mongodb.yaml
├── examples/      # NOT loaded (kept as .yaml.example) - copy from here to add your own
│   ├── new-sql-connection.yaml.example
│   └── custom-tool.yaml.example
└── .env.example
```

Every file in `connections/` is independent - Toolbox merges all `*.yaml`/`*.yml` files in
that directory (`--config-folder`), but each connection's `source`/`tool`/`toolset` blocks
only reference names within its own file. This means:

- **Don't need a connection?** Delete its file, or move it out of `connections/`. Nothing
  else breaks.
- **Have a database not listed here?** Copy `examples/new-sql-connection.yaml.example` into
  `connections/`, rename it, and fill in the placeholders - works for any SQL type Toolbox
  supports (postgres, mysql, tidb, mssql, sqlite, spanner, bigquery, ...), not just the six
  pre-built here. For a second Redis/MongoDB-shaped connection, duplicate `redis.yaml` /
  `mongodb.yaml` and rename every identifier inside.
- **Want a specific, hand-written tool** (a fixed query/aggregation with named parameters)
  instead of - or alongside - the generic `query_data`/`list_tables` pair? Copy
  `examples/custom-tool.yaml.example` into `connections/`, point it at an existing
  `source:` name, and write the exact statement/parameters you want. It becomes just
  another tool Claude Code can call, no different from the built-in ones.

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

## Configure `.env`

```bash
cp .env.example .env
```

| Variable | Applies to | Note |
|---|---|---|
| `POSTGRES_PRIMARY_*` | `connections/postgres-primary.yaml` | host/port/database/user/password - read-only account |
| `POSTGRES_ANALYTICS_*` | `connections/postgres-analytics.yaml` | same, if there's a second source |
| `MYSQL_*` | `connections/mysql.yaml` | host/port/database/user/password - read-only account |
| `TIDB_*` | `connections/tidb.yaml` | host/port/database/user/password - read-only account; default port `4000` |
| `REDIS_ADDRESS` | `connections/redis.yaml` | in the form `host:port` |
| `REDIS_USERNAME` / `REDIS_PASSWORD` | `connections/redis.yaml` | leave blank if no auth is used |
| `REDIS_DATABASE` | `connections/redis.yaml` | database index, defaults to `0` |
| `MONGODB_URI` | `connections/mongodb.yaml` | the full connection string |
| `MONGODB_DATABASE` / `MONGODB_COLLECTION` | `connections/mongodb.yaml` | default database/collection |

Any connection you're not using can keep its sample value, or have its file removed
entirely (see "Structure" above). Add your own connection's variables here too, following
`examples/new-sql-connection.yaml.example`'s naming convention.

## Register with Claude Code

This plugin ships a `.mcp.json` at its root that declares `toolbox` in stdio mode, pointed
at `connections/`, so Claude Code starts and connects it automatically whenever this plugin
is enabled - there's no `claude mcp add` step, and no separate process to keep running in
another terminal. Toolbox itself does the `${VAR}` substitution inside each connection file,
reading straight from the process environment it inherits, so the variables from `.env`
need to be exported into your shell **before** you start `claude`:

```bash
set -a && source mcp/toolbox/.env && set +a
claude
```

Any connection whose variables aren't set is simply skipped by `toolbox`, without affecting
the others - so this is safe to run even if you've only filled in some connections.

Confirm it connected:

```bash
claude mcp list
```

A `✔ Connected` status next to `toolbox` means it's done. If you see `✘ Failed to connect`,
double check that the `toolbox` binary is on `PATH` (`toolbox --version`) and that `.env`
was sourced into the shell Claude Code was started from - it's usually a missing or
incorrect value in `.env`, or `claude` having been started from a different shell than the
one `.env` was sourced into.

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
set -a && source .env && set +a
toolbox --config-folder connections
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

Each connection file in `connections/` defines its own toolset with a matching name (e.g.
`redis-toolset`, `postgres-primary-toolset`) - check the file for the exact name, or a
custom one you added.

**TiDB and TLS** - for TiDB Cloud, Toolbox auto-enables TLS when `TIDB_HOST` matches the
`*.tidbcloud.com` pattern, no extra config needed. For a self-hosted TiDB cluster that
requires TLS, add `ssl: true` to the `tidb-source` block in `connections/tidb.yaml`.

## Why PostgreSQL, MySQL, and TiDB are read-only

Toolbox doesn't inspect the content of SQL statements before executing them - whatever is
passed in gets run verbatim, as long as the connecting account has the permission to
execute it. The `connections/*.yaml` files deliberately don't define any write/delete/modify
tool, but this is only a protection layer at the configuration level, not a hard technical
limit. The same is true of any custom SQL tool you add via
`examples/custom-tool.yaml.example` - write the statement as read-only, but don't rely on it
alone.

The real protection layer is the database account declared in `.env`. This account should
only have SELECT permission - no INSERT/UPDATE/DELETE, doesn't own any tables, has no DDL
permission. In that case, even if a write statement is requested, the database will reject
it with a permission-denied error, regardless of the YAML config's content.

This repo doesn't create or modify that account's permissions - request a read-only account
from your database administrator, the same as the process for granting access to any other
read-only reporting tool.
