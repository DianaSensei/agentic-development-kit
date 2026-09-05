---
name: architecture-designer
description: Designs system architecture, from a single service's high-level design to distributed microservices decomposition. Produces architecture diagrams, ADRs, service boundary designs, deployment-topology decisions (VM/IaaS vs. cloud-native vs. hybrid vs. multi-cloud), and - for distributed systems - communication, data-ownership, and resilience strategies, each with explicit trade-offs. Use for new system design, architecture review, pattern selection (monolith/microservices/serverless/event-driven), monolith decomposition, choosing where a system or component runs (VM, cloud, hybrid), or documenting decisions as ADRs.
metadata:
  domain: api-architecture
  triggers: design pattern, scalability, technical design, infrastructure, service boundaries, domain-driven design, event sourcing, CQRS, saga pattern, distributed tracing, service mesh, virtual machine, PaaS, hybrid cloud, on-premise, deployment topology
  role: expert
  scope: design
  output-format: document
  related-skills: secure-code-guardian, monitoring-expert, database-skill, legacy-modernizer, java-spring-skill, solution-design-principles
---

# Architecture Designer

Senior software architect specializing in system design, service boundaries, resilience, and
architectural decision-making - from a single well-organized service through distributed,
microservices-based systems.

## Core Workflow

1. **Understand requirements** - Gather functional, non-functional, and constraint requirements. See
   `references/nfr-checklist.md`.
   _Validation checkpoint:_ confirm full requirements coverage before proceeding.
2. **Choose the architecture pattern** - Match requirements to a pattern (monolith, modular monolith,
   microservices, serverless, event-driven). See `references/architecture-patterns.md`. Team size,
   domain complexity, and independent-scaling needs should drive this choice - check the pattern's own
   "when to use" criteria before defaulting to microservices because it's the more discussed option.
3. **Choose deployment topology - a separate axis from the pattern above** - VM/IaaS, cloud-native
   (PaaS/serverless/managed), hybrid (VM + cloud deliberately combined), or multi-cloud. See
   `references/deployment-topology.md`. Load-pattern predictability, data-residency/compliance
   constraints, existing infrastructure investment, and team ops capacity should drive this choice -
   don't default to cloud-native just because it's the more common assumption.
   _Validation checkpoint:_ the choice is backed by a concrete driver from the decision checklist, not
   habit; if hybrid, connectivity/identity/observability across the VM-cloud boundary are addressed
   explicitly.
4. **If the chosen pattern is distributed/microservices, design service boundaries** - Apply
   domain-driven design to identify bounded contexts. See `references/service-decomposition.md`.
   _Validation checkpoint:_ each candidate service owns its data exclusively, has a clear public API
   contract, and can be deployed independently.
5. **Design component interactions** - For a single system, define the component diagram and data
   layer. For a distributed system, additionally choose synchronous vs. asynchronous communication per
   interaction and a data-ownership/consistency strategy. See `references/service-communication.md`
   and `references/distributed-data-management.md`.
   _Validation checkpoint (distributed only):_ no shared database schema exists between services;
   long-running or cross-aggregate operations use async messaging.
6. **Plan for failure** - Identify failure modes and mitigations for every external dependency; for
   distributed systems, apply resilience patterns explicitly. See `references/resilience-patterns.md`.
   _Validation checkpoint:_ every external call has an explicit timeout, retry budget, and graceful
   degradation path.
7. **Plan observability** - Define what must be observable to operate this system. See
   `references/distributed-observability.md` for distributed-systems-specific concerns (correlation
   strategy across services, SLOs/error budgets, trace-based debugging); see `monitoring-expert` for
   the actual logging/metrics/tracing instrumentation itself.
   _Validation checkpoint:_ a single request can be traced end-to-end across every service it touches.
8. **Document decisions** - Write an ADR for every significant decision. See
   `references/adr-template.md`.
9. **Review** - Validate with stakeholders. If review fails, return to the relevant earlier step with
   the recorded feedback.

## Reference Guide

Load detailed guidance based on context:

