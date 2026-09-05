---
name: messaging-skill
description: In-depth broker knowledge for asynchronous messaging - Apache Kafka (topic/partition design, consumer groups, delivery semantics, idempotency, schema evolution, dead-letter topics, consumer lag) and RabbitMQ (exchange types, routing, queue durability, dead-letter exchange, prefetch, quorum and priority queues), plus how to choose between them. Use when a feature publishes or consumes messages through a broker. If the request only says "async processing" with no technology named, check the project's actual dependency first rather than defaulting to either.
metadata:
  domain: messaging
  triggers: Kafka, RabbitMQ, topic, partition, consumer group, offset, consumer lag, rebalance, idempotent producer, dead letter topic, event streaming, replay, exchange, routing key, fanout, dead letter exchange, prefetch, quorum queue, task queue, delivery semantics
  role: specialist
  scope: implementation
  output-format: code
  related-skills: api-contract-skill, java-spring-skill, test-master, monitoring-expert, redis-skill
---

# Messaging - Kafka & RabbitMQ

## Discover

Confirm which broker the project actually uses from its dependency (`spring-kafka` or an equivalent
Kafka client; `spring-boot-starter-amqp` for RabbitMQ) and read the existing topic/exchange/queue
config. **Never default to one because the request said "async"** - check first.

If `api-contract-skill` already finalized a message contract (schema, topic/queue name, required
delivery semantics), follow it exactly. Don't redefine it here.

## Choosing between them

Only relevant when nothing is established yet - if the project already runs one broker, use it.

**Kafka** - an immutable, replayable log. Pick it for high throughput, replaying history, several
independent consumer groups each reading the same stream, or event sourcing.

**RabbitMQ** - a queue that deletes a message once acked. Pick it for classic task queues,
content-based routing (topic/header exchange), fine-grained per-message ack/priority/TTL, or moderate
throughput where Kafka's operational cost (broker cluster, partition and consumer-group tuning) isn't
worth it.

The two decisive questions:

- **Does anything need to replay history, or does more than one independent consumer need the full
  stream?** Only Kafka can do that - RabbitMQ drops a message the moment it's acked.
- **Is routing content-based, or does a message need its own priority/TTL?** That's RabbitMQ's
  strength; Kafka has no equivalent.

## Rules that apply to both

- **At-least-once is the normal case, so the consumer MUST be idempotent** - a dedup key, or a check
  for "already processed" before performing the side effect. Design this in from the start; it's not a
  hardening pass added later.
- **Every failure path ends at a dead-letter destination, with a bounded retry count.** Never retry a
  message in place forever.
- **For anything NEW** (topic, exchange, queue, delivery semantics), pick the option that best fits what
  is already known and state the reasoning in the report. Stop and present trade-offs only when there
  isn't enough information to estimate (throughput or consumer count unknown), or when the change
  touches something **already running in production**.
- **Test with Testcontainers** (see `test-master/references/testcontainers.md`): the delivery/ack
  semantics actually implemented, idempotency under duplicate delivery, and dead-letter behavior on a
  processing failure. Pure business-logic unit tests → `java-spring-skill`.

## Kafka

### Topic & partition design

- Naming follows the project's existing convention (e.g. `<domain>.<entity>.<event-past-tense>`).
- **Partition key** keeps messages for one entity on one partition, preserving per-entity order. Never
  use a random key when order matters.
- **Partition count is the hard ceiling on consumer parallelism, and it is close to irreversible.**
  Kafka cannot decrease it - only increase, and a new topic is the only way down. Increasing it later
  breaks the "same key always lands on the same partition" guarantee for existing keys, because the
  hash-modulo-partition-count result changes. If per-entity ordering matters, choose generously up
  front rather than growing into it.

### Consumer groups & rebalancing

- One clear consumer group per consuming service - sharing a group across unrelated services causes
  unintended message contention.
- Tune `max.poll.records`/`session.timeout.ms` from measured evidence (lag, average processing time).
  With no measurements yet, keep the current production config and say measurement is needed rather than
  guessing.

### Delivery semantics

