# Skills

A library of [Claude Code Skills](https://docs.claude.com/en/docs/claude-code/skills) — each
subdirectory is one skill: a `SKILL.md` (name, description, and core method) plus, for most skills, a
`references/` folder of detail loaded only when actually needed. Claude Code surfaces every skill's
name and description automatically and picks the matching one for a given task — nothing here needs to
be invoked by hand except the few explicitly marked manual-only below.

## How This Library Is Organized

Two different kinds of skill live side by side here, and it matters which kind you're looking at:

- **Workflow orchestrators** — own an entire task end-to-end (interview → propose → implement/test loop
  → report → knowledge capture). They hold no technology-specific knowledge themselves; they read the
  matching technical skill's full content at the point of applying it.
- **Technical/knowledge skills** — everything else. Each owns one technology or one discipline in
  depth, and is read in full by an orchestrator (or invoked directly) when that specific expertise is
  needed.

The three workflow orchestrators carry hooks in their frontmatter: while one of them is running, a
`PreToolUse` gate checks that the technical skill owning a file was read in the current request before
that file is edited, and a `Stop` gate checks that `code-review-skill` was run on the diff before the
change is reported done. Both warn by default and can be set to block. See [`hooks/README.md`](../hooks/README.md).

`workflow-router` is the entry point for any code-writing request — it classifies the request and hands
off to the right orchestrator, so in practice you rarely need to name a workflow skill yourself.

## Workflow Orchestrators

| Skill | Use For |
|-------|---------|
| [`workflow-router`](./workflow-router/SKILL.md) | First stop for any "write or change code" request — classifies it as a new feature, a bug fix, or a refactor, then hands off |
| [`feature-development`](./feature-development/SKILL.md) | New capability or an intentional behavior change, start to finish |
| [`bug-fix`](./bug-fix/SKILL.md) | Current behavior is actually wrong — reproduce, confirm root cause, fix, postmortem |
| [`refactor`](./refactor/SKILL.md) | Structure/performance/maintainability improvement with external behavior required to stay 100% identical |

## Requirements & Design

| Skill | Use For |
|-------|---------|
| [`architecture-designer`](./architecture-designer/SKILL.md) | System design, from a single service to distributed microservices decomposition, deployment topology (VM/cloud/hybrid), ADRs |
| [`solution-design-principles`](./solution-design-principles/SKILL.md) | SOLID, DRY/KISS/YAGNI, method decomposition (SLAP), Command-Query Separation/TOCTOU, Well-Architected pillars, 12-Factor, VM/cloud portability — judging whether a design/codebase follows sound engineering principles |
| [`api-contract-skill`](./api-contract-skill/SKILL.md) | REST/GraphQL/RPC/async message contract design, before implementation |
| [`ui-ux-design-skill`](./ui-ux-design-skill/SKILL.md) | UI/UX design (usability, accessibility, responsive/cross-platform) before implementation |
| [`spec-miner`](./spec-miner/SKILL.md) | Reverse-engineer a spec from an undocumented/legacy/inherited codebase |
| [`legacy-modernizer`](./legacy-modernizer/SKILL.md) | Incremental migration strategy for a large-scale legacy change (strangler fig, branch by abstraction) |
| [`technical-proposal-writer`](./technical-proposal-writer/SKILL.md) | Writing/reviewing a technical proposal, RFC, or "đề xuất kỹ thuật" that argues a decision to stakeholders — problem, alternatives, risks, plan, timeline |

## Language & Framework Implementation

| Skill | Use For |
|-------|---------|
| [`java-spring-skill`](./java-spring-skill/SKILL.md) | Java + Spring Boot business logic, data access, security, cloud/resilience, package structure, code style |
| [`rust-engineer`](./rust-engineer/SKILL.md) | Idiomatic Rust — ownership, lifetimes, traits, async/tokio |
| [`tauri-react-skill`](./tauri-react-skill/SKILL.md) | Tauri (Rust backend) + React (frontend) desktop app implementation |

## Data & Messaging Infrastructure

| Skill | Use For |
|-------|---------|
| [`database-skill`](./database-skill/SKILL.md) | RDBMS (Oracle/PostgreSQL/MySQL) and NoSQL (MongoDB/DynamoDB/Cassandra/ScyllaDB) design and optimization |
| [`kafka-skill`](./kafka-skill/SKILL.md) | Apache Kafka topic/partition design, delivery semantics, consumer groups |
| [`rabbitmq-skill`](./rabbitmq-skill/SKILL.md) | RabbitMQ exchanges, routing, dead-letter, queue durability |
| [`pubsub-skill`](./pubsub-skill/SKILL.md) | Google Cloud Pub/Sub topics/subscriptions, ordering, delivery |
| [`redis-skill`](./redis-skill/SKILL.md) | Redis caching, distributed locks, lightweight queues, leaderboards |
| [`elasticsearch-skill`](./elasticsearch-skill/SKILL.md) | Elasticsearch index/mapping design, Query DSL, aggregations |
| [`testcontainers-skill`](./testcontainers-skill/SKILL.md) | Container-based integration test setup/lifecycle (pairs with the infra skills above) |

## Quality, Security & Documentation

| Skill | Use For |
|-------|---------|
| [`test-master`](./test-master/SKILL.md) | Test plans, mocking strategy, coverage analysis, performance/security test design |
| [`code-review-skill`](./code-review-skill/SKILL.md) | The proactive self-check Claude runs before reporting any code change done — checked by the `Stop` gate in [`hooks/`](../hooks/README.md) rather than left to memory |
| [`secure-code-guardian`](./secure-code-guardian/SKILL.md) | Implementing secure code — auth, input validation, hashing, OWASP prevention |
| [`security-reviewer`](./security-reviewer/SKILL.md) | Auditing existing code/infrastructure for vulnerabilities, producing a report |
| [`monitoring-expert`](./monitoring-expert/SKILL.md) | Production observability — logging, metrics, tracing, alerting, capacity forecasting |
| [`code-documenter`](./code-documenter/SKILL.md) | Docstrings/comments, API docs, doc sites, user guides — any language or framework |

## MCP & Integrations

| Skill | Use For |
|-------|---------|
| [`mcp-developer`](./mcp-developer/SKILL.md) | Building a new MCP server/client (protocol, SDKs, authorization) |
| [`mcp-setup`](./mcp-setup/SKILL.md) | **Manual-only** — connecting an existing third-party MCP server to Claude Code, given a link |
| [`atlassian-mcp`](./atlassian-mcp/SKILL.md) | Jira/Confluence via MCP — JQL/CQL queries, tickets, sprints, docs |

## Conventions Used Across These Skills

- **`description` is the trigger** — it's what Claude Code matches against, so it states both what the
  skill does and, where another skill could plausibly also match, why not that one instead.
- **`references/` is progressive disclosure** — a skill's `SKILL.md` stays lean; deep detail (code
  patterns, decision tables, troubleshooting trees) lives in `references/*.md`, loaded only when the
  matching step is actually reached, listed in each skill's Reference Guide table.
- **`## Boundaries`** — most skills state explicitly what they do *not* own, and which sibling skill
  owns it instead. This is what keeps two skills with adjacent expertise (e.g. `secure-code-guardian` vs.
  `security-reviewer`, `monitoring-expert` vs. `test-master`) from being ambiguous about which one a
  given request should trigger.
- **Technology-specific vs. technology-agnostic** — a skill that isn't inherently about one language or
  framework (e.g. `architecture-designer`, `code-documenter`) stays free of language-specific code in
  its core file even if its references illustrate a pattern concretely; a skill that *is* inherently
  about one technology (e.g. `kafka-skill`) is expected to be technology-specific throughout.
- **Orchestrators never guess technical detail** — `feature-development`/`bug-fix`/`refactor` always
  `Read` a technical skill's full content before applying it; they never infer conventions from a name
  or description alone.
