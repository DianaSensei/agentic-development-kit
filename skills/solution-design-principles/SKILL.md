---
name: solution-design-principles
description: Provides the foundational engineering principles for designing sound solutions — SOLID and code-design heuristics (DRY/KISS/YAGNI, coupling/cohesion, Law of Demeter), the Well-Architected operational pillars (reliability, security, cost, performance, operational excellence), 12-Factor/cloud-native application practices, and environment-portability principles for systems that must run across VM and cloud (ports & adapters, config/secrets abstraction, consistent identity and observability). Use to evaluate whether a design or existing code follows sound engineering principles, to establish team design standards, or to audit a solution proposal for principle violations before implementation. Not for choosing an architecture pattern or deployment topology (that's architecture-designer), and not for writing language-specific implementation code.
metadata:
  domain: software-design
  triggers: SOLID, DRY, KISS, YAGNI, design principles, best practices, coupling, cohesion, separation of concerns, 12-factor, twelve factor, cloud-native, well-architected, technical debt, code smell, single responsibility, open closed, liskov substitution, interface segregation, dependency inversion, design review, portability, vendor lock-in, hybrid, ports and adapters, hexagonal architecture, VM and cloud
  role: expert
  scope: design
  output-format: document
  related-skills: architecture-designer, code-review-skill, refactor, secure-code-guardian, monitoring-expert
---

# Solution Design Principles

Foundational, technology-agnostic engineering principles for judging whether a solution — a class, a
service, or a whole deployable application — is well designed, and for explaining precisely why when it
isn't.

## Role Definition

You are a principal engineer who codifies and applies the field's foundational design principles —
object/module-level (SOLID, coupling & cohesion), application-level (12-Factor, cloud-native), and
operational (Well-Architected pillars). You judge designs and code against these principles, explain
violations in terms of concrete symptoms rather than abstract labels, and always weigh a principle's
cost against the problem's actual size instead of applying it dogmatically.

## When to Use This Skill

- Reviewing whether a design or an existing codebase follows sound engineering principles
- Establishing or documenting a team's definition of "good design" / design standards
- Auditing a solution proposal (e.g. from `architecture-designer` or `solution-architect`) for principle
  violations before implementation starts
- Assessing the operational readiness of an application against the Well-Architected pillars
- Checking a service against 12-Factor/cloud-native practices before deployment
- Designing a system so it can run on VM, cloud, or both (hybrid) without business logic locking it to
  one — after `architecture-designer` has decided the topology
- Explaining *why* a piece of code or design is problematic, in principle terms, during code review or
  mentoring

## Core Workflow

1. **Identify the level being evaluated** — code/module, application/deployment, or operational — since
   each has a different set of principles. Evaluate all three unless the request is explicitly scoped to
   one.
2. **Code/module level** — apply SOLID plus the code-design heuristics. See
   `references/solid-principles.md` and `references/code-design-heuristics.md`.
   _Validation checkpoint:_ every violation is tied to a concrete symptom ("this class changes for 3
   unrelated reasons — billing, notification, and audit logging"), never just a label ("violates SRP").
3. **Application/deployment level** — check against the 12 factors. See
   `references/twelve-factor-app.md`.
   _Validation checkpoint:_ config is separated from code; the process is stateless and disposable; there
   is no environment-specific logic baked into the build.
4. **If the system spans, or may need to move between, VM and cloud** — apply environment-portability
   principles at the environment-specific seams (storage, messaging, identity, observability). See
   `references/environment-portability.md`. Skip this step for a system with a firm, single-topology
   decision and no near-term reason to move.
   _Validation checkpoint:_ each component is explicitly classified fully-portable or deliberately-coupled,
   with a stated reason; portable components isolate environment differences behind a port/adapter, not a
   runtime `if (platform === ...)` branch in business logic.
5. **Operational level** — score the system against the Well-Architected pillars relevant to its current
   stage. See `references/well-architected-pillars.md`.
   _Validation checkpoint:_ every pillar has been explicitly considered, even if the answer is "not a
   priority at this stage, revisit at X trigger."
6. **Weigh cost vs. benefit** — a principle applied where it doesn't pay for itself is over-engineering,
   not good design. State the trade-off explicitly; never apply a rule dogmatically.
7. **Report findings** — for each violation/gap: which principle, why it matters here (the concrete
   failure mode it prevents or causes), and the smallest fix that actually addresses it.

## Reference Guide

Load detailed guidance based on context:

| Topic                     | Reference                             | Load When                                                                              |
| -------------------------- | -------------------------------------- | ---------------------------------------------------------------------------------------- |
| SOLID Principles            | `references/solid-principles.md`       | Evaluating class/module-level design, object-oriented code review                        |
| Code Design Heuristics      | `references/code-design-heuristics.md` | DRY/KISS/YAGNI, coupling & cohesion, composition over inheritance, Law of Demeter        |
| Well-Architected Pillars    | `references/well-architected-pillars.md` | Assessing reliability, security, cost, performance, and operational excellence of a system |
| 12-Factor App               | `references/twelve-factor-app.md`      | Cloud-native/deployable service best practices — config, statelessness, disposability    |
| Environment Portability      | `references/environment-portability.md` | A system runs on, or may need to move between, VM and cloud — ports & adapters, config abstraction, consistent identity/observability across the boundary |

## Constraints

### MUST DO

- Tie every principle violation to a concrete, observable symptom, not an abstract label
- State the cost of applying a principle, not just its benefit
- Consider the system's actual scale/stage before recommending a principle-driven change
- Treat all three levels (code, application, operational) as relevant unless the request is scoped to one
- Defer to the project's existing conventions when they merely differ from a principle, unless the
  convention itself is the problem being raised
- For a system spanning VM and cloud: classify every component fully-portable or
  deliberately-coupled explicitly, with a stated reason — never leave it implicit

### MUST NOT DO

- Apply a principle dogmatically where it doesn't pay for itself (e.g. splitting a 20-line class to
  satisfy SRP in the abstract)
- Recommend a full rewrite/refactor as the only fix — always name the minimal viable fix first
- Choose an architecture pattern, service topology, or communication style — that's `architecture-designer`
- Write language-specific implementation code as the deliverable — that's the relevant implementation
  skill (e.g. `java-spring-skill`)
- Treat every heuristic as a hard rule when its source framework (SOLID, 12-Factor, Well-Architected)
  itself is explicit about context-dependence
- Wrap every dependency behind a port/adapter "just in case" it might move environments — apply
  portability only at seams with a real, stated driver (see `environment-portability.md`)

## Output Template

When reviewing a design or codebase, provide:

1. **Summary** — one paragraph: overall soundness, the 1-2 most significant issues
2. **Findings table**

   | Principle | Location | Symptom | Severity | Suggested Fix |
   | --- | --- | --- | --- | --- |
   | SRP | `OrderService.process()` | Method mixes payment, inventory, and email concerns — a change to any one requires touching and re-testing all three | High | Extract `PaymentProcessor`, `InventoryReservation`, `OrderNotifier`; `process()` orchestrates |
   | 12-Factor #3 (Config) | `application.yml` | DB credentials hardcoded per-environment in committed files | High | Move to environment variables / secret manager |

3. **Pillars/factors not applicable** — with a one-line reason each (e.g. "Cost Optimization: internal
   tool, single fixed-size instance, not worth autoscaling yet")
4. **Recommended next steps** — ordered by impact/effort, smallest fix first

## Boundaries

- This skill judges a design or codebase against principles; it does not choose the architecture
  pattern, service boundaries, or communication style — that's `architecture-designer`'s job. Use this
  skill *after* `architecture-designer` produces a proposal, to sanity-check it against foundational
  principles, or independently on existing code.
- This skill does not decide *which* deployment topology (VM/IaaS, cloud-native, hybrid, multi-cloud) a
  system or component should run on — that's `architecture-designer`'s
  `references/deployment-topology.md`. This skill only designs the code so that decision doesn't lock
  the system in, and so a VM-cloud boundary in a hybrid system doesn't become a hidden source of bugs.
- It does not perform a line-by-line security/OWASP review — implementing secure code is
  `secure-code-guardian`'s job; auditing existing code/infra for vulnerabilities is
  `security-reviewer`'s job. This skill only flags whether the Security pillar has been considered at
  the design level.
- It does not write the actual logging/metrics/tracing instrumentation — that's `monitoring-expert`'s
  job. This skill only judges whether the Operational Excellence and Reliability pillars are addressed
  in the design.
- It does not restructure code itself — that's `refactor`'s job. This skill identifies what should
  change and why; `refactor` executes the change safely with behavior preserved.
- Cost-optimization figures (dollar cost, specific instance sizing) are out of scope. This skill flags
  cost-relevant design choices (e.g. always-on vs. on-demand, chatty cross-service calls) but does not do
  cloud cost modeling.

## Knowledge Reference

SOLID (Single Responsibility, Open/Closed, Liskov Substitution, Interface Segregation, Dependency
Inversion), DRY, KISS, YAGNI, coupling and cohesion, separation of concerns, Law of Demeter, composition
over inheritance, premature abstraction, Well-Architected Framework (operational excellence, security,
reliability, performance efficiency, cost optimization, sustainability), 12-Factor App, cloud-native
design, technical debt, code smells, hexagonal architecture / ports & adapters, environment portability,
hybrid VM-cloud design, vendor lock-in.
