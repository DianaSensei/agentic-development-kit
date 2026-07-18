# Interactive API Documentation

This file covers the documentation *formats* used to describe APIs (OpenAPI, GraphQL SDL, AsyncAPI,
Protocol Buffers) — these are schema/interface-definition languages, not implementation languages, so
the same guidance applies whether the API itself is implemented in any given language or framework.

## OpenAPI (REST)

Design the spec so definitions are written once and referenced everywhere they recur — a schema, a
reusable parameter, a security scheme, or a common error response should each be defined once under
`components` and referenced (`$ref`) from every path that uses it. Duplicating a schema inline at each
usage site is what makes an OpenAPI spec drift out of sync with itself as the API evolves.

```yaml
openapi: 3.1.0
info:
  title: Users API
  version: 2.0.0

components:
  schemas:
    User:
      type: object
      required: [id, email]
      properties:
        id: { type: string, format: uuid }
        email: { type: string, format: email }
    Error:
      type: object
      properties:
        code: { type: string }
        message: { type: string }

  parameters:
    PageParam:
      name: page
      in: query
      schema: { type: integer, default: 1, minimum: 1 }

  securitySchemes:
    BearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT

  responses:
    NotFound:
      description: Resource not found
      content:
        application/json:
          schema: { $ref: '#/components/schemas/Error' }

paths:
  /users:
    get:
      summary: List users
      parameters:
        - $ref: '#/components/parameters/PageParam'
      security:
        - BearerAuth: []
      responses:
        '200':
          description: Success
          content:
            application/json:
              schema:
                type: array
                items: { $ref: '#/components/schemas/User' }
        '404': { $ref: '#/components/responses/NotFound' }
```

Every operation needs, at minimum: a `summary`, every parameter/request-body field described (not just
typed), every realistic response status documented (not only the success case), and the
`securitySchemes` that actually apply to it.

## GraphQL Schema Documentation

GraphQL's schema description syntax (triple-quoted strings preceding a type/field) is itself the
documentation — a well-documented schema is queryable via introspection, so the doc-comments become
the API reference automatically.

```graphql
"""
User account in the system
"""
type User {
  """Unique user identifier"""
  id: ID!

  """User's email address (unique)"""
  email: String!

  """User's posts (paginated)"""
  posts(
    """Number of items per page (max 100)"""
    limit: Int = 20
  ): PostConnection!
}

type Query {
  """Fetch a user by ID"""
  user("User's unique identifier" id: ID!): User
}
```

Document every field and every argument — an undocumented field in a GraphQL schema is invisible to
consumers using introspection-driven tooling, which is how most GraphQL clients discover the API.

## AsyncAPI (Event-Driven / WebSocket APIs)

For message-based APIs (WebSocket, pub/sub, queues), document channels, the messages published/
subscribed on them, and the payload schema for each — the same rigor as a REST response schema:

```yaml
asyncapi: 2.5.0
info:
  title: Chat WebSocket API
  version: 1.0.0

channels:
  chat/{roomId}:
    parameters:
      roomId:
        description: Chat room identifier
        schema: { type: string }
    subscribe:
      summary: Receive messages
      message: { $ref: '#/components/messages/ChatMessage' }

components:
  messages:
    ChatMessage:
      payload:
        type: object
        properties:
          userId: { type: string }
          content: { type: string }
          timestamp: { type: string, format: date-time }
```

## gRPC / Protocol Buffers

`.proto` files support comments directly above services, RPCs, messages, and fields — treat every RPC
method's comment as its API-reference entry, including what error condition maps to each gRPC status
code it can return:

```protobuf
service UserService {
  // Get a user by ID.
  // Returns NOT_FOUND if no user with this id exists.
  rpc GetUser(GetUserRequest) returns (User) {}
}

message User {
  string id = 1;       // Unique identifier
  string email = 2;     // Email address (unique, required)
}
```

## Interactive Documentation Portals

A rendered, browsable portal (generated from the spec above) typically needs: the ability to try a
request against a real or sandbox server from the page itself, persisted auth credentials across page
reloads within a session, and a way to filter/search operations once the API has more than a handful
of endpoints. Which specific portal tool renders this is an implementation detail to choose based on
the project's existing stack and hosting constraints — evaluate options against those three
capabilities plus how well each renders the specific spec format (OpenAPI vs. AsyncAPI vs. GraphQL
need different renderers) rather than defaulting to whichever tool is most familiar.

## SDK Reference Documentation

When a product ships client SDKs in multiple languages, the goal is a *parallel* structure: the same
method, in the same conceptual order, with the same level of coverage (parameters, return value,
exceptions/errors, one example) in every language's reference — a consumer switching from one SDK's
docs to another's should find the same information in the same place. Missing an error case or an
example in one language's reference but not another's is a documentation gap, not a stylistic
difference, and should be flagged the same way an undocumented function would be.

## Boundary

This file covers what to document and how the documentation format itself works (schema/interface
definition languages, which are language/framework-agnostic by design). It does not cover how to write
the underlying API implementation, or the concrete build/deploy setup for any specific portal-rendering
tool — those depend on the project's actual stack.
