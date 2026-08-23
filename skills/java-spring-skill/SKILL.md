---
name: java-spring-skill
description: In-depth Java + Spring ecosystem knowledge (Spring Boot 3.x, Java 21) — Spring MVC/WebFlux, Spring Data JPA, Spring Security 6 (JWT/OAuth2), Spring Cloud (Config/Eureka/Gateway)/Resilience4j, package structure (package-by-layer vs. package-by-feature, Spring Modulith, cross-module transactions), Java code style/formatting (Google Java Style, Spotless/Checkstyle), plus unit + integration testing (JUnit5, Mockito, Testcontainers). Does NOT cover Kafka/RabbitMQ (see `kafka-skill`/`rabbitmq-skill`), API contract design (see `api-contract-skill`), or DB schema design (see `database-skill`). Use when implementing Java/Spring business logic.
metadata:
  domain: java-backend
  triggers: Java, Spring Boot, Spring MVC, Spring WebFlux, Spring Data JPA, Spring Security, Spring Cloud, Resilience4j, JUnit, Mockito, Java microservices, reactive Java, package structure, package by feature, package by layer, Spring Modulith, modular monolith, Google Java Style, code format, Checkstyle, Spotless
  role: engineer
  scope: implementation
  output-format: code
  related-skills: database-skill, kafka-skill, rabbitmq-skill, api-contract-skill, testcontainers-skill, code-review-skill, architecture-designer, solution-design-principles
---

# Java + Spring Ecosystem

Implement Java/Spring business logic following the project's existing conventions, prioritizing data safety and maintainability over adopting a new pattern just because it's "more modern."

**Governing principle: KISS first, in every case.** Prioritize simple and easy to understand over
clever or "future-proof." Start every structural or implementation decision — package layout, layering
inside a module, transaction pattern, abstraction — from the simplest option that correctly solves the
problem in front of you. Add complexity (a new layer, a new interface, an async/event path, a new
abstraction) only when a concrete, present requirement demands it, never because it might be needed
later. When unsure between a simpler and a more elaborate option, default to the simpler one.

## When to Use This Skill

- Implementing/modifying Java business logic with Spring Boot (MVC or WebFlux).
- Designing the data-access layer (JPA), security (JWT/OAuth2), or cloud-native infrastructure (Config/Discovery/Gateway/Resilience4j) for a Java service.
- Choosing or evaluating package structure (package-by-layer vs. package-by-feature, module boundaries,
  cross-module transactions) for a Spring Boot service.
- Applying or checking Java code style/formatting conventions.
- Writing unit tests for logic just implemented (JUnit5 + Mockito).

## Core Workflow

1. **Discover** — Read `pom.xml`/`build.gradle`: exact Java/Spring Boot version, reactive (WebFlux) or servlet (MVC), whether Resilience4j/Spring Security is present, the test framework in use (JUnit4 vs. 5, Mockito/AssertJ). Read `CLAUDE.md`/existing conventions, and any existing formatter config (`.editorconfig`, Spotless/Checkstyle). Do NOT assume anything without evidence.
2. **Architecture & Layering** — Preserve the existing layer convention (Controller → Service → Repository, package-by-layer, package-by-feature, or hexagonal/onion if the project already uses one) — don't change architecture mid-task. For a new project or a genuine restructuring request, see `references/project-structure.md` to choose the simplest structure that fits the system's actual current scale — default to the plainest option (flat package-by-layer) and only move to package-by-feature, internal hexagonal layering, or Spring Modulith enforcement when the reference's own "move up when..." signals are actually present. Absent a specific need, prefer Spring MVC over WebFlux — WebFlux is only for high I/O-bound load or when the project already uses it from the start; switching MVC ↔ WebFlux is a major, hard-to-reverse architectural decision — never do it unprompted without an explicit request.
3. **Implement** — Apply the correct pattern for the layer being worked on (see Reference Guide), following the project's existing code style or, absent one, `references/code-style.md`, while ensuring the three aspects below are addressed as the code is written, not fixed later in review:
   - *Safety*: clear transaction boundaries (avoid self-invocation, which silently defeats the `@Transactional`/`@Async`/`@Cacheable` proxy), idempotency for endpoints that can be called twice, thread safety for stateful singleton beans, input validation at the boundary (`@Valid`).
   - *Performance*: avoid N+1 (`@EntityGraph`/`JOIN FETCH`), batch processing for large volumes, connection-pool tuning (HikariCP) based on measured evidence — don't guess without data.
   - *Scalability*: prefer stateless services for horizontal scaling; Resilience4j (circuit breaker/retry/bulkhead) for calls to dependent services if the project already has this convention, or add it for a specific call site that clearly needs it (state this in the report, no need to stop and wait for approval).
