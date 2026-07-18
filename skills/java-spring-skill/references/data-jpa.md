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

    // Projection — chỉ lấy field cần, không load cả entity
    @Query("""
        SELECT new com.example.dto.UserSummary(u.id, u.email, u.username, COUNT(o))
        FROM User u LEFT JOIN u.orders o WHERE u.active = true GROUP BY u.id, u.email, u.username
        """)
    List<UserSummary> findActiveUsersSummary();

    // Pagination — tránh count query full-table khi không cần chính xác tuyệt đối
    @Query(value = "SELECT u FROM User u WHERE u.active = true", countQuery = "SELECT COUNT(u) FROM User u WHERE u.active = true")
    Page<User> findActiveUsers(Pageable pageable);

    @Modifying
    @Query("UPDATE User u SET u.active = false WHERE u.createdAt < :date")
    int deactivateOldUsers(@Param("date") Instant date);
}
```

`@EntityGraph`/`JOIN FETCH` là 2 cách khác nhau giải quyết N+1 — `@EntityGraph` khai báo tại repository, không cần viết lại JPQL; `JOIN FETCH` linh hoạt hơn khi câu query đã phức tạp sẵn. Chọn 1 trong 2 theo convention hiện có của project, không trộn lẫn tùy hứng trong cùng codebase.

## Dynamic Query — Specifications

Dùng khi filter là tổ hợp nhiều điều kiện optional (search form nhiều field) — tránh viết N phương thức `findByXAndY...` bùng nổ tổ hợp.

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
        // toàn bộ trong 1 transaction — throw bất kỳ đâu trong method này sẽ rollback hết
        Order order = buildOrder(request);
        order = orderRepository.save(order);
        paymentService.processPayment(order); // throw → rollback cả order vừa save
        return order;
    }

    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public void logOrderEvent(Long orderId, String event) {
        // Transaction riêng — vẫn commit dù transaction cha rollback (dùng cho audit log không nên mất)
        orderEventRepository.save(new OrderEvent(orderId, event));
    }

    @Transactional(noRollbackFor = NotificationException.class)
    public void completeOrder(Long orderId) {
        // Lỗi gửi notification không nên làm rollback việc complete order đã thành công
        Order order = orderRepository.findById(orderId).orElseThrow();
        order.setStatus(OrderStatus.COMPLETED);
        orderRepository.save(order);
        notificationService.sendCompletionEmail(order); // exception loại này không rollback
    }
}
```

## Batch Insert/Update (bulk, không qua Hibernate first-level cache tích lũy)

```java
@Transactional
public void batchInsert(List<User> users) {
    int batchSize = 50;
    for (int i = 0; i < users.size(); i++) {
        entityManager.persist(users.get(i));
        if (i % batchSize == 0 && i > 0) {
            entityManager.flush();
            entityManager.clear(); // tránh OOM khi insert dataset lớn — clear persistence context định kỳ
        }
    }
    entityManager.flush();
}
```

## Auditing (`createdBy`/`updatedBy` tự động)

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

Thiết kế schema/bảng/quan hệ ban đầu là phạm vi của `database-skill` — file migration ở đây chỉ hiện thực hóa schema đã quyết định, không tự ý đổi thiết kế bảng khi viết migration.

## Quick Reference

| Pattern | Use Case |
|---------|----------|
| `@EntityGraph` / `JOIN FETCH` | Ngăn N+1 |
| DTO Projection (constructor expression) | Query read-only, chỉ lấy field cần |
| `@BatchSize` | Batch fetch collection con |
| `Specification` | Filter động nhiều điều kiện optional |
| `@Modifying` | Bulk update/delete |
| `Propagation.REQUIRES_NEW` | Transaction con độc lập, không rollback theo cha |
| `noRollbackFor` | Loại trừ exception cụ thể khỏi rollback |
| `entityManager.clear()` theo batch | Tránh OOM khi insert/update dataset lớn |
| `@EnableJpaAuditing` | Tự động `createdAt`/`createdBy`/`updatedAt`/`updatedBy` |
