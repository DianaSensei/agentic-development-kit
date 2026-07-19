# Protocol Comparison — REST vs GraphQL vs RPC vs Message

Choose the right protocol for the RIGHT type of communication — a wrong choice here is
hard to fix later because many clients/consumers will depend on it.

## REST (OpenAPI)
- Suitable for: public APIs, APIs facing the browser directly, needing native HTTP
  caching (cacheable GET), diverse clients you don't control (mobile, third-party).
- Advantages: easy to debug (curl/browser), widespread tooling, familiar HTTP
  semantics.
- Disadvantages: over-fetching/under-fetching (clients must call multiple endpoints or
  receive excess fields), versioning must be managed manually via URL/header.

## GraphQL
- Suitable for: clients that need flexibility in choosing which fields to return
  (mobile wants fewer fields than web), many different client types with different
  data needs for the SAME domain, avoiding over-fetching.
- Advantages: single endpoint, self-documenting schema, versioning via field
  deprecation instead of URL.
- Disadvantages: HTTP caching isn't as natural as REST (needs application-layer
  caching/persisted queries), risk of N+1 at the resolver layer if not careful, harder
  to secure correctly (rate-limiting by query complexity, not request count).

## RPC (gRPC/Protobuf)
- Suitable for: INTERNAL service-to-service communication needing high performance,
  streaming (server/client/bidirectional), type-safety via codegen between services in
  the same ecosystem.
- Advantages: faster than REST (binary + HTTP/2 multiplexing), tight contracts via
  `.proto`.
- Disadvantages: NOT suitable for a public API facing the browser directly (needs a
  proxy like grpc-web), harder to debug manually than REST (needs a dedicated tool
  like `grpcurl`).

## Message (Kafka/RabbitMQ/Pub-Sub)
- Suitable for: ASYNCHRONOUS communication — no immediate response needed, need to
  decouple producer/consumer, need retry/replay capability, one-to-many consumers
  interested in the same event.
- Not suitable for: needing an immediate response within the same request (use
  REST/RPC), business flows requiring strong consistency right away (use synchronous
  transactions).
- See `references/message-contract.md` to choose the right broker (Kafka vs RabbitMQ
  vs Pub/Sub) — that decision belongs to the corresponding broker's technical skill,
  not this skill.

## Quick decision rules
1. Need an immediate response + public/browser-facing → **REST**.
2. Need an immediate response + client needs field flexibility/many different client
   types → **GraphQL**.
3. Need an immediate response + internal service-to-service + high performance →
   **RPC**.
4. Don't need an immediate response, need decoupling/replay/multiple consumers →
   **Message**.

If a requirement could reasonably go multiple ways — decide using the rules above and
briefly state the reasoning in the report; no need to ask unless this is a decision
that affects many services already running in production (changing the communication
protocol between existing services).
