# Agentic Development Kit

Claude Code plugins for AI-assisted software development: an agentic development lifecycle (ADLC) core (workflows with checkpoints,
quality-check hooks, a tiered subagent pipeline, an independent reviewer and a maintain loop for CI)
and three stack plugins with the technology skills it reads. Works with GitHub and GitLab: the few
steps that touch the code host go through its own MCP server.

The workflow core is stack-agnostic. Anything technology-specific lives in a stack plugin, so a
project installs only the stacks it uses, and a project in an uncovered stack still gets the structure
(checkpoints, fix-attempt limits, reporting).

| Plugin | What it carries |
|---|---|
| `adk-adlc` | The ADLC core: `workflow-router`, `intent-capture`, `feature-development`, `bug-fix`, `refactor`, `project-setup`, `code-review-skill`, `independent-review`, `test-master`, `code-host`; the hooks; the Tier-1 agents and `unit-implementer`; `ci/`, `codehost/`, `maintain/`, `metrics/`. |
| `adk-backend` | Java/Spring Boot, databases, messaging (Kafka, RabbitMQ), Redis, Elasticsearch, API contracts, monitoring, the Toolbox MCP server for database connections, and the `java-ecosystem-engineer`, `data-storage-architect` and `api-spec-designer` agents. |
| `adk-desktop` | Tauri + React, Rust, UI/UX design, and the `tauri-react-engineer` agent. |
| `adk-architecture` | Architecture design, design principles, technical proposals, legacy modernization, code documentation, application security and security audits, MCP server development. |

## Install

```
/plugin marketplace add DianaSensei/agentic-development-kit
/plugin install adk-adlc@agentic-development-kit
/plugin install adk-backend@agentic-development-kit        # the stacks you use
/plugin install adk-desktop@agentic-development-kit
/plugin install adk-architecture@agentic-development-kit
```

This repo is both the plugins and their marketplace, so nothing gets copied into `.claude/`. The core
works without any stack plugin; the workflows read a stack's skills when it is installed, and the
gates only ask for skills that are. Each stack plugin also works on its own. To test local changes
instead of installing: `claude --plugin-dir /path/to/agentic-development-kit` (the core, which finds
the stack plugins under `plugins/`), plus `--plugin-dir /path/to/agentic-development-kit/plugins/<name>`
for each stack whose skills the session should list.

**Upgrading from 0.6 or earlier**, when the kit was one plugin named `agentic-development-kit`: that
plugin is now `adk-adlc`, and its technology skills and the Toolbox MCP server moved to the stack
plugins. The old name no longer exists in the marketplace, so it will not update again:

```
/plugin uninstall agentic-development-kit@agentic-development-kit
/plugin install adk-adlc@agentic-development-kit
/plugin install adk-backend@agentic-development-kit      # and the other stacks you use
```

In each repository, replace `"agentic-development-kit@agentic-development-kit": true` in
`.claude/settings.json`'s `enabledPlugins` with `"adk-adlc@agentic-development-kit": true` plus the
stack plugins it uses (`project-setup` does this when run again). Until then the old key still counts
as opting the repository in. Toolbox connections live in each plugin's data directory: copy yours from
`~/.claude/plugins/data/agentic-development-kit*/connections/` to
`~/.claude/plugins/data/adk-backend*/connections/`.

**Upgrading from 0.7**, where the core was briefly named `adk-sdlc`: it is now `adk-adlc`, for the
agentic development lifecycle it covers. Run `/plugin uninstall adk-sdlc@agentic-development-kit` and
`/plugin install adk-adlc@agentic-development-kit`, and update the key in `enabledPlugins` the same
way (the old key still counts as opting in until you do). The stack plugins keep their names.

**The kit stays quiet until a project opts in.** Installed this way (user scope), its skills are
available everywhere, but its session reminders - route code changes through `workflow-router`,
confirm the Checkpoint, self-review before "done" - appear only in a repository that chose the kit.
To opt a repository in, open it and say *"set this repo up for the agentic development kit"*:
`project-setup` writes the committed settings that enable the kit for every teammate, plus
`CLAUDE.md`, `REVIEW.md` and the CI reviewer.

To keep the kit out of every other project entirely - its skills included, which also cost tokens of
skill descriptions in every session - install it per project instead:
`claude plugin install <plugin>@agentic-development-kit --scope project`. `project-setup` enables the
stack plugins that match the repository's stack for everyone who opens it.

### Auto-update

Since this is a self-added (non-Anthropic) marketplace, Claude Code leaves auto-update off by default.
Turn it on once per machine:

```
/plugin
```

Open the **Marketplaces** tab, select `agentic-development-kit`, and choose **Enable auto-update**. From
then on, Claude Code checks each plugin's `version` field in the background each session and offers to
reload when it changes - no reinstalling needed. To check manually instead: `/plugin marketplace update
agentic-development-kit`.

### Releasing

The version is chosen in the pull request, and the four plugins share it: one number, raised together
in every `plugin.json` and in each of `.claude-plugin/marketplace.json`'s entries. When a PR changes
anything a plugin ships - everything except `evals/`, `.github/` and the repository README/LICENSE -
the **Version check** fails until the version is raised: patch for a fix, minor for a new capability,
major for a change users must act on. Merging it releases it:
[`release.yml`](./.github/workflows/release.yml) tags `v<version>` and creates the GitHub release.
Without the bump, installed plugins would never see the change. A shared version means a plugin
sometimes updates with no change of its own; in exchange, one tag names the whole kit.

