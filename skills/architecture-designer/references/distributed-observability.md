# Observability in Distributed Systems

This file covers what's specific to *distributed* observability - correlating signals across service
boundaries, SLOs/error budgets, dependency mapping, and multi-service incident debugging. For the
actual logging/metrics/tracing instrumentation itself (structured logging setup, Prometheus metric
types, OpenTelemetry SDK configuration, alert rule syntax, tool selection) see `monitoring-expert` -
that skill owns the pillars themselves; this file assumes them and focuses on what changes when a
request spans multiple services instead of one.

## Why Distributed Observability Is Different

A single service can often be debugged from its own logs. A distributed request cannot: the failure
might be in any of N services, so the something all three pillars need is a way to correlate them
*across* service boundaries, not just within one:

- **Correlation ID propagation** - every service a request touches must accept an incoming
  correlation/trace ID (or generate one if absent, as the entry point) and forward it to every
  downstream call it makes - HTTP headers, message headers, and log context alike. A gap anywhere in
  this chain breaks the ability to reconstruct the full request path later.
- **Distributed tracing** - a **trace** is the full journey of one request across every service it
  touched; a **span** is one operation within that trace (one HTTP call, one DB query), with a parent
  span linking it back to what triggered it. The trace is what turns "service X is slow" into "service
  X is slow because it's waiting on service Y's database query" - see `monitoring-expert` for how to
  actually instrument spans; this file is about *why* the trace must span every service, not drop at a
  boundary.
- **Sampling at the architecture level** - tracing every request is expensive at scale, so sampling
  strategy is itself an architecture decision made once, consistently, across all services (not
  per-service): probabilistic (trace N% uniformly), tail-based (always trace errors and slow requests,
  sample the rest), or priority-based (always trace premium users / critical endpoints). Whichever is
  chosen must be applied consistently, or traces break at the boundary where sampling policy changes.

## Service Level Objectives (SLOs)

### Defining SLOs

**SLI (Service Level Indicator):**
```
Quantitative measure of service level

Examples:
- Request latency: p99 < 200ms
- Availability: 99.9% of requests succeed
- Throughput: Handle 10,000 requests/sec
```

**SLO (Service Level Objective):**
```
Target value for SLI

Examples:
- 99.9% of requests complete in < 200ms
- 99.95% availability over 30 days
- Zero data loss

SLO Components:
- Metric: What you measure (latency, availability)
- Target: Threshold (99.9%, 200ms)
- Time window: Evaluation period (30 days, weekly)
```

**SLA (Service Level Agreement):**
```
Contract with consequences if SLO not met

Example:
- SLO: 99.9% availability
- SLA: If availability < 99.9%, customers get 10% credit

SLA ≤ SLO (leave buffer for incidents)
```

**Error Budget:**
```
Allowed failure to meet SLO = (100% - SLO target)

Example:
SLO: 99.9% availability
Error budget: 0.1% = 43.8 minutes downtime per month

Error budget consumed:
- Outages
- Slow responses
- Failed requests

When error budget exhausted:
- Freeze feature deployments
- Focus on reliability
- Only critical fixes deployed

Benefits:
- Balances innovation vs stability
- Data-driven deployment decisions
- Aligns engineering priorities
```

In a distributed system, define an SLO per service boundary that other services depend on, not just
one SLO for the system as a whole - a downstream service's SLO is effectively a contract the upstream
services are implicitly relying on when they set their own SLOs, so an unbudgeted downstream SLO makes
every upstream SLO built on top of it meaningless.

### SLO Monitoring (PromQL Sketch)

```
# SLI: Availability
availability_sli = (
    sum(rate(http_requests_total{status!~"5.."}[30d]))
    /
    sum(rate(http_requests_total[30d]))
) * 100

# Error Budget
error_budget_remaining = (
    1 - (target_slo / 100)
) - (
    1 - (availability_sli / 100)
)

Alert when error budget < 10%:
alert: ErrorBudgetCritical
expr: error_budget_remaining < 0.1
annotations:
  summary: "Error budget critically low"
  description: "Only 10% error budget remaining. Freeze deployments."
```

