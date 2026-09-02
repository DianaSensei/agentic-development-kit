---
name: monitoring-expert
description: Sets up continuous production observability - structured logging pipelines, Prometheus/Grafana metrics and dashboards, distributed tracing, and alerting rules - plus application profiling and capacity forecasting from real production trends. Use when adding observability to a service, debugging production issues via logs/metrics/traces, profiling CPU/memory bottlenecks, or forecasting capacity needs. For a one-off load test gating a merge or release as part of the QA test lifecycle (pass/fail, defect report), use `test-master` instead - this skill's load-testing content targets capacity/production-readiness validation, not CI gating.
metadata:
  domain: devops
  triggers: monitoring, observability, logging, metrics, tracing, alerting, Prometheus, Grafana, DataDog, APM, performance testing, load testing, profiling, capacity planning, bottleneck
  role: specialist
  scope: implementation
  output-format: code
  related-skills: java-spring-skill, architecture-designer, test-master
---

# Monitoring Expert

Observability specialist implementing production monitoring, alerting, distributed tracing, application profiling, and capacity forecasting.

## Core Workflow

1. **Assess** - Identify what needs monitoring (SLIs, critical paths, business metrics)
2. **Instrument** - Add logging, metrics, and traces to the application (see **Three Pillars of Observability** below, then load the matching reference for the stack in use)
3. **Collect** - Configure aggregation and storage (Prometheus scrape, log shipper, OTLP endpoint); verify data arrives before proceeding
4. **Visualize** - Build dashboards using RED (Rate/Errors/Duration) or USE (Utilization/Saturation/Errors) methods
5. **Alert** - Define threshold and anomaly alerts on critical paths; validate no false-positive flood before shipping

## Three Pillars of Observability

This skill's core is stack-agnostic - pick the right pillar for the question being asked, then load the
matching reference for the concrete, language-specific implementation.

- **Logs** - discrete, timestamped events with context. Best for reconstructing exactly what happened
  during one specific request or error. Must be structured (JSON fields), never free-text string
  interpolation, or they stop being queryable at any real volume. → `references/structured-logging.md`
- **Metrics** - numeric time series (counters, gauges, histograms) aggregated over time. Best for
  trends, dashboards, and alert thresholds - not for reconstructing what happened in one specific
  request (that's what logs/traces are for). → `references/prometheus-metrics.md`
- **Traces** - a single request's path across services/functions as connected spans. Best for locating
  where latency or errors originate in a distributed call chain. → `references/opentelemetry.md`

All three need a correlation ID (request ID / trace ID) threaded through, or they can't be cross-referenced
against each other when debugging an incident.

## Alert Design Principles

- Alert on symptoms that affect users or business outcomes (error rate, latency, saturation) - not on
  every possible internal cause. An alert that fires on `errors_total > 0` will always fire and trains
  people to ignore it.
- Every alert must be actionable: if there's no clear next step when it fires, it shouldn't page anyone
  - route it to a lower-severity channel or remove it.
- Use a `for:`-style duration before firing to avoid flapping on transient blips, and route by severity
  (critical → page, warning → investigate soon, info → check later).
- See `references/alerting-rules.md` for concrete Prometheus rule syntax and Alertmanager routing.

## Load Testing & Capacity Planning

- Load testing validates the system holds up at expected (and above-expected) traffic before users find
  out the hard way - ramp up, sustain, ramp down, and assert on latency/error-rate thresholds rather than
  just "it didn't crash."
- Capacity planning projects growth forward from current trends to catch resource exhaustion (CPU,
  memory, disk, connection pools) before it happens, not after an incident.
- See `references/performance-testing.md` (k6/Artillery, test types) and `references/capacity-planning.md`
  (forecasting, resource budgets).

## Reference Guide

Load detailed guidance based on context:

| Topic               | Reference                             | Load When                                                      |
| ------------------- | ------------------------------------- | -------------------------------------------------------------- |
| Logging             | `references/structured-logging.md`    | Pino/structlog JSON logging (Node/Python), Logback JSON (Java) |
| Metrics             | `references/prometheus-metrics.md`    | Counter, Histogram, Gauge (Node/Python), Micrometer (Java)     |
| Tracing             | `references/opentelemetry.md`         | OpenTelemetry, spans (Node/Python/Java agent)                  |
| Alerting            | `references/alerting-rules.md`        | Prometheus alerts                                              |
| Dashboards          | `references/dashboards.md`            | RED/USE method, Grafana                                        |
| Performance Testing | `references/performance-testing.md`   | Load testing, k6, Artillery, benchmarks                        |
| Profiling           | `references/application-profiling.md` | CPU/memory profiling, bottlenecks                              |
| Capacity Planning   | `references/capacity-planning.md`     | Scaling, forecasting, budgets                                  |

## Constraints

### MUST DO

- Use structured logging (JSON)
- Include request IDs for correlation
- Set up alerts for critical paths
- Monitor business metrics, not just technical
- Use appropriate metric types (counter/gauge/histogram)
- Implement health check endpoints

### MUST NOT DO

- Log sensitive data (passwords, tokens, PII)
- Alert on every error (alert fatigue)
- Use string interpolation in logs (use structured fields)
- Skip correlation IDs in distributed systems
- Duplicate a framework's built-in instrumentation (e.g. hand-writing HTTP metrics Spring Boot
  Actuator/Micrometer already expose) instead of configuring and wiring up what already exists
- Make an architectural change (add a cache, split a service, resize infrastructure) on the basis of
  a capacity forecast without the user's/architecture owner's approval - this skill measures and
  projects, it does not decide the response

## Boundaries

- **vs. `test-master`**: both skills touch k6/load testing, so pick based on the goal, not the tool.
  `test-master` owns performance testing as part of the QA/CI test lifecycle - a pass/fail test plan
  gating a merge or release, with defect reports. `monitoring-expert` owns the always-on production
  side - dashboards, alerts, and tracing that run continuously, plus capacity forecasting from real
  production trends (not a one-off test run). A one-off "does this endpoint hold up under load before
  we merge" task is `test-master`; "set up ongoing visibility into this service's health in
  production" is this skill.
- **vs. framework-specific skills** (e.g. `java-spring-skill`): this skill decides *what* to
  instrument and *why* (which pillar, which metric type, what to alert on); language/framework
  implementation specifics live in this skill's own references, and anything already owned by a
  framework skill (e.g. Spring Boot Actuator health/readiness endpoint wiring) is deferred there
  rather than duplicated - see the note in `references/prometheus-metrics.md`.
- **vs. `architecture-designer`**: this skill produces the data (capacity trends, resource
  exhaustion forecasts, profiling results) - it does not decide the architectural response to that
  data (scaling strategy, caching layer, service decomposition). Present the forecast/finding and
  defer the architectural decision to `architecture-designer`.

## Knowledge Reference

Structured logging, correlation IDs, Prometheus metric types (counter/gauge/histogram/summary),
Grafana dashboards, distributed tracing (spans, trace context propagation, sampling), alert design
(symptom-based alerting, alert fatigue, runbooks), SLI/SLO/error budgets, CPU/memory/heap profiling,
capacity forecasting from production trends.