## What's in it

The core's directories sit at the repository root, where Claude Code's
[plugin loader](https://code.claude.com/docs/en/plugins) expects them; each stack plugin has the same
layout under `plugins/<name>/`.

| Directory | What it is |
|---|---|
| [`skills/`](./skills/README.md) | The core's skills; the index lists the stack plugins' skills too. Claude Code picks the right one from its `description`, so there is nothing to invoke by hand. Also reachable as `/<plugin>:<skill-name>`. |
| [`plugins/`](./plugins/) | The stack plugins: `adk-backend`, `adk-desktop`, `adk-architecture`, each with its own `skills/`, `agents/` and manifest. |
| [`agents/`](./agents-guide.md) | Tiered Task subagents. Tier 1 clarifies requirements and proposes solutions, Tier 2 implements. They pass a fixed JSON contract between steps. |
| [`hooks/`](./hooks/README.md) | Gates for the rules a model cannot self-police: the owning `SKILL.md` was read before an edit, `code-review-skill` ran before "done", and a whole-file `Read` past a line threshold routes to the cheap `bulk-reader` agent instead of the expensive model's context. Warn by default, blocking per gate. |
| [`ci/`](./ci/README.md) | Independent review for GitHub Actions and GitLab CI: every pull or merge request reviewed by a fresh Claude session running `independent-review` - against its intent and plan, then for correctness - with inline findings and one summary comment for the approver. Claude only returns data; a script posts it through the code host's MCP server. A person still approves. |
| [`codehost/`](./codehost/README.md) | How the pipelines reach the code host: provider profiles for GitHub's and GitLab's MCP servers, and a small MCP client that posts reviews and opens the maintain loop's triage request. Tested against a fake server that serves the real tool schemas. |
| [`evals/`](./evals/README.md) | Behavioral regression tests for the kit, run with `claude plugin eval` on every PR that touches a skill, hook or agent: routing, the Checkpoint, intent files, and the independent reviewer against planted defects. |
| [`maintain/`](./maintain/README.md) | The maintain loop: a scheduled, deterministic check of control bands (`bands.yaml`) and of CI failures on the default branch; each problem becomes a `proposed` intent on one triage pull or merge request, on GitHub or GitLab. It also judges shipped intents against their success signal: did the change work? Claude writes only under `docs/intents/` and fixes nothing. |
| [`plugins/adk-backend/mcp/`](./plugins/adk-backend/mcp/README.md) | Toolbox config for databases - PostgreSQL, MySQL, TiDB, Redis, MongoDB, or any other type Toolbox supports. Ships with no pre-built connections; add exactly what you have. Declared in `adk-backend`'s `.mcp.json`, connected automatically once a connection exists - no repo clone needed. |
| [`metrics/`](./metrics/README.md) | The playbook's measures - acceptance rate, time to decision, plan to shipped, design rework, repeated mistakes, monitoring triage - computed from the committed intents, plans, changelogs and experience log. Deterministic, no network. |

## Using it

- **Skills** run themselves. Describe the request; `workflow-router` classifies it and hands off to
  `feature-development` / `bug-fix` / `refactor`.
- **A new project** starts with `project-setup` ("set this repo up for the kit"): it writes `CLAUDE.md`,
  `REVIEW.md`, `CODEOWNERS`, a committed `.claude/settings.json` that enables the kit for every
  teammate, the code host's MCP server, and the CI reviewer for GitHub or GitLab - adding to files that
  exist, never overwriting them.
- **Ideas not ready to build** go to `intent-capture`, which writes `docs/intents/<slug>.md` - the
  problem, evidence, and desired outcome, no solution. Later, "implement `docs/intents/<slug>.md`" starts
  the workflow from it, and the workflow links the intent to its plan and changelog as it goes.
- **Agents** are invoked through the Task tool, starting at `business-analyst`. See
  [`agents-guide.md`](./agents-guide.md).
- **Hooks** need no setup. They register wherever the plugin is enabled. To tune them for a project,
  drop a `.claude/quality-check.config.json` in that project's root.
- **MCP** auto-connects once you've added a connection: `adk-backend`'s `.mcp.json` declares `toolbox`,
  so Claude Code starts and connects it whenever that plugin is enabled - but it ships with none pre-built,
  so `✘ Failed to connect` right after installing is expected until you add one. Install the `toolbox`
  binary, then follow [`mcp/README.md`](./plugins/adk-backend/mcp/README.md) or just ask ("add a toolbox connection for my
  orders Postgres database") - the `toolbox-connections` skill handles the rest.

## skills/ vs agents/

Two models for the same work. A skill runs in the current session, sequentially, reading further
skills as it goes. An agent is a separate subagent with a fixed role.

`feature-development` uses both: Steps 1 and 2 go to `business-analyst` and `solution-architect` as
subagents precisely because those carry no `Edit`/`Write` tool, so requirements and design happen where
code is impossible to touch. A missing tool guarantees that; a hook reading transcripts afterwards
cannot. Step 3 may dispatch a Tier-2 specialist when one exists for the task. Independent units the
approved plan declares are built at the same time by `unit-implementer` agents, each in a git worktree
of its own, and applied to the working tree afterwards. `bug-fix` and `refactor` stay in-session, since
their checkpoints are simpler.

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
