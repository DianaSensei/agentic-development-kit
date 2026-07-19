# Web Layer — Controller, DTO, Exception Handling

## REST Controller

```java
@RestController
@RequestMapping("/api/v1/users")
@Validated
@RequiredArgsConstructor
public class UserController {
    private final UserService userService;

    @GetMapping
    public ResponseEntity<Page<UserResponse>> getUsers(
            @PageableDefault(size = 20, sort = "createdAt") Pageable pageable) {
        return ResponseEntity.ok(userService.findAll(pageable));
    }

    @GetMapping("/{id}")
    public ResponseEntity<UserResponse> getUser(@PathVariable Long id) {
        return ResponseEntity.ok(userService.findById(id));
    }

    @PostMapping
    public ResponseEntity<UserResponse> createUser(@Valid @RequestBody UserCreateRequest request) {
        UserResponse user = userService.create(request);
        URI location = ServletUriComponentsBuilder.fromCurrentRequest()
            .path("/{id}").buildAndExpand(user.id()).toUri();
        return ResponseEntity.created(location).body(user);
    }

    @PutMapping("/{id}")
    public ResponseEntity<UserResponse> updateUser(@PathVariable Long id, @Valid @RequestBody UserUpdateRequest request) {
        return ResponseEntity.ok(userService.update(id, request));
    }

    @DeleteMapping("/{id}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void deleteUser(@PathVariable Long id) {
        userService.delete(id);
    }
}
```

## Request/Response DTO (record + Bean Validation)

```java
public record UserCreateRequest(
    @NotBlank @Email String email,
    @NotBlank @Size(min = 8, max = 100)
    @Pattern(regexp = "^(?=.*[A-Z])(?=.*[a-z])(?=.*\\d).*$", message = "Must contain an uppercase letter, a lowercase letter, and a digit")
    String password,
    @NotBlank @Size(min = 3, max = 50) @Pattern(regexp = "^[a-zA-Z0-9_]+$")
    String username,
    @Min(18) @Max(120) Integer age
) {}

public record UserResponse(
    Long id, String email, String username, Integer age, Boolean active,
    LocalDateTime createdAt, LocalDateTime updatedAt
) {
    public static UserResponse from(User user) {
        return new UserResponse(user.getId(), user.getEmail(), user.getUsername(),
            user.getAge(), user.getActive(), user.getCreatedAt(), user.getUpdatedAt());
    }
}
```

## Global Exception Handling (ProblemDetail — RFC 7807)

Use `ProblemDetail` (built-in to Spring 6+) instead of defining a custom error record — it directly matches the RFC 7807 standard that `api-contract-skill` has already chosen as the default error format, avoiding format drift between the spec and the real implementation.

```java
@RestControllerAdvice
@Slf4j
public class GlobalExceptionHandler {

    @ExceptionHandler(EntityNotFoundException.class)
    public ProblemDetail handleNotFound(EntityNotFoundException ex) {
        ProblemDetail problem = ProblemDetail.forStatusAndDetail(HttpStatus.NOT_FOUND, ex.getMessage());
        problem.setProperty("timestamp", Instant.now());
        return problem;
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ProblemDetail handleValidation(MethodArgumentNotValidException ex) {
        ProblemDetail problem = ProblemDetail.forStatusAndDetail(HttpStatus.BAD_REQUEST, "Validation failed");
        problem.setProperty("errors", ex.getBindingResult().getFieldErrors().stream()
            .map(e -> e.getField() + ": " + e.getDefaultMessage()).toList());
        return problem;
    }

    @ExceptionHandler(DataIntegrityViolationException.class)
    public ProblemDetail handleDataIntegrity(DataIntegrityViolationException ex) {
        log.error("Data integrity violation", ex);
        return ProblemDetail.forStatusAndDetail(HttpStatus.CONFLICT, "Resource may already exist");
    }

    @ExceptionHandler(Exception.class)
    public ProblemDetail handleUnexpected(Exception ex) {
        log.error("Unexpected error", ex);
        // Don't expose the raw ex.getMessage() to the client for an unidentified 500 error — the details are
        // already logged; the client only needs to know an infrastructure error occurred so it can retry/contact support.
        return ProblemDetail.forStatusAndDetail(HttpStatus.INTERNAL_SERVER_ERROR, "An unexpected error occurred");
    }
}
```

## Custom Validation Annotation

```java
@Target({ElementType.FIELD, ElementType.PARAMETER})
@Retention(RetentionPolicy.RUNTIME)
@Constraint(validatedBy = UniqueEmailValidator.class)
public @interface UniqueEmail {
    String message() default "Email already exists";
    Class<?>[] groups() default {};
    Class<? extends Payload>[] payload() default {};
}

@Component
@RequiredArgsConstructor
public class UniqueEmailValidator implements ConstraintValidator<UniqueEmail, String> {
    private final UserRepository userRepository;

    @Override
    public boolean isValid(String email, ConstraintValidatorContext context) {
        return email == null || !userRepository.existsByEmail(email);
    }
}
```

## WebClient for calling an external service

```java
@Configuration
public class WebClientConfig {
    @Bean
    public WebClient webClient(WebClient.Builder builder) {
        return builder.baseUrl("https://api.example.com")
            .defaultHeader(HttpHeaders.CONTENT_TYPE, MediaType.APPLICATION_JSON_VALUE)
            .build();
    }
}

@Service
@RequiredArgsConstructor
public class ExternalApiService {
    private final WebClient webClient;

    public Mono<ExternalDataResponse> fetchData(String id) {
        return webClient.get().uri("/data/{id}", id).retrieve()
            .onStatus(HttpStatusCode::is4xxClientError, r -> Mono.error(new ResourceNotFoundException("Not found")))
            .onStatus(HttpStatusCode::is5xxServerError, r -> Mono.error(new ServiceUnavailableException("Unavailable")))
            .bodyToMono(ExternalDataResponse.class)
            .timeout(Duration.ofSeconds(5))
            .retry(3);
    }
}
```

## CORS Configuration

```java
@Configuration
public class WebConfig implements WebMvcConfigurer {
    @Override
    public void addCorsMappings(CorsRegistry registry) {
        registry.addMapping("/api/**")
            .allowedOrigins("http://localhost:3000", "https://example.com")
            .allowedMethods("GET", "POST", "PUT", "DELETE", "OPTIONS")
            .allowedHeaders("*")
            .allowCredentials(true)
            .maxAge(3600);
    }
}
```

## Quick Reference

| Annotation | Purpose |
|------------|---------|
| `@RestController` | REST controller (`@Controller` + `@ResponseBody`) |
| `@PathVariable` / `@RequestParam` | Get a value from the path / query string |
| `@RequestBody` + `@Valid` | Bind + validate the request body |
| `@RestControllerAdvice` | Global exception handling |
| `@ResponseStatus` | Set the status code for a method |
| `ProblemDetail` | RFC 7807 error response |
