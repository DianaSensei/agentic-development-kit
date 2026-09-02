# Project Setup - Spring Boot 3.x / Java 21

## Project structure (Clean Architecture, reference only - not mandatory if the project already has a different layout)

```
src/main/java/com/example/
├── domain/              # Core business logic
│   ├── model/          # Entities, value objects
│   ├── repository/     # Repository interfaces
│   └── service/        # Domain services
├── application/         # Use cases
│   ├── dto/            # Request/Response DTOs
│   ├── mapper/         # Entity <-> DTO mappers
│   └── service/        # Application services
├── infrastructure/      # External concerns
│   ├── persistence/    # JPA implementations
│   ├── config/         # Spring configuration
│   └── security/       # Security setup
└── presentation/        # API layer
    └── rest/           # REST controllers
```

If the project already has a different layout (e.g. flat Controller/Service/Repository) - keep the existing convention, don't change the directory structure midway on your own.

## pom.xml (Spring Boot 3.2, Java 21)

```xml
<project xmlns="http://maven.apache.org/POM/4.0.0">
    <modelVersion>4.0.0</modelVersion>
    <parent>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-parent</artifactId>
        <version>3.2.1</version>
    </parent>
    <groupId>com.example</groupId>
    <artifactId>demo-service</artifactId>
    <version>1.0.0</version>
    <packaging>jar</packaging>
    <properties>
        <java.version>21</java.version>
        <mapstruct.version>1.5.5.Final</mapstruct.version>
        <testcontainers.version>1.19.3</testcontainers.version>
    </properties>
    <dependencies>
        <dependency><groupId>org.springframework.boot</groupId><artifactId>spring-boot-starter-web</artifactId></dependency>
        <dependency><groupId>org.springframework.boot</groupId><artifactId>spring-boot-starter-data-jpa</artifactId></dependency>
        <dependency><groupId>org.springframework.boot</groupId><artifactId>spring-boot-starter-validation</artifactId></dependency>
        <dependency><groupId>org.postgresql</groupId><artifactId>postgresql</artifactId></dependency>
        <dependency><groupId>org.flywaydb</groupId><artifactId>flyway-core</artifactId></dependency>
        <dependency><groupId>org.mapstruct</groupId><artifactId>mapstruct</artifactId><version>${mapstruct.version}</version></dependency>
        <dependency><groupId>org.springframework.boot</groupId><artifactId>spring-boot-starter-test</artifactId><scope>test</scope></dependency>
        <dependency><groupId>org.testcontainers</groupId><artifactId>postgresql</artifactId><scope>test</scope></dependency>
    </dependencies>
    <build>
        <plugins>
            <plugin><groupId>org.springframework.boot</groupId><artifactId>spring-boot-maven-plugin</artifactId></plugin>
            <plugin>
                <groupId>org.apache.maven.plugins</groupId>
                <artifactId>maven-compiler-plugin</artifactId>
                <configuration>
                    <annotationProcessorPaths>
                        <path><groupId>org.mapstruct</groupId><artifactId>mapstruct-processor</artifactId><version>${mapstruct.version}</version></path>
                        <path><groupId>org.projectlombok</groupId><artifactId>lombok</artifactId></path>
                    </annotationProcessorPaths>
                </configuration>
            </plugin>
        </plugins>
    </build>
</project>
```

## application.yml

```yaml
spring:
  application:
    name: demo-service
  datasource:
    url: ${DATABASE_URL:jdbc:postgresql://localhost:5432/demo}
    username: ${DATABASE_USER:demo}
    password: ${DATABASE_PASSWORD:demo}
    hikari:
      maximum-pool-size: 10
      minimum-idle: 5
      connection-timeout: 20000
  jpa:
    hibernate:
      ddl-auto: validate
    open-in-view: false
    properties:
      hibernate:
        jdbc: { batch_size: 20 }
        order_inserts: true
        order_updates: true
  flyway:
    enabled: true
    baseline-on-migrate: true
    locations: classpath:db/migration

server:
  port: 8080
  shutdown: graceful
  error:
    include-message: always
    include-binding-errors: always

management:
  endpoints:
    web:
      exposure:
        include: health,info,metrics,prometheus
  endpoint:
    health:
      show-details: when-authorized
  metrics:
    export:
      prometheus: { enabled: true }
```

`ddl-auto: validate` (not `update`) - the real schema is managed via Flyway migrations; JPA only validates that it matches the schema rather than auto-generating DDL in real environments (avoiding silent schema drift between instances).

## Main Application Class

```java
@SpringBootApplication
@EnableJpaAuditing
public class DemoServiceApplication {
    public static void main(String[] args) {
        SpringApplication.run(DemoServiceApplication.class, args);
    }
}
```

## OpenAPI Config (if the project exposes Swagger UI)

```java
@Configuration
public class OpenApiConfig {
    @Bean
    public OpenAPI customOpenAPI() {
        return new OpenAPI().info(new Info()
            .title("Demo Service API")
            .version("1.0.0")
            .description("Enterprise microservice API"));
    }
}
```

The actual spec content (paths, schemas, security schemes) is the scope of `api-contract-skill` - this file only sets up the bean that renders Swagger UI from an existing spec.

## Quick Reference

| Component | Purpose |
|-----------|---------|
| `@SpringBootApplication` | Entry point |
| `@Configuration` / `@Bean` | Manual bean declaration |
| `@Value` / `@ConfigurationProperties` | Inject config (prefer `@ConfigurationProperties` for groups of related properties - more type-safe) |
| `@Profile` | Environment-specific beans |
| `@EnableJpaAuditing` | Automatic audit fields (`@CreatedDate`/`@LastModifiedDate`) |
| `ProblemDetail` | RFC 7807 error response - see `references/web-layer.md` |
