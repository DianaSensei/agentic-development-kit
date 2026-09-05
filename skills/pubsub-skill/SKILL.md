---
name: pubsub-skill
description: In-depth Google Cloud Pub/Sub knowledge - topics/subscriptions, push vs. pull, ack deadlines, ordering keys, dead-letter topics, exactly-once delivery. Use when the feature needs Pub/Sub (project already uses a GCP client, or the infrastructure already runs on GCP). If the request only says "async processing" with no technology named, check the actual dependency/infrastructure first - don't default to Pub/Sub; for multi-cloud/on-prem see `kafka-skill`/`rabbitmq-skill`.
metadata:
  domain: messaging
  triggers: GCP messaging, push subscription, pull subscription, dead letter topic
  role: specialist
  scope: implementation
  output-format: code
  related-skills: api-contract-skill, kafka-skill, rabbitmq-skill, architecture-designer
---

# Google Cloud Pub/Sub

## Discover
Confirm the project already uses Pub/Sub via its dependency (`spring-cloud-gcp-starter-pubsub` or a direct GCP client library), read the existing topic/subscription config, and read `api-contract-skill` if a message contract was already finalized there.

## When It Fits
Fits when the infrastructure is already on GCP - fully managed (no broker to operate), auto-scales with load, integrates well with Cloud Run/Functions/Dataflow. For multi-cloud/on-prem, or routing as complex as RabbitMQ's, think carefully before locking into Pub/Sub (GCP vendor lock-in).

## Common Real-World Issues
- **An ordering key can still bottleneck**: Pub/Sub processes sequentially within a single ordering key (similar in spirit to a Kafka partition but a different unit) - if one key is unusually "hot" (disproportionate traffic), that key's throughput is still capped even though other keys run in parallel fine.
- **Per-project GCP quotas**: publish/subscribe throughput and the number of subscriptions/topics all have default quotas - check quota before designing for large traffic; don't assume "serverless means infinite auto-scale."
- **Duplicates still happen even with exactly-once enabled**: if a subscriber crashes AFTER completing the side effect but BEFORE acking, Pub/Sub redelivers - Pub/Sub's exactly-once guarantees no duplicate at the message-delivery layer, not that the side effect runs exactly once; a truly important side effect (a financial transaction) still needs to be genuinely idempotent.

## Topic & Subscription
- One topic can have multiple independent subscriptions (each subscription receives every message - unlike a Kafka consumer group, where members split the messages within one group).
- Naming follows the project's existing convention.

## Push vs. Pull
- **Pull**: the subscriber actively fetches messages (good when processing rate needs to be controlled, or batch processing is needed) - the common choice for backend services.
- **Push**: Pub/Sub calls your HTTP endpoint directly - fits serverless (Cloud Run/Functions), needs a properly public/authenticated endpoint (OIDC token verification).
- For a NEW subscription, choose push or pull based on the existing deployment model (serverless → push; a backend service that wants to control its own processing rate → pull) and state the reasoning. Only ask back when changing the model of a subscription ALREADY RUNNING (affects the deploy config/endpoint currently serving real traffic).

## Ack Deadline & Retry
- The default ack deadline is short (typically 10s) - if processing takes longer, you MUST extend the deadline (`modifyAckDeadline`) or configure a longer one, otherwise the message gets redelivered mid-processing (causing duplicate processing if not idempotent).
- Retry policy: configure exponential backoff instead of leaving the default of immediate redelivery on nack.

## Ordering Key
When per-entity processing order must be guaranteed, use an `ordering key` (requires enabling ordering on the subscription) - plays a similar role to a Kafka partition key but works differently (Pub/Sub guarantees order within the same ordering key, not via physical partitions).

## Dead-Letter Topic
Configure a dead-letter topic + `maxDeliveryAttempts` - after a set number of nacks, the message automatically moves to the dead-letter topic instead of retrying indefinitely.

## Exactly-Once Delivery
Pub/Sub supports exactly-once delivery at the subscription level (a separate setting) - but the consumer should still be idempotent for edge cases (duplicates from publisher retries) unless a publisher-side dedup mechanism is also in place.

## Idempotency
Treat delivery as at-least-once by default unless exactly-once is explicitly enabled - the consumer should always have a dedup key or a check for prior processing before the side effect, which is safe regardless of configuration.

## Test
Use the Pub/Sub emulator (provided by GCP) for local integration tests - test ack/nack behavior, test dead-letter behavior once `maxDeliveryAttempts` is exceeded, test idempotency on duplicate delivery.

## Boundary
For a NEW topic/subscription, choose push/pull and whether to enable ordering/exactly-once based on the described requirement (cross-check `api-contract-skill` if already finalized), and state the reasoning in the report. Only present trade-offs and wait for the user when the change affects a subscription ALREADY RUNNING in production, or the request isn't clear enough to infer from (e.g. unclear whether ordering is required).
