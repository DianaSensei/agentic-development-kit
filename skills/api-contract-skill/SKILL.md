---
name: api-contract-skill
description: In-depth API contract design knowledge — REST (OpenAPI 3.x/3.1), GraphQL, RPC (gRPC/Protobuf), and asynchronous message contracts for Kafka/RabbitMQ/Pub-Sub under the AsyncAPI 3.x standard (the same role as OpenAPI, but for messages instead of REST). Covers design principles, security (OWASP API Security Top 10), naming/versioning, and standardized error format (RFC 7807). Use before implementation, to finalize the communication contract before writing code.
metadata:
  domain: api-architecture
  triggers: API design, REST API, OpenAPI, GraphQL, gRPC, Protobuf, message contract, AsyncAPI, event schema, API versioning, API security
  role: architect
  scope: design
  output-format: specification
  related-skills: architecture-designer, kafka-skill, rabbitmq-skill, pubsub-skill, java-spring-skill, tauri-react-skill, code-review-skill
---

# API & Message Contract Design

Acts as the contract architect — finalizes the communication contract before a single line of
implementation code is written, for both synchronous (REST/GraphQL/RPC) and asynchronous
(message-via-broker) communication.

## When to Use This Skill

- Designing a new endpoint/API, or changing the shape of an existing one (breaking or not).
- Designing an event/message contract for communication over Kafka/RabbitMQ/Pub-Sub.
- Deciding between REST, GraphQL, or RPC for a specific communication need.
- Standardizing the error format, versioning strategy, or security scheme shared across the whole API.

## Core Workflow

1. **Discover** — Read the existing contract (OpenAPI/`.graphql`/`.proto`/AsyncAPI if present) and the naming/versioning/auth conventions already in use. Determine the kind of communication being designed: synchronous (REST/GraphQL/RPC) or asynchronous via a broker (`kafka-skill`/`rabbitmq-skill`/`pubsub-skill`). If a distributed-systems-level decision is still open (which services should even talk to each other, sync vs. async as an architecture choice), that's `architecture-designer`'s call to make first — this skill takes it from there to the concrete contract.
2. **Choose the Protocol** — If not already constrained by an existing convention, compare trade-offs (see `references/protocol-choice.md`) and choose the best-fitting option, stating the reasoning in the report. Only ask the user back when the decision affects multiple services already running in production.
3. **Design the Contract** — Apply the correct principles for the chosen protocol type (see the Reference Guide below), including error format and security scheme. Always write message contracts to the AsyncAPI standard.
4. **Validate** — If the project already has a spec-lint tool (e.g. `@redocly/cli` for OpenAPI), run it before reporting done. Don't add a new tool just for this purpose if the project doesn't already have one.
5. **Write the Contract to a Real File** — Mandatory, see Output below. This is an artifact that must exist BEFORE coding — not something held in mind and coded straight into a Controller/Producer.
6. **Handoff** — List every file created/updated clearly in the report, so the lead orchestrator (`feature-development`/`bug-fix`) can add it to the "Files Changed" list.

## Reference Guide

Load detail based on the context currently being designed:

| Topic | Reference | Load When |
|-------|-----------|-----------|
| Protocol Comparison | `references/protocol-choice.md` | Unclear whether to use REST/GraphQL/RPC/message |
| REST Patterns | `references/rest-patterns.md` | Designing a REST endpoint, resource, pagination, caching |
| OpenAPI | `references/openapi.md` | Writing/validating an OpenAPI 3.x/3.1 spec, codegen, mock server |
| GraphQL | `references/graphql.md` | Schema-first GraphQL design |
| RPC (gRPC/Protobuf) | `references/rpc-grpc.md` | Designing a `.proto`, high-performance internal services |
| Message Contract (AsyncAPI) | `references/message-contract.md` | Event/topic/queue contracts for Kafka/RabbitMQ/Pub-Sub |
| Error Handling | `references/error-handling.md` | Standardizing the error schema (RFC 7807) |
| Security (OWASP) | `references/security-owasp.md` | AuthN/authZ, input validation, rate limiting |

## Constraints

