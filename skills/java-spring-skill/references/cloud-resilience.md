# Cloud Native — Spring Cloud, Resilience4j, Actuator

Chỉ áp dụng khi project thật sự là microservices cần các thành phần này — không tự thêm Config Server/Eureka/Gateway cho 1 service đơn lẻ chỉ vì "best practice", đây là hạ tầng nặng, chỉ hợp lý khi có nhiều service cần chia sẻ config/tự discover nhau.

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
@RefreshScope // cho phép reload giá trị khi POST /actuator/refresh, không cần restart service
public class ConfigController {
    @Value("${app.feature.enabled:false}")
    private boolean featureEnabled;
}
```

## Service Discovery — Eureka

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

## Spring Cloud Gateway — routing + circuit breaker + rate limit

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

## Resilience4j — Circuit Breaker / Retry / Rate Limiter

Dùng cho lời gọi phụ thuộc service khác — bảo vệ service hiện tại khỏi cascading failure khi dependency chậm/down.

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

## Distributed Tracing — Micrometer Tracing

```yaml
management:
  tracing:
    sampling: { probability: 1.0 }
  zipkin:
    tracing: { endpoint: http://localhost:9411/api/v2/spans }
```

`sampling.probability: 1.0` (trace 100%) chỉ hợp lý ở dev/staging hoặc service traffic thấp — production traffic cao nên giảm xuống (VD `0.1`) để tránh overhead, trừ khi đang debug sự cố cụ thể cần trace đầy đủ tạm thời.

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

`livenessState`/`readinessState` riêng biệt quan trọng cho Kubernetes: liveness fail → pod bị restart; readiness fail → pod bị rút khỏi load balancer nhưng KHÔNG restart (dùng đúng probe cho đúng mục đích, nhầm lẫn 2 cái này gây restart loop không cần thiết khi service chỉ đang tạm thời không sẵn sàng nhận traffic, VD đang warm up cache).

## Kubernetes Deployment (tham khảo tối thiểu)

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
| Config Server | Config tập trung cho nhiều service |
| Eureka | Service discovery |
| Gateway | Routing/filter/load balancing tại 1 điểm vào |
| Resilience4j | Circuit breaker/retry/rate-limiter cho call ra service khác |
| Micrometer Tracing | Distributed tracing xuyên nhiều service |
| Actuator | Health/metrics production-ready |
