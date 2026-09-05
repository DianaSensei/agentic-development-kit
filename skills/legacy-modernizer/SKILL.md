---
name: legacy-modernizer
description: "Two jobs on aging or inherited codebases. UNDERSTAND - reverse-engineer a specification from a system nobody documented: map structure and dependencies, trace data flows and request paths, recover the business rules from the implementation, write them up as EARS requirements, and flag what's still unclear. MIGRATE - turn that understanding into a safe incremental change: service boundaries, dependency maps, migration roadmaps, API facade designs, strangler fig or branch-by-abstraction rollout. Use for legacy or undocumented systems, inherited projects, onboarding to an unfamiliar codebase, figuring out what existing code actually does, monolith decomposition, framework/language upgrades, or reducing technical debt without disrupting operations."
metadata:
  domain: specialized
  triggers: legacy modernization, legacy refactoring, system migration, modernize codebase, reverse engineer, no docs, no documentation, figure out how this works, inherited project, legacy analysis, code archaeology, undocumented features, understand codebase, existing system
  role: specialist
  scope: architecture
  output-format: code+analysis
  related-skills: test-master, architecture-designer, code-documenter, refactor
---

# Legacy Modernizer

Two phases that usually run in order. **Understand** produces a specification of what the system does
today. **Migrate** turns that into a safe path to what it should do next. A request may need only the
first - stop there when it does, rather than proposing a migration nobody asked for.

## Phase 1 - Understand (reverse-engineer the spec)

Run this when the system is undocumented, inherited, or simply unfamiliar. Skip it when the system is
already well understood and the request is purely "migrate X".

1. **Scope** - full system, or one feature.
2. **Explore** - map structure with Glob/Grep/Read.
   _Checkpoint:_ enough coverage before writing anything. If key entry points, config files, or core
   modules are still unread, keep exploring.
3. **Trace** - follow data flows and request paths.
4. **Document** - write observed behavior as EARS requirements (below).
5. **Flag** - name what's still unclear in its own section, rather than smoothing it over.

**Identify the stack FIRST** from its dependency manifest - `pom.xml`/`build.gradle` → Java/Spring,
`Cargo.toml` → Rust/Tauri, `package.json` → Node/TS, `requirements.txt`/`pyproject.toml` → Python,
`go.mod` → Go. Never assume a language before confirming it. Full pattern set per stack:
`references/analysis-process.md`.

```
# Technical debt markers - applies to every stack
Grep('TODO|FIXME|HACK|XXX')

# Java/Spring: entry point + route
Grep('@RestController|@RequestMapping|@GetMapping|@PostMapping', include='*.java')

# Rust/Tauri: command handler
Grep('#\[tauri::command\]', include='*.rs')

# Node/TS (Express/NestJS): route
Grep('@Controller|@Get|@Post|router\.|app\.get', include='*.ts,*.js')

# Python (Flask/Django/FastAPI): route
Grep('@app\.route|@router\.|def .*\(request', include='*.py')
```

### EARS format

| Type | Pattern | Example |
|------|---------|---------|
| Ubiquitous | The `<system>` shall `<action>`. | The API shall return JSON responses. |
| Event-driven | When `<trigger>`, the `<system>` shall `<action>`. | When a request lacks an auth token, the system shall return HTTP 401. |
| State-driven | While `<state>`, the `<system>` shall `<action>`. | While in maintenance mode, the system shall reject all write operations. |
| Optional | Where `<feature>` is supported, the `<system>` shall `<action>`. | Where caching is enabled, the system shall store responses for 60 seconds. |

Full reference: `references/ears-format.md`.

**Rules for this phase**: ground every observation in actual code, with its location. Distinguish
observed fact from inference explicitly - never present a guess as a finding. Cover security and error
handling patterns, not just the happy path. Save the specification to
`specs/{project_name}_reverse_spec.md` per `references/specification-template.md`.

## Phase 2 - Migrate

1. **Assess** - codebase, dependencies, risks, business constraints. Produce a dependency map and risk
   register (Phase 1's output feeds directly into this; don't re-derive it).
   _Checkpoint:_ all external integrations and data contracts documented before step 2.
2. **Plan** - an incremental roadmap with an explicit rollback strategy per phase
   (`references/system-assessment.md`).
   _Checkpoint:_ every phase has a defined rollback trigger and an owner.
3. **Build the safety net** - characterization tests and monitoring **before** touching production code,
   targeting 80%+ coverage of existing behavior.
   _Checkpoint:_ the suite passes green against the *unmodified* legacy system first.
