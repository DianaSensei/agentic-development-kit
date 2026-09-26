# Project Structure: Package-by-Layer, Package-by-Feature, and Modular Monolith

How to organize a Spring Boot codebase so that day-to-day complexity (finding code, changing one
feature without touching five folders) stays low while the system remains clean, extensible, and safe
from bugs caused by leaking implementation detail across boundaries. This file covers *in-service*
package structure. For deciding *whether to split into multiple services* in the first place, see
`architecture-designer`'s `service-decomposition.md` - the identification technique below is the same
DDD approach, applied at a coarser, cheaper-to-get-wrong granularity than a microservice boundary.

**Governing principle: KISS first, in every case.** Every choice in this file - package-by-layer vs.
feature, flat module vs. internal hexagonal layering, Modulith enforcement, sync vs. event transaction -
has a simplest default and a more elaborate option. Start from the simplest structure that correctly
fits the system *today*. Add a more complex option only when a concrete, already-observed symptom
demands it (named explicitly in each section below as "move up when..."), never speculatively because
the system *might* grow. When genuinely unsure which level fits, pick the simpler one - the cost of
moving from simple to more structured later is a local refactor; the cost of unwinding premature
structure is convincing a team to give up ceremony they've already built habits around.

## Package-by-Layer vs. Package-by-Feature

**Quick test**: can you tell what the application *does* from its top-level package names alone?
`order/`, `payment/`, `inventory/` - yes, feature-oriented. `controller/`, `service/`, `repository/`,
`dto/` - no, you have to open `service/` to find out - layer-oriented.

| | Package-by-Layer | Package-by-Feature |
| --- | --- | --- |
| **Structure** | `controller/`, `service/`, `repository/`, `dto/`, `model/` at the top | `order/`, `payment/`, `inventory/` at the top, each containing its own slice |
| **Good for** | Small app (< ~10-15 endpoints), one small team, mostly CRUD | Multiple distinct business capabilities, growing/parallel teams, long-lived codebase |
| **Failure mode when outgrown** | "Shotgun surgery" - one feature change touches many top-level folders | If done naively (flat bag per feature, no internal discipline) loses layering inside each feature |

**Default**: start with package-by-layer for a genuinely small service; move to package-by-feature once
2-3 of these symptoms show up - this is YAGNI applied to directory structure, not a decision to guess
perfectly on day one:
- A single feature change routinely touches 4-5 top-level layer folders.
- More than one person/team works on clearly distinct business areas in the same codebase.
- You can already name the domain nouns (Order, Payment, Inventory...) without hesitation, and they each
  have their own lifecycle/state.

## Identifying Feature/Module Boundaries

Same underlying method as DDD bounded-context identification (`service-decomposition.md`), calibrated
for module (not microservice) granularity - getting a package boundary slightly wrong costs a
refactor, not a network/deployment boundary, so start coarser than you would for a service split.

1. **Ubiquitous language** - list the domain nouns stakeholders repeat: Order, Customer, Payment,
   Shipment, Inventory. Each with its own lifecycle/invariants is a module candidate.