4. **Test** — Write unit tests (JUnit5 + Mockito) for every Acceptance Criterion/edge case, mock every external dependency, test the exception path too. Run the tests for real (`mvn test`/`gradle test`) before reporting done; if they fail, fix within reasonable scope and re-run. For integration tests against real infrastructure (DB/broker) → coordinate with `testcontainers-skill`.
5. **Handoff** — List every file created/modified clearly in the report, so the lead orchestrator (`feature-development`/`bug-fix`) can add it to the "Files Changed" list.

## Reference Guide

Load detail based on the context currently being coded:

| Topic | Reference | Load When |
|-------|-----------|-----------|
| Project setup | `references/project-setup.md` | Setting up a new project, `pom.xml`, `application.yml` |
| Project structure | `references/project-structure.md` | Choosing/evaluating package-by-layer vs. package-by-feature, module boundaries, Spring Modulith, cross-module transactions |
| Code style | `references/code-style.md` | Java formatting/naming conventions, Google Java Style, Spotless/Checkstyle setup |
| Web layer | `references/web-layer.md` | Controller, DTO, validation, exception handling (ProblemDetail) |
| Data JPA | `references/data-jpa.md` | Entity, repository, N+1, transactions, Specification, migration |
| Reactive WebFlux | `references/reactive-webflux.md` | Reactive Controller/Service, R2DBC, Reactor operators |
| Security | `references/security.md` | JWT, method security, OAuth2 resource server |
| Cloud & Resilience | `references/cloud-resilience.md` | Spring Cloud Config/Eureka/Gateway, Resilience4j, Actuator |
| Testing | `references/testing.md` | Unit/slice/integration test patterns |

## Constraints

### MUST DO
- Read `pom.xml`/`build.gradle` + existing conventions before coding — never assume the version/framework.
- Default to the simplest structure/pattern that correctly solves the problem at hand (KISS) — escalate
  to a more complex option only when a concrete, present requirement demands it.
- Constructor injection (`public MyService(Dep dep) { this.dep = dep; }`), never field injection.
- Validate input on every mutating endpoint (`@Valid @RequestBody`).
- Clear, correctly-scoped transaction boundaries (`@Transactional(readOnly = true)` for reads, a write transaction only for writes).
- Externalize config/secrets via environment variables — never hardcoded in `application.properties`/`application.yml`.
- Follow the project's existing code style/formatter config if one exists; apply `references/code-style.md` only when none exists yet.
- Run the tests for real before reporting done.

### MUST NOT DO
- Field injection (`@Autowired` on a field).
- Calling `.block()` inside a reactive chain (mixing blocking code into WebFlux).
- Switching MVC ↔ WebFlux, or adding a new runtime framework, mid-task without an explicit request.
- Using deprecated Spring Boot 2.x APIs (e.g. `WebSecurityConfigurerAdapter`).
- Skipping the exception path when writing tests — testing only the happy path.
- Introducing package-by-feature, internal hexagonal layering, Spring Modulith enforcement, or an
  event-driven transaction path speculatively — apply only when `references/project-structure.md`'s
  concrete "move up when..." signal is actually present, not by default or "to be safe."
