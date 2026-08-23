# Data Access — Spring Data JPA

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

## Repository — N+1 prevention, projection, bulk update

```java
public interface UserRepository extends JpaRepository<User, Long>, JpaSpecificationExecutor<User> {

    // N+1 prevention: EntityGraph
    @EntityGraph(attributePaths = {"orders", "roles"})
    @Query("SELECT u FROM User u WHERE u.id = :id")
    Optional<User> findByIdWithAssociations(@Param("id") Long id);

    // N+1 prevention: JOIN FETCH
    @Query("SELECT DISTINCT u FROM User u LEFT JOIN FETCH u.orders WHERE u.department.id = :deptId")
    List<User> findByDepartmentWithOrders(@Param("deptId") Long deptId);

    // Projection — fetch only the fields needed, without loading the whole entity
    @Query("""
        SELECT new com.example.dto.UserSummary(u.id, u.email, u.username, COUNT(o))
        FROM User u LEFT JOIN u.orders o WHERE u.active = true GROUP BY u.id, u.email, u.username
        """)
    List<UserSummary> findActiveUsersSummary();

    // Pagination — avoid a full-table count query when exact accuracy isn't needed
    @Query(value = "SELECT u FROM User u WHERE u.active = true", countQuery = "SELECT COUNT(u) FROM User u WHERE u.active = true")
    Page<User> findActiveUsers(Pageable pageable);

    @Modifying
    @Query("UPDATE User u SET u.active = false WHERE u.createdAt < :date")
    int deactivateOldUsers(@Param("date") Instant date);
}
```

`@EntityGraph`/`JOIN FETCH` are two different ways of solving N+1 — `@EntityGraph` is declared on the repository without rewriting the JPQL; `JOIN FETCH` is more flexible when the query is already complex. Pick one according to the project's existing convention — don't mix them arbitrarily within the same codebase.

## Dynamic Query — Specifications

Use this when the filter is a combination of many optional conditions (a multi-field search form) — avoiding an explosion of `findByXAndY...` method combinations.

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

## Transaction Management

