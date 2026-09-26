# .claude/settings.json

The project's shared Claude Code settings: committed, so every teammate and every cloud session gets
the same guardrails and the same kit. Strict JSON - a comment or a trailing comma makes Claude Code
report a settings error at the next start.

## What goes in

```json
{
  "$schema": "https://json.schemastore.org/claude-code-settings.json",
  "permissions": {
    "allow": [
      "Bash(<test command> *)",
      "Bash(<lint command> *)"
    ],
    "ask": [
      "Bash(git push *)"
    ],
    "deny": [
      "Read(.env)",
      "Read(.env.*)",
      "Read(/secrets/**)",
      "Edit(<lockfile name>)"
    ]
  },
  "extraKnownMarketplaces": {
    "agentic-development-kit": {
      "source": {
        "source": "github",
        "repo": "DianaSensei/agentic-development-kit"
      }
    }
  },
  "enabledPlugins": {
    "adk-sdlc@agentic-development-kit": true,
    "<stack plugin>@agentic-development-kit": true
  }
}
```

Keep only the rules that match this repo:

| Rule | Include when | Why |
|---|---|---|
| `allow` for the test and lint commands, written `Bash(<command> *)` with a space before `*` | `CLAUDE.md` names them | The feedback loop runs them constantly; a prompt on each run teaches people to click through prompts. The space matters: `Bash(make test *)` matches `make test` and `make test -k x`, while `Bash(make test*)` also matches `make testdata-wipe` |
| `ask` for `git push` | always | Publishing leaves the session's control; a person confirms it |
| `deny` `Read(.env)`, `Read(.env.*)` | a `.env*` file exists, or `.gitignore` lists one | Secrets never enter the model's context. Always write both: a `.env` created later is covered too |
| `deny` `Read(/secrets/**)`, and each `*.pem` / `*.key` path found, anchored the same way | that path exists | Same |
| `deny` `Edit(<lockfile name>)` for each lockfile present | a lockfile exists | Lockfiles change only through the package manager; a hand edit desyncs them from the manifest |
| a stack plugin in `enabledPlugins`, one entry per match: `adk-backend` for a JVM build file (`pom.xml`, `build.gradle*`), database migrations, a Kafka/RabbitMQ/Redis/Elasticsearch client or an OpenAPI/AsyncAPI file; `adk-desktop` for `src-tauri/`, `Cargo.toml` or a React front end; `adk-architecture` always | that evidence exists | The core reads a stack's skills only when its plugin is installed; enabling the matching ones here gives every teammate the technical skills the workflows and gates expect for this repository, and nothing for stacks it does not use |
| `extraKnownMarketplaces` + `enabledPlugins` | always | Every teammate is offered this kit, with its gates and workflows, when they open the repo. It is also what opts the repo in: the kit's session reminders appear only where a project enables it |

**Path anchors decide what a rule covers.** A bare name follows gitignore rules and matches at any depth:
`Read(.env)` covers the root `.env` and every package's `.env` in a monorepo. `/path` is anchored to
the project root: `Read(/secrets/**)`. Never use `./path` in a committed file - it is relative to the
directory the session started in, so a session opened in a subdirectory is not covered. A `Read` deny
also blocks the Edit and Write tools on that path; `NotebookEdit` is not covered.

Notes for the report:
- `deny` and `ask` apply immediately. `allow` rules and the marketplace entry take effect only after each
  person trusts the folder in Claude Code.
- A `Read` deny stops Claude Code's file tools and commands that name the file; it does not stop a
  `grep -r` across the directory. Turning on the sandbox closes that gap, which is a team decision:
  mention it, don't enable it.
- `enabledPlugins` enables the kit, but a plugin from a GitHub marketplace still needs each person to
  install it once (`/plugin install adk-sdlc@agentic-development-kit`, and each stack
  plugin enabled here the same way).
- The marketplace entry points at GitHub whatever host the project itself uses. A team that mirrors the
  kit on its own git server (a GitLab project, say) registers the mirror instead:
  `"source": {"source": "git", "url": "https://gitlab.example.com/tools/agentic-development-kit.git"}`.

## An existing settings.json

Merge key by key, never replace the file:
- Arrays (`allow`, `ask`, `deny`): append the rules that are missing; keep every existing rule, in
  order. A new rule that contradicts an existing one (a `deny` for something they `allow`) is reported,
  not added.
- Objects (`extraKnownMarketplaces`, `enabledPlugins`): add each of the kit's keys that is absent. If a kit key is
  present and set to `false`, someone turned it off - leave it and say so. A key for the core's old
  name, `agentic-development-kit@agentic-development-kit` (before 0.7), is replaced by
  `adk-sdlc@agentic-development-kit` with the same value; say so in the report.
- Every other key stays exactly as it is.

Then parse the result (`jq empty .claude/settings.json`). A settings file that fails to parse breaks
Claude Code for the whole team, so a parse failure is fixed before the report, never left in it.
