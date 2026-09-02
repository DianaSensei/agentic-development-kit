# Secrets Handling Policy

## The Core Rule

Whether a secret can be written as a literal value depends entirely on where the config entry lives:

| Scope | File | Committed to git? | Literal secret OK? |
|-------|------|---------------------|----------------------|
| Local | `~/.claude.json` | No (home directory, per-machine) | Yes |
| User | `~/.claude.json` | No (home directory, per-machine) | Yes |
| Project | `.mcp.json` | **Yes** | **No - use `${VAR}` expansion** |

A Project-scoped server is exactly the case where getting this wrong leaks a real credential into git
history - which isn't fixed by deleting it in a later commit, since it stays in history unless the
repo's history itself is rewritten. Treat this as a hard rule, not a judgment call.

## Local/User Scope: Direct Values Are Fine

```bash
claude mcp add --env API_KEY=sk-abc123 --transport stdio my-server -- npx -y some-mcp-server
```

This is safe because `~/.claude.json` never leaves the user's machine via version control.

## Project Scope: Use `${VAR}` Expansion

Never do this in a file that gets committed:
```json
{ "mcpServers": { "my-server": { "env": { "API_KEY": "sk-abc123" } } } }
```

Do this instead - the committed file has no secret in it:
```json
{ "mcpServers": { "my-server": { "env": { "API_KEY": "${MY_SERVER_API_KEY}" } } } }
```

Each teammate then sets `MY_SERVER_API_KEY` in their own environment before running `claude` - in
their shell profile, or in a project-root `.env` file loaded before launching `claude`, as long as that
`.env` file is itself listed in `.gitignore`. Document the required variable *name* (never the value)
in the project's README or `CLAUDE.md` so teammates know what to set.

For values that are machine-specific but not secret (a local path, a per-developer port), the same
`${VAR:-default}` syntax works and a sensible default avoids needing every teammate to set it:
```json
{ "url": "${API_BASE_URL:-https://api.example.com}/mcp" }
```

## What This Skill Does With a Secret the User Provides

- Ask for the value as a normal message (not `AskUserQuestion` - that tool is for enumerable choices).
- Use it immediately to register the server (Local/User scope) or to tell the user which variable name
  to export locally (Project scope) - never write it into a git-committed file, never restate it back
  in a confirmation message, a report, or a commit message.
- If the user pastes a secret directly into chat, that's already logged in the conversation history
  outside this skill's control - don't compound it by also writing that same value somewhere persistent
  and committed.

## Missing or Wrong Secret Symptoms

- Config loads but `claude mcp list` shows a missing-variable warning → the referenced `${VAR}` isn't
  set in the environment `claude` was started from.
- Server connects but the tool list is empty → very often a missing or wrong API key/token the server
  needed to initialize; see `references/troubleshooting.md`.
- OAuth-based servers don't use this file-based mechanism at all - the token lives in Claude Code's own
  credential storage after the `/mcp` → `Authenticate` browser flow, not in `.mcp.json`.
