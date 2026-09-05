# Message Contract (Kafka/RabbitMQ/Pub-Sub) - AsyncAPI standard

This skill decides the CONTRACT portion of asynchronous communication. Specific broker
infrastructure details (partitions, consumer groups, ack mode, exchange type) belong to
`kafka-skill`/`rabbitmq-skill` at implementation time - they are not
decided here.

**AsyncAPI is the mandatory standard for message contracts** - it plays the same role
for asynchronous messaging that OpenAPI plays for REST. For new projects or projects
without an existing message contract convention, always use AsyncAPI rather than
inventing an ad-hoc JSON format or free-form descriptive documentation. If the project
already has a different convention in consistent use (e.g. Avro schema via Schema
Registry), keep that convention instead of imposing AsyncAPI on top of it.

## Event Schema - written in AsyncAPI 3.x
- Define `channels` (topic/queue), `messages` (payload schema), `operations`
  (send/receive) following the correct AsyncAPI 3.x structure - see the sample
  skeleton below.
- The payload inside each message is described using JSON Schema - these are not two
  separate choices; AsyncAPI uses JSON Schema as its own payload description language.
- Name topics/queues/exchanges consistently with existing conventions (e.g. Kafka:
  `<domain>.<entity>.<event-past-tense>`, e.g. `order.payment.completed`).

## AsyncAPI 3.x - minimal structure

```yaml
asyncapi: "3.0.0"
info:
  title: Order Events
  version: "1.0.0"
channels:
  order.payment.completed:
    address: order.payment.completed
    messages:
      PaymentCompleted:
        $ref: "#/components/messages/PaymentCompleted"
operations:
  publishPaymentCompleted:
    action: send
    channel:
      $ref: "#/channels/order.payment.completed"
    messages:
      - $ref: "#/channels/order.payment.completed/messages/PaymentCompleted"
components:
  messages:
    PaymentCompleted:
      payload:
        type: object
        required: [order_id, amount, event_version]
        properties:
          order_id:      { type: string, format: uuid }
          amount:        { type: number }
          event_version: { type: integer, default: 1 }
```

## Schema Versioning & Compatibility
- The evolution strategy MUST be backward-compatible: only add optional fields, never
  change the type of an existing field, never remove a field that's in use - this is a
  hard constraint to avoid breaking consumers still running an older version (in an
  asynchronous system, consumers aren't guaranteed to deploy in sync with producers).
- If using a Schema Registry (Avro/Protobuf), follow the configured compatibility mode
  (BACKWARD/FORWARD/FULL) - don't change the mode without understanding the impact.
- If a breaking change is unavoidable → version the event (e.g. an `event_version`
  field in the payload, or a new topic) - don't silently change the shape of an
  existing event.

## Delivery Semantics - this is a REQUIREMENT/contract, not a technical config
- Determine whether the business needs **at-least-once** (common, duplicates
  acceptable, consumer must be idempotent) or **exactly-once** (more complex, only use
  when truly necessary - e.g. financial transactions that cannot tolerate
  double-processing).
- Record the required delivery semantic clearly in the contract - the specific
  implementation mechanism (Kafka transactions, RabbitMQ manual ack, Pub/Sub
  exactly-once subscription) is decided by the corresponding broker's technical skill,
  as long as it satisfies this requirement.

## Consumer Contract (Dead-letter)
- Clearly describe what a consumer should do when it receives a malformed/unparseable
  message: is there a dead-letter topic/queue, who is responsible for handling messages
  there - don't go deep into specific broker configuration (retry count, backoff) at
  this contract layer.

## Choosing a Broker (quick reference - detailed decisions belong to the corresponding
technical skill)
- **Kafka**: high throughput, need historical replay, many independent consumer groups.
- **RabbitMQ**: flexible routing, classic task queues, moderate scale.
- **Google Pub/Sub**: infrastructure already on GCP, don't want to self-manage a
  broker.
- If the project already uses a specific broker, always design the contract to be
  compatible with that broker - don't suggest switching brokers just because it seems
  "more suitable" in theory without a clear requirement.
