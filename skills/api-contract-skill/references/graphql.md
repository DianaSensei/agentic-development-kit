# GraphQL

## Schema-first
- Define types, queries, and mutations BEFORE writing resolvers — the schema itself is
  the contract. Naming: PascalCase for types (`User`, `OrderInput`), camelCase for
  fields/arguments.
- Clearly separate `Query` (read), `Mutation` (write), `Subscription` (real-time, if
  needed) — don't put write actions inside a Query.

## Input & Validation
- Use a dedicated input type for mutations (`CreateUserInput`) instead of listing
  separate arguments — easier to extend later (adding a field to an input type is
  non-breaking).
- Constrain via custom scalars (e.g. `Email`, `PositiveInt`) where possible, so the
  schema validates itself instead of pushing all the logic into the resolver.

## N+1 (a note, not part of contract design scope)
- Nested resolvers (e.g. `User.orders` querying the DB again for each user in a list)
  can easily cause N+1 queries — this is an IMPLEMENTATION concern (solved with
  Dataloader/batching), not a contract design decision. Just note it in the handoff to
  the implementer if the schema has a clear risk of causing N+1 (a field returning a
  deeply nested list).

## Versioning
- Do NOT version via URL like REST (GraphQL usually has only one `/graphql` endpoint).
- Add new fields/types instead of changing existing ones. Mark old fields with
  `@deprecated(reason: "...")` before removing them entirely, giving consumers time to
  migrate.
- A truly breaking change (changing a field's type, changing an argument's semantics)
  needs advance notice and a migration plan — same as REST, don't change it silently.

## Error Handling
- GraphQL always returns HTTP 200 even when there's a business-logic error — the error
  lives in the response's `errors[]` field, not in the HTTP status code as with REST.
- Use `extensions` in the error object to carry structured information (error code,
  related field) instead of only a free-text `message` — this lets clients handle
  errors conditionally instead of comparing strings.

## GraphQL-specific security
- Limit query depth (`query depth limit`) and complexity (`query complexity`) — a
  GraphQL query can nest arbitrarily deep, unlike REST (each request costs a fixed
  single call), so rate-limiting by request count is NOT sufficient; complexity-based
  limits are needed.
- Disable `introspection` in production if the API isn't public, to avoid exposing the
  entire internal schema to outside probing.