4. **Migrate incrementally** - strangler fig with feature flags; route traffic through a facade and
   shift load gradually.
   _Checkpoint:_ error rate and latency stay within baseline after each increment (5% → 25% → 50% →
   100%).
5. **Validate & iterate** - full suite, monitoring dashboards, business behavior preserved before
   retiring legacy code.
   _Checkpoint:_ new code proven stable at 100% traffic for at least one release cycle before the legacy
   path is removed.

### Core patterns

- **Facade / strangler fig routing** - a thin layer in front of both implementations deciding per
  request which one handles it (feature flag, percentage, user attribute). Only the facade changes as
  traffic shifts; callers never know which side served them. → `references/strangler-fig-pattern.md`
- **Feature flags for every rollout** - each traffic shift (facade routing, branch by abstraction,
  dual-write cutover) is gated by a flag revertible instantly without a deploy. Never a one-shot switch
  with no way back. → `references/refactoring-patterns.md`
- **Characterization tests as the safety net** - lock in *current* behavior, bugs included, not what the
  behavior *should* be. This is what makes the refactor safe: a change that alters undocumented legacy
  behavior then fails loudly instead of shipping silently. → `references/legacy-testing.md`

## Reference Guide

Every reference is stack-agnostic - method and boundary only, no language specifics. Applying the
approach to whatever stack the codebase actually uses is part of the task.

| Phase | Topic | Reference | Load When |
| ----- | ----- | --------- | --------- |
| Understand | Analysis Process | `references/analysis-process.md` | Starting exploration, Glob/Grep patterns per stack |
| Understand | EARS Format | `references/ears-format.md` | Writing observed requirements |
| Understand | Specification Template | `references/specification-template.md` | Producing the final spec document |
| Understand | Analysis Checklist | `references/analysis-checklist.md` | Confirming the analysis was thorough |
| Migrate | Assessment | `references/system-assessment.md` | Codebase analysis, dependency mapping, technical debt, risk matrix, roadmap, stakeholder communication |
| Migrate | Strangler Fig | `references/strangler-fig-pattern.md` | Incremental replacement, facade/router layer, traffic-shift rollout |
| Migrate | Refactoring | `references/refactoring-patterns.md` | Branch by abstraction, extract service, adapter, facade, replace algorithm, repository |
| Migrate | Migration | `references/migration-strategies.md` | Database dual-write, schema evolution, API versioning, framework/UI/language migration, microservices extraction |
| Migrate | Testing | `references/legacy-testing.md` | Characterization tests, golden master, snapshot, parallel run, mutation, property-based, coverage-guided |

## Output

**Understand**: `specs/{project_name}_reverse_spec.md` - structure, data flows, EARS requirements with
code locations, and an explicit uncertainties section.

**Migrate**: assessment summary (risks, dependencies, approach); migration plan (phases, rollback
strategy, metrics); implementation code (facades, adapters, new services); test coverage
(characterization, integration, e2e); monitoring setup.

## Boundaries

- Supplies *method*, not the surrounding workflow - no CHECKPOINT gate, no fix-attempt counter, no
  final-report/changelog step of its own. When a migration is part of a larger request, `refactor`
  (behavior-preserving structural change) or `feature-development` (decomposition framed as new
  capability) owns the checkpoints, the implement/test loop, and reporting; this skill is read in full
  and applied inside that orchestrator's implementation step. The phase sequences above are a *method*,
  not a second driver of user interaction - don't run them standalone without that discipline.
- Phase 1's output is *understanding*, not change. It doesn't fix the code, and it doesn't decide what
  should happen next - if code turns out to be wrong or oddly structured, flag it rather than silently
  fixing it during an analysis pass.
- Overlaps `refactor` on characterization testing and incremental rollback, differing by scale and
  mechanism: `refactor` handles small-to-medium structural change with git-revert rollback; this skill is
  for change large enough to need a live facade/router, gradual traffic shift, and a flag-gated cutover.
  A "refactor" that turns out to need a facade and traffic shift is this skill, not a bigger version of
  `refactor`'s in-place loop.
- Overlaps `code-documenter` on producing docs from source, differing by starting condition: this skill
  is for a legacy/undocumented/inherited system whose spec must be recovered from behavior;
  `code-documenter` is for a system with a known owner, documented going forward as normal development.
  Once a system has been reverse-engineered once, ongoing doc maintenance is `code-documenter`'s job, not
  a repeated mining pass.
- Deep test-strategy questions beyond characterization testing (test architecture, mocking strategy) →
  `test-master`. What the system *should* look like once migrated → `architecture-designer`; this skill
  owns the safe path there, not the target's design.