2. **Use-case clustering, not entity wrapping** - list actual use cases ("place order," "reserve
   inventory," "process payment") and group the ones that act on the same core data. This is event
   storming in miniature: cluster commands/events by which aggregate they touch.

   **Avoid the Entity Service anti-pattern** - one module per database table, with no real business
   logic:
   ```
   Weak:   UserService, OrderService, ProductService        - anemic, CRUD-only
   Better: AccountManagement (auth, profile, permissions)
           OrderFulfillment  (cart → payment → shipping, one workflow)
           ProductCatalog    (search, recommendations, inventory)
   ```
   A module with zero business rules to protect usually doesn't deserve its own top-level package -
   fold it into a related module or a shared reference-data package.
3. **Data ownership test** - for each table, ask "which module is the single source of truth?" Two
   features both needing to write the same table for their own core logic is a sign they're either the
   same module, or the ownership split needs to be explicit (one owns writes, the other reads only
   through the owner's public API).
4. **Public API surface test** - list the operations another module would actually need to call
   (`InventoryService.reserve()`, `.release()`). A small, business-named set means the boundary is
   right. Needing dozens of fine-grained getters/setters to make it work means the split is either too
   fine-grained or the relationship between the two wasn't understood yet.
5. **Co-change analysis** (for retrofitting structure onto an existing codebase) - files that change
   together in the same commits are probably the same feature, even if scattered across layer folders
   today; files sharing a folder that never change together are split candidates.

## The Pragmatic Middle: Feature Packages with Selective Internal Layering

Full hexagonal/clean architecture (separate domain/application/infrastructure packages) inside *every*
feature is real overhead - mapper explosion between domain/JPA/DTO, interfaces for things that never
vary. Reserve it for the module(s) with genuine domain complexity or volatile external dependencies;
let simple CRUD modules stay flat. **Default every module to flat until it hurts** - move a specific
module to internal layering only when it actually shows real business rules that need protecting from
framework/persistence detail, or a dependency (payment gateway, external API) that's genuinely likely to
change - not because "the other module has it" or as a precaution.

```
src/main/java/com/example/
├── order/                          # simple-ish module - flat is fine
│   ├── OrderController.java
│   ├── OrderService.java           # business logic lives here
│   ├── OrderRepository.java        # interface - order's own port
│   ├── OrderJpaRepository.java     # adapter - JPA detail, not exposed outward
│   ├── Order.java                  # entity doubles as domain model - no real invariants to hide yet
│   └── dto/
├── payment/                        # real domain complexity + external gateway → full layering earns its cost
│   ├── domain/                     # no Spring/JPA imports here
│   ├── application/
│   └── adapter/{web,persistence,external}/
├── inventory/
└── shared/                         # cross-cutting only (error types, base config) - keep this small
```

**MUST NOT**: reach directly into another module's `Repository`/`Entity` to "just update it quickly."
This is the exact implementation-detail leak this skill exists to prevent, and it defeats the module
boundary as thoroughly as a shared database defeats a microservice boundary - go through the owning
module's public service instead (see below on transactions).

## Enforcing Boundaries Without Splitting into Multiple Maven Modules

Discipline alone rots as a team grows. **Spring Modulith** gives most of the benefit of a "modular
monolith" without forcing multi-module Maven/Gradle builds or full hexagonal ceremony everywhere:

- Mark a module's public surface with `@NamedInterface`; everything else in the package is private by
  default.
- `ApplicationModules.verify()` runs as a test - CI fails automatically if a module reaches into
  another module's internals, or if a dependency cycle exists between modules.

This turns boundary discipline into something CI enforces, not something code review has to catch by
inspection. **Move up to this only when package-by-feature alone has already been outgrown** - a small
service with a handful of modules and no cross-team friction doesn't need `ApplicationModules.verify()`
wired in yet; adding it is cheap to defer and cheap to add later, so don't pay the setup cost before a
real boundary violation has actually happened.

## Transactions Across Module Boundaries

The system is still one database, one JVM - real ACID `@Transactional` still works across modules; the
problem is getting that consistency *without* reaching into another module's repository. Two patterns:

### Pattern A - Synchronous, same transaction (strong consistency)

Use when both modules' state MUST change together atomically. Call the other module's **public
service** (not its repository) from inside one `@Transactional` method - default propagation
(`REQUIRED`) joins the existing transaction, one commit/rollback for both.

```java
@Service
public class OrderService {
    private final InventoryService inventoryService; // public API of another module
    private final OrderRepository orderRepository;    // this module's own repo

    @Transactional
    public Order placeOrder(PlaceOrderCommand cmd) {
        inventoryService.reserve(cmd.items()); // joins the same transaction
        return orderRepository.save(Order.from(cmd));
    }
}
```

Watch for the self-invocation/proxy pitfall (see this skill's "Common Real-World Issues"): the call
must go through the real Spring-managed bean, not `this.xxx()`.

### Pattern B - Event-driven (eventual consistency)

Use when strict atomicity isn't required (send a notification, write an audit log, update a read
model). `@ApplicationModuleListener` (Spring Modulith's shortcut for `@Async` +
`@TransactionalEventListener(phase = AFTER_COMMIT)`) runs the listener only after the publisher's
transaction has actually committed.

```java
// publisher, inside its own transaction
orderRepository.save(order);
events.publishEvent(new OrderPlaced(order.getId()));

// listener, in a different module - runs only after Order's transaction commits
@ApplicationModuleListener
void on(OrderPlaced event) { ... }
```

Spring Modulith persists the event in an `event_publication` table as part of the *same* transaction as
the publisher's own change - a Transactional Outbox pattern with no extra code. If the listener fails
or the app crashes, the un-completed log entry is retried on restart; no event is silently lost. This is
also exactly the shape needed if the module is later extracted to its own service - only the event
transport changes (in-process → Kafka/RabbitMQ), not the domain events themselves.

### Choosing Between Them

| Situation | Pattern |
| --- | --- |
| Both modules must succeed or roll back together | A - synchronous, shared `@Transactional` |
| A short delay / eventual consistency is acceptable | B - `@ApplicationModuleListener`, free outbox |
| Module is a near-term candidate for microservice extraction | Design with events now (B), even while still in-process |
| Multi-step flow, possibly with an external call in between | Neither as one giant transaction - model as a local saga/process manager, one short transaction per step plus a compensating action if a later step fails |

**Default to Pattern A** (a direct synchronous call in one transaction) unless there's a concrete reason
for eventual consistency - it's fewer moving parts, easier to reason about, and easier to debug than an
event chain. Reach for Pattern B only when the decoupling or the outbox's failure-safety is a real,
present need, not because event-driven "feels more scalable."

Never hold one `@Transactional` open across a call to an external system (HTTP, message broker) - that
holds a DB connection/locks for the duration of a slow, unreliable call. Database-only work inside the
transaction; everything else is a separate step.

## Scaling the Structure With the System

| Scale | Structure |
| --- | --- |
| Small (< 10 endpoints, one team) | Flat package-by-layer |
| Growing (multiple features, team expanding) | Package-by-feature, light internal layering only where a module's domain is genuinely complex |
| Large (clear bounded contexts, multiple teams) | Package-by-feature as Spring Modulith modules with `@NamedInterface`/`ApplicationModules.verify()` enforcing boundaries; hexagonal layering only for the modules that need it |
| Preparing to extract a service | The Modulith module boundary *is* the future service boundary - extraction becomes repackaging, not redesign |
