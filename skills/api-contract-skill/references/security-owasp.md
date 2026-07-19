# Security — OWASP API Security Top 10 (applies to REST/GraphQL/RPC)

## Authentication & Authorization
- Declare the authentication/authorization scheme CLEARLY for each endpoint/method —
  don't leave "auth required" vaguely implied; state explicitly which role/scope can
  call which endpoint.
- Clearly distinguish the two error types: **401** (not authenticated — the system
  doesn't know who you are) vs **403** (authenticated but insufficient permission) —
  returning the wrong one sends the client down the wrong debugging path.
- Broken Object Level Authorization (BOLA) — the most common API vulnerability per
  OWASP: always check that the current user is authorized to access the SPECIFIC
  object being requested (e.g. `/orders/{id}` must verify that order belongs to the
  calling user, not just check "is logged in").

## Input Validation
- Validate strictly: type, format, min/max, pattern — or the corresponding field
  constraint in `.proto`/GraphQL schema. Don't trust data from the client even if
  UI-side validation already exists.
- Limit request payload size (to avoid DoS via oversized bodies).

## Response
- Avoid **over-fetching/mass assignment**: responses should only return the fields
  that are needed, not the entire internal object (e.g. fields like `password_hash`,
  `internal_notes` leaking out because a default serializer was used instead of an
  explicit DTO).
- Use an `Idempotency-Key` for endpoints that aren't naturally idempotent (e.g.
  creating an order via `POST`) if the business logic needs to avoid double-submits.

## Rate Limiting
- Note rate-limiting for endpoints at risk of abuse (login, search, bulk resource
  creation) — for REST, rate-limiting by request count is sufficient; **GraphQL needs
  rate-limiting by query complexity**, not just request count, since a single GraphQL
  query can consume many times more resources than a simple REST request.

## Secrets & Configuration
- Do NOT hardcode secrets/API keys in the contract/spec file (e.g. examples in OpenAPI
  should not use real keys).
- For `.proto`/GraphQL schemas: don't expose unnecessary internal fields/messages to
  the public API just for the "convenience" of reusing an existing type — create a
  separate type/message for the public contract if it differs from the internal model.

## Quick checklist before finalizing a contract
- [ ] Every endpoint/method has a clearly declared auth scheme.
- [ ] 401 vs 403 are distinguished correctly per context.
- [ ] Object-level authorization is addressed for ID-based access endpoints.
- [ ] Responses don't leak sensitive/internal fields.
- [ ] Endpoints at risk of abuse are noted as needing rate-limiting.
