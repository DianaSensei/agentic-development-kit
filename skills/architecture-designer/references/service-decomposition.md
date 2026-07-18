# Service Decomposition and Boundaries

Guide for identifying service boundaries using domain-driven design principles. For the mechanics of
*incrementally migrating* an existing monolith toward these boundaries (strangler fig, phased
extraction, parallel-run/shadow testing), see `legacy-modernizer` instead — this file is about
designing the target boundaries, not the migration path to get there.

## Domain-Driven Design Foundation

### Bounded Context Identification

**Strategic Patterns:**
- **Ubiquitous Language** - Each bounded context has its own domain language
- **Context Mapping** - Define relationships between bounded contexts
- **Subdomain Classification** - Core, supporting, generic domains

**Bounded Context Indicators:**
```
Strong Indicators:
- Different teams own different parts
- Different release cadences needed
- Different scalability requirements
- Different technology stacks optimal
- Clear domain model boundaries

Warning Signs:
- Entities mean different things in different contexts
- Same term used with different meanings
- Workflows cross multiple aggregates
- Teams communicate frequently about shared data
```

### Service Boundary Patterns

**Database-Driven Decomposition:**
```
1. Identify aggregates (entities with invariants)
2. Each aggregate becomes a service candidate
3. Group related aggregates by transaction boundaries
4. Services own their data (no shared databases)
```

**Business Capability Decomposition:**
```
Services organized by:
- User Management (authentication, profiles, permissions)
- Order Management (cart, checkout, fulfillment)
- Inventory Management (stock, warehousing, allocation)
- Payment Processing (transactions, refunds, reconciliation)
- Notification Service (email, SMS, push notifications)
```

## Service Sizing Guidelines

### Microservice Characteristics

**Right-Sized Service:**
```
Team Metrics:
- 2-pizza team can own it (5-9 people)
- Single team has full ownership
- Can be rewritten in 2-4 weeks if needed
- Independent deployment pipeline

Technical Metrics:
- 100-1000 lines of business logic
- 5-15 API endpoints
- 1-5 database tables
- Startup time < 30 seconds
- Single responsibility focus
```

**Too Small (Nano-service):**
```
Warning Signs:
- Services with 1-2 endpoints
- Excessive network overhead
- More infrastructure than business logic
- Difficult to trace requests
- Version coupling between services
```

**Too Large (Distributed Monolith):**
```
Warning Signs:
- Multiple teams working on same service
- Conflicting scalability requirements
- Difficult to understand in one sitting
- Long deployment times
- Tight coupling with other services
```

## Conway's Law Alignment

### Team Structure and Service Design

**Team Topologies:**
```
Stream-Aligned Teams:
- Own end-to-end service lifecycle
- Aligned to business capabilities
- Full-stack ownership (frontend to database)

Platform Teams:
- Provide self-service capabilities
- Enable stream-aligned teams
- Kubernetes, CI/CD, observability

Enabling Teams:
- Help with complex implementations
- Service mesh setup, security patterns
- Temporary coaching role

Complicated Subsystem Teams:
- Specialized domains (ML, search, payments)
- Heavy technical expertise required
- Clear interfaces to other teams
```

## Decomposition Checklist

### Pre-Decomposition Analysis

**Business Justification:**
```
Check:
- Independent scalability needed?
- Different teams responsible?
- Isolated failure acceptable?
- Frequent independent deployments?
- Technology diversity required?

If mostly "no" → Consider modular monolith first
```

**Technical Readiness:**
```
Prerequisites:
✓ CI/CD pipelines automated
✓ Monitoring and alerting in place
✓ Distributed tracing capability
✓ Container orchestration ready
✓ Team has microservices experience
✓ Clear service ownership model
```

### Decomposition Steps

**1. Identify Bounded Contexts:**
```
Activities:
- Event storming workshop
- Identify aggregates and entities
- Map business workflows
- Document ubiquitous language
- Draw context boundaries
```

**2. Define Service Contracts:**
```
For each service:
- REST/gRPC API specification
- Event schema definitions
- Data ownership boundaries
- SLA commitments (latency, availability)
- Versioning strategy
```

**3. Plan Data Migration:**
```
Data Strategy:
- Identify shared data
- Choose consistency model (eventual vs strong)
- Design data synchronization mechanism
- Plan schema evolution
- Test rollback scenarios
```

**4. Extract Service — target end-state per service:**
```
1. New service skeleton with its own database
2. Business logic implemented
3. Observability in place (logs, metrics, traces)
4. Deployed to staging, then production

For the actual step-by-step extraction sequence from a live monolith (dual-write, traffic
shifting, decommissioning the old code path safely) — see `legacy-modernizer`'s strangler-fig-pattern
and migration-strategies references, which cover this in full depth including rollback mechanics.
```

## Anti-Patterns to Avoid

### Common Mistakes

**Distributed Monolith:**
```
Symptoms:
- Services must deploy together
- Shared database between services
- Synchronous coupling everywhere
- Version lock-step required
- Cascading failures common

Solution:
- Enforce database per service
- Use async communication
- Version APIs independently
- Add circuit breakers
```

**Entity Services:**
```
Anti-Pattern:
UserService (CRUD on User entity)
OrderService (CRUD on Order entity)
ProductService (CRUD on Product entity)

Problem: Anemic domain model, no business logic

Better Approach:
AccountManagement (authentication, authorization, profiles)
OrderFulfillment (workflow: cart → payment → shipping)
ProductCatalog (search, recommendations, inventory)
```

**Shared Libraries with Business Logic:**
```
Anti-Pattern:
common-lib (shared across all services with domain logic)

Problem:
- Tight coupling via dependency
- Forces synchronized deployments
- Violates service autonomy

Better:
- Shared libraries for technical concerns only
- Duplicate business logic per service
- Use events to keep data synchronized
```

## Service Boundary Validation

### Design Review Checklist

**Service Independence:**
```
Questions:
- Can this service be deployed independently?
- Does it own its data completely?
- Can it function if dependencies are down?
- Is the team autonomous to make changes?
- Are integration points well-defined?
```

**Data Ownership:**
```
Verify:
- No shared database tables
- Clear data ownership boundaries
- Event-driven synchronization for shared concepts
- API provides all necessary data
- No direct database access from other services
```

**Operational Readiness:**
```
Check:
- Health check endpoint implemented
- Readiness probe configured
- Circuit breakers for external calls
- Distributed tracing instrumented
- Logs structured with correlation IDs
- Metrics exposed (Prometheus format)
- Documentation up to date
```

## Summary

Service decomposition is both art and science. Start with domain-driven design to identify natural boundaries, align with team structure, and extract incrementally. Avoid the temptation to over-decompose. A modular monolith is better than a poorly designed distributed system.

**Key Takeaways:**
- Bounded contexts define service boundaries
- Database per service is non-negotiable
- Team autonomy drives service design
- Extract incrementally (see `legacy-modernizer` for how), not all at once
- Observability is prerequisite for microservices
