# Testing — JUnit 5, Mockito, MockMvc/WebTestClient, Testcontainers

Setup/lifecycle container (dependency, wait strategy, reuse, network) là phạm vi của `testcontainers-skill` — file này chỉ tập trung PATTERN viết test ở từng tầng (unit/slice/integration), không lặp lại nội dung cấu hình container.

## Unit Test — mock toàn bộ dependency ngoài

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

## Web Layer Test — `@WebMvcTest` (mock service, không load full context)

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

## Reactive Controller Test — `@WebFluxTest` + `WebTestClient`

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

## Repository Test — `@DataJpaTest` + Testcontainers thật (không H2)

Dùng Postgres thật qua Testcontainers thay vì H2 in-memory khi query có dùng feature đặc thù dialect (JSONB, native query, index hint) — H2 không tái hiện đúng hành vi. Setup container chi tiết xem `testcontainers-skill`; ví dụ dưới đây chỉ minh họa cách viết test dùng container đã setup.

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

## Full Integration Test — `@SpringBootTest`

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

## Test Data Builder (tránh lặp lại setup dài dòng ở mỗi test)

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

## Shared Testcontainers Instance (dùng chung 1 container cho nhiều test class, tránh khởi động lại tốn thời gian)

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
// Các integration test class khác extends AbstractIntegrationTest thay vì tự khai báo @Container riêng
```

## Quick Reference

| Annotation | Purpose |
|------------|---------|
| `@ExtendWith(MockitoExtension.class)` | Unit test thuần, mock dependency |
| `@WebMvcTest` | Test tầng MVC controller, mock service |
| `@WebFluxTest` + `WebTestClient` | Test controller reactive |
| `@DataJpaTest` | Test repository (dùng Testcontainers thay H2 nếu cần dialect thật) |
| `@SpringBootTest` | Full context — integration test end-to-end |
| `@MockBean` | Mock 1 bean trong Spring context |
| `@WithMockUser` | Giả lập user đã authenticate |
| `AssertJ` (`assertThat`) | Assertion fluent, ưu tiên hơn assert thô |

## Testing Best Practices

- AAA pattern (Arrange/Given, Act/When, Assert/Then) rõ ràng trong từng test.
- Unit test mock hết dependency ngoài; integration test dùng Testcontainers cho hạ tầng thật — không trộn 2 loại trong cùng 1 test class.
- Test cả exception path, không chỉ happy path.
- Tên test method mô tả rõ hành vi đang test (`should_X_when_Y` hoặc `@DisplayName` tiếng Việt/Anh rõ ràng).
- Chạy test thật (`mvn test`/`gradle test`) trước khi báo hoàn thành — không chỉ viết xong là coi như xong.
