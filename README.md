# Agentic Development Kit

A Claude Code plugin for AI-assisted software development: a library of skills used within a single
agent, a tiered multi-agent pipeline, MCP configuration so Claude Code can connect beyond the codebase
(database, dashboard, ticket tracker), and quality-check hooks that check the workflow rules a model
cannot be trusted to self-police (advisory by default, enforcing when configured to). Usable for any
project/stack — the core (workflow, process) has no dependency on any specific technology; tech-specific
details live in their own modules.

## Install

This repo is itself a Claude Code plugin (`.claude-plugin/plugin.json`) and its own marketplace
(`.claude-plugin/marketplace.json`), so it installs the same way any plugin does — no copying files
into `.claude/`:

```
/plugin marketplace add DianaSensei/agentic-development-kit
/plugin install agentic-development-kit@agentic-development-kit
```

(or the `claude plugin marketplace add` / `claude plugin install` CLI equivalents, run from outside
Claude Code). This single install also pulls in [`taste-skill`](https://github.com/Leonxlnx/taste-skill)
(design-taste skills: `brandkit`, `gpt-taste`, `minimalist-ui`, and others) — declared as a
[plugin dependency](#bundled-plugins) below, so it's installed and enabled automatically alongside this
plugin, with no separate step. Verified end to end: `claude plugin install agentic-development-kit@...`
reports `(+ 1 dependency: taste-skill)`, and both show zero errors in `claude plugin list --json`.

To try changes locally before publishing them, run Claude Code against the checked-out repo directly
instead of installing it:

```
claude --plugin-dir /path/to/agentic-development-kit
```

`--plugin-dir` does not resolve marketplace dependencies, so `taste-skill` won't come along this way —
add a second `--plugin-dir` pointing at a checkout of it if you need both while developing locally (see
[Test a plugin and its dependency locally](https://code.claude.com/docs/en/plugin-dependencies#test-a-plugin-and-its-dependency-locally)).

Once enabled, `skills/` and `agents/` work exactly as described below in every project the plugin is
active in — nothing about them is specific to this repo. See
[`hooks/README.md`](./hooks/README.md) if a hook needs troubleshooting, and
`.claude-plugin/plugin.json` for the manifest itself.

### Bundled plugins

`agentic-development-kit`'s own skills/agents/hooks are only part of what one install can bring in.
`.claude-plugin/plugin.json` declares a `dependencies` array — every plugin listed there installs and
enables automatically alongside this one, and stays enabled as long as this plugin is (Claude Code
refuses to disable a dependency that another enabled plugin still needs). Currently:

| Dependency | Marketplace | What it adds |
|---|---|---|
| [`taste-skill`](https://github.com/Leonxlnx/taste-skill) | `taste-skill` (self-hosted by that repo) | Frontend design-taste skills (`brandkit`, `gpt-taste`, `minimalist-ui`, `stitch-design-taste`, and others) |

To bundle another plugin (another skill/agent/MCP-server plugin — the same `dependencies` mechanism
covers all three, since an MCP server just ships as part of some plugin's `.mcp.json`):

1. Confirm the target is an actual Claude Code plugin (has its own `.claude-plugin/plugin.json`) — a
   plain skill/agent repo with no manifest has to be packaged as a plugin first, either upstream or by
   listing it as a second entry in *this* repo's own `marketplace.json`.
2. If it lives in a different marketplace than this one (the common case — most plugins are), add that
   marketplace's `name` (from *its* `marketplace.json`, not the repo name) to
   `allowCrossMarketplaceDependenciesOn` in this repo's `.claude-plugin/marketplace.json`. Skipped this
   step → install fails with a `cross-marketplace` error naming exactly this field.
3. Add `{ "name": "<plugin-name>", "marketplace": "<marketplace-name>" }` to `dependencies` in
   `.claude-plugin/plugin.json` (a bare version constraint like `"version": "^1.0"` is optional).
4. A user who has never added that dependency's marketplace before needs to run
   `claude plugin marketplace add <owner>/<repo>` once, manually — a `dependencies` entry names an
   already-known marketplace, it does not discover/add an unknown one on its own. After that one-time
   step, install/update/`/reload-plugins` resolve it automatically from then on.

For a role-specific set with no skills/hooks of its own, a `plugin.json` containing only `name` +
`dependencies` works too — installing it pulls in every dependency as one bundle (see
[Bundle plugins for a team](https://code.claude.com/docs/en/plugin-dependencies#bundle-plugins-for-a-team)).

## Directory structure

Every directory below sits at the plugin root — this is where Claude Code's plugin loader expects
`skills/`, `agents/`, and `hooks/` to live (see [Create plugins](https://code.claude.com/docs/en/plugins)).

| Directory | What it is | See also |
|---|---|---|
| [`skills/`](./skills/README.md) | A library of 30 Claude Code Skills — workflow (feature/bug-fix/refactor), technical knowledge by language/infrastructure, quality/security, MCP integration. Claude Code automatically recognizes the right skill via its `description`, no manual invocation needed (except a few skills marked manual-only); each is also reachable explicitly as `/agentic-development-kit:<skill-name>`. | [`skills/README.md`](./skills/README.md) |
| [`agents/`](./agents-guide.md) | A tiered Task subagent pipeline (Tier 1 clarifies requirements + proposes solutions, Tier 2 implements specialized work), communicating via a fixed JSON contract. | [`agents-guide.md`](./agents-guide.md) |
| [`hooks/`](./hooks/README.md) | Quality-check hooks covering the parts of the skill workflow a model cannot be trusted to self-police: that the owning `SKILL.md` was read before code was edited, and that `code-review-skill` ran on the diff before the change was reported done. They warn by default and can be switched to block per gate. | [`hooks/README.md`](./hooks/README.md) |
| [`mcp/`](./mcp/README.md) | MCP server configuration so Claude Code can connect to external systems: database (PostgreSQL/MySQL/TiDB/Redis/MongoDB, read-only), Grafana, self-hosted Jira/Confluence. This one is documentation to follow manually, not something the plugin wires up automatically. | [`mcp/README.md`](./mcp/README.md) |

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

## Using it once installed

1. **Skill**: nothing to invoke manually — describe your request, `workflow-router` recognizes it and
   routes automatically. See the full list at [`skills/README.md`](./skills/README.md).
2. **Agent**: invoke directly via the Task tool, starting from `business-analyst` for a new request. See
   [`agents-guide.md`](./agents-guide.md) for the order and input/output schema of each agent.
3. **Hook**: nothing to do — `hooks/hooks.json` and the three workflow skills' frontmatter register them
   automatically wherever the plugin is enabled. See [`hooks/README.md`](./hooks/README.md) for what
   each gate checks, how to switch a gate from warn to block, and how to trim `skill_map` to your stack
   by dropping an override file in the target project.
4. **MCP**: if you need Claude Code to access database/Grafana/Jira-Confluence, follow
   [`mcp/README.md`](./mcp/README.md) — or just ask directly, e.g. "set up Grafana MCP for me", and
   Claude Code will read the corresponding README and follow it (or use the `mcp-setup` skill for an MCP
   server not already covered here).

## General conventions

- The orchestration/workflow part (both in `skills/` and `agents/`) is designed to be independent of any
  specific language/framework — all tech-specific detail lives in specialized modules (technical skills
  or Tier-2 agents), auto-detected from real evidence (dependencies, configuration, existing code), never
  assumed in advance. In practice the technical skills currently cover Java/Spring, Rust, and Tauri+React
  most deeply — a request in an uncovered stack still gets the workflow's structure (checkpoints,
  fix-attempt limits, reporting), just without a matching technical skill to read at Step 3.1.
- The rules the workflows state as mandatory are backed by hooks wherever they are mechanically
  checkable (skill read before edit, review before done); judgement-based checks stay with
  `code-review-skill`. Hooks warn by default and are switched to blocking per gate, and every one of
  them fails open, so none can become the reason work cannot proceed.
- Changes affecting external behavior (new features, bug fixes) always have a checkpoint waiting for user
  confirmation before execution; purely structural refactors must preserve 100% of observable behavior.
- Secret/credential files are never committed to the repo — see each `README.md` under `mcp/*/` for how
  to use `.env` (not tracked by git).
