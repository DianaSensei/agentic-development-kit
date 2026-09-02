# Agentic Development Kit

A Claude Code plugin for AI-assisted software development: a library of skills used within a single
agent, a tiered multi-agent pipeline, MCP configuration so Claude Code can connect beyond the codebase
(database, dashboard, ticket tracker), and quality-check hooks that check the workflow rules a model
cannot be trusted to self-police (advisory by default, enforcing when configured to). Usable for any
project/stack - the core (workflow, process) has no dependency on any specific technology; tech-specific
details live in their own modules.

## Install

This repo is itself a Claude Code plugin (`.claude-plugin/plugin.json`) and its own marketplace
(`.claude-plugin/marketplace.json`), so it installs the same way any plugin does - no copying files
into `.claude/`:

```
/plugin marketplace add DianaSensei/agentic-development-kit
/plugin install agentic-development-kit@agentic-development-kit
```

(or the `claude plugin marketplace add` / `claude plugin install` CLI equivalents, run from outside
Claude Code).

To try changes locally before publishing them, run Claude Code against the checked-out repo directly
instead of installing it:

```
claude --plugin-dir /path/to/agentic-development-kit
```

Once enabled, `skills/` and `agents/` work exactly as described below in every project the plugin is
active in - nothing about them is specific to this repo. See
[`hooks/README.md`](./hooks/README.md) if a hook needs troubleshooting, and
`.claude-plugin/plugin.json` for the manifest itself.

### Companion plugins (not a manifest dependency, and deliberately so)

[`taste-skill`](https://github.com/Leonxlnx/taste-skill) (design-taste skills: `brandkit`, `gpt-taste`,
`minimalist-ui`, and others) pairs well with this plugin but is **not** declared as a `dependencies`
entry in `.claude-plugin/plugin.json`, even though Claude Code supports that mechanism. This was tried
and reverted after testing it for real: Claude Code resolves a plugin's `dependencies` at load time, and
if that dependency's marketplace was never added (the common first-run case - a `dependencies` entry
only *names* an already-known marketplace, it never adds an unknown one itself), the *entire declaring
plugin* fails to load - not just the missing piece. Verified two ways: `--plugin-dir` silently loaded
zero skills/agents with `taste-skill` undeclared as a marketplace, and even `claude plugin install`
(which reports `√ Successfully installed` with no visible warning) left every one of this plugin's own
skills uninvokable, confirmed by trying to actually call one rather than trusting the success message or
the `errors` field in `claude plugin list --json`. That is a single point of failure this plugin's core
functionality must never depend on.

Install both with one copy-paste instead - no manifest coupling, so a problem with one marketplace can
never take the other down:

```
claude plugin marketplace add Leonxlnx/taste-skill
claude plugin marketplace add DianaSensei/agentic-development-kit
claude plugin install taste-skill@taste-skill
claude plugin install agentic-development-kit@agentic-development-kit
```

To bundle another companion plugin the same way, add its `marketplace add` + `install` pair to that
same block rather than reaching for `dependencies` - unless you have specifically verified, the way
described above, that its marketplace will already be present for every user before they ever install
this plugin.

Where a companion skill is genuinely useful mid-task, a `SKILL.md` here may name it as an *if present*
instruction that does nothing when the skill is absent - `ui-ux-design-skill` does this for the
design-taste family, since it owns usability and accessibility but deliberately not visual direction.
That is the only form of coupling allowed: no `dependencies` entry, and no step a skill cannot finish
on its own.

### The third install channel, and the one trap in it

Skills reach a session through three independent channels, and only the first is this repository:

| Channel | Installed by | Updates when | Lives in |
|---|---|---|---|
| Plugin skill | `/plugin install`, or `--plugin-dir` | the plugin updates | `skills/` in this repo |
| Personal skill synced from claude.ai | uploading a file at Settings → Capabilities → Skills | **you upload it again by hand** | `~/.claude/skills/synced/<account>/` |
| Project skill | committed to the project being worked on | that project's git | `.claude/skills/` of that project |

The trap: uploading a skill *from this repo* to claude.ai as a personal skill. Two copies then answer
to the same name, you cannot tell which one a session loaded, and the synced copy is a frozen snapshot
that never follows this repo again. It also arrives flattened - the web upload keeps `SKILL.md` and
drops `references/`, so a skill whose method depends on progressive disclosure ends up pointing at
reference files that are not there.

This is not hypothetical: `architecture-designer` was uploaded that way, froze at the 2026-07-18 state,
and so never received the deployment-topology step added on 2026-08-23 - while still instructing the
agent to open eleven `references/*.md` files its copy did not contain.

So: install skills from this repo **only** as a plugin. Personal-skill sync is the right channel for
skills that have no other home, not for anything already published here.

### Companion tools that aren't Claude Code plugins at all

