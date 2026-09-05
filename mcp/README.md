# Common MCP Server

Configuration for connecting Claude Code to external systems via MCP (Model Context
Protocol) - a mechanism that lets Claude Code reach beyond the local codebase, e.g. query a
database, through MCP servers that act as bridges to each specific system.

## List of MCP servers

| Directory | Function |
|---|---|
| [`mcp/toolbox/`](./toolbox/README.md) | Query PostgreSQL, MySQL, TiDB, Redis, MongoDB, or any other type [MCP Toolbox](https://github.com/googleapis/mcp-toolbox) supports (SQL connections read-only by default) |

`toolbox` is declared in the plugin's root `.mcp.json`, so Claude Code starts and connects
it automatically whenever this plugin is enabled - no `claude mcp add` step. It still needs
the `toolbox` binary installed, and at least one connection added before it actually
connects (ships with none pre-built - see [`mcp/toolbox/README.md`](./toolbox/README.md) for
setup and why `✘ Failed to connect` right after installing is expected, not a bug).

Ask Claude Code to add one for you - for example, "add a toolbox connection for my orders
Postgres database" - and the [`toolbox-connections`](../skills/toolbox-connections/SKILL.md)
skill will walk you through it, including checking for an existing connection first and
asking about read-only permissions.

## Adding some other MCP server

Use `claude mcp add` - run `claude mcp --help` for the current flags rather than trusting a
written-down summary, since they change between versions.

Two rules worth knowing before you do, because getting them wrong is expensive:

- **Secrets depend on the scope.** A Local- or User-scoped server lives in `~/.claude.json`, which is
  never committed, so passing a secret value directly is fine. A **Project**-scoped one lives in
  `.mcp.json` **in git** - never write a literal secret there. Use `${VAR}` so the file carries only
  the variable name, and each teammate sets the real value in their own environment.
- **"Added" does not mean connected.** `claude mcp add` printing a success line only means the entry
  was saved. Always confirm with `claude mcp list` that the server actually shows `✔ Connected`;
  `! Needs authentication` is resolved with `claude mcp login <name>`.