```java
@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class OrderService {

    @Transactional
    public Order createOrder(OrderCreateRequest request) {
        // everything happens within a single transaction — a throw anywhere in this method rolls back all of it
        Order order = buildOrder(request);
        order = orderRepository.save(order);
        paymentService.processPayment(order); // throw → rolls back the order that was just saved too
        return order;
    }

    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public void logOrderEvent(Long orderId, String event) {
        // Separate transaction — still commits even if the parent transaction rolls back (used for audit logs that must not be lost)
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
            entityManager.clear(); // avoid OOM when inserting a large dataset — periodically clear the persistence context
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

The initial schema/table/relationship design is the scope of `database-skill` — the migration file here only implements a schema decision that's already been made; don't redesign tables on the fly while writing a migration.

## Performance Tips

Distilled from Vlad Mihalcea's [14 High-Performance Java Persistence Tips](https://vladmihalcea.com/14-high-performance-java-persistence-tips/) — apply the ones relevant to the current task, don't retrofit all of them into unrelated code.

- **Log and validate generated SQL** — enable statement logging (`org.hibernate.SQL=DEBUG` or a testing-time assertion library) so N+1s and unexpected queries are caught before commit, not in production.
- **Connection pooling** — always go through HikariCP (Spring Boot default), size the pool from measured load (see `references/project-setup.md`), and keep transactions short so connections are released quickly.
- **JDBC batching** — for bulk writes, enable Hibernate batching so multiple `INSERT`/`UPDATE` statements go in one roundtrip:
  ```yaml
  spring.jpa.properties.hibernate.jdbc.batch_size: 50
  spring.jpa.properties.hibernate.order_inserts: true
  spring.jpa.properties.hibernate.order_updates: true
  ```
- **Identifier generation** — `GenerationType.IDENTITY` disables JDBC batching for inserts (Hibernate must flush each row immediately to read back the generated id). Prefer `GenerationType.SEQUENCE` with a pooled/pooled-lo optimizer when the target database supports sequences and insert batching matters:
  ```java
  @Id
  @GeneratedValue(strategy = GenerationType.SEQUENCE, generator = "user_seq")
  @SequenceGenerator(name = "user_seq", sequenceName = "user_seq", allocationSize = 50)
  private Long id;
  ```
- **Column types** — map to the narrowest/most specific column type the database offers (e.g. `inet` for IP addresses in PostgreSQL instead of `varchar`) — smaller rows mean more of the working set fits in the buffer cache and denser indexes.
- **Relationships** — avoid unidirectional `@OneToMany`/list-based `@ManyToMany` (they generate inefficient extra `UPDATE`/junction-table SQL); prefer bidirectional `@OneToMany(mappedBy = ...)` or map the join table as its own entity. Question whether a collection mapping is needed at all versus just querying the child side directly.
- **Inheritance strategy** — `SINGLE_TABLE` is fastest (no joins) but weakens `NOT NULL`/FK constraints on subclass columns; `JOINED` keeps integrity at the cost of join overhead; avoid `TABLE_PER_CLASS` (poor polymorphic query SQL, no shared sequence).
- **Persistence context size** — don't let one transaction load/manage thousands of entities; a bloated first-level cache slows dirty checking and risks OOM. Page results, use projections, or `entityManager.clear()` periodically (see Batch Insert/Update above).
- **Fetch only what's needed** — prefer DTO projections for read views over loading full entities; avoid `FetchType.EAGER` and the Open-Session-in-View anti-pattern (`spring.jpa.open-in-view: false`).
- **Caching** — tune the database buffer pool/working-set size first; add Hibernate's second-level cache (`@Cache(usage = ...)`) only for read-heavy, rarely-changing entities, picking the concurrency strategy (`READ_ONLY`, `NONSTRICT_READ_WRITE`, `READ_WRITE`, `TRANSACTIONAL`) that matches actual write frequency.
- **Concurrency control** — use `@Version` (optimistic locking, already in the Entity template above) for multi-request/detached-entity flows to prevent lost updates; reserve pessimistic locking/stricter isolation levels for cases optimistic locking can't cover.
- **Unleash native query capabilities** — when JPQL forces post-fetch processing in Java, drop to a native query using window functions, CTEs, or `PIVOT` so the database does the aggregation and only the final result crosses the wire.
- **Scale up/out** — read replicas and sharding are infrastructure decisions (see `database-skill`), not something to design ad hoc inside a service method.

## Quick Reference

| Pattern | Use Case |
|---------|----------|
| `@EntityGraph` / `JOIN FETCH` | Prevent N+1 |
| DTO Projection (constructor expression) | Read-only queries, fetching only needed fields |
| `@BatchSize` | Batch fetch child collections |
| `Specification` | Dynamic filtering with many optional conditions |
| `@Modifying` | Bulk update/delete |
| `Propagation.REQUIRES_NEW` | Independent child transaction, not rolled back with the parent |
| `noRollbackFor` | Exclude specific exceptions from rollback |
| `entityManager.clear()` per batch | Avoid OOM when inserting/updating large datasets |
| `@EnableJpaAuditing` | Automatic `createdAt`/`createdBy`/`updatedAt`/`updatedBy` |
| `GenerationType.SEQUENCE` + pooled optimizer | Keep JDBC insert batching working (`IDENTITY` disables it) |
| `hibernate.jdbc.batch_size` + `order_inserts`/`order_updates` | Enable JDBC batching for bulk writes |
| `@Version` | Optimistic locking to prevent lost updates |
| `@Cache(usage = ...)` | Second-level cache for read-heavy, rarely-changing entities |
| `spring.jpa.open-in-view: false` | Disable Open-Session-in-View anti-pattern |
