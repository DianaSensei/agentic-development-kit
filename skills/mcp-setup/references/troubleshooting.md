# Troubleshooting Decision Tree

Work through this in order - don't guess at a fix before isolating which layer the problem is in
(config not loaded, network/URL wrong, auth missing, or the server process itself erroring).

## `claude mcp list` shows nothing / "No MCP servers configured"

- Most common cause: the server was added Local-scoped from a *different* project directory - Local
  scope is tied to the exact project path it was added from. Re-add from the current project, or use
  `--scope user` if it shouldn't be tied to one project.
- Confirm the file was actually written to one of the two real locations: `~/.claude.json` or
  `<project>/.mcp.json`. Claude Code does not read any other path (not `~/.claude/mcp.json`, not
  `~/.claude/config/mcp.json`) - a server "added" to the wrong file silently does nothing.

## Status: `✘ Failed to connect` / `✘ Connection error`

**For an HTTP/SSE server**, check the URL is actually reachable:
```bash
curl -I <the-server-url>
```
- `404` or `405` → the server is up; many MCP endpoints only answer POST, so this still confirms
  reachability. If it's a genuine 404, double check the URL against the server's documented MCP
  endpoint path - a wrong path is a common copy-paste error.
- `401` or `403` → the server is up and needs authentication. Use OAuth (`/mcp` → `Authenticate`) or
  pass a token with `--header "Authorization: Bearer <token>"`, per whichever the server's docs specify.
- No response at all → check the URL for typos, and check network/firewall/VPN requirements.

**For a stdio server**, run its exact registered command directly in a terminal:
```bash
npx -y @some/mcp-server        # whatever `claude mcp get <name>` shows as the command
```
- If it starts and waits for input → the server itself works; the issue is in how it was registered.
  Run `claude mcp get <name>` and confirm the command shown matches exactly what you ran - a missing
  `--` separator before the command is the most common cause of a mismatch (Claude Code may have parsed
  part of the server's own arguments as its own flags instead).
- If it errors → the error message names what's actually missing (a runtime like Node/Python, a
  required file, a bad argument) - fix that directly rather than re-registering blindly.

## Status: `! Needs authentication`

Expected for OAuth-based servers immediately after adding. Inside a session: `/mcp` → select the
server → `Authenticate` → complete the browser sign-in. If the browser doesn't open automatically, copy
the printed URL and open it manually.

## Connected, but the tool list is empty

Run `/mcp`, select the server, and check its tool list. An empty list after a successful connection
almost always means a required environment variable (an API key, typically) wasn't actually set - the
server started, but immediately failed to initialize its tools without it. Re-check the required
variable name against the server's documentation, and confirm it's set with the exact name expected
(case-sensitive) in the environment `claude` was launched from - or, for Project scope, that the
teammate hitting this has actually exported the `${VAR}`-referenced variable locally.

## "Server already exists"

A server with that name is already registered - possibly at a different scope than intended.
```bash
claude mcp remove <name>                    # if only one scope has it
claude mcp remove <name> --scope local      # if it exists at multiple scopes, pick one
```
Confirm with the user before removing anything that might be a working, intentionally-configured entry.

## Changes to `.mcp.json` don't take effect

Claude Code reads `.mcp.json` at session start only - exit and restart the session after any edit.
If servers still don't appear, run `/mcp` and check for a parse warning (a malformed field is skipped
silently otherwise). If the user previously declined the approval prompt for a project-scoped server,
run `claude mcp reset-project-choices` to be re-prompted.

## Slow first connection / timeout

A stdio server's very first run can be slow while its package manager (`npx`, `uvx`) downloads it -
`✘ Failed to connect` on the first check right after adding is often just that; wait a few seconds and
re-run `claude mcp list`. If it's a genuinely slow-starting server, raise the timeout:
```bash
MCP_TIMEOUT=60000 claude   # milliseconds; default is 30000 (30s)
```
