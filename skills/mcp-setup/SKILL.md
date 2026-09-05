---
name: mcp-setup
description: End-to-end setup for connecting a third-party MCP server to Claude Code - given a GitHub link, package name, or hosted URL, determines the transport and auth it needs, registers it via `claude mcp add` at the right scope, handles secrets safely, and verifies the connection actually works. Use when asked to install, connect, add, or set up a specific MCP server, or to diagnose one that was added but shows as failed or not connected. Not for authoring a new MCP server (`mcp-developer`), and not for this plugin's own bundled toolbox database MCP (`toolbox-connections`).
argument-hint: "[MCP server GitHub link, package name, or hosted URL]"
metadata:
  domain: platform
  triggers: install MCP server, connect MCP server, set up MCP, MCP transport, stdio, Streamable HTTP, MCP scope, MCP secrets, MCP connection failed
  role: specialist
  scope: implementation
  output-format: code
  related-skills: mcp-developer, toolbox-connections, security-audit
---

# MCP Setup

Single point of entry for connecting one third-party MCP server to Claude Code, start to finish:
identify what the server needs, register it correctly, handle any secrets safely, and confirm it's
actually connected - not just that a config entry was written.

Input: `$ARGUMENTS` - a GitHub link, package name, or hosted MCP URL for the server to set up.

## Step 1 - Identify Target & Scope

If `$ARGUMENTS` doesn't clearly give a link/package/URL, ask for it before proceeding - don't guess
which server is meant.

Ask which installation scope this server should use (`AskUserQuestion`, structured choice - see
`references/cli-reference.md` → "Scopes" for the full trade-off table):

- **Local** (default) - private to this user, this project only. Use for personal/experimental servers
  or anything with credentials that shouldn't be shared.
- **Project** - shared with the whole team via `.mcp.json`, committed to git. Use when the team should
  all get this server automatically when they clone the repo.
- **User** - private to this user, active in every project. Use for a server this user wants everywhere
  (e.g. a personal productivity tool), not tied to this specific repo.

If the user has already stated intent ("share this with the team") don't re-ask - just confirm the
inferred scope in one line before proceeding.

## Step 2 - Discover Requirements

Fetch the server's own documentation (README, `docs/`, or its listing page) and determine, in order:

1. **Transport**: local process (`stdio`) or hosted endpoint (`http`, or the deprecated `sse` only if
   `http` truly isn't offered). See `references/cli-reference.md` → "Transports" - most server READMEs
   have an explicit "Claude Code" or "MCP client configuration" section with this spelled out; use that
   over guessing from the repo's language/package manager.
2. **Exact run command** (stdio) or **endpoint URL** (http/sse) - copy this precisely; don't
   approximate a package name or flag.
3. **Runtime prerequisite** for stdio servers (Node.js/`npx`, Python/`uvx`, Docker, a specific binary) -
   check it's actually installed (e.g. `node --version`, `uvx --version`) before registering; don't
   assume it's present.
4. **Authentication**: none, a static token/API key (passed via `--header` or `--env`), or OAuth
   (browser sign-in after registration via `/mcp`). See `references/cli-reference.md` → "Authentication
   Patterns" for exactly how each is registered.
5. **Every required environment variable/secret** the server needs to function - list them explicitly;
   don't register the server and let the user discover a missing one from a cryptic empty tool list
   later (though Step 5 covers recovering from that if it happens anyway).

## Step 3 - Handle Secrets Safely

**Critical distinction by scope** - see `references/secrets-handling.md` for the full policy and
worked examples:

- **Local or User scope** (`~/.claude.json`, never committed to git): fine to pass secret values
  directly with `--env KEY=value` or `--header "Authorization: Bearer <token>"` at add time.
- **Project scope** (`.mcp.json`, committed to git): NEVER write a literal secret value into the file.
  Use `${VAR}` (or `${VAR:-default}` for non-secret, machine-specific values) so the file itself has no
  secret in it - each teammate sets the actual value in their own shell environment before running
  `claude`. State clearly, in the Step 6 summary, which environment variable name(s) each teammate needs
  to set.

Ask the user for each required secret value as a normal message, not `AskUserQuestion` (that tool is
for enumerable choices, not free-text secrets). Never echo a secret value back in your own output -
not in a confirmation message, not in the final report, not in anything written to a file.

## Step 4 - Register the Server

Run `claude mcp add` with the transport/scope/env/header flags determined in Steps 1–3 (see
`references/cli-reference.md` for exact syntax, including the `--` separator required before a stdio
server's command). For Project scope, editing `.mcp.json` directly is equally valid (it's the file
that gets committed either way) - use whichever is clearer for the specific case.

If a server with the same name already exists, confirm with the user before overwriting it - don't
silently replace a working configuration.

## Step 5 - Verify

`claude mcp add` printing "Added" only means the entry was saved - it does NOT mean the server
connects. Always verify:

1. Run `claude mcp list` and check the status next to the server's name.
2. `✔ Connected` - done, move to Step 6.
3. `! Needs authentication` - walk the user through `/mcp` → select the server → `Authenticate` (OAuth
   browser sign-in).
4. `✘ Failed to connect` / `✘ Connection error` / connected-but-empty-tool-list - work through
   `references/troubleshooting.md`'s diagnostic tree (curl-based checks for HTTP servers, direct-run
   checks for stdio servers, the common "missing env var" cause of an empty tool list) rather than
   guessing at the fix.

Don't report success until status shows `✔ Connected`.

## Step 6 - Report & Document

Summarize: server name, scope, transport, connection status, and - if Project-scoped - the exact
environment variable name(s) (never values) each teammate must set locally before the server will
connect for them. Remind the user to commit `.mcp.json` if Project-scoped, and to note the required
env var names somewhere teammates will see them (README, `CLAUDE.md`, or wherever the project already
documents required local setup).

## Constraints

### MUST DO

- Get the exact transport and run command/URL from the server's own documentation before registering -
  never guess syntax from the repo's language or package manager alone.
- Use `--` to separate Claude Code's own flags from a stdio server's command and arguments.
- Default to Local scope unless the user has stated this should be shared with the team.
- Use `${VAR}` expansion for any secret going into a Project-scoped (git-committed) entry - never a
  literal value.
- Verify connection status with `claude mcp list` after every add - never declare success on the
  "Added" confirmation alone.
- Confirm required runtime prerequisites (Node/npx, Python/uvx, Docker) are installed before
  registering a stdio server that depends on them.

### MUST NOT DO

- Write a literal secret/token value into a Project-scoped `.mcp.json` entry.
- Echo a secret value back anywhere in output, reports, or commits.
- Reach for the deprecated SSE transport when the server also offers HTTP.
- Skip the verification step or treat a "Failed to connect" status as something to just note and move
  past.
- Overwrite an existing server entry with the same name without confirming with the user first.

## Boundaries

- This skill connects an EXISTING third-party MCP server to Claude Code. Authoring a new MCP server -
  writing its tool/resource/prompt handlers, choosing its SDK - is `mcp-developer`'s job.
- This skill doesn't audit the third-party server's own security posture (what it does with data once
  granted access, whether its maintainer is trustworthy) - that judgment belongs to the user, and a
  deeper look coordinates with `security-audit` if the server will get broad tool permissions.
- Runs on a request to set up, connect, or fix one *specific* server. A general question about what MCP
  is, or which servers exist, doesn't need this whole workflow - answer it directly.
  `references/troubleshooting.md`'s diagnostic tree is fine to use ad hoc without running the rest.
