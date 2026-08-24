# Agentic Development Kit

A Claude Code configuration kit for AI-assisted software development: 1 skill library used within a
single agent, 1 tiered multi-agent pipeline, MCP configuration so Claude Code can connect beyond
the codebase (database, dashboard, ticket tracker), and hooks that enforce the workflow rules a model
cannot be trusted to self-police. Usable for any project/stack — the core (workflow,
process) has no dependency on any specific technology; tech-specific details live in their own modules.

## Directory structure

| Directory | What it is | See also |
|---|---|---|
| [`skills/`](./skills/README.md) | A library of 30 Claude Code Skills — workflow (feature/bug-fix/refactor), technical knowledge by language/infrastructure, quality/security, MCP integration. Claude Code automatically recognizes the right skill via its `description`, no manual invocation needed (except a few skills marked manual-only). | [`skills/README.md`](./skills/README.md) |
| [`agents/`](./agents/README.md) | A tiered Task subagent pipeline (Tier 1 clarifies requirements + proposes solutions, Tier 2 implements specialized work), communicating via a fixed JSON contract. | [`agents/README.md`](./agents/README.md) |
| [`mcp/`](./mcp/README.md) | MCP server configuration so Claude Code can connect to external systems: database (PostgreSQL/MySQL/TiDB/Redis/MongoDB, read-only), Grafana, self-hosted Jira/Confluence. | [`mcp/README.md`](./mcp/README.md) |
| [`.claude/hooks/`](./.claude/hooks/README.md) | Quality-check hooks that enforce the parts of the skill workflow a model cannot be trusted to self-police: the owning `SKILL.md` gets read before code is edited, and `code-review-skill` runs on the diff before any change is reported done. | [`.claude/hooks/README.md`](./.claude/hooks/README.md) |

## How do `skills/` and `agents/` differ?

These two systems are **independent and currently don't reference each other** — both aim at structured
feature development, but follow 2 different models:

- **`skills/`** — 1 agent (the current Claude Code session) reads the appropriate skill itself and does
  all the work in the same session, sequentially. It starts from `workflow-router` (a skill), classifies
  the request, then hands off to `feature-development`/`bug-fix`/`refactor`, and these skills read further
  technical skills (`java-spring-skill`, `database-skill`...) as needed.
- **`agents/`** — multiple separate Task subagents, each agent with a fixed role (`business-analyst` →
  `solution-architect` → Tier-2 specialist), input/output as JSON with a clear schema, allowing multiple
  independent Tier-2 agents to run in parallel.

Which to use depends on the situation — `skills/` is suited when you want a single continuous flow, easy
to follow within one session; `agents/` is suited when you want clear separation of responsibility per
role and the ability to run multiple independent pieces of work in parallel.

## Quick start

1. **Skill**: no extra setup needed — open Claude Code in this repo, describe your request,
   `workflow-router` will recognize and route it automatically. See the full list at
   [`skills/README.md`](./skills/README.md).
2. **Agent**: invoke directly via the Task tool, starting from `business-analyst` for a new request. See
   [`agents/README.md`](./agents/README.md) for the order and input/output schema of each agent.
3. **Hook**: nothing to do — `.claude/settings.json` and the three workflow skills already register
   them. See [`.claude/hooks/README.md`](./.claude/hooks/README.md) for what each gate checks and how
   to trim `skill_map` to your own stack.
4. **MCP**: if you need Claude Code to access database/Grafana/Jira-Confluence, follow
   [`mcp/README.md`](./mcp/README.md) — or just ask directly, e.g. "set up Grafana MCP for me", and
   Claude Code will read the corresponding README and follow it (or use the `mcp-setup` skill for an MCP
   server not already covered here).

## General conventions

- The orchestration/workflow part (both in `skills/` and `agents/`) is designed to be independent of any
  specific language/framework — all tech-specific detail lives in specialized modules (technical skills
  or Tier-2 agents), auto-detected from real evidence (dependencies, configuration, existing code), never
  assumed in advance.
- The rules the workflows state as mandatory are backed by hooks where they are mechanically
  checkable (skill read before edit, review before done); judgement-based checks stay with
  `code-review-skill`, and every hook fails open so it can never block work it cannot verify.
- Changes affecting external behavior (new features, bug fixes) always have a checkpoint waiting for user
  confirmation before execution; purely structural refactors must preserve 100% of observable behavior.
- Secret/credential files are never committed to the repo — see each `README.md` under `mcp/*/` for how
  to use `.env` (not tracked by git).
