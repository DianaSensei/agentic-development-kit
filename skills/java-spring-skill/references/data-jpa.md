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
