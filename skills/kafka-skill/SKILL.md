---
name: kafka-skill
description: In-depth Apache Kafka knowledge - topic/partition design, consumer groups, delivery semantics, idempotency, schema evolution, dead-letter handling, lag monitoring. Use when the feature needs Kafka (project already depends on `spring-kafka` or an equivalent client, or the user names Kafka explicitly). If the request only says "async processing" with no technology named, check the actual dependency first - don't default to Kafka; for a simple queue see `rabbitmq-skill`, for GCP see `pubsub-skill`.
metadata:
  domain: messaging
  triggers: offset, idempotent producer, dead letter topic, consumer lag, rebalance, event streaming, replay
  role: specialist
  scope: implementation
  output-format: code
  related-skills: api-contract-skill, rabbitmq-skill, pubsub-skill, java-spring-skill, testcontainers-skill, monitoring-expert
---

# Apache Kafka

## Discover
Confirm the project already uses Kafka via its dependency (`spring-kafka` or the equivalent client library), read the existing topic/config, and read `api-contract-skill` if a message contract (schema, topic name, required delivery semantics) was already finalized there - follow it exactly, don't redefine it here.

## When It Fits / When It Doesn't
Fits: high throughput, need to replay history (log-based), multiple independent consumer groups reading the same event stream, event sourcing. Prefer RabbitMQ (`rabbitmq-skill`) over Kafka if: complex content-based routing is needed (topic/header exchange), a priority queue is needed, or the scale is small enough that Kafka's much higher operational cost (broker cluster, partition/consumer-group tuning) isn't worth it for a simple task queue.

## Common Real-World Issues
- **Rebalance storm**: consumers repeatedly joining/leaving (crash loops, `session.timeout.ms` too short) stalls the whole consumer group on every rebalance - consider the cooperative-sticky assignor (partial rebalance, doesn't stop the whole group) instead of the older default eager assignor, if the client version supports it.
- **False "dead" consumer**: processing one message longer than `max.poll.interval.ms` makes the broker think the consumer died and triggers a rebalance even though it's still running - this is caused by slow processing between polls, not a lost connection.
- **In-place retry breaks ordering**: blocking retry inside the consumer loop for a failed message can delay processing of other messages on the same partition (even under a different key) - use a separate retry topic instead of blocking retry if ordering across different keys matters.
- **Message size**: exceeding the default limit (~1MB) requires raising BOTH `max.request.size` (producer) AND `message.max.bytes`/`replica.fetch.max.bytes` (broker) together - raising only one side still fails.
- **Exactly-once has limited scope**: Kafka transactions only guarantee exactly-once within the Kafka system itself (consume-transform-produce). If a consumer writes a side effect to something OUTSIDE Kafka (a direct DB write, an HTTP call), that effect still needs to be idempotent on its own - a Kafka transaction can't protect a side effect outside its scope.

## Topic & Partition Design
- Naming follows the project's existing convention (e.g. `<domain>.<entity>.<event-past-tense>`).
- Partition key: choose a key that keeps messages for the same entity on the same partition (preserves per-entity processing order) - do NOT choose a random key if order matters.
- Partition count: weigh expected throughput against the expected number of consumer instances (partition count is the hard ceiling on parallelism). **Hard constraint**: Kafka does NOT support decreasing a topic's partition count (only increasing - a new topic is required to decrease), and increasing it later breaks the "same key always lands on the same partition" guarantee for existing keys (the hash-modulo-partition-count result changes). If per-entity ordering matters, pick a generous partition count up front rather than growing it later. For a NEW topic, choose a reasonably generous partition count based on the known throughput/consumer expectations and state the reasoning - only ask the user back when there isn't enough information to estimate throughput (not just because this is "a big decision" in the abstract).

## Consumer Group & Rebalancing
- Clear consumer group names per consuming service - don't share one group across unrelated services (causes unintended message contention).
- Consider `max.poll.records`/`session.timeout.ms` if slow processing is causing repeated rebalances - propose and apply a reasonable value based on measured evidence (lag, average processing time); if no measurements exist yet, keep the current production config and state that measurement is needed before changing it, rather than guessing.

## Delivery Semantics & Idempotency
- At-least-once (most common): the consumer MUST be idempotent (a dedup key, or checking whether it already processed this message before performing the side effect).
- Exactly-once: use Kafka transactions (`transactional.id`, `isolation.level=read_committed`) when needed - higher complexity cost, only use when genuinely necessary, and state the trade-off.
- Producer: `acks=all` + `enable.idempotence=true` when the producer side must not lose or duplicate messages.

## Schema Evolution
- Backward compatibility is mandatory: only add optional fields, never change the type of or remove a field in use (if using Schema Registry + Avro/Protobuf, follow the configured compatibility mode).
- Version the event if a breaking change is unavoidable - never silently change an existing event's shape.

## Dead-Letter & Error Handling
- Define a clear dead-letter topic for messages that fail processing (no infinite in-place retry).
- `SeekToCurrentErrorHandler`/`DefaultErrorHandler` (Spring Kafka) with bounded retry before routing to the DLT.

## Monitoring to Flag (note only, don't build a dashboard)
Consumer lag is the single most important metric - flag in the output if a feature could cause high lag (processing slower than produce rate), so the user can consider scaling the consumer.

## Test
Testcontainers Kafka for integration tests - test the delivery semantics actually implemented, test idempotency on duplicate consumption, test dead-letter behavior on processing failure. For pure business-logic unit tests, see `java-spring-skill`.

## Boundary
For a NEW topic, choose the most sensible partition count/delivery semantics based on what's already known (cross-check `api-contract-skill` if already finalized there), and state the choice and reasoning in the report. Only stop to present trade-offs and wait for the user when there isn't enough information to estimate (throughput/consumer count unknown), or when the change affects a topic ALREADY RUNNING in production.
