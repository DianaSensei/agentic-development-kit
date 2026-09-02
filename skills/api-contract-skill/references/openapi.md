# OpenAPI 3.x/3.1

OpenAPI is the REAL artifact of a REST contract - not supplementary reference
documentation, this is the actual file that must be written out (see the Output
section in the main SKILL.md).

## Minimal valid structure

```yaml
openapi: "3.1.0"
info:
  title: My API
  version: "1.0.0"
servers:
  - url: https://api.example.com/v1
    description: Production
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

## Rules when writing the spec
- `operationId` must be unique, used for client/server codegen - give it a clear,
  meaningful name (`listUsers`, `getUser`, `createUser`), never leave it blank (many
  codegen tools require this field).
- Mark read-only fields (`id`, `created_at`) with `readOnly: true` - to prevent clients
  from sending them when creating/updating a resource.
- Use `$ref` to reuse common schemas (`Problem`, `Pagination`) - don't copy-paste error
  response definitions into every endpoint.
- Declare `securitySchemes` + `security` explicitly - don't leave "every endpoint
  requires auth" implied without stating it clearly in the spec.

## Validate & Mock (if the project already has tooling)
- Lint the spec before reporting completion if a tool is already available: `npx
  @redocly/cli lint <file>.openapi.yaml` - don't add a new dependency for this if the
  project doesn't already have one; just note in the report that it should be added.
- Mock server to verify the contract before consumers code against it: `npx
  @stoplight/prism-cli mock <file>.openapi.yaml` - useful when the frontend/consumer
  needs to start coding in parallel before the backend implementation is finished.

## OpenAPI 3.0 vs 3.1
- 3.1 has fuller JSON Schema compatibility (supports `type` as an array, `const`, more
  flexible composition) - prefer 3.1 for NEW specs if the project's tooling supports
  it.
- If the project already has a large 3.0 spec, don't upgrade to 3.1 midway just because
  it's "newer" in theory - upgrading the spec version affects all the codegen tooling
  currently in use, and should be discussed separately if there's a concrete reason
  (e.g. needing a JSON Schema feature that 3.0 doesn't support).
