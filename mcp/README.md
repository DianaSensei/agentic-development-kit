# Common MCP Server

Configuration for connecting Claude Code to external systems via MCP (Model Context
Protocol) - a mechanism that lets Claude Code reach beyond the local codebase, e.g. query a
database, through MCP servers that act as bridges to each specific system.

## List of MCP servers

| Directory | Function |
|---|---|
| [`mcp/toolbox/`](./toolbox/README.md) | Query PostgreSQL, MySQL, TiDB, Redis, MongoDB (read-only) |

`toolbox` is declared in the plugin's root `.mcp.json`, so Claude Code starts and connects
it automatically whenever this plugin is enabled - no `claude mcp add` step. It still needs
the `toolbox` binary installed, and its connection values configured via this plugin's
settings (`/plugin`); see [`mcp/toolbox/README.md`](./toolbox/README.md) for setup. Six
connections (PostgreSQL x2, MySQL, TiDB, Redis, MongoDB) ship pre-built and are seeded
automatically into a persistent, writable directory the first time you use the plugin - the
set isn't fixed there either, so add, remove, or hand-write custom tools freely; see the
"Structure" section of that README. Any connection without configuration info is simply
skipped, without affecting the others.

You can also ask Claude Code to carry out the whole setup itself - for example, "set up the
toolbox MCP for me" - and it will read the README and walk you through it.
