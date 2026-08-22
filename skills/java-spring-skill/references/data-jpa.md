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

`@DynamicUpdate` on the entity makes the `UPDATE` statement include only the columns that actually changed, instead of every column — worth adding on entities with a large number of columns where most updates only touch a few fields. `@Version` (or implementing `Persistable<ID>` for entities with an application-assigned/sequence ID) also avoids an extra `SELECT` Hibernate would otherwise issue before `INSERT` to decide whether the entity is new.

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

    // Reference only (no SELECT) — use when you just need the FK/proxy to set an association,
    // not the entity's actual data (e.g. order.setUser(userRepository.getReferenceById(userId)))
    // Throws EntityNotFoundException lazily on first field access if the row doesn't exist.

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

## Connection Management

Establishing a DB connection is expensive relative to running most queries (often tens of ms vs. low single-digit ms) — a leaked or needlessly-held-open connection hurts far more than an unoptimized query. Two settings matter regardless of query-level tuning:

- Set `spring.jpa.open-in-view=false` (Spring Boot defaults this to `true`, which keeps a connection checked out for the entire HTTP request just in case a lazy association is touched in the view layer). Leaving it on is a common source of connection-pool exhaustion under load; turning it off surfaces `LazyInitializationException` at dev time instead — that's the point, it forces explicit fetching (`@EntityGraph`/`JOIN FETCH`/projection) instead of accidental N+1 in the view.
- Size HikariCP (`spring.datasource.hikari.maximum-pool-size`, `connection-timeout`) from measured concurrency/throughput, not a guess — see `references/project-setup.md`.

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
        return orderRepository.save(order);
        // do NOT call paymentService (or any other network call) here while the transaction is still open —
        // it holds the DB connection checked out for the full duration of that external call. Call it after
        // this method returns (from the caller, or split into a non-transactional method), or use
        // TransactionTemplate to commit the DB write first and then perform the external call afterward.
    }

    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public void logOrderEvent(Long orderId, String event) {
        // Separate transaction — still commits even if the parent transaction rolls back (used for audit logs that must not be lost)
        // Caution: this suspends the caller's transaction and checks out a SECOND connection from the pool for
        // the duration of this call — nesting REQUIRES_NEW calls (or calling one from a hot path under load)
        // can exhaust the pool faster than expected. Use it only where the "commits independently" semantics
        // are actually needed, not as a default.
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

Prefer declarative `@Transactional` by default. Reach for `TransactionTemplate` only when the transaction boundary can't be expressed declaratively — e.g. committing a DB write first and then conditionally starting a second transaction based on the result of an external call in between:

```java
@RequiredArgsConstructor
public class OrderService {
    private final TransactionTemplate transactionTemplate;

    public Order createOrderThenCharge(OrderCreateRequest request) {
        Order order = transactionTemplate.execute(status -> orderRepository.save(buildOrder(request)));
        paymentService.processPayment(order); // runs after the DB transaction has already committed, connection released
        return order;
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

## Query Logging (development only)

Turn this on while developing/debugging a data-access change so N+1s and unexpectedly-issued queries are visible immediately instead of discovered under load. Never leave it on in production (log volume, minor overhead).

```yaml
# application-local.yml / application-dev.yml — not the production profile
logging:
  level:
    org.hibernate.SQL: DEBUG
    org.hibernate.orm.jdbc.bind: TRACE # bound parameter values
spring:
  jpa:
    properties:
      hibernate:
        format_sql: true
```

For a fuller picture than log lines (query counts per request, N+1 assertions in tests), consider `datasource-proxy` or `p6spy` for dev-time query logging, and QuickPerf (`@ExpectSelect(n)`, `@DisableJPAWarnings` etc.) for asserting query counts in tests.

## Quick Reference

| Pattern | Use Case |
|---------|----------|
| `spring.jpa.open-in-view=false` | Stop holding a DB connection for the whole HTTP request; forces explicit fetching |
| `@EntityGraph` / `JOIN FETCH` | Prevent N+1 |
| DTO Projection (constructor expression) | Read-only queries, fetching only needed fields |
| `Repository#getReferenceById` | Get a proxy/FK reference without issuing a SELECT |
| `@BatchSize` | Batch fetch child collections |
| `@DynamicUpdate` | UPDATE only changed columns — worth it on wide tables |
| `@Version` / `Persistable<ID>` | Avoid an extra SELECT before INSERT on new entities |
| `Specification` | Dynamic filtering with many optional conditions |
| `@Modifying` | Bulk update/delete |
| Never call external services inside `@Transactional` | Don't hold a DB connection open for the duration of a network call |
| `TransactionTemplate` | Fine-grained transaction boundaries declarative `@Transactional` can't express |
| `Propagation.REQUIRES_NEW` | Independent child transaction, not rolled back with the parent — costs a second pooled connection, use sparingly |
| `noRollbackFor` | Exclude specific exceptions from rollback |
| `entityManager.clear()` per batch | Avoid OOM when inserting/updating large datasets |
| `@EnableJpaAuditing` | Automatic `createdAt`/`createdBy`/`updatedAt`/`updatedBy` |
| `org.hibernate.SQL=DEBUG` (dev only) | Surface N+1/unexpected queries during development |
