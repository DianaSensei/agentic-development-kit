# Database MCP (PostgreSQL, MySQL, TiDB, Redis, MongoDB)

Configuration for Google's [MCP Toolbox](https://github.com/googleapis/mcp-toolbox) - a
locally-run binary that sits between Claude Code and your database. Once connected, you can
ask Claude Code directly: "list the tables in the primary database", "get the value of key
user:123 in Redis", instead of opening each database's own client.

Pre-configured for two PostgreSQL sources (`primary`, `analytics`), one MySQL, one TiDB, one
Redis, and one MongoDB. You don't have to use all six - any source without connection info
is simply skipped, without affecting the others.

Important note: the PostgreSQL, MySQL, and TiDB portions of this configuration are
read-only, with no tool that writes/deletes/modifies tables. The reasoning and how this is
enforced are described at the end of this document.

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
For PostgreSQL, MySQL, and TiDB specifically, request an account with read-only
permissions, not an admin account.

## Configure `.env`

```bash
cp .env.example .env
```

| Variable | Applies to | Note |
|---|---|---|
| `POSTGRES_PRIMARY_*` | PostgreSQL #1 | host/port/database/user/password - the user must be a read-only account |
| `POSTGRES_ANALYTICS_*` | PostgreSQL #2 | same, if there's a second source |
| `MYSQL_*` | MySQL | host/port/database/user/password - the user must be a read-only account |
| `TIDB_*` | TiDB | host/port/database/user/password - the user must be a read-only account; default port `4000` |
| `REDIS_ADDRESS` | Redis | in the form `host:port` |
| `REDIS_USERNAME` / `REDIS_PASSWORD` | Redis | leave blank if no auth is used |
| `REDIS_DATABASE` | Redis | database index, defaults to `0` |
| `MONGODB_URI` | MongoDB | the full connection string |
| `MONGODB_DATABASE` / `MONGODB_COLLECTION` | MongoDB | default database/collection |

Any source you're not using can keep its sample value.

## Register with Claude Code

This plugin ships a `.mcp.json` at its root that declares `toolbox` in stdio mode, so
Claude Code starts and connects it automatically whenever this plugin is enabled - there's
no `claude mcp add` step, and no separate process to keep running in another terminal.
Toolbox itself does the `${VAR}` substitution in `tools.yaml`, reading straight from the
process environment it inherits, so the variables from `.env` need to be exported into your
shell **before** you start `claude`:

```bash
set -a && source mcp/toolbox/.env && set +a
claude
```

Any source whose variables aren't set is simply skipped by `toolbox`, without affecting the
others - so this is safe to run even if you've only filled in some of the six sources.

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
- "Query the first 10 rows of the users table in MySQL"
- "List the tables in the TiDB database"
- "Query the first 10 rows of the users table in TiDB"
- "Get the value of key session:abc123 in Redis"
- "Find documents with status=active in MongoDB"

Mention the data source explicitly (primary/analytics/MySQL/TiDB/Redis/MongoDB) in your
request, Claude Code will pick the right tool accordingly.

---

## Advanced configuration

**Running it as a standalone HTTP server instead** - useful if you want to keep toolbox
running independently of any single Claude Code session (e.g. sharing one instance across
machines), instead of relying on the plugin's bundled stdio config:

```bash
set -a && source .env && set +a
toolbox --config tools.yaml
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

Available toolsets: `postgres-primary-toolset`, `postgres-analytics-toolset`,
`mysql-toolset`, `tidb-toolset`, `redis-toolset`, `mongodb-toolset`, `all` (default, and
what the plugin's bundled stdio config uses).

**Adding a third PostgreSQL data source** - copy a `kind: source` block in `tools.yaml`
(e.g. `postgres-analytics-source`), rename it, point it to a new set of environment
variables (e.g. `POSTGRES_REPORTING_*`), and add those variables to `.env` and
`.env.example`. Also copy the accompanying `*_query_data` and `*_list_tables` tools and add
them to a toolset.

**TiDB and TLS** - for TiDB Cloud, Toolbox auto-enables TLS when `TIDB_HOST` matches the
`*.tidbcloud.com` pattern, no extra config needed. For a self-hosted TiDB cluster that
requires TLS, add `ssl: true` to the `tidb-source` block in `tools.yaml`.

## Why PostgreSQL, MySQL, and TiDB are read-only

Toolbox doesn't inspect the content of SQL statements before executing them - whatever is
passed in gets run verbatim, as long as the connecting account has the permission to
execute it. `tools.yaml` deliberately doesn't define any write/delete/modify tool, but this
is only a protection layer at the configuration level, not a hard technical limit.

The real protection layer is the PostgreSQL/MySQL/TiDB account declared in `.env`. This
account should only have SELECT permission - no INSERT/UPDATE/DELETE, doesn't own any
tables, has no DDL permission. In that case, even if a write statement is requested, the
database will reject it with a permission-denied error, regardless of `tools.yaml`'s
content.

This repo doesn't create or modify that account's permissions - request a read-only
account from your database administrator, the same as the process for granting access to
any other read-only reporting tool.
