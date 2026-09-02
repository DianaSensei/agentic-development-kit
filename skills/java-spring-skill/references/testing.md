# Testing - JUnit 5, Mockito, MockMvc/WebTestClient, Testcontainers

Container setup/lifecycle (dependencies, wait strategies, reuse, network) is the scope of `testcontainers-skill` - this file focuses only on PATTERNS for writing tests at each layer (unit/slice/integration), and doesn't repeat container configuration content.

## Unit Test - mock all external dependencies

```java
@ExtendWith(MockitoExtension.class)
@DisplayName("User Service Tests")
class UserServiceTest {
    @Mock private UserRepository userRepository;
    @Mock private UserMapper userMapper;
    @InjectMocks private UserService userService;

    @Test
    @DisplayName("Should find user by ID successfully")
    void shouldFindUserById() {
        // Given
        User user = User.builder().id(1L).email("test@example.com").build();
        when(userRepository.findById(1L)).thenReturn(Optional.of(user));
        when(userMapper.toResponse(user)).thenReturn(new UserResponse(1L, "test@example.com", "testuser"));

        // When
        UserResponse result = userService.findById(1L);

        // Then
        assertThat(result.email()).isEqualTo("test@example.com");
        verify(userRepository).findById(1L);
    }

    @Test
    @DisplayName("Should throw exception when user not found")
    void shouldThrowWhenUserNotFound() {
        when(userRepository.findById(anyLong())).thenReturn(Optional.empty());

        assertThatThrownBy(() -> userService.findById(999L))
            .isInstanceOf(EntityNotFoundException.class)
            .hasMessageContaining("User not found");
        verifyNoInteractions(userMapper);
    }

    @ParameterizedTest
    @ValueSource(strings = {"admin", "user", "moderator"})
    @DisplayName("Should validate different user roles")
    void shouldValidateUserRoles(String role) {
        assertThat(role).isNotBlank();
    }
}
```

## Web Layer Test - `@WebMvcTest` (mocks the service, doesn't load the full context)

```java
@WebMvcTest(UserController.class)
class UserControllerTest {
    @Autowired private MockMvc mockMvc;
    @Autowired private ObjectMapper objectMapper;
    @MockBean private UserService userService;

    @Test
    @WithMockUser(roles = "ADMIN")
    void shouldCreateUser() throws Exception {
        var request = new UserCreateRequest("test@example.com", "Password123", "testuser", 25);
        var response = new UserResponse(1L, request.email(), request.username(), request.age(), true, null, null);
        when(userService.create(any())).thenReturn(response);

        mockMvc.perform(post("/api/v1/users")
                .with(csrf())
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(request)))
            .andExpect(status().isCreated())
            .andExpect(header().exists("Location"))
            .andExpect(jsonPath("$.email").value(request.email()));
    }

    @Test
    void shouldReturn401WhenNotAuthenticated() throws Exception {
        mockMvc.perform(get("/api/v1/users")).andExpect(status().isUnauthorized());
    }
}
```

## Reactive Controller Test - `@WebFluxTest` + `WebTestClient`

```java
@WebFluxTest(UserController.class)
class UserControllerReactiveTest {
    @Autowired private WebTestClient webTestClient;
    @MockBean private UserService userService;

    @Test
    void shouldGetUserReactively() {
        when(userService.findById(1L)).thenReturn(Mono.just(new UserResponse(1L, "test@example.com", "testuser")));

        webTestClient.get().uri("/api/users/{id}", 1L)
            .exchange()
            .expectStatus().isOk()
            .expectBody(UserResponse.class)
            .value(r -> assertThat(r.email()).isEqualTo("test@example.com"));
    }
}
```

## Repository Test - `@DataJpaTest` + real Testcontainers (not H2)

Use a real Postgres via Testcontainers instead of in-memory H2 when a query relies on dialect-specific features (JSONB, native queries, index hints) - H2 doesn't reproduce that behavior correctly. See `testcontainers-skill` for detailed container setup; the example below only illustrates how to write a test using an already-set-up container.