- **At-least-once** (most common) - see the shared idempotency rule above.
- **Exactly-once** - Kafka transactions (`transactional.id`, `isolation.level=read_committed`). Higher
  complexity; use only when genuinely necessary and state the trade-off. **Its scope is Kafka-internal
  only** (consume-transform-produce): a side effect written outside Kafka - a direct DB write, an HTTP
  call - still has to be idempotent on its own, because no Kafka transaction covers it.
- **Producer durability** - `acks=all` + `enable.idempotence=true` when the producer must not lose or
  duplicate.

### Schema evolution

Backward compatibility is mandatory: add optional fields only, never change the type of or remove a
field in use (with Schema Registry + Avro/Protobuf, follow the configured compatibility mode). If a
breaking change is unavoidable, version the event - never silently change an existing event's shape.

### Dead-letter & error handling

A clear dead-letter topic, with `SeekToCurrentErrorHandler`/`DefaultErrorHandler` (Spring Kafka)
applying bounded retry before routing to it.

### Common real-world issues

- **Rebalance storm** - consumers repeatedly joining/leaving (crash loops, `session.timeout.ms` too
  short) stall the whole group on every rebalance. Use the cooperative-sticky assignor (partial
  rebalance) instead of the older eager default where the client version supports it.
- **False "dead" consumer** - processing one message for longer than `max.poll.interval.ms` makes the
  broker declare the consumer dead and rebalance, even though it's running fine. The cause is slow
  processing between polls, not a lost connection.
- **In-place retry breaks ordering** - blocking retry inside the consumer loop delays every other
  message on that partition, including ones under a different key. Use a separate retry topic when
  cross-key ordering matters.
- **Message size** - exceeding the ~1MB default requires raising **both** `max.request.size` (producer)
  and `message.max.bytes`/`replica.fetch.max.bytes` (broker). Raising one side alone still fails.

### Monitoring (flag only, don't build a dashboard)

Consumer lag is the single most important metric. Flag it in the report if a feature could push
processing slower than the produce rate, so the user can consider scaling consumers.

## RabbitMQ

### Exchange types

- **Direct** - exact routing-key match, 1:1.
- **Topic** - pattern routing (`order.*.created`), for consumers each caring about a different slice of
  the same event type.
- **Fanout** - broadcasts to every bound queue, ignoring the routing key.
- **Headers** - routes on headers instead of routing key. Rarely worth it.

### Durability & reliability

- `durable=true` on queues/exchanges for important data (survives a broker restart), and `persistent`
  messages when data must survive a broker crash.
- **Default a NEW queue to a quorum queue** rather than a classic mirrored queue. Changing the type of a
  queue already in production requires recreating it - not an in-place change - so it risks downtime or
  losing messages still waiting; ask first in that case.

### Ack strategy & prefetch

Manual ack when processing must be confirmed complete before acking (safer, but requires correct
reject/requeue handling on failure). Match `prefetch count` to consumer processing speed - too high lets
one consumer hoard while others idle, too low costs throughput.

### Dead-letter exchange

Configure a DLX plus a clear `x-dead-letter-routing-key` for rejected, TTL-expired, and
retry-exhausted messages - never let a failed message vanish silently. Bound the retry count so the main
queue and DLX can't loop forever.

### Priority queue

`x-max-priority` at declaration, only when there's a genuinely clear processing-priority requirement.
Don't add the complexity when plain FIFO already works.

### Common real-world issues

- **Unbounded queue growth** - a slow or long-down consumer with no queue limit grows broker memory
  without bound. Set `x-max-length`/`x-max-length-bytes` or a message TTL.
- **Memory/disk alarm** - at `vm_memory_high_watermark` RabbitMQ **blocks publishers** outright until
  memory frees up. Alert on memory/disk *before* the threshold, not after publishing has already stopped.
- **Backlog of unacked messages** - a consumer that receives a message then crashes before ack/nack
  leaves it "unacked" until the connection closes (timeout or restart) and only then requeued. Looks
  exactly like a stuck message if you don't know the mechanism.
- **No global ordering** - order holds only within a single queue with a single consumer. Multiple
  consumers round-robin off one queue and lose it.