### MUST DO
- Determine clearly whether this is a NEW contract or a change to one with existing dependent consumers/producers — that determines whether a breaking change needs user confirmation first.
- Use one shared error schema across the whole API/service — never let each endpoint invent its own format.
- Include a clear deprecation policy whenever releasing a version with a breaking change.
- For message contracts (Kafka/RabbitMQ/Pub-Sub): always write them to the AsyncAPI 3.x standard, never an ad-hoc, disconnected JSON format.
- Always specify the REQUIRED delivery semantics (at-least-once/exactly-once) for a message contract — this is a contract term, not a broker implementation detail.
- Write the contract to a real file (see Output), even when the feature only adds one small endpoint/event.

### MUST NOT DO
- Never decide broker infrastructure detail (partitions, consumer groups, ack mode) — that belongs to `kafka-skill`/`rabbitmq-skill`/`pubsub-skill` at implementation time.
- Never change the shape/field number/type of a contract that ALREADY has real dependent consumers without asking the user first.
- Never skip writing the file just because "the endpoint is too simple to need its own contract."
- Never put a verb in a REST URI (`/getUser/{id}` — wrong; `/users/{id}` — right).
- Never change or reuse a `.proto` field number that's already been published.

## Output — MANDATORY, must be written to a real file

1. **REST**: update the existing OpenAPI file (`openapi.yaml`/`.json`) if the project has one, or create `docs/api/<feature-slug>.openapi.yaml`.
2. **GraphQL**: update the existing schema file (`.graphql`/`schema.gql`) if the project has one, or create `docs/api/<feature-slug>.graphql`.
3. **RPC**: update/create the matching `.proto` file in the project's existing package.
4. **Message contract (Kafka/RabbitMQ/Pub-Sub)**: ALWAYS write it to the AsyncAPI standard at `docs/api/<feature-slug>.asyncapi.yaml` — a living doc to cross-check against later, even if the project has no existing AsyncAPI convention (see `references/message-contract.md` for a starter skeleton).

## Templates

### OpenAPI 3.1 Resource Endpoint (copy-paste starter)

```yaml
openapi: "3.1.0"
info:
  title: Example API
  version: "1.0.0"
paths:
  /users/{id}:
    get:
      summary: Get a user
      operationId: getUser
      tags: [Users]
      parameters:
        - name: id
          in: path
          required: true
          schema: { type: string, format: uuid }
      responses:
        "200":
          description: User found
          content:
            application/json:
              schema: { $ref: "#/components/schemas/User" }
        "404": { $ref: "#/components/responses/NotFound" }
components:
  schemas:
    User:
      type: object
      required: [id, email]
      properties:
        id:    { type: string, format: uuid, readOnly: true }
        email: { type: string, format: email }
  responses:
    NotFound:
      description: Resource not found
      content:
        application/problem+json:
          schema: { $ref: "#/components/schemas/Problem" }
  securitySchemes:
    BearerAuth: { type: http, scheme: bearer, bearerFormat: JWT }
security:
  - BearerAuth: []
```

See `references/openapi.md` for the full rule set + validate/mock commands.

### RFC 7807 Error Response (copy-paste)

```json
{
  "type": "https://api.example.com/errors/validation-error",
  "title": "Validation Error",
  "status": 422,
  "detail": "The 'email' field must be a valid email address.",
  "instance": "/users/req-abc123",
  "errors": [
    { "field": "email", "message": "Must be a valid email address." }
  ]
}
```

See `references/error-handling.md` for the full application rules.

## Boundaries

This skill decides data shape, endpoint/method/topic naming, required delivery semantics, and
versioning strategy. It does NOT decide deployment infrastructure detail (partitions, consumer groups,
ack mode, resolver caching) — that belongs to the relevant technical skill at implementation time.
It also does NOT decide whether two services should communicate synchronously or asynchronously in the
first place, or what the service boundaries are — that's `architecture-designer`'s job; this skill
finalizes the contract once that architectural decision is already made.

For a COMPLETELY NEW contract (no consumer/producer depends on it yet), if multiple reasonable designs
exist, choose the best one by clear criteria — simplicity, consistency with existing conventions, fewest
breaking changes — and state the reasoning in the report, no need to ask first. Only stop to ask the
user when the contract already has a real consumer and the change would be breaking, or when the
original request is too vague to infer the actual business intent.

## Knowledge Reference

REST, OpenAPI 3.0/3.1, GraphQL, gRPC/Protobuf, JSON Schema, AsyncAPI, RFC 7807 Problem
Details, OWASP API Security Top 10, OAuth 2.0/JWT, HATEOAS, cursor/offset pagination, API
versioning strategies.