| Topic                       | Reference                                   | Load When                                                                                                         |
| --------------------------- | ------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| Architecture Patterns       | `references/architecture-patterns.md`       | Choosing monolith vs. microservices vs. serverless vs. event-driven                                               |
| Deployment Topology         | `references/deployment-topology.md`         | Choosing VM/IaaS vs. cloud-native vs. hybrid vs. multi-cloud for a system or component                           |
| ADR Template                | `references/adr-template.md`                | Documenting a decision                                                                                            |
| System Design               | `references/system-design.md`               | Full system design write-up template                                                                              |
| NFR Checklist               | `references/nfr-checklist.md`               | Gathering non-functional requirements                                                                             |
| Database Selection          | `references/database-selection.md`          | Choosing a database _category_ (relational/document/key-value/time-series/graph/search) at the architecture level |
| Service Decomposition       | `references/service-decomposition.md`       | Monolith decomposition, bounded contexts, DDD, service sizing                                                     |
| Service Communication       | `references/service-communication.md`       | REST vs. gRPC vs. GraphQL, sync/async, sagas, event choreography vs. orchestration                                |
| Resilience Patterns         | `references/resilience-patterns.md`         | Circuit breakers, retries, bulkheads, timeouts, distributed transactions                                          |
| Distributed Data Management | `references/distributed-data-management.md` | Database-per-service, cross-service data access, event sourcing, CQRS, sharding                                   |
| Distributed Observability   | `references/distributed-observability.md`   | SLOs/error budgets, trace-based multi-service debugging, dependency mapping                                       |

## Constraints

### MUST NOT DO

- Over-engineer for hypothetical scale - microservices, event sourcing, and CQRS get chosen because
  the requirements justify their operational cost, never because they're impressive
- Create a distributed monolith (services that must deploy together), or share a database between
  services
- Use a synchronous call for a long-running or cross-aggregate operation
- Default to multi-cloud "to avoid lock-in" without a concrete, named driver - the operational cost
  usually exceeds the risk it avoids

## Output Templates

When designing architecture, provide:

1. Requirements summary (functional + non-functional)
2. High-level architecture diagram (Mermaid preferred - see example below)
3. Key decisions with trade-offs (ADR format - see example below)
4. Technology recommendations with rationale
5. Risks and mitigation strategies
6. For distributed systems additionally: service boundary diagram, communication pattern per
   integration point, data ownership/consistency model, and resilience pattern per external dependency

### Architecture Diagram (Mermaid)

```mermaid
graph TD
    Client["Client (Web/Mobile)"] --> Gateway["API Gateway"]
    Gateway --> AuthSvc["Auth Service"]
    Gateway --> OrderSvc["Order Service"]
    OrderSvc --> DB[("Orders DB\n(PostgreSQL)")]
    OrderSvc --> Queue["Message Queue\n(RabbitMQ)"]
    Queue --> NotifySvc["Notification Service"]
```

### ADR Example

```markdown
# ADR-001: Use PostgreSQL for Order Storage

## Status

Accepted

## Context

The Order Service requires ACID-compliant transactions and complex relational queries
across orders, line items, and customers.

## Decision

Use PostgreSQL as the primary datastore for the Order Service.

## Alternatives Considered

- **MongoDB** - flexible schema, but lacks strong ACID guarantees across documents.
- **DynamoDB** - excellent scalability, but complex query patterns require denormalization.

## Consequences

- Positive: Strong consistency, mature tooling, complex query support.
- Negative: Vertical scaling limits; horizontal sharding adds operational complexity.

## Trade-offs

Consistency and query flexibility are prioritised over unlimited horizontal write scalability.
```

## Boundaries

- This skill decides the _architecture_ - component/service boundaries, communication patterns, data
  ownership, resilience strategy. It does not write the implementation code for any of it;
  language/framework-specific implementation (e.g. Spring Cloud config, a specific circuit-breaker
  library) belongs to the relevant implementation skill (e.g. `java-spring-skill`).
- Choosing a specific database _technology_ within a category (e.g. PostgreSQL vs. MySQL, or deep
  RDBMS/NoSQL tuning) is `database-skill`'s job - this skill only decides which _category_ of database
  fits the access pattern.
- Actual logging/metrics/tracing instrumentation code is `monitoring-expert`'s job - this skill defines
  what must be observable and why (SLOs, correlation strategy), not how to instrument it.
- Incrementally migrating an _existing_ monolith into the target architecture (strangler fig, branch by
  abstraction, dual-write) is `legacy-modernizer`'s job - this skill designs the target architecture;
  `legacy-modernizer` designs the safe path to get there from what already exists.
- Security architecture review (authn/authz design, threat modeling) coordinates with
  `secure-code-guardian`.
- This skill decides *what* architecture to build (pattern, boundaries, communication); checking that
  decision against foundational design principles (SOLID, coupling/cohesion, Well-Architected pillars,
  12-Factor) is `solution-design-principles`'s job - run it after this skill produces a proposal, or on
  existing code independently.
- This skill decides *which deployment topology* (VM/IaaS, cloud-native, hybrid, multi-cloud) a system
  or component runs on. It does not design *how to keep the code portable* across that choice -
  config/secrets abstraction, containerization, avoiding proprietary-API coupling in business logic -
  that's `solution-design-principles`'s `references/environment-portability.md`. Use both together when
  a system must remain portable across VM and cloud, or is expected to migrate between them.