- Imposing a new formatter/style convention over an existing one already in use in the codebase.

## Common Real-World Issues

- **Self-invocation defeats the AOP proxy**: calling a method annotated `@Transactional`/`@Async`/`@Cacheable` from ANOTHER method in the SAME class (`this.methodX()`) bypasses the Spring proxy entirely — the annotation is silently ignored, with no clear error or warning. Move that method to a different bean if the annotation must take effect.
- **Singleton bean with unsynchronized mutable state**: an instance field on a `@Service` (singleton scope by default) read/written by multiple concurrent requests causes a race condition — the service must be stateless, or properly synchronized if state is unavoidable.
- **ThreadLocal never cleared**: using a ThreadLocal to hold per-request context (userId, tenant, etc.) without calling `remove()` afterward — a thread reused from the pool for a different request still carries the old value, leaking data across requests (severe if it's authorization/tenant information).

## Templates

### Quick Start — One Complete Slice (copy-paste starter)

```java
@Entity
public class Product {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    @NotBlank private String name;
    @DecimalMin("0.0") private BigDecimal price;
}

public interface ProductRepository extends JpaRepository<Product, Long> {
    List<Product> findByNameContainingIgnoreCase(String name);
}

@Service
public class ProductService {
    private final ProductRepository repo;
    public ProductService(ProductRepository repo) { this.repo = repo; } // constructor injection

    @Transactional(readOnly = true)
    public List<Product> search(String name) { return repo.findByNameContainingIgnoreCase(name); }

    @Transactional
    public Product create(ProductRequest request) {
        var product = new Product();
        product.setName(request.name());
        product.setPrice(request.price());
        return repo.save(product);
    }
}

public record ProductRequest(@NotBlank String name, @DecimalMin("0.0") BigDecimal price) {}

@RestController
@RequestMapping("/api/v1/products")
@Validated
public class ProductController {
    private final ProductService service;
    public ProductController(ProductService service) { this.service = service; }

    @GetMapping
    public List<Product> search(@RequestParam(defaultValue = "") String name) { return service.search(name); }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public Product create(@Valid @RequestBody ProductRequest request) { return service.create(request); }
}
```

See `references/web-layer.md` for exception handling (`ProblemDetail`) and `references/data-jpa.md` for more advanced N+1-avoidance/transaction patterns.

## Boundary

This skill decides the Java/Spring implementation: business logic, transaction boundaries, internal
layering, data-access patterns, security/resilience configuration. It does NOT decide the API contract's
shape (that's `api-contract-skill`, which runs BEFORE implementation), does NOT design the DB schema
(that's `database-skill`), and does NOT decide messaging infrastructure detail (that's
`kafka-skill`/`rabbitmq-skill`). It decides *in-service* package structure (`project-structure.md`); it
does NOT decide whether to split into multiple deployable services in the first place — that's
`architecture-designer`'s `deployment-topology.md`/`service-decomposition.md`. It does NOT check the
implementation against foundational design principles (SOLID, coupling/cohesion) as a distinct review
pass — that's `solution-design-principles`'s job, complementary to the concrete Java patterns here.

Decide local technical choices within the task's scope (method structure, exception types, variable
names, how to break down logic) without asking — this is this skill's routine, everyday work. Only stop
to present trade-offs and wait for user approval on a LARGE architectural decision affecting the whole
service and hard to reverse (switching MVC ↔ WebFlux, adding a new runtime framework, changing the
service-discovery/gateway strategy).

## Knowledge Reference

Spring Boot 3.x, Java 21, Spring MVC/WebFlux, Project Reactor, R2DBC, Spring Data JPA, Spring Security 6,
OAuth2/JWT, Spring Cloud (Config/Eureka/Gateway), Resilience4j, Micrometer, Hibernate, JUnit 5, Mockito,
AssertJ, Testcontainers, Maven/Gradle, package-by-layer/package-by-feature, Spring Modulith, Google Java
Style Guide, google-java-format, Spotless, Checkstyle.
