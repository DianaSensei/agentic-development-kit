# Reactive — Spring WebFlux / Project Reactor / R2DBC

Chỉ dùng khi project đã chọn WebFlux hoặc I/O-bound thật sự cao (xem lý do chọn MVC vs WebFlux ở SKILL.md chính) — nội dung dưới đây là pattern cụ thể khi đã ở trong ngữ cảnh reactive.

## WebFlux Controller

```java
@RestController
@RequestMapping("/api/users")
@RequiredArgsConstructor
public class UserController {
    private final UserService userService;

    @GetMapping
    public Flux<UserResponse> getAllUsers() { return userService.findAll(); }

    @GetMapping("/{id}")
    public Mono<UserResponse> getUserById(@PathVariable Long id) { return userService.findById(id); }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public Mono<UserResponse> createUser(@RequestBody @Valid UserRequest request) { return userService.create(request); }
}
```

## Reactive Service — luôn propagate lỗi qua `Mono.error`, KHÔNG throw trực tiếp

```java
@Service
@RequiredArgsConstructor
public class UserService {
    private final UserRepository userRepository;
    private final UserMapper userMapper;

    public Mono<UserResponse> findById(Long id) {
        return userRepository.findById(id)
            .map(userMapper::toResponse)
            .switchIfEmpty(Mono.error(new EntityNotFoundException("User not found: " + id)));
    }

    @Transactional
    public Mono<UserResponse> create(UserRequest request) {
        return Mono.just(request)
            .map(userMapper::toEntity)
            .flatMap(userRepository::save)
            .map(userMapper::toResponse);
    }
}
```

`throw` trực tiếp trong 1 reactive chain không lan truyền lỗi đúng cách cho subscriber (lỗi xảy ra khi build chain, không phải khi execute) — luôn dùng `Mono.error()`/`Flux.error()` hoặc để lỗi tự nhiên nổi lên từ 1 operator (`.map()` ném exception vẫn được Reactor bắt đúng, nhưng `throw` ở ngoài chain thì không).

## R2DBC Repository & Entity

```java
public interface UserRepository extends R2dbcRepository<User, Long> {
    Mono<User> findByEmail(String email);

    @Query("SELECT u.* FROM users u WHERE u.email LIKE CONCAT('%', :domain, '%') ORDER BY u.created_at DESC")
    Flux<User> findByEmailDomain(String domain);
}

@Table("users")
public record User(
    @Id Long id, String email, String username, Boolean active,
    @CreatedDate Instant createdAt, @LastModifiedDate Instant updatedAt
) {}
```

R2DBC record entity là immutable — update field nào cũng phải tạo instance mới (`new User(...)` hoặc method `withX()`), không có JPA-style dirty checking.

```yaml
spring:
  r2dbc:
    url: r2dbc:postgresql://localhost:5432/demo
    pool: { initial-size: 10, max-size: 20, max-idle-time: 30m }
```

## WebClient gọi service ngoài (reactive)

```java
@Component
@RequiredArgsConstructor
public class ExternalUserClient {
    private final WebClient webClient;

    public Mono<ExternalUserDto> getUser(Long id) {
        return webClient.get().uri("/users/{id}", id).retrieve()
            .bodyToMono(ExternalUserDto.class)
            .retryWhen(Retry.backoff(3, Duration.ofSeconds(1)))
            .timeout(Duration.ofSeconds(5));
    }
}
```

## Reactor Operators thường dùng

```java
// Chain async operations
Mono<UserResponse> result = userRepository.findById(id)
    .flatMap(user -> orderRepository.findByUserId(user.id()).collectList()
        .map(orders -> new UserResponse(user, orders)));

// Combine multiple sources song song
Mono<UserDetails> combined = Mono.zip(
    userService.getUser(id), addressService.getAddress(id),
    (user, address) -> new UserDetails(user, address));

// Error handling — fallback nguồn khác khi lỗi
Mono<User> safe = userRepository.findById(id)
    .onErrorResume(DatabaseException.class, e -> cacheRepository.findById(id))
    .doOnError(e -> log.error("Failed to fetch user", e));

// Backpressure — xử lý theo batch, giới hạn concurrency
Flux<Data> stream = dataRepository.findAll()
    .buffer(100)
    .flatMap(batch -> processBatch(batch), 5); // tối đa 5 batch chạy đồng thời
```

## Testing Reactive Code — StepVerifier

```java
@ExtendWith(MockitoExtension.class)
class UserServiceTest {
    @Mock private UserRepository userRepository;
    @InjectMocks private UserService userService;

    @Test
    void shouldFindUserById() {
        when(userRepository.findById(1L)).thenReturn(Mono.just(new User(1L, "test@example.com", "testuser", true, null, null)));

        StepVerifier.create(userService.findById(1L))
            .expectNextMatches(response -> response.email().equals("test@example.com"))
            .verifyComplete();
    }

    @Test
    void shouldThrowWhenUserNotFound() {
        when(userRepository.findById(1L)).thenReturn(Mono.empty());

        StepVerifier.create(userService.findById(1L))
            .expectError(EntityNotFoundException.class)
            .verify();
    }
}
```

## Quick Reference

| Operator | Purpose |
|----------|---------|
| `.map()` | Transform đồng bộ |
| `.flatMap()` | Transform ra Mono/Flux khác (async chaining) |
| `.switchIfEmpty()` | Fallback khi rỗng |
| `.zip()` | Kết hợp nhiều nguồn song song |
| `.onErrorResume()` | Fallback nguồn khác khi lỗi |
| `.retryWhen()` / `.retry()` | Retry khi lỗi |
| `.timeout()` | Giới hạn thời gian chờ |
| `StepVerifier` | Test Mono/Flux (thay cho assert thông thường) |
