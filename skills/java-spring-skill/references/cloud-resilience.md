# Cloud Native - Spring Cloud, Resilience4j, Actuator

Only apply this when the project is genuinely a microservices setup that needs these components - don't add Config Server/Eureka/Gateway to a single standalone service just because it's "best practice"; this is heavy infrastructure that only makes sense when there are multiple services that need to share config or discover each other.

## Spring Cloud Config (Server + Client)

```yaml
# Config Server application.yml
spring:
  cloud:
    config:
      server:
        git:
          uri: https://github.com/example/config-repo
          default-label: main

# Config Client application.yml
spring:
  config:
    import: "configserver:http://localhost:8888"
```

```java
@RestController
@RefreshScope // allows reloading the value on POST /actuator/refresh, without restarting the service
public class ConfigController {
    @Value("${app.feature.enabled:false}")
    private boolean featureEnabled;
}
```

## Service Discovery - Eureka

```yaml
# Eureka Client
spring:
  application:
    name: user-service
eureka:
  client:
    service-url: { defaultZone: http://localhost:8761/eureka/ }
  instance:
    prefer-ip-address: true
```

## Spring Cloud Gateway - routing + circuit breaker + rate limit

```java
@Bean
public RouteLocator customRouteLocator(RouteLocatorBuilder builder) {
    return builder.routes()
        .route("user-service", r -> r.path("/api/users/**")
            .filters(f -> f
                .circuitBreaker(c -> c.setName("userServiceCircuitBreaker").setFallbackUri("forward:/fallback/users"))
                .retry(c -> c.setRetries(3).setStatuses(HttpStatus.SERVICE_UNAVAILABLE)))
            .uri("lb://user-service"))
        .build();
}
```

## Resilience4j - Circuit Breaker / Retry / Rate Limiter

Used for calls that depend on other services - protects the current service from cascading failure when a dependency is slow or down.

```java
@Service
@RequiredArgsConstructor
public class ExternalApiService {
    private final WebClient webClient;

    @CircuitBreaker(name = "externalApi", fallbackMethod = "getFallbackData")
    @Retry(name = "externalApi")
    @RateLimiter(name = "externalApi")
    public Mono<ExternalData> getData(String id) {
        return webClient.get().uri("/data/{id}", id).retrieve()
            .bodyToMono(ExternalData.class).timeout(Duration.ofSeconds(3));
    }

    private Mono<ExternalData> getFallbackData(String id, Exception e) {
        log.warn("Fallback triggered for id={}: {}", id, e.getMessage());
        return Mono.just(ExternalData.fallback(id));
    }
}
```

```yaml
resilience4j:
  circuitbreaker:
    instances:
      externalApi:
        sliding-window-size: 10
        minimum-number-of-calls: 5
        failure-rate-threshold: 50
        wait-duration-in-open-state: 5s
  retry:
    instances:
      externalApi: { max-attempts: 3, wait-duration: 1s, enable-exponential-backoff: true }
  ratelimiter:
    instances:
      externalApi: { limit-for-period: 10, limit-refresh-period: 1s }
```

## Distributed Tracing - Micrometer Tracing

```yaml
management:
  tracing:
    sampling: { probability: 1.0 }
  zipkin:
    tracing: { endpoint: http://localhost:9411/api/v2/spans }
```

`sampling.probability: 1.0` (100% tracing) only makes sense in dev/staging or for low-traffic services - high-traffic production should lower this (e.g. `0.1`) to avoid overhead, unless you're temporarily debugging a specific incident that needs full tracing.

## Health Checks & Actuator

```java
@Component
public class CustomHealthIndicator implements HealthIndicator {
    @Override
    public Health health() {
        return checkExternalService()
            ? Health.up().withDetail("externalService", "Available").build()
            : Health.down().withDetail("externalService", "Unavailable").build();
    }
}
```

```yaml
management:
  endpoints:
    web:
      exposure: { include: health,info,metrics,prometheus }
  endpoint:
    health: { show-details: always, probes: { enabled: true } }
  health:
    livenessState: { enabled: true }
    readinessState: { enabled: true }
```

Keeping `livenessState`/`readinessState` separate matters for Kubernetes: a liveness failure restarts the pod; a readiness failure removes the pod from the load balancer but does NOT restart it (use the right probe for the right purpose - mixing these up causes unnecessary restart loops when a service is merely temporarily not ready to receive traffic, e.g. while warming up a cache).

## Kubernetes Deployment (minimal reference)

```yaml
spec:
  containers:
  - name: user-service
    image: user-service:1.0.0
    livenessProbe: { httpGet: { path: /actuator/health/liveness, port: 8080 }, initialDelaySeconds: 60 }
    readinessProbe: { httpGet: { path: /actuator/health/readiness, port: 8080 }, initialDelaySeconds: 30 }
    resources:
      requests: { memory: "512Mi", cpu: "500m" }
      limits: { memory: "1Gi", cpu: "1000m" }
```

## Quick Reference

| Component | Purpose |
|-----------|---------|
| Config Server | Centralized config for multiple services |
| Eureka | Service discovery |
| Gateway | Routing/filtering/load balancing at a single entry point |
| Resilience4j | Circuit breaker/retry/rate-limiter for calls to other services |
| Micrometer Tracing | Distributed tracing across multiple services |
| Actuator | Production-ready health/metrics |
