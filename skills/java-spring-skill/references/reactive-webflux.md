# Reactive — Spring WebFlux / Project Reactor / R2DBC

Only use this when the project has already chosen WebFlux or has genuinely high I/O-bound load (see the reasoning for MVC vs WebFlux in the main SKILL.md) — the content below is a set of concrete patterns for when you're already in a reactive context.

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

## Reactive Service — always propagate errors via `Mono.error`, do NOT throw directly

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

Throwing directly inside a reactive chain does not propagate the error correctly to the subscriber (the error occurs while building the chain, not while executing it) — always use `Mono.error()`/`Flux.error()`, or let the error surface naturally from an operator (an exception thrown inside `.map()` is caught correctly by Reactor, but a `throw` outside the chain is not).

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

An R2DBC record entity is immutable — updating any field requires creating a new instance (`new User(...)` or a `withX()` method); there's no JPA-style dirty checking.

```yaml
spring:
  r2dbc:
    url: r2dbc:postgresql://localhost:5432/demo
    pool: { initial-size: 10, max-size: 20, max-idle-time: 30m }
```

## WebClient calling an external service (reactive)

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

## Commonly Used Reactor Operators

```java
// Chain async operations
Mono<UserResponse> result = userRepository.findById(id)
    .flatMap(user -> orderRepository.findByUserId(user.id()).collectList()
        .map(orders -> new UserResponse(user, orders)));

// Combine multiple sources in parallel
Mono<UserDetails> combined = Mono.zip(
    userService.getUser(id), addressService.getAddress(id),
    (user, address) -> new UserDetails(user, address));

// Error handling — fall back to another source on error
Mono<User> safe = userRepository.findById(id)
    .onErrorResume(DatabaseException.class, e -> cacheRepository.findById(id))
    .doOnError(e -> log.error("Failed to fetch user", e));

// Backpressure — process in batches, limiting concurrency
Flux<Data> stream = dataRepository.findAll()
    .buffer(100)
    .flatMap(batch -> processBatch(batch), 5); // at most 5 batches running concurrently
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
| `.map()` | Synchronous transform |
| `.flatMap()` | Transform into another Mono/Flux (async chaining) |
| `.switchIfEmpty()` | Fallback when empty |
| `.zip()` | Combine multiple sources in parallel |
| `.onErrorResume()` | Fallback to another source on error |
| `.retryWhen()` / `.retry()` | Retry on error |
| `.timeout()` | Limit wait time |
| `StepVerifier` | Test Mono/Flux (replaces ordinary assertions) |
