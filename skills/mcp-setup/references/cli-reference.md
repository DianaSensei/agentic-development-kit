# `claude mcp` CLI Reference

## Scopes

| Scope | Flag | Stored in | Loads in | Shared with team |
|-------|------|-----------|----------|-------------------|
| Local | (default, or `--scope local`) | `~/.claude.json`, under this project's entry | This project only | No |
| Project | `--scope project` | `.mcp.json` in the project root | This project only | Yes - commit `.mcp.json` |
| User | `--scope user` | `~/.claude.json`, top-level `mcpServers` key | Every project | No |

**Precedence when the same server name exists at more than one scope**: Local > Project > User >
plugin-provided servers > claude.ai connectors. The entire entry from the highest-precedence source is
used - fields are never merged across scopes. A scope is fixed at add time; to change it, remove the
entry and re-add at the new scope.

## Transports

| Transport | Flag | Use for |
|-----------|------|---------|
| stdio | (default; no flag needed) | A local process Claude Code starts as a subprocess (`npx`, `uvx`, `python`, `docker run`, a binary) |
| http | `--transport http` | A hosted server reached over a URL. `streamable-http` is accepted as an alias - some server docs use that name directly from the MCP spec. |
| sse | `--transport sse` | **Deprecated.** Only use if the server has no HTTP endpoint. |
| ws | `--transport ws` | A hosted server needing a persistent bidirectional connection (server can push events unprompted). Does not support OAuth or `--transport` shorthand the same way HTTP does - check the server's own docs for exact setup. |

An entry with a `url` but no `type`/`--transport` is a configuration error - Claude Code will otherwise
assume stdio and fail with a confusing error. Always be explicit.

## Command Syntax

**Remote server (http/sse/ws):**
```bash
claude mcp add --transport http <name> <url>
claude mcp add --transport http --scope project <name> <url>   # team-shared
```

**Local stdio server** - everything after `--` is passed to the server untouched; this separates
Claude Code's own flags (`--transport`, `--env`, `--scope`, `--header`) from the server's command/args:
```bash
claude mcp add <name> -- <command> [args...]

# Example
claude mcp add playwright -- npx -y @playwright/mcp@latest
```

**With environment variables** (`--env` accepts multiple `KEY=value` pairs; place at least one other
flag between `--env` and the server name, or the name gets parsed as another `KEY=value` pair):
```bash
claude mcp add --env API_KEY=your-key --transport stdio <name> -- npx -y some-mcp-server
```

**With a static-token auth header** (for HTTP/SSE servers that use a bearer token instead of OAuth):
```bash
claude mcp add --transport http <name> <url> --header "Authorization: Bearer <token>"
```

## Managing Servers

```bash
claude mcp list                    # status of every registered server
claude mcp get <name>              # which scope holds this server's definition, and its config
claude mcp remove <name>           # remove; add --scope if the name exists in multiple scopes
claude mcp reset-project-choices   # re-prompt for approval on project-scoped servers you'd previously rejected
```

Inside a running session, `/mcp` opens an interactive panel: check status, authenticate a server that
needs OAuth sign-in, or reconnect one that failed - without leaving the conversation.

## `.mcp.json` Schema (Project Scope)

```json
{
  "mcpServers": {
    "a-stdio-server": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@some/mcp-server"],
      "env": { "API_KEY": "${SOME_SERVICE_API_KEY}" }
    },
    "a-http-server": {
      "type": "http",
      "url": "${API_BASE_URL:-https://api.example.com}/mcp",
      "headers": { "Authorization": "Bearer ${SOME_SERVICE_TOKEN}" }
    }
  }
}
```

Fields by type:
- `stdio`: `command`, `args`, `env` (all optional except `command`)
- `http` / `sse` / `ws`: `url`, `headers` (both optional except `url`)

Claude Code re-reads `.mcp.json` at session start only - changes require a new session to take effect.
The first time a project-scoped server is seen, each teammate gets a one-time approval prompt (so a
cloned repo can't silently launch processes on their machine); approve it, or run `/mcp` to approve
later if missed.

## Environment Variable Expansion (any `.mcp.json` or `~/.claude.json` entry)

Supported inside `command`, `args`, `env`, `url`, and `headers`:
- `${VAR}` - expands to the value of environment variable `VAR`
- `${VAR:-default}` - expands to `VAR` if set, else `default`

This is the mechanism that lets a Project-scoped, git-committed config carry no literal secrets - see
`references/secrets-handling.md`. If a referenced variable isn't set and has no default, the config
still loads, but `claude mcp list` reports a missing-variable warning for that server and the literal
`${VAR}` text is used as-is (the server will then fail to authenticate).

## Authentication Patterns

| Pattern | How it's registered | Verification |
|---------|----------------------|----------------|
| None | Just add the server, no extra flags | `claude mcp list` → `✔ Connected` |
| Static token/API key | `--header "Authorization: Bearer <token>"` (http/sse) or `--env API_KEY=...` (stdio) | `claude mcp list` → `✔ Connected` immediately |
| OAuth | Add with no token; status shows `! Needs authentication` | Run `/mcp` in a session → select the server → `Authenticate` → browser sign-in |

`CLAUDE_PROJECT_DIR` is automatically set in a stdio server's environment to the project root - a
server can read it (`process.env.CLAUDE_PROJECT_DIR` in Node, `os.environ["CLAUDE_PROJECT_DIR"]` in
Python) to resolve project-relative paths. If referencing it via `${CLAUDE_PROJECT_DIR}` expansion in
a config entry (not inside the spawned server's own code), use the default form
`${CLAUDE_PROJECT_DIR:-.}`, since that variable isn't set in Claude Code's own environment.