```java
@DataJpaTest
@Testcontainers
@AutoConfigureTestDatabase(replace = AutoConfigureTestDatabase.Replace.NONE)
class UserRepositoryTest {
    @Container
    static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:16-alpine");

    @DynamicPropertySource
    static void configureProperties(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", postgres::getJdbcUrl);
        registry.add("spring.datasource.username", postgres::getUsername);
        registry.add("spring.datasource.password", postgres::getPassword);
    }

    @Autowired private TestEntityManager entityManager;
    @Autowired private UserRepository userRepository;

    @Test
    void shouldFindUserByEmail() {
        entityManager.persistAndFlush(User.builder().email("test@example.com").active(true).build());
        assertThat(userRepository.findByEmail("test@example.com")).isPresent();
    }
}
```

## Full Integration Test - `@SpringBootTest`

```java
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@Testcontainers
class UserIntegrationTest {
    @Container
    static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:16-alpine");

    @DynamicPropertySource
    static void configureProperties(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", postgres::getJdbcUrl);
    }

    @Autowired private TestRestTemplate restTemplate;

    @Test
    void shouldCreateAndRetrieveUser() {
        var createResponse = restTemplate.postForEntity("/api/users",
            new UserRequest("test@example.com", "testuser"), UserResponse.class);
        assertThat(createResponse.getStatusCode()).isEqualTo(HttpStatus.CREATED);

        var getResponse = restTemplate.getForEntity("/api/users/" + createResponse.getBody().id(), UserResponse.class);
        assertThat(getResponse.getBody().email()).isEqualTo("test@example.com");
    }
}
```

## Test Data Builder (avoids repeating lengthy setup in every test)

```java
public class UserTestBuilder {
    private Long id = 1L;
    private String email = "test@example.com";
    private Boolean active = true;

    public static UserTestBuilder aUser() { return new UserTestBuilder(); }
    public UserTestBuilder withEmail(String email) { this.email = email; return this; }
    public UserTestBuilder inactive() { this.active = false; return this; }
    public User build() { return User.builder().id(id).email(email).active(active).build(); }
}

// Usage
User user = aUser().withEmail("custom@example.com").inactive().build();
```

## Shared Testcontainers Instance (share one container across multiple test classes, avoiding time-consuming restarts)

```java
public abstract class AbstractIntegrationTest {
    static final PostgreSQLContainer<?> postgres;
    static {
        postgres = new PostgreSQLContainer<>("postgres:16-alpine").withReuse(true);
        postgres.start();
    }

    @DynamicPropertySource
    static void configureProperties(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", postgres::getJdbcUrl);
    }
}
// Other integration test classes extend AbstractIntegrationTest instead of declaring their own @Container
```

## Quick Reference

| Annotation | Purpose |
|------------|---------|
| `@ExtendWith(MockitoExtension.class)` | Pure unit test, mocked dependencies |
| `@WebMvcTest` | Test the MVC controller layer, mocked service |
| `@WebFluxTest` + `WebTestClient` | Test a reactive controller |
| `@DataJpaTest` | Test a repository (use Testcontainers instead of H2 when real dialect behavior matters) |
| `@SpringBootTest` | Full context - end-to-end integration test |
| `@MockBean` | Mock a single bean in the Spring context |
| `@WithMockUser` | Simulate an already-authenticated user |
| `AssertJ` (`assertThat`) | Fluent assertions, preferred over plain assertions |

## Testing Best Practices

- Use a clear AAA pattern (Arrange/Given, Act/When, Assert/Then) in every test.
- Unit tests mock all external dependencies; integration tests use Testcontainers for real infrastructure - don't mix the two in the same test class.
- Test the exception path as well, not just the happy path.
- Test method names should clearly describe the behavior under test (`should_X_when_Y`, or a clear `@DisplayName`).
- Actually run the tests (`mvn test`/`gradle test`) before reporting completion - don't consider it done just because it's written.
