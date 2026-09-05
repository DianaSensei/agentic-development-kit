# Database MCP (arbitrary connections)

Configuration for Google's [MCP Toolbox](https://github.com/googleapis/mcp-toolbox) - a
locally-run binary that sits between Claude Code and your database(s). Once connected, you
can ask Claude Code directly: "list the tables in the users database", "get the value of key
user:123 in Redis", instead of opening each database's own client.

This plugin ships no pre-built connections - you add exactly the ones you actually have,
nothing more. See [`../../skills/toolbox-connections/SKILL.md`](../../skills/toolbox-connections/SKILL.md)
for the skill that does this for you when you ask ("add a toolbox connection for my orders
Postgres database"); the rest of this document is the manual version of the same flow, and
background on how it all fits together.

## Structure

```
mcp/toolbox/
├── validate.sh                       snapshot/check/restore helper - see below
└── examples/                         reference templates, never loaded by Toolbox
    ├── new-sql-connection.yaml.example
    ├── new-redis-connection.yaml.example
    ├── new-mongodb-connection.yaml.example
    └── custom-tool.yaml.example

${CLAUDE_PLUGIN_DATA}/connections/    (your actual, writable, live config - not in the repo)
├── orders-db.yaml                    ← whatever you've added, entirely yours
├── ...
└── (empty until you add a connection - toolbox refuses to start with none)
```

Every file Toolbox loads is independent - it merges all `*.yaml`/`*.yml` files in
`${CLAUDE_PLUGIN_DATA}/connections/` (`--config-folder`), but each connection's
`source`/`tool`/`toolset` blocks only reference names within its own file. This is a private,
writable directory Claude Code creates for this plugin (persists across plugin updates,
deleted only if you uninstall the plugin) - nothing here comes from a repo clone, and nothing
is pre-seeded into it.

Since it's private to your machine (not committed to git, not shared with a team), it's fine
to write real connection values directly into a file there - no `${VAR}`/`.env`/settings-UI
indirection. This is the only way connections work here: unlike an earlier version of this
plugin, there's no separate "pre-built connection configured through `/plugin` settings" path
- one mechanism for everything, so adding your fifth connection works exactly like your
first.

**Have a database to connect?** Ask Claude Code (e.g. "add a toolbox connection for my orders
Postgres database"), or copy the matching template into
`${CLAUDE_PLUGIN_DATA}/connections/` yourself:

- `examples/new-sql-connection.yaml.example` - any SQL type Toolbox supports (postgres,
  mysql, tidb, mssql, sqlite, spanner, bigquery, ...)
- `examples/new-redis-connection.yaml.example` - Redis
- `examples/new-mongodb-connection.yaml.example` - MongoDB

Rename the file and every `CONN_NAME` placeholder inside to something unique, fill in the
real values, and follow the "Adding a connection safely" flow below before it's live.

**Want a specific, hand-written tool** (a fixed query/aggregation with named parameters)
instead of - or alongside - the generic `query_data`/`list_tables` pair? Copy
`examples/custom-tool.yaml.example`, point it at an existing `source:` name, and write the
exact statement/parameters you want.

Important note: the SQL templates here default to read-only, with no tool that
writes/deletes/modifies tables. The reasoning and how this is enforced are described at the
end of this document.

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

## Adding a connection safely

Always go through `validate.sh` rather than writing a connection/tool file directly:

```bash
DIR="$(claude mcp list | grep '^plugin:agentic-development-kit:toolbox' \
  | grep -oE -- '--config-folder [^ ]+' | awk '{print $2}')"
./validate.sh snapshot "$DIR"   # before making any change
# ... write/edit/delete the file(s) ...
./validate.sh check "$DIR"      # confirms toolbox can actually start with the change
```

If `check` fails, `./validate.sh restore "$DIR"` undoes it, then fix the printed error and
try again. This matters because `--config-folder` is validated as one unit - a single mistake
in a new or edited file fails the *entire* server, taking every other working connection down
with it, not just the one being changed. The
[`toolbox-connections`](../../skills/toolbox-connections/SKILL.md) skill does this
automatically whenever Claude Code adds or edits a connection on your behalf.

## Nothing else to run - but nothing connects until you add one

This plugin ships a `.mcp.json` at its root declaring `toolbox` in stdio mode, so Claude Code
starts and connects it automatically whenever the plugin is enabled - no `claude mcp add`
step. But `toolbox` refuses to start with zero connection files (`"no YAML files found"`), so
right after installing you'll see `✘ Failed to connect` in `/mcp` - that's expected, not a
bug, until you add at least one connection per the section above.

Confirm it connected:

```bash
claude mcp list
```

A `✔ Connected` status next to `toolbox` means it's done. If you still see `✘ Failed to
connect` after adding a connection, double check that the `toolbox` binary is on `PATH`
(`toolbox --version`), and that you reconnected after adding the file - a config change only
takes effect after you open `/mcp` → `toolbox` → Reconnect (or start a new session); there's
no automatic hot-reload.

## Verify after connecting

Try a few requests with Claude Code, using whatever name you gave a connection:
- "List the tables in the orders database"
- "Query the first 10 rows of the users table"
- "Get the value of key session:abc123 in Redis"
- "Find documents with status=active in MongoDB"

Mention the connection explicitly if you have more than one of the same database type,
Claude Code will pick the right tool accordingly.

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

Each connection file defines its own toolset with a matching name - check the file for the
exact name you gave it.

**TiDB and TLS** - for TiDB Cloud, Toolbox auto-enables TLS when the host matches the
`*.tidbcloud.com` pattern, no extra config needed. For a self-hosted TiDB cluster that
requires TLS, add `ssl: true` to the source block in your connection file.

## Why the SQL templates default to read-only

Toolbox doesn't inspect the content of SQL statements before executing them - whatever is
passed in gets run verbatim, as long as the connecting account has the permission to
execute it. `examples/new-sql-connection.yaml.example` deliberately doesn't define any
write/delete/modify tool, but this is only a protection layer at the configuration level, not
a hard technical limit. The same is true of any custom SQL tool you add via
`examples/custom-tool.yaml.example` - write the statement as read-only, but don't rely on it
alone.

The real protection layer is the database account you configure. This account should only
have SELECT permission - no INSERT/UPDATE/DELETE, doesn't own any tables, has no DDL
permission. In that case, even if a write statement is requested, the database will reject
it with a permission-denied error, regardless of the YAML config's content.

This repo doesn't create or modify that account's permissions - request a read-only account
from your database administrator, the same as the process for granting access to any other
read-only reporting tool.