[`lavish-axi`](https://github.com/kunchenguid/lavish-axi) (`lavish` - a CLI/editor for reviewing and
iterating on HTML artifacts with an agent) pairs well with this kit but, unlike `taste-skill` above,
isn't a Claude Code plugin to begin with: its `plugin.json` follows the generic
[agent-plugins.org](https://agent-plugins.org) schema, not `.claude-plugin/plugin.json`, and it has no
marketplace - `claude plugin marketplace add`/`install` cannot see it at all. There is no automatic
step here: an install hook running this on every session would reach outside this plugin's own scope
and onto the user's machine without asking, which this kit's hooks deliberately never do (see
[`hooks/README.md`](./hooks/README.md) → Operating rules). Install it yourself when you want it - its
own README recommends the skill-only method, which needs no global install at all (the skill teaches
the agent to run `npx -y lavish-axi` on demand):

```
npx skills add kunchenguid/lavish-axi --skill lavish
```

For the deeper hook/plugin integration instead (persistent, requires a global install):

```
npm install -g lavish-axi
lavish-axi setup plugin
```

## Directory structure

Every directory below sits at the plugin root - this is where Claude Code's plugin loader expects
`skills/`, `agents/`, and `hooks/` to live (see [Create plugins](https://code.claude.com/docs/en/plugins)).

| Directory | What it is | See also |
|---|---|---|
| [`skills/`](./skills/README.md) | A library of 30 Claude Code Skills - workflow (feature/bug-fix/refactor), technical knowledge by language/infrastructure, quality/security, MCP integration. Claude Code automatically recognizes the right skill via its `description`, no manual invocation needed (except a few skills marked manual-only); each is also reachable explicitly as `/agentic-development-kit:<skill-name>`. | [`skills/README.md`](./skills/README.md) |
| [`agents/`](./agents-guide.md) | A tiered Task subagent pipeline (Tier 1 clarifies requirements + proposes solutions, Tier 2 implements specialized work), communicating via a fixed JSON contract. | [`agents-guide.md`](./agents-guide.md) |
| [`hooks/`](./hooks/README.md) | Quality-check hooks covering the parts of the skill workflow a model cannot be trusted to self-police: that the owning `SKILL.md` was read before code was edited, and that `code-review-skill` ran on the diff before the change was reported done. They warn by default and can be switched to block per gate. | [`hooks/README.md`](./hooks/README.md) |
| [`mcp/`](./mcp/README.md) | MCP server configuration so Claude Code can connect to external systems: database (PostgreSQL/MySQL/TiDB/Redis/MongoDB, read-only), Grafana, self-hosted Jira/Confluence. This one is documentation to follow manually, not something the plugin wires up automatically. | [`mcp/README.md`](./mcp/README.md) |

## How do `skills/` and `agents/` relate?

Mostly two different models for structured feature development, but `feature-development` now bridges
them for its two highest-stakes steps:

- **`skills/`** - 1 agent (the current Claude Code session) reads the appropriate skill itself and does
  the work in the same session, sequentially. It starts from `workflow-router` (a skill), classifies the
  request, then hands off to `feature-development`/`bug-fix`/`refactor`, and these skills read further
  technical skills (`java-spring-skill`, `database-skill`...) as needed.
- **`agents/`** - separate Task subagents, each with a fixed role and a JSON contract so the next step
  can use its output directly. `feature-development` launches `business-analyst` (Step 1) and
  `solution-architect` (Step 2) as subagents specifically *because* they carry no `Edit`/`Write` tool -
  requirements analysis and solution design happen where code is architecturally impossible to touch,
  which a hook checking transcripts after the fact can't guarantee the way a missing tool can. Its
  Step 3 may optionally dispatch a Tier-2 specialist (`java-ecosystem-engineer`, etc.) for a task
  `solution-architect` assigned to one that actually exists; everything else stays a direct
  technical-skill implementation, unchanged. `bug-fix` and `refactor` don't use this pipeline (their
  checkpoints are simpler, single-direction decisions) - see [`agents-guide.md`](./agents-guide.md).

Which to reach for depends on the situation - a skill invoked directly (not through
`feature-development`) is suited to a single continuous flow, easy to follow within one session;
`agents/` is suited when a step needs a hard guarantee the main thread's tool access can't provide, or
when independent Tier-2 work can run in parallel.

## Using it once installed

1. **Skill**: nothing to invoke manually - describe your request, `workflow-router` recognizes it and
   routes automatically. See the full list at [`skills/README.md`](./skills/README.md).
2. **Agent**: invoke directly via the Task tool, starting from `business-analyst` for a new request. See
   [`agents-guide.md`](./agents-guide.md) for the order and input/output schema of each agent.
3. **Hook**: nothing to do - `hooks/hooks.json` and the three workflow skills' frontmatter register them
   automatically wherever the plugin is enabled. See [`hooks/README.md`](./hooks/README.md) for what
   each gate checks, how to switch a gate from warn to block, and how to trim `skill_map` to your stack
   by dropping an override file in the target project.
4. **MCP**: if you need Claude Code to access database/Grafana/Jira-Confluence, follow
   [`mcp/README.md`](./mcp/README.md) - or just ask directly, e.g. "set up Grafana MCP for me", and
   Claude Code will read the corresponding README and follow it (or use the `mcp-setup` skill for an MCP
   server not already covered here).

## General conventions

- The orchestration/workflow part (both in `skills/` and `agents/`) is designed to be independent of any
  specific language/framework - all tech-specific detail lives in specialized modules (technical skills
  or Tier-2 agents), auto-detected from real evidence (dependencies, configuration, existing code), never
  assumed in advance. In practice the technical skills currently cover Java/Spring, Rust, and Tauri+React
  most deeply - a request in an uncovered stack still gets the workflow's structure (checkpoints,
  fix-attempt limits, reporting), just without a matching technical skill to read at Step 3.1.
- The rules the workflows state as mandatory are backed by hooks wherever they are mechanically
  checkable (skill read before edit, review before done); judgement-based checks stay with
  `code-review-skill`. Hooks warn by default and are switched to blocking per gate, and every one of
  them fails open, so none can become the reason work cannot proceed.
- Changes affecting external behavior (new features, bug fixes) always have a checkpoint waiting for user
  confirmation before execution; purely structural refactors must preserve 100% of observable behavior.
- Secret/credential files are never committed to the repo - see each `README.md` under `mcp/*/` for how
  to use `.env` (not tracked by git).
