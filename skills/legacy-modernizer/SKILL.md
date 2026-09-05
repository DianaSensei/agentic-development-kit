---
name: legacy-modernizer
description: Designs incremental migration strategies, identifies service boundaries, produces dependency maps and migration roadmaps, and generates API facade designs for aging codebases. Use when modernizing legacy systems, implementing strangler fig pattern or branch by abstraction, decomposing monoliths, upgrading frameworks or languages, or reducing technical debt without disrupting business operations.
metadata:
  domain: specialized
  triggers: legacy modernization, legacy refactoring, system migration, modernize codebase
  role: specialist
  scope: architecture
  output-format: code+analysis
  related-skills: test-master, architecture-designer, spec-miner
---

# Legacy Modernizer

## Core Workflow

1. **Assess system** - Analyze codebase, dependencies, risks, and business constraints. Produce a dependency map and risk register before proceeding.
   - _Validation checkpoint:_ Confirm all external integrations and data contracts are documented before moving to step 2.

2. **Plan migration** - Design an incremental roadmap with explicit rollback strategies per phase. Reference `references/system-assessment.md` for code analysis templates.
   - _Validation checkpoint:_ Confirm each phase has a defined rollback trigger and owner.

3. **Build safety net** - Create characterization tests and monitoring before touching production code. Target 80%+ coverage of existing behavior.
   - _Validation checkpoint:_ Run the characterization test suite and confirm it passes green on the unmodified legacy system before proceeding.

4. **Migrate incrementally** - Apply strangler fig pattern with feature flags. Route traffic via a facade; shift load gradually.
   - _Validation checkpoint:_ Verify error rates and latency metrics remain within baseline thresholds after each traffic increment (e.g., 5% → 25% → 50% → 100%).

5. **Validate & iterate** - Run full test suite, review monitoring dashboards, and confirm business behavior is preserved before retiring legacy code.
   - _Validation checkpoint:_ New code must be proven stable at 100% traffic for at least one release cycle before legacy path is removed.

## Reference Guide

Every reference below is stack-agnostic - method and boundary only, no code, no language or framework
specifics. Load whichever is relevant to the current step; applying the described approach to whatever
language/framework the codebase actually uses is part of the task, not something the reference decides
for you.

| Topic         | Reference                             | Load When                                                                                                        |
| ------------- | ------------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| Strangler Fig | `references/strangler-fig-pattern.md` | Incremental replacement, facade/router layer, traffic-shift rollout                                              |
| Refactoring   | `references/refactoring-patterns.md`  | Branch by abstraction, extract service, adapter, facade, replace algorithm, repository                           |
| Migration     | `references/migration-strategies.md`  | Database dual-write, schema evolution, API versioning, framework/UI/language migration, microservices extraction |
| Testing       | `references/legacy-testing.md`        | Characterization tests, golden master, snapshot, parallel run, mutation, property-based, coverage-guided         |
| Assessment    | `references/system-assessment.md`     | Codebase analysis, dependency mapping, technical debt, risk matrix, roadmap, stakeholder communication           |

## Core Patterns

- **Facade / strangler fig routing** - a thin layer in front of both the legacy and new implementation
  that decides, per request, which one handles it (feature flag, percentage rollout, or user
  attribute). The facade is the only thing that changes as traffic shifts; callers never know which
  implementation served them. → `references/strangler-fig-pattern.md`
- **Feature flags for incremental rollout** - every traffic shift (facade routing, branch by
  abstraction, dual-write cutover) is gated by a flag that can be reverted instantly without a
  deploy - never a one-shot switch with no way back. → `references/refactoring-patterns.md`
- **Characterization tests as a safety net** - before touching legacy code, write tests that lock in
  _current_ behavior (bugs included), not tests of what the behavior _should_ be. These are what makes
  refactoring safe: a change that alters undocumented legacy behavior fails loudly instead of shipping
  silently. → `references/legacy-testing.md`

## Output Templates

When implementing modernization, provide:

1. Assessment summary (risks, dependencies, approach)
2. Migration plan (phases, rollback strategy, metrics)
3. Implementation code (facades, adapters, new services)
4. Test coverage (characterization, integration, e2e)
5. Monitoring setup (metrics, alerts, dashboards)

## Boundaries

- This skill supplies *method*, not the surrounding workflow - it has no CHECKPOINT gate, no
  fix-attempt counter, and no final-report/changelog step of its own. When a migration is part of a
  larger request, `refactor` (behavior-preserving structural change) or `feature-development` (a
  monolith decomposition framed as new capability) owns the checkpoints, the implement/test loop, and
  reporting; this skill is read in full and applied within that orchestrator's implementation step, the
  same way any other technical skill is.
- The "Core Workflow" above (assess → plan → safety net → migrate → validate) describes the *method
  sequence* to follow once invoked - it is not a second, independent driver of user interaction. Don't
  run it standalone without the orchestrator's checkpoint/rollback discipline around it.
- Overlaps with `refactor` on characterization testing and incremental, rollback-capable execution -
  the difference is scale and mechanism: `refactor` handles small-to-medium structural changes with a
  git-revert-based rollback; this skill is for changes large enough to need a live facade/router,
  gradual traffic shift, and a feature-flag-gated cutover (strangler fig, branch by abstraction,
  dual-write). If a "refactor" turns out to need a facade and gradual traffic shift, that's this skill,
  not a bigger version of `refactor`'s in-place small-step loop.
- Overlaps with `spec-miner` on dependency mapping - `spec-miner` maps a system to document/explain it
  (output: understanding); this skill maps it as input to a migration plan (output: a roadmap and a
  safe path). If the system isn't understood yet, run `spec-miner` first; don't re-derive its analysis
  here.
- Deep test-strategy questions beyond characterization testing (broader test architecture, mocking
  strategy) are `test-master`'s job; deep target-architecture questions (what the system should look
  like once migrated) are `architecture-designer`'s job - this skill owns the safe *path* from the
  current system to that target, not the target's design itself.
