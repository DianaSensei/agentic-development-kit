# Agentic Development Kit

A Claude Code plugin for AI-assisted software development: a library of 30 skills, a tiered subagent
pipeline, quality-check hooks, and MCP configs for reaching beyond the codebase.

The workflow core is stack-agnostic. Anything technology-specific lives in its own skill, so a project
in an uncovered stack still gets the structure (checkpoints, fix-attempt limits, reporting).

## Install

```
/plugin marketplace add DianaSensei/agentic-development-kit
/plugin install agentic-development-kit@agentic-development-kit
```

This repo is both the plugin and its own marketplace, so nothing gets copied into `.claude/`.
To test local changes instead of installing: `claude --plugin-dir /path/to/agentic-development-kit`.

## What's in it

Each directory sits at the plugin root, where Claude Code's
[plugin loader](https://code.claude.com/docs/en/plugins) expects it.

| Directory | What it is |
|---|---|
| [`skills/`](./skills/README.md) | 30 skills. Claude Code picks the right one from its `description`, so there is nothing to invoke by hand (a few are manual-only). Also reachable as `/agentic-development-kit:<skill-name>`. |
| [`agents/`](./agents-guide.md) | Tiered Task subagents. Tier 1 clarifies requirements and proposes solutions, Tier 2 implements. They pass a fixed JSON contract between steps. |
| [`hooks/`](./hooks/README.md) | Gates for the rules a model cannot self-police: the owning `SKILL.md` was read before an edit, and `code-review-skill` ran before "done". Warn by default, blocking per gate. |
| [`mcp/`](./mcp/README.md) | Toolbox config for databases - PostgreSQL, MySQL, TiDB, Redis, MongoDB, or any other type Toolbox supports. Ships with no pre-built connections; add exactly what you have. Declared in the root `.mcp.json`, connected automatically once a connection exists - no repo clone needed. |

## Using it

- **Skills** run themselves. Describe the request; `workflow-router` classifies it and hands off to
  `feature-development` / `bug-fix` / `refactor`.
- **Agents** are invoked through the Task tool, starting at `business-analyst`. See
  [`agents-guide.md`](./agents-guide.md).
- **Hooks** need no setup. They register wherever the plugin is enabled. To tune them for a project,
  drop a `.claude/quality-check.config.json` in that project's root.
- **MCP** auto-connects once you've added a connection: the plugin's root `.mcp.json` declares `toolbox`,
  so Claude Code starts and connects it whenever the plugin is enabled - but it ships with none pre-built,
  so `✘ Failed to connect` right after installing is expected until you add one. Install the `toolbox`
  binary, then follow [`mcp/README.md`](./mcp/README.md) or just ask ("add a toolbox connection for my
  orders Postgres database") - the `toolbox-connections` skill handles the rest.

## skills/ vs agents/

Two models for the same work. A skill runs in the current session, sequentially, reading further
skills as it goes. An agent is a separate subagent with a fixed role.

`feature-development` uses both: Steps 1 and 2 go to `business-analyst` and `solution-architect` as
subagents precisely because those carry no `Edit`/`Write` tool, so requirements and design happen where
code is impossible to touch. A missing tool guarantees that; a hook reading transcripts afterwards
cannot. Step 3 may dispatch a Tier-2 specialist when one exists for the task. `bug-fix` and `refactor`
stay in-session, since their checkpoints are simpler.

## Companion tools

None of these ship with this plugin, and none is a declared dependency. Install what you want:

```
claude plugin marketplace add Leonxlnx/taste-skill
claude plugin install taste-skill@taste-skill          # design-taste skills

npx skills add kunchenguid/lavish-axi --skill lavish   # lavish: review HTML artifacts with an agent
```

[`taste-skill`](https://github.com/Leonxlnx/taste-skill) is a normal plugin.
[`lavish-axi`](https://github.com/kunchenguid/lavish-axi) is not: it follows the generic
[agent-plugins.org](https://agent-plugins.org) schema and has no marketplace, so
`claude plugin install` cannot see it. The command above installs it as a skill only, with no global
install; for the persistent hook integration use `npm install -g lavish-axi && lavish-axi setup plugin`.

Nothing here installs automatically. A hook that reached onto your machine uninvited is exactly what
this kit's hooks never do (see [`hooks/README.md`](./hooks/README.md)). `ui-ux-design-skill` picks up a
design-taste skill if one is present, and works normally when none is.

<details>
<summary><b>Why no <code>dependencies</code> entry in the manifest</b></summary>

Claude Code supports `dependencies`, and this plugin deliberately does not use it.

Claude Code resolves them at load time. A `dependencies` entry only *names* an already-known
marketplace; it never adds an unknown one. So on the common first run, where the dependency's
marketplace was never added, **the entire declaring plugin fails to load** rather than just the missing
piece.

Verified twice: `--plugin-dir` silently loaded zero skills and agents, and `claude plugin install`
printed `√ Successfully installed` while leaving every skill here uninvokable. Neither the success
message nor the `errors` field in `claude plugin list --json` showed anything wrong; only actually
calling a skill revealed it.

To add another companion, extend the copy-paste block above instead.
</details>

<details>
<summary><b>Do not upload these skills to claude.ai</b></summary>

Skills reach a session through three channels:

| Channel | Updates when |
|---|---|
| Plugin skill (this repo) | the plugin updates |
| Personal skill synced from claude.ai | you upload it again by hand |
| Project skill in `.claude/skills/` | that project's git |

Uploading a skill *from this repo* to claude.ai forks it under the same name. Two copies then answer to
it, you cannot tell which one loaded, and the synced copy never follows this repo again. The web upload
also flattens it, keeping `SKILL.md` and dropping `references/`.

This happened to `architecture-designer`: frozen at its 2026-07-18 state, missing the
deployment-topology step added on 2026-08-23, still telling the agent to open eleven `references/*.md`
files its copy did not have. The upload has since been removed. Nothing warns you when this occurs,
which is why it is written down here.
</details>

## Conventions

- Tech-specific detail is detected from real evidence (dependencies, config, existing code), never
  assumed. Coverage is deepest for Java/Spring, Rust, and Tauri+React.
- Mechanically checkable rules are enforced by hooks; judgement-based ones stay with
  `code-review-skill`. Every hook fails open, so none can block work.
- Changes to external behavior wait at a checkpoint for user confirmation. Refactors must preserve
  observable behavior exactly.
- Secrets never get committed. See each `mcp/*/README.md` for `.env` handling.