For the full Prometheus alerting rule syntax and Alertmanager routing setup, see
`monitoring-expert`'s `references/alerting-rules.md` - the query above is the SLO-specific shape to
add on top of that general alerting setup.

## Dependency Mapping

A service dependency graph (which service calls which, and how critical each edge is) is a
distributed-observability deliverable in its own right - it's what turns "service X is down" into
"here are the N services whose SLOs are now at risk because they depend on X," and it's the input to
deciding where circuit breakers and fallbacks are actually necessary (see
`references/resilience-patterns.md`). Distributed tracing data is the most reliable source for
building this graph automatically (span parent/child relationships across services reveal real
call patterns, which are often out of date in whatever diagram was last drawn by hand).

## Troubleshooting Workflow

**Incident Response:**
```
1. Detect (Alert fires)
   - Check dashboard
   - Verify alert is valid
   - Assess impact

2. Triage (Determine severity)
   - Critical: Page on-call
   - Warning: Create ticket
   - How many users affected?
   - What functionality broken?

3. Investigate (Find root cause)
   - Check recent deployments
   - Review logs (search by correlation ID)
   - Analyze traces (slow operations)
   - Check metrics (resource saturation)
   - Examine dependencies

4. Mitigate (Stop the bleeding)
   - Rollback deployment
   - Scale up resources
   - Failover to backup
   - Enable circuit breakers
   - Rate limit traffic

5. Resolve (Fix root cause)
   - Deploy fix
   - Verify resolution
   - Monitor for recurrence

6. Post-mortem (Learn and improve)
   - Timeline of events
   - Root cause analysis
   - Action items
   - Update runbooks
```

**Using Traces to Debug a Multi-Service Failure:**
```
Scenario: API returning 500 errors

1. Find failing trace:
   - Filter: status = error, service = api-gateway
   - Sort by timestamp (most recent)

2. Analyze span waterfall:
   - Identify which service failed (order-service returned 500)
   - Check error message in span
   - Review span attributes

3. Correlate with logs:
   - Extract trace ID from failed trace
   - Search logs: traceId:"trace-abc123"
   - Find exception stack trace

4. Check related metrics:
   - order-service error rate spiked 10 min ago
   - Corresponds with deployment
   - Likely cause: Bad deployment

5. Remediate:
   - Rollback order-service
   - Verify errors stopped
   - Create ticket for bug fix
```

This is the concrete payoff of correlation ID propagation and distributed tracing being set up
correctly ahead of time (see above) - without them, step 2-3 above degenerates into manually
cross-referencing timestamps across N services' separate logs, which doesn't reliably work once
request volume is more than trivial.

## Architecture-Level Readiness Checklist

**For Each Service (design-time requirement, not just an ops checklist):**
```
✓ Structured logging with correlation IDs
✓ Metrics exported
✓ Distributed tracing instrumented
✓ Health check endpoints (/health/live, /health/ready)
✓ Graceful shutdown handling
✓ Alerts configured for critical paths
✓ Runbooks documented
```

**For the System as a Whole:**
```
✓ Centralized log aggregation
✓ Distributed tracing backend
✓ Consistent sampling policy across all services
✓ Unified dependency map (see above)
✓ SLO definitions per service boundary that other services depend on
✓ Alert routing configured
✓ Incident management process
✓ Post-mortem template
```

A service that's missing any of these is not actually ready to be a dependency other services rely
on - treat this checklist as part of the service's Definition of Done during decomposition (see
`references/service-decomposition.md`), not as something bolted on after the service is already live.

## Summary

Observability is non-negotiable in distributed systems, specifically because failure diagnosis that
works fine within one service (grep the logs) stops working once a request crosses service
boundaries. The distributed-specific must-haves are: correlation IDs that actually propagate end to
end, distributed tracing that doesn't drop at any service boundary, a consistent sampling policy, and
SLOs defined at every service boundary another service depends on. Everything else (what tool to use
for logs/metrics/tracing, how to instrument a specific language/framework) is `monitoring-expert`'s
job, not this file's.
