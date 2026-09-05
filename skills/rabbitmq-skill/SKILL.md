---
name: rabbitmq-skill
description: In-depth RabbitMQ knowledge - exchange types, routing, queue durability, dead-letter exchange, prefetch, quorum queues, priority queues. Use when the feature needs RabbitMQ (project already depends on `spring-boot-starter-amqp` or the user names RabbitMQ explicitly). If the request only says "async processing" with no technology named, check the actual dependency first - don't default to RabbitMQ; for high throughput/replay see `kafka-skill`.
metadata:
  domain: messaging
  triggers: direct exchange, topic exchange, fanout, routing key, dead letter exchange, task queue
  role: specialist
  scope: implementation
  output-format: code
  related-skills: api-contract-skill, kafka-skill, java-spring-skill, testcontainers-skill
---

# RabbitMQ

## Discover
Confirm the project already uses RabbitMQ via its dependency (`spring-boot-starter-amqp`), read the existing exchange/queue config, and read `api-contract-skill` if a message contract was already finalized there - follow it exactly.

## When It Fits / When It Doesn't
Fits: classic task queues, flexible content-based routing (topic/header exchange), fine-grained per-message ack/priority/TTL, moderate throughput. Does NOT fit if history replay is needed - RabbitMQ deletes a message from the queue as soon as a consumer acks it (it's not an immutable log like Kafka); if the business need is "replay from the start" or multiple independent consumer groups each seeing the full event stream, consider `kafka-skill` instead of forcing RabbitMQ into that role.

## Common Real-World Issues
- **Unbounded queue growth**: a slow or long-down consumer with no queue limit → uncontrolled broker memory growth - configure `x-max-length`/`x-max-length-bytes` or a message TTL to prevent the broker running out of memory when a consumer has an outage.
- **Memory/disk alarm**: once the broker hits its configured threshold (`vm_memory_high_watermark`), RabbitMQ automatically BLOCKS publishers (rejects new messages) until enough memory is freed - alert on memory/disk usage BEFORE hitting the threshold, not after publishers are already blocked.
- **Backlog of unacked messages**: a consumer receives a message but crashes before ack/nack - the message stays "unacked" until the connection closes (timeout or consumer restart) and only then gets requeued, which can look like a "stuck message" if this mechanism isn't understood.
- No global ordering guarantee - ordering is only guaranteed within a single queue with a single consumer; multiple consumers on the same queue (round-robin) lose processing order.

## Exchange Types
- **Direct**: clear 1:1 routing by exact routing key.
- **Topic**: pattern-based routing (`order.*.created`) - use when multiple consumers care about different slices of the same event type.
- **Fanout**: broadcasts to every queue bound to the exchange, ignoring the routing key.
- **Headers**: routes by header instead of routing key - rarely used, only when genuinely needed.

## Queue Durability & Reliability
- `durable=true` on queues/exchanges for important data (survives a broker restart).
- Message `persistent` when data must not be lost on a broker crash.
- Consider a **quorum queue** (instead of a classic mirrored queue) for modern high availability - default to a quorum queue for a NEW queue (the current general recommendation). If changing the type of a queue already running in production, ask first - changing type requires recreating the queue (not an in-place change), which can cause downtime or lose messages still waiting to be processed.

## Ack Strategy & Prefetch
- Manual ack when processing must be confirmed complete before acking (safer, but requires correct reject/requeue handling on failure).
- A sensible `prefetch count` matched to consumer processing speed - too high lets one consumer hoard messages while others sit idle; too low reduces throughput.

## Dead-Letter Exchange (DLX)
- Configure a DLX + a clear `x-dead-letter-routing-key` for rejected/TTL-expired/retry-exhausted messages - never let a failed message silently disappear.
- Bound the retry count before routing to the DLX (avoid an infinite loop between the main queue and the DLX).

## Priority Queue (only if the business actually needs it)
`x-max-priority` at queue declaration - only use this when there's a genuinely clear processing-priority requirement; don't add the complexity if plain FIFO is already sufficient.

## Idempotency
The consumer MUST be idempotent under at-least-once delivery (the common default with manual ack + reject-requeue) - use a dedup key or check whether the message was already processed before performing the side effect.

## Test
Testcontainers RabbitMQ for integration tests - test correct ack/requeue behavior, test DLX behavior on message failure, test idempotency on duplicate delivery.

## Boundary
For a NEW exchange/queue, choose the type that best fits the described routing need (state the reasoning briefly), cross-checking `api-contract-skill` if a contract was already finalized there. Only stop to present trade-offs and wait for the user when the change affects an exchange/queue ALREADY RUNNING in production (changing type, changing the routing of messages currently in flight) - these are hard to reverse without downtime.
