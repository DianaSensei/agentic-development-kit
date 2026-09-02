# Data Access - Spring Data JPA

Jump to the section matching the task - the file is long, and most tasks need only one or two sections.

| Section | Covers |
| --- | --- |
| [Design Criteria](#design-criteria--reuse-vs-performance) | Reuse vs. performance: method boundaries, fetch shape for writes, entity lifecycle, cascade/aggregate boundary |
| [Entity](#entity-index-cache-batch-fetch-optimistic-lock) | Mapping, indexes, `@BatchSize`, `@Version` |
| [Repository](#repository--n1-prevention-projection-bulk-update) | `@EntityGraph`/`JOIN FETCH`, DTO projection, pagination, `@Modifying` |
| [Dynamic Query - Specifications](#dynamic-query--specifications) | Many optional filter conditions |
| [Filtering a Lazy Collection](#filtering-a-lazy-collection-without-loading-everything-aggregate-root-readwrite-split) | Filtering `@OneToMany`/`@ManyToMany` without loading it all; the `JOIN FETCH` + `WHERE` trap |
| [Bulk Update as Atomic Invariant](#bulk-update-as-atomic-invariant-enforcement) | `UPDATE ... WHERE` for race-safe check-and-mutate, and its four silent risks |
| [Editing One Child](#editing-one-child-without-loading-the-whole-aggregate) | Mutating one nested entity; delta updates; deeply nested relationships |
| [Concurrency Across Instances](#concurrency-across-multiple-instances) | Optimistic/pessimistic locking, DB constraints, distributed locks |
| [Transaction Management](#transaction-management) | Propagation, `REQUIRES_NEW`, `noRollbackFor` |
| [Batch Insert/Update](#batch-insertupdate-bulk-without-accumulating-in-the-hibernate-first-level-cache) | Large-volume writes without OOM |
| [Performance Tips](#performance-tips) | Query-count assertions, batching, projections |
| [Auditing](#auditing-automatic-createdbyupdatedby) · [Migration](#database-migration-flyway) · [Quick Reference](#quick-reference) | Audit fields, Flyway, pattern cheat-sheet |

## Design Criteria - Reuse vs. Performance

Apply before writing repository/service methods on any entity with multiple callers. Rule of thumb: **reuse small, single-purpose building blocks (Specification, projection, one fetch method per use case) - never reuse one method by adding flags/eager-loading "to be safe."**

### 1. Method boundary - one method, one intent

| Layer | Reuse via | Never do |
|---|---|---|
| Repository | Fine-grained query methods, `Specification` composition | One method with `boolean loadEverything`/similar flags |
| Service | Compose small repo calls per use case (`getSummary`, `getDetail`, `loadForCancel`) | One "God" method serving list + detail + edit with different needs |
| Controller/API | DTO per response shape, mapped explicitly | Returning `@Entity` straight out as API response |

Only merge two fetch methods into one when **≥80% of callers need the exact same shape**; otherwise keep them separate - a `JOIN FETCH`/`@EntityGraph` is cheap to duplicate, over-fetching in the other callers is not.

The "never do" column is the JPA-specific form of a general anti-pattern - see `solution-design-principles`'s "The Reuse Trap" for the symptom checklist that catches it before it accretes, and the way back out once it has.

### 2. Fetch shape for writes - managed vs. read-only

| Need | Fetch as |
|---|---|
| Will be mutated (set field) in this transaction | Managed entity via `@EntityGraph`/`JOIN FETCH` scoped to **this specific write use case only** |
| Read only to decide/validate (credit limit, policy check, another aggregate's state) | Lightweight projection/native query - do NOT join into the entity graph you're about to save |
| Cross-aggregate data needed inside a write transaction | Fetch each aggregate independently in the service method; do not widen one entity's `@EntityGraph` to cover another aggregate's needs |

If one write use case is repeatedly forced to pull in unrelated aggregates just to decide something → aggregate boundary is likely wrong (see §4), not a fetch-method problem.

### 3. Entity lifecycle & conflict handling

| State | How it got there | Save needed? |
|---|---|---|
| Transient | `new Entity()`, no id yet | `save()`/`persist()` - required |
| Managed | Loaded via `findById`/query inside an open `@Transactional` | None - dirty checking flushes on commit |
| Detached | Persistence context closed (previous transaction/request ended), or entity mapped from an incoming DTO that carries an id | `save()`/`merge()` required - **and the entity MUST carry `@Version`**, or conflicting concurrent writes fail silently (lost update) |
| Removed | `remove()`/`deleteById()` called | Flushed as `DELETE` on commit |

- Never let a managed entity leak across a transaction boundary (return it from a `@Transactional` method, then mutate it later expecting persistence - it's a silent no-op once detached).
- Any entity mutable from more than one request/thread needs `@Version` from day one, not added reactively after a lost-update bug.
- Default every read-only method to `@Transactional(readOnly = true)` - it also suppresses accidental flush-writes from a stray mutation inside a "read" call.

### 4. Cascade & aggregate boundary

- Cascade only **within** a true aggregate (parent fully owns the child's lifecycle, e.g. `Order` → `OrderItem`): `PERSIST, MERGE, REMOVE` (+ `orphanRemoval = true` if the child cannot exist without the parent).
- Never cascade **across** independent aggregates (e.g. `Order` → `Customer`, `Order` → `Payment`) - no `cascade` attribute at all; mutate the other aggregate through its own repository/service call.
- Don't default new relationships to `CascadeType.ALL` - pick cascade types deliberately per relationship, based on "does this child have a lifecycle independent of the parent?"
- Remember dirty checking follows the whole managed graph, not just the entity you called `save()` on - touching a field on `order.getCustomer()` inside the same transaction writes `Customer` too, with no `save()` call anywhere in sight. Keep fetched graphs narrow (§2) so there's nothing unrelated to accidentally mutate.
- Verification: assert the exact SQL/query count in tests (see Performance Tips below) - an unexpected `UPDATE`/`INSERT` on an associated entity in a "read" test is the fastest way to catch a cascade/dirty-checking leak.

For mutating a child once the boundary is settled - without loading the parent's whole collection to do it - see "Editing One Child Without Loading the Whole Aggregate" below.

## Entity (index, cache, batch fetch, optimistic lock)

```java
@Entity
@Table(name = "users", indexes = {
    @Index(name = "idx_email", columnList = "email", unique = true),
    @Index(name = "idx_created_at", columnList = "created_at")
})
@EntityListeners(AuditingEntityListener.class)
@Cache(usage = CacheConcurrencyStrategy.READ_WRITE)
@Getter @Setter @NoArgsConstructor @AllArgsConstructor @Builder
public class User {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, unique = true, length = 100)
    private String email;

    @Column(nullable = false)
    @Builder.Default
    private Boolean active = true;

    @OneToMany(mappedBy = "user", cascade = CascadeType.ALL, orphanRemoval = true, fetch = FetchType.LAZY)
    @BatchSize(size = 25)
    @Builder.Default
    private List<Order> orders = new ArrayList<>();

    @ManyToMany
    @JoinTable(name = "user_roles", joinColumns = @JoinColumn(name = "user_id"), inverseJoinColumns = @JoinColumn(name = "role_id"))
    @Builder.Default
    private Set<Role> roles = new HashSet<>();

    @CreatedDate @Column(nullable = false, updatable = false)
    private Instant createdAt;

    @LastModifiedDate
    private Instant updatedAt;

    @Version
    private Long version;

    public void addOrder(Order order) { orders.add(order); order.setUser(this); }
    public void removeOrder(Order order) { orders.remove(order); order.setUser(null); }
}
```

## Repository - N+1 prevention, projection, bulk update

```java
public interface UserRepository extends JpaRepository<User, Long>, JpaSpecificationExecutor<User> {

    // N+1 prevention: EntityGraph
    @EntityGraph(attributePaths = {"orders", "roles"})
    @Query("SELECT u FROM User u WHERE u.id = :id")
    Optional<User> findByIdWithAssociations(@Param("id") Long id);

    // N+1 prevention: JOIN FETCH
    @Query("SELECT DISTINCT u FROM User u LEFT JOIN FETCH u.orders WHERE u.department.id = :deptId")
    List<User> findByDepartmentWithOrders(@Param("deptId") Long deptId);

    // Projection - fetch only the fields needed, without loading the whole entity
    @Query("""
        SELECT new com.example.dto.UserSummary(u.id, u.email, u.username, COUNT(o))
        FROM User u LEFT JOIN u.orders o WHERE u.active = true GROUP BY u.id, u.email, u.username
        """)
    List<UserSummary> findActiveUsersSummary();

    // Pagination - avoid a full-table count query when exact accuracy isn't needed
    @Query(value = "SELECT u FROM User u WHERE u.active = true", countQuery = "SELECT COUNT(u) FROM User u WHERE u.active = true")
    Page<User> findActiveUsers(Pageable pageable);

    @Modifying
    @Query("UPDATE User u SET u.active = false WHERE u.createdAt < :date")
    int deactivateOldUsers(@Param("date") Instant date);
}
```

`@EntityGraph`/`JOIN FETCH` are two different ways of solving N+1 - `@EntityGraph` is declared on the repository without rewriting the JPQL; `JOIN FETCH` is more flexible when the query is already complex. Pick one according to the project's existing convention - don't mix them arbitrarily within the same codebase.

## Dynamic Query - Specifications

Use this when the filter is a combination of many optional conditions (a multi-field search form) - avoiding an explosion of `findByXAndY...` method combinations.

```java
public class UserSpecifications {
    public static Specification<User> hasEmail(String email) {
        return (root, query, cb) -> email == null ? null : cb.equal(root.get("email"), email);
    }
    public static Specification<User> isActive() {
        return (root, query, cb) -> cb.isTrue(root.get("active"));
    }
    public static Specification<User> createdAfter(Instant date) {
        return (root, query, cb) -> date == null ? null : cb.greaterThanOrEqualTo(root.get("createdAt"), date);
    }
}

// Usage
Specification<User> spec = Specification
    .where(UserSpecifications.hasEmail(criteria.email()))
    .and(UserSpecifications.isActive())
    .and(UserSpecifications.createdAfter(criteria.createdAfter()));
Page<User> result = userRepository.findAll(spec, pageable);
```

## Filtering a Lazy Collection Without Loading Everything (Aggregate Root Read/Write Split)

`@OneToMany(fetch = LAZY)` has exactly one mode: all-or-nothing. Calling `order.getItems()` issues one
SELECT for the *entire* collection by FK - there is no ORM-level "lazy but filtered" access. Filtering
after calling the getter always means loading everything into memory first, then filtering in Java -
wasteful for a large collection, and a real N+1/memory risk when it happens per-parent across a list.

**The rule that resolves it**: mutation whose invariant spans the aggregate goes through the aggregate
root's own methods (needs the whole object, needs invariant/cascade enforcement); reads/filters go
through a dedicated repository query returning a **DTO projection**, never through the entity's own
mapped collection field. This also follows `solution-design-principles`'s "Encapsulate Invariants, Not
Cost" - a filtered read is exactly the case where hiding cost behind `order.getItems()` does the most
damage.

Note the qualifier on the mutation half: editing a *single child* whose change touches no parent-level
invariant does not need the aggregate root loaded at all - see "Editing One Child Without Loading the
Whole Aggregate" below for how to tell the two cases apart and handle each.

```java
// Mutation - through the aggregate root, needs the whole object + invariant enforcement
public void addOrder(Order order) { orders.add(order); order.setUser(this); }

// Read/filter - dedicated query, DTO projection, DB does the filtering
@Query("""
    SELECT new com.example.dto.OrderItemSummary(i.id, i.status, i.quantity)
    FROM OrderItem i WHERE i.order.id = :orderId AND i.status = :status
    """)
List<OrderItemSummary> findByOrderIdAndStatus(@Param("orderId") Long orderId, @Param("status") ItemStatus status);
```

**A specific trap to avoid - `JOIN FETCH` combined with a `WHERE` on the child**:

```java
// DANGEROUS - looks like it prevents N+1, actually creates a silent bug
@Query("SELECT o FROM Order o JOIN FETCH o.items i WHERE o.id = :id AND i.status = :status")
Optional<Order> findWithFilteredItems(@Param("id") Long id, @Param("status") ItemStatus status);
```

This assigns the *filtered* result onto `order.items` and Hibernate marks that collection
**initialized**. If anything else in the same persistence context later calls `order.getItems()`
expecting the full list, Hibernate does **not** re-query - it silently returns the incomplete collection
already sitting on the entity. This is a genuine silent-inconsistency bug, and it comes specifically from
assigning a filtered result onto the entity's own mapped field - never do that; return the filtered
result as an independent DTO/list instead, as above.

## Bulk Update as Atomic Invariant Enforcement

A bulk `@Modifying` `UPDATE ... WHERE` does not bypass the aggregate root rule - it's a valid way to
*enforce the same invariant*, when that invariant reduces to a single-row precondition plus a mechanical
field change and needs true DB-level atomicity under concurrency (see `solution-design-principles`'s
Command-Query Separation & TOCTOU section - this is the JPA implementation of the atomic
check-and-reserve pattern described there). Keep the method inside the repository/service that owns the
invariant - the enforcement mechanism changed from Java to SQL, ownership did not.

```java
@Modifying(clearAutomatically = true, flushAutomatically = true)
@Query("""
    UPDATE Quota q SET q.used = q.used + :qty, q.version = q.version + 1
    WHERE q.id = :id AND q.used + :qty <= q.limit
    """)
int reserve(@Param("id") Long id, @Param("qty") int qty); // 0 rows affected = reservation failed
```

**Four risks specific to bulk update - all silent if missed**:

1. **Stale entities already in the persistence context**: if the same row is already loaded/managed in
   this transaction, a bulk update does **not** refresh it - the in-memory entity is now stale relative
   to the DB. `@Modifying(clearAutomatically = true)` clears the persistence context afterward so
   subsequent reads go back to the DB; `flushAutomatically = true` flushes pending changes first so
   nothing is silently overwritten out of order. Treat both as required, not optional, on any bulk
   update sharing a transaction with entity reads/writes.
2. **Lifecycle callbacks, auditing, and domain events are skipped**: `@PreUpdate`/`@LastModifiedDate`
   and any `@ApplicationModuleListener`-based domain event normally triggered by an entity mutation do
   **not** fire for a bulk JPQL/SQL update, since no entity is actually touched by Java code. If a
   listener elsewhere depends on this change, publish the event explicitly right after the bulk update
   succeeds, in the same service method/transaction.
3. **`@Version` does not auto-increment**: if the entity uses optimistic locking elsewhere, bump the
   version explicitly in the JPQL (as in the example above) - otherwise a bulk update silently breaks
   optimistic-lock protection for any other code path relying on it.
4. **No cascade**: a bulk update only touches the table named in the query. If the true invariant spans
   multiple related entities that must change together, that's a sign the invariant belongs to the
   "needs object-level reasoning" category - go through the aggregate root instead, don't try to chain
   multiple bulk updates to fake a cascade.

**Decision rule**: invariant reduces to one row + one WHERE condition + needs atomicity under
concurrency → bulk update, with the four safeguards above. Invariant needs multi-field/cross-entity logic
or cascade → aggregate root. Unsure → default to the aggregate root; only move to bulk update once the
invariant is confirmed to fit the narrow case.

## Editing One Child Without Loading the Whole Aggregate

Nesting depth (`Order → OrderItem → OrderItemAddon → ...`) matters less than identifying which
invariant a given edit actually implicates, then fetching only what that specific invariant needs - not
"the aggregate root pattern means loading the whole object graph."

**The cost asymmetry this relies on**: parent → collection navigation (`order.getItems()`) is expensive,
all-or-nothing (see above). Child → parent scalar navigation (`item.getOrder().getStatus()`) is cheap -
a single row fetched by primary key, which does **not** trigger the parent's own collections. Editing one
child efficiently means using the cheap direction and avoiding the expensive one.

**Default pattern - a scoped repository method on the child itself**:

```java
public interface OrderItemRepository extends JpaRepository<OrderItem, Long> {
    Optional<OrderItem> findByIdAndOrderId(Long itemId, Long orderId); // efficient single row + ownership check in one query
}
```

`findByIdAndOrderId` does two jobs in one query: an efficient single-row fetch, and confirming the item
actually belongs to the claimed order (guards against an IDOR-style bug - editing another order's item
via a guessable ID).

**Then branch on whether the edited field crosses an aggregate-level invariant**:

- **No cross-entity effect** (e.g. editing an item's `note`, with nothing at the `Order` level depending
  on it) - stop here. `item.setNote(...)`, dirty checking handles the UPDATE. This is not bypassing the
  aggregate root - the invariant genuinely belongs to `OrderItem` alone.
- **Crosses into a parent-level invariant** (e.g. `quantity` changing means `order.totalAmount` must
  change too) - enforce it, but with a **delta update**, never by reloading the full collection to
  recompute from scratch:

```java
@Transactional
public void updateItemQuantity(Long orderId, Long itemId, int newQty) {
    OrderItem item = orderItemRepository.findByIdAndOrderId(itemId, orderId).orElseThrow();
    if (item.getOrder().getStatus() != OrderStatus.DRAFT) { // cheap: single-row fetch by PK, not a collection load
        throw new IllegalStateException("Cannot edit item on non-draft order");
    }
    var delta = item.getUnitPrice().multiply(BigDecimal.valueOf(newQty - item.getQuantity()));
    item.setQuantity(newQty);
    orderRepository.adjustTotal(orderId, delta); // atomic UPDATE orders SET total = total + :delta WHERE id = :orderId
}
```

For an even cheaper precondition check, fold it into the fetch itself instead of a separate parent read -
`findByIdAndOrderIdAndOrderStatus(itemId, orderId, DRAFT)` returning empty when ineligible, the same
technique used for the quota reservation above.

**For 3+ levels of nesting, ask first whether it's genuinely one aggregate.** Per Vernon's "aggregates
should be small": if editing `OrderItemAddon` has no effect at the `Order` level, it isn't really part of
the same aggregate for that purpose - fetch and edit it directly
(`addonRepository.findByIdAndOrderItemId(...)`), without touching `OrderItem`'s or `Order`'s collections
at all. Only when an invariant genuinely spans every level (e.g. order total depends on both item
quantities and addon surcharges) does it need coordinating - and even then, propagate as a **delta at
each level** rather than reloading and recomputing the whole tree: an addon change adjusts its item's
subtotal atomically, which (directly, or via a published domain event - see
`references/project-structure.md`'s transaction patterns) adjusts the order's total atomically. Each
level owns and updates only its own invariant.

## Concurrency Across Multiple Instances

Running N application instances does not create a new class of problem - from the database's
perspective, two transactions from two different JVMs and two transactions from the same JVM are
identical; the DB serializes them the same way either way. The only thing that changes is which
concurrency-control mechanisms actually work: **anything enforced in DB stays correct across instances;
anything enforced in JVM memory does not.**

**The trap**: "fixing" a race condition with `synchronized`/`ReentrantLock`/an in-memory lock (see this
skill's "Common Real-World Issues" on singleton bean state) only protects within one JVM. It gives every
appearance of being fixed - passes locally, passes in a single-instance test environment - and silently
stops protecting anything the moment a second instance is deployed. Concurrency control for
shared/persisted data must live in the database (or a real distributed lock), never in JVM memory.

| Mechanism | When | How |
| --- | --- | --- |
| **Atomic `UPDATE ... WHERE`** | High contention (many instances hitting the same counter/quota) | See "Bulk Update as Atomic Invariant Enforcement" above - best throughput, one round trip, no lock held |
| **Optimistic locking (`@Version`)** | Low contention (rare conflicts) - user edits, admin forms | `@Version` field; Hibernate adds `WHERE version = ?` to every UPDATE; catch `ObjectOptimisticLockingFailureException` and retry the read-modify-write cycle, or surface "someone else updated this" to the user |
| **Pessimistic locking (`SELECT ... FOR UPDATE`)** | Must fully serialize access; short transaction; invariant too complex for one SQL statement | `@Lock(LockModeType.PESSIMISTIC_WRITE)` - other instances block on the row until the lock-holding transaction commits/rolls back; holds a DB connection for the duration, watch for deadlock if lock order isn't consistent across code paths |
| **DB constraint (`UNIQUE`/`CHECK`)** | Always, as a backstop for any invariant that must never be violated | Enforced unconditionally regardless of whether application logic has a bug - add this in addition to, never instead of, the mechanisms above for critical invariants |
| **Distributed lock (Redis/Redisson, ZooKeeper)** | The protected resource is outside any single DB transaction (an external API call, cross-service coordination) | See `redis-skill` - harder to get right than a DB transaction (lock-expiry-vs-still-running-critical-section, split-brain on failover); prefer a DB-level mechanism whenever the resource lives in the DB |

```java
// Optimistic - retry loop for low-contention edits
@Retryable(retryFor = ObjectOptimisticLockingFailureException.class, maxAttempts = 3)
@Transactional
public void updateProfile(Long userId, ProfileUpdate update) {
    var user = userRepository.findById(userId).orElseThrow();
    user.applyProfileUpdate(update); // aggregate root method, enforces invariants
    userRepository.save(user);       // throws on version mismatch - @Retryable re-runs the whole method
}

// Pessimistic - full serialization for a short, complex critical section
@Transactional
public void transferSeat(Long seatId, Long fromBookingId, Long toBookingId) {
    var seat = seatRepository.findByIdForUpdate(seatId); // blocks other instances until commit
    seat.reassign(fromBookingId, toBookingId);
}
```

**Note - this is a different problem from idempotency**: concurrency control protects against two
*different* operations racing on the same data; idempotency (an idempotency key on a mutating endpoint)
protects against the *same* logical request being executed twice (client retry, message redelivery).
Real systems usually need both together - e.g. an idempotency key guarding the endpoint, plus an atomic
`UPDATE ... WHERE` guarding the row itself.

## Transaction Management

```java
@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class OrderService {

    @Transactional
    public Order createOrder(OrderCreateRequest request) {
        // everything happens within a single transaction - a throw anywhere in this method rolls back all of it
        Order order = buildOrder(request);
        order = orderRepository.save(order);
        paymentService.processPayment(order); // throw → rolls back the order that was just saved too
        return order;
    }

    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public void logOrderEvent(Long orderId, String event) {
        // Separate transaction - still commits even if the parent transaction rolls back (used for audit logs that must not be lost)
        orderEventRepository.save(new OrderEvent(orderId, event));
    }

    @Transactional(noRollbackFor = NotificationException.class)
    public void completeOrder(Long orderId) {
        // A failure sending the notification shouldn't roll back an order that already completed successfully
        Order order = orderRepository.findById(orderId).orElseThrow();
        order.setStatus(OrderStatus.COMPLETED);
        orderRepository.save(order);
        notificationService.sendCompletionEmail(order); // this exception type doesn't trigger a rollback
    }
}
```

## Batch Insert/Update (bulk, without accumulating in the Hibernate first-level cache)

```java
@Transactional
public void batchInsert(List<User> users) {
    int batchSize = 50;
    for (int i = 0; i < users.size(); i++) {
        entityManager.persist(users.get(i));
        if (i % batchSize == 0 && i > 0) {
            entityManager.flush();
            entityManager.clear(); // avoid OOM when inserting a large dataset - periodically clear the persistence context
        }
    }
    entityManager.flush();
}
```

## Auditing (automatic `createdBy`/`updatedBy`)

```java
@Configuration
@EnableJpaAuditing
public class JpaAuditingConfig {
    @Bean
    public AuditorAware<String> auditorProvider() {
        return () -> {
            var auth = SecurityContextHolder.getContext().getAuthentication();
            return (auth == null || !auth.isAuthenticated())
                ? Optional.of("system")
                : Optional.of(auth.getName());
        };
    }
}
```

## Database Migration (Flyway)

```sql
-- V1__create_users_table.sql
CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    email VARCHAR(100) NOT NULL UNIQUE,
    active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    version BIGINT NOT NULL DEFAULT 0
);
CREATE INDEX idx_users_email ON users(email);
```

The initial schema/table/relationship design is the scope of `database-skill` - the migration file here only implements a schema decision that's already been made; don't redesign tables on the fly while writing a migration.

## Performance Tips

Distilled from Vlad Mihalcea's [14 High-Performance Java Persistence Tips](https://vladmihalcea.com/14-high-performance-java-persistence-tips/) - apply the ones relevant to the current task, don't retrofit all of them into unrelated code.

- **Log and validate generated SQL** - enable statement logging (`org.hibernate.SQL=DEBUG` or a testing-time assertion library) so N+1s and unexpected queries are caught before commit, not in production.
- **Connection pooling** - always go through HikariCP (Spring Boot default), size the pool from measured load (see `references/project-setup.md`), and keep transactions short so connections are released quickly.
- **JDBC batching** - for bulk writes, enable Hibernate batching so multiple `INSERT`/`UPDATE` statements go in one roundtrip:
  ```yaml
  spring.jpa.properties.hibernate.jdbc.batch_size: 50
  spring.jpa.properties.hibernate.order_inserts: true
  spring.jpa.properties.hibernate.order_updates: true
  ```
- **Identifier generation** - `GenerationType.IDENTITY` disables JDBC batching for inserts (Hibernate must flush each row immediately to read back the generated id). Prefer `GenerationType.SEQUENCE` with a pooled/pooled-lo optimizer when the target database supports sequences and insert batching matters:
  ```java
  @Id
  @GeneratedValue(strategy = GenerationType.SEQUENCE, generator = "user_seq")
  @SequenceGenerator(name = "user_seq", sequenceName = "user_seq", allocationSize = 50)
  private Long id;
  ```
- **Column types** - map to the narrowest/most specific column type the database offers (e.g. `inet` for IP addresses in PostgreSQL instead of `varchar`) - smaller rows mean more of the working set fits in the buffer cache and denser indexes.
- **Relationships** - avoid unidirectional `@OneToMany`/list-based `@ManyToMany` (they generate inefficient extra `UPDATE`/junction-table SQL); prefer bidirectional `@OneToMany(mappedBy = ...)` or map the join table as its own entity. Question whether a collection mapping is needed at all versus just querying the child side directly.
- **Inheritance strategy** - `SINGLE_TABLE` is fastest (no joins) but weakens `NOT NULL`/FK constraints on subclass columns; `JOINED` keeps integrity at the cost of join overhead; avoid `TABLE_PER_CLASS` (poor polymorphic query SQL, no shared sequence).
- **Persistence context size** - don't let one transaction load/manage thousands of entities; a bloated first-level cache slows dirty checking and risks OOM. Page results, use projections, or `entityManager.clear()` periodically (see Batch Insert/Update above).
- **Fetch only what's needed** - prefer DTO projections for read views over loading full entities; avoid `FetchType.EAGER` and the Open-Session-in-View anti-pattern (`spring.jpa.open-in-view: false`).
- **Caching** - tune the database buffer pool/working-set size first; add Hibernate's second-level cache (`@Cache(usage = ...)`) only for read-heavy, rarely-changing entities, picking the concurrency strategy (`READ_ONLY`, `NONSTRICT_READ_WRITE`, `READ_WRITE`, `TRANSACTIONAL`) that matches actual write frequency.
- **Concurrency control** - use `@Version` (optimistic locking, already in the Entity template above) for multi-request/detached-entity flows to prevent lost updates; reserve pessimistic locking/stricter isolation levels for cases optimistic locking can't cover.
- **Unleash native query capabilities** - when JPQL forces post-fetch processing in Java, drop to a native query using window functions, CTEs, or `PIVOT` so the database does the aggregation and only the final result crosses the wire.
- **Scale up/out** - read replicas and sharding are infrastructure decisions (see `database-skill`), not something to design ad hoc inside a service method.

## Quick Reference

| Pattern | Use Case |
|---------|----------|
| `@EntityGraph` / `JOIN FETCH` | Prevent N+1 |
| DTO Projection (constructor expression) | Read-only queries, fetching only needed fields |
| `@BatchSize` | Batch fetch child collections |
| `Specification` | Dynamic filtering with many optional conditions |
| `@Modifying` | Bulk update/delete |
| `@Modifying(clearAutomatically = true, flushAutomatically = true)` | Bulk update sharing a transaction with entity reads - avoids stale persistence-context reads after the bulk write |
| `@Version` + retry on `ObjectOptimisticLockingFailureException` | Optimistic locking - low-contention concurrent edits, safe across multiple app instances |
| `@Lock(LockModeType.PESSIMISTIC_WRITE)` | Pessimistic locking - must fully serialize access to a row |
| DTO projection instead of entity's mapped collection field | Filtering a `@OneToMany`/`@ManyToMany` without loading the full lazy collection |
| `Propagation.REQUIRES_NEW` | Independent child transaction, not rolled back with the parent |
| `noRollbackFor` | Exclude specific exceptions from rollback |
| `entityManager.clear()` per batch | Avoid OOM when inserting/updating large datasets |
| `@EnableJpaAuditing` | Automatic `createdAt`/`createdBy`/`updatedAt`/`updatedBy` |
| `GenerationType.SEQUENCE` + pooled optimizer | Keep JDBC insert batching working (`IDENTITY` disables it) |
| `hibernate.jdbc.batch_size` + `order_inserts`/`order_updates` | Enable JDBC batching for bulk writes |
| `@Version` | Optimistic locking to prevent lost updates |
| `@Cache(usage = ...)` | Second-level cache for read-heavy, rarely-changing entities |
| `spring.jpa.open-in-view: false` | Disable Open-Session-in-View anti-pattern |
