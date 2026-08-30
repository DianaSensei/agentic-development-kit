# Agents

A set of Claude Code subagents (`agents/*.md` at this plugin's root, invoked via the Task tool) forming
a tiered pipeline for feature development: Tier 1 clarifies requirements + proposes a plan, Tier 2
implements specialized work per technical area. Each agent receives input and returns output following
a fixed JSON contract, so the next agent can use it directly without having to re-infer anything. Once
this plugin is enabled, each agent also appears under `/context` → Custom Agents and can be @-mentioned
by its scoped name.

> **How this relates to `skills/`**: `feature-development` (in `skills/`) launches `business-analyst`
> and `solution-architect` as Task subagents for Steps 1-2, specifically because they carry no
> `Edit`/`Write` tool — requirements analysis and solution design happen where code genuinely cannot be
> touched, not just where the prose says not to. `bug-fix` and `refactor` don't use this pipeline yet;
> their checkpoints are enforced by `checkpoint-gate.sh` instead (see
> [`hooks/README.md`](./hooks/README.md)). Tier-2 specialists remain optional from `feature-development`
> Step 3 — dispatched only for a task whose `task_breakdown` entry names one that actually exists;
> everything else is still implemented directly against the matching technical skill.

## Pipeline

```
business-analyst  →  solution-architect  →  Tier-2 specialist(s), per task_breakdown
   (Tier 1)              (Tier 1)              (parallel or sequential, depending on dependencies)
```

| Step | Agent | Role |
|------|-------|---------|
| 1 | [`business-analyst`](./business-analyst.md) | Reviews current state, clarifies requirements, assesses feasibility. Completely agnostic — doesn't know/need to know the stack. Output: draft AC/Edge Case/DoD + a preliminary impact assessment. |
| 2 | [`solution-architect`](./solution-architect.md) | Takes the output from Step 1, identifies the stack (`CLAUDE.md` → memory/MCP → code evidence), produces 1+ proposal(s) complete with diagrams/tradeoffs/finalized AC-DoD + a `task_breakdown` assigning work to the right Tier-2 agent. Does NOT write code, does NOT finalize a specific storage schema/technology. |
| 3 | Tier-2 specialist(s) | Each agent in `task_breakdown` implements exactly the assigned piece of work, can run in parallel if independent (`can_run_parallel_with`). |

`solution-architect` **does not use a hardcoded list of agent names** — it reads `agents/*.md` itself
(Step 0.5 in its own file) to find out which Tier-2 agents actually exist and what they do, before
assigning work. This means adding a new Tier-2 agent to this directory doesn't require editing
`solution-architect.md`.

## Existing Tier-2 Specialists

| Agent | Specialty | Called after |
|-------|--------------|---------|
| [`api-spec-designer`](./api-spec-designer.md) | API contracts — synchronous REST (OpenAPI) + asynchronous message contracts (Kafka/RabbitMQ/Pub-Sub, AsyncAPI-style). Defines the contract only, does not implement the server/broker. | `solution-architect` |
| [`data-storage-architect`](./data-storage-architect.md) | Designs data storage for ANY technology (Oracle/PostgreSQL/MySQL/Redis/MongoDB/Elasticsearch/local SQLite). Auto-detects the technology in use, always presents tradeoffs, never decides unilaterally. | `solution-architect` |
| [`java-ecosystem-engineer`](./java-ecosystem-engineer.md) | Implements + self-tests Java Spring Boot business/functional flows (MVC/WebFlux, Spring Data, Security, Kafka, RabbitMQ, resilience). | `data-storage-architect` + `api-spec-designer` (if applicable) |
| [`tauri-react-engineer`](./tauri-react-engineer.md) | Implements + self-tests Tauri (Rust commands) + React (UI) for a cross-platform desktop app. | `data-storage-architect` (if persisted data is needed) + `api-spec-designer` (if applicable) |

Every implementing (Tier 2) agent writes AND runs its own tests for the part it did before reporting
done, leaving no verification work for a later step.

## General conventions

- **Structured JSON output** — each agent returns a JSON object following a fixed schema defined in its
  own file, so the next agent/step can use it directly rather than parsing free-form text.
- **`checkpoint`** — most outputs have a `checkpoint` field (`required`, `type`, `summary`) that clearly
  marks when to pause and wait for user confirmation (e.g., choosing among multiple `solution-architect`
  proposals) before proceeding.
- **`context_sources_used` / `provenance`** — agents always record where information came from
  (CLAUDE.md, memory/MCP, or reading code) so the next step knows how much to trust it, rather than
  treating every input as already confirmed.
- **Tier 1 is stack-agnostic, Tier 2 is not** — `business-analyst` is deliberately designed to be
  completely agnostic (usable for any type of project); starting from `solution-architect` onward, the
  stack must be identified in order to route to the right specialist.
- **Every `solution-architect` proposal must be self-contained** — since this agent runs only once in
  the normal flow, once the user picks a proposal, the lead agent uses that proposal's AC/Edge
  Case/DoD/task_breakdown directly, without calling `solution-architect` again for more input.
