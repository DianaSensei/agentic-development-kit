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

## Try it out

In this directory (use `toolbox` if installed via Homebrew, or `./toolbox` if you
downloaded the binary directly into this directory):

```bash
set -a && source .env && set +a
toolbox --config tools.yaml
```

Seeing `Server ready to serve!` means it started successfully. Keep this process running,
don't close the terminal.

If you run into an error, it's usually caused by an incorrect value in `.env` - the error
message typically points out which field is invalid.

## Register with Claude Code

Open a different terminal (don't close the running toolbox process):

```bash
claude mcp add toolbox --scope user --transport http http://127.0.0.1:5000/mcp
```

Confirm:

```bash
claude mcp list
```

A `✔ Connected` status next to `toolbox` means it's done. If you see
`✘ Failed to connect`, check whether the toolbox process from the previous step is still
running.

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

**Running as stdio instead of keeping an HTTP process alive** - Claude Code will start
toolbox itself when needed, no need to keep a terminal running continuously:

```bash
claude mcp add toolbox --scope user -- toolbox --stdio --config /absolute-path/tools.yaml
```

This approach requires the variables in `.env` to be loaded into the environment before
Claude Code starts the process - more complex than HTTP, so only use it if you have a
specific reason.

**Limiting connection scope, e.g. only exposing Redis** - add the toolset name to the end
of the URL:

```bash
claude mcp add redis-only --scope user --transport http http://127.0.0.1:5000/mcp/redis-toolset
```

Available toolsets: `postgres-primary-toolset`, `postgres-analytics-toolset`,
`mysql-toolset`, `tidb-toolset`, `redis-toolset`, `mongodb-toolset`, `all` (default).

**Registering via a config file instead of the CLI command** - `claude mcp add`
essentially just writes to a config file, which can be edited directly. Personal scope,
edit `~/.claude.json`:

```json
{
  "mcpServers": {
    "toolbox": { "type": "http", "url": "http://127.0.0.1:5000/mcp" }
  }
}
```

To share with the team, create `.mcp.json` at the project root and commit it to git (each
team member still runs toolbox on their own machine):

```json
{
  "mcpServers": {
    "toolbox": {
      "type": "stdio",
      "command": "toolbox",
      "args": ["--stdio", "--config", "${CLAUDE_PROJECT_DIR}/mcp/toolbox/tools.yaml"]
    }
  }
}
```

Claude Code only re-reads `.mcp.json` when a new session is opened.

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
