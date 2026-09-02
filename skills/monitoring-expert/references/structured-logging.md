# Structured Logging

## Pino (Node.js)

```typescript
import pino from 'pino';

const logger = pino({
  level: process.env.LOG_LEVEL || 'info',
  formatters: {
    level: (label) => ({ level: label }),
  },
  redact: ['password', 'token', 'authorization'],
});

// Structured logging
logger.info({
  event: 'user.login',
  userId: user.id,
  ip: req.ip,
  userAgent: req.headers['user-agent'],
  duration: Date.now() - start,
});

// Error logging with context
logger.error({
  event: 'payment.failed',
  error: err.message,
  stack: err.stack,
  orderId: order.id,
  amount: order.total,
  userId: user.id,
});
```

## Request Logging Middleware

```typescript
import { randomUUID } from 'crypto';

app.use((req, res, next) => {
  const requestId = req.headers['x-request-id'] || randomUUID();
  const start = Date.now();

  res.setHeader('x-request-id', requestId);

  res.on('finish', () => {
    logger.info({
      event: 'http.request',
      requestId,
      method: req.method,
      path: req.path,
      status: res.statusCode,
      duration: Date.now() - start,
      userAgent: req.headers['user-agent'],
      ip: req.ip,
    });
  });

  next();
});
```

## Python (structlog)

```python
import structlog

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
)

logger = structlog.get_logger()

# Structured logging
logger.info(
    "user.login",
    user_id=user.id,
    ip=request.client.host,
    duration=elapsed_time,
)

# Error logging
logger.error(
    "payment.failed",
    error=str(exc),
    order_id=order.id,
    amount=order.total,
)
```

## Java (Spring Boot / Logback)

Spring Boot uses Logback + SLF4J by default. Add `logstash-logback-encoder` to get JSON output instead
of plain text - Spring Boot itself has no built-in JSON encoder.

```xml
<!-- pom.xml -->
<dependency>
    <groupId>net.logstash.logback</groupId>
    <artifactId>logstash-logback-encoder</artifactId>
    <version>8.0</version>
</dependency>
```

```xml
<!-- logback-spring.xml -->
<configuration>
    <appender name="JSON" class="ch.qos.logback.core.ConsoleAppender">
        <encoder class="net.logstash.logback.encoder.LogstashEncoder">
            <includeMdc>true</includeMdc>
        </encoder>
    </appender>
    <root level="INFO">
        <appender-ref ref="JSON" />
    </root>
</configuration>
```

```java
import net.logstash.logback.argument.StructuredArguments;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.slf4j.MDC;

private static final Logger log = LoggerFactory.getLogger(OrderService.class);

// Correlation ID: put requestId in MDC once per request (e.g. in a filter/interceptor),
// includeMdc=true above then adds it to every JSON log line automatically.
MDC.put("requestId", requestId);

// Structured fields via StructuredArguments - prefer this over string concatenation
log.info("order.created", StructuredArguments.kv("orderId", order.getId()),
    StructuredArguments.kv("userId", userId), StructuredArguments.kv("durationMs", elapsed));
```

## Java (Log4j2)

Use this instead of the Logback section above when the project has standardized on Log4j2 (check
`pom.xml`/`build.gradle` for `log4j-core`/`spring-boot-starter-log4j2` before assuming - don't add a
second logging framework alongside whichever one is already in use). Log4j2's API differs from SLF4J:
`ThreadContext` instead of `MDC`, and no `StructuredArguments`-style key-value helper - use a
`MapMessage` for structured fields instead.

```xml
<!-- pom.xml - Spring Boot excludes its default Logback starter when switching to Log4j2 -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter</artifactId>
    <exclusions>
        <exclusion>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-logging</artifactId>
        </exclusion>
    </exclusions>
</dependency>
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-log4j2</artifactId>
</dependency>
<dependency>
    <groupId>org.apache.logging.log4j</groupId>
    <artifactId>log4j-layout-template-json</artifactId>
</dependency>
```

```xml
<!-- log4j2-spring.xml - JsonTemplateLayout with the built-in Logstash-compatible template -->
<Configuration status="WARN">
    <Appenders>
        <Console name="JSON" target="SYSTEM_OUT">
            <JsonTemplateLayout eventTemplateUri="classpath:LogstashJsonEventLayoutV1.json" />
        </Console>
    </Appenders>
    <Loggers>
        <Root level="INFO">
            <AppenderRef ref="JSON" />
        </Root>
    </Loggers>
</Configuration>
```

```java
import org.apache.logging.log4j.CloseableThreadContext;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.apache.logging.log4j.message.MapMessage;

private static final Logger log = LogManager.getLogger(OrderService.class);

// Correlation ID: ThreadContext is Log4j2's MDC equivalent - CloseableThreadContext
// auto-clears on close(), avoiding leaked context across requests on pooled threads.
try (var ignored = CloseableThreadContext.put("requestId", requestId)) {
    // Structured fields via MapMessage - the built-in Logstash template above
    // serializes these as top-level JSON fields, not string-concatenated.
    MapMessage<?, ?> msg = new MapMessage<>()
        .with("event", "order.created")
        .with("orderId", order.getId())
        .with("userId", userId)
        .with("durationMs", elapsed);
    log.info(msg);
}
```

## Log Levels

| Level | Use Case |
|-------|----------|
| `error` | Failures needing attention |
| `warn` | Potential problems |
| `info` | Business events, requests |
| `debug` | Development details |
| `trace` | Verbose debugging |

## Best Practices

```typescript
// Good: Structured fields
logger.info({ event: 'order.created', orderId: '123', total: 99.99 });

// Bad: String interpolation
logger.info(`Order 123 created with total 99.99`);

// Good: Consistent event names
logger.info({ event: 'user.registered' });
logger.info({ event: 'user.login' });
logger.info({ event: 'user.logout' });

// Good: Include correlation ID
logger.info({ event: 'request.processed', requestId, userId });
```

## Quick Reference

| Field | Purpose |
|-------|---------|
| `event` | Event name |
| `requestId` | Correlation ID |
| `userId` | User context |
| `duration` | Timing info |
| `error` / `stack` | Error details |
| `timestamp` | When (auto-added) |

| Library | Language |
|---------|----------|
| pino | Node.js |
| structlog | Python |
| slog | Go |
| logrus | Go |
| Logback + logstash-logback-encoder | Java |
| Log4j2 + log4j-layout-template-json | Java |
