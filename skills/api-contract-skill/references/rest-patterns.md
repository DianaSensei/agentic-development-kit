# REST Patterns

## Resource & URI
- Resource-oriented URLs, plural nouns: `/users`, `/users/{id}/orders` - do NOT put
  verbs in the URI (`/getUser/{id}` is wrong, `/users/{id}` is correct - the verb
  already lives in the HTTP method).
- Nested resources at most 2 levels deep (`/users/{id}/orders`) - deeper nesting should
  use a query param filter instead (`/orders?user_id=...`) to avoid an overly complex
  URI.
- HTTP methods with correct semantics: `GET` (read, idempotent, safe), `POST` (create/
  non-idempotent action), `PUT` (full replacement, idempotent), `PATCH` (partial
  update), `DELETE` (delete, idempotent).
- Status codes matching context: `200` OK, `201` Created (with `Location` header),
  `204` No Content (successful deletion, no body returned), `400` Bad Request (invalid
  input), `401` Unauthorized (not authenticated), `403` Forbidden (authenticated but
  insufficient permission), `404` Not Found, `409` Conflict (state conflict), `422`
  Unprocessable Entity (business rule validation failed), `429` Too Many Requests.

## Pagination
- **Cursor-based** (recommended for large datasets/deep pagination): return
  `next_cursor` + `has_more`, the client doesn't need to know the offset - avoids the
  "shifted page" problem when data changes between calls.
- **Offset-based** (`?page=2&limit=20`): simple, easy to understand, acceptable for
  small datasets/UIs that need to "jump to page N" - but slows down with large offsets
  and can produce shifted data.
- Always enforce a maximum `limit` (e.g. `maximum: 100`) to prevent a client from
  requesting the entire table.

## Filtering & Sorting
- Consistent query params: `?status=active&sort=-created_at` (the `-` prefix means
  descending).
- Validate filter/sort field values - don't allow sorting by an arbitrary field (risk
  of exposing internal fields or causing N+1 queries if sorting by an unindexed field).

## Versioning
- Pick one consistent strategy: URL path (`/v1/users`) is the clearest/easiest to
  debug, recommended as the default unless the project already follows header
  versioning (`Accept: application/vnd.api+json;version=1` - cleaner in pure REST
  terms but harder to test/debug manually than URL path).
- Only use major versions (`v1`, `v2`) - don't version individual fields piecemeal
  (`v1.1`, `v1.2` creates confusion about when something is truly breaking).
- **Deprecation must have a clear, explicit signaling mechanism, not just a verbal
  notice**: return the header `Deprecation: true` + `Sunset: <shutdown date, RFC 8594>`
  + `Link: <new-version-url>; rel="successor-version"` on every response of the version
  being phased out. After the sunset date, return `410 Gone` with a message guiding
  migration - don't shut it down abruptly without notice.
- Support both versions in parallel for at least a few months (depending on actual
  consumer impact) - don't shorten this arbitrarily unless it's confirmed that
  consumers have finished migrating.
- Small field-level changes (adding an optional field) do NOT require a version bump -
  only bump when the change is breaking (type change, field removal, semantic change).

## Caching (conditional requests)
- `Cache-Control` for cacheable responses (`public, max-age=3600` for rarely-changing
  data, `private, no-cache` for user-specific data, `no-store` for sensitive data that
  should never be cached).
- `ETag` for responses that need precise cache validation: the client resends
  `If-None-Match: <etag>` on the next request, and the server returns `304 Not
  Modified` (no body) if nothing changed - saves bandwidth for large/rarely-changing
  resources.
- `If-Match` for conditional writes (to avoid lost updates when two clients edit the
  same resource concurrently): the client sends the known ETag, and the server returns
  `412 Precondition Failed` if the resource has changed since then - use this when the
  business logic needs optimistic concurrency at the HTTP layer rather than only at the
  DB layer.

## HATEOAS (apply selectively, not mandatory)
- Return related navigation links in the response (`_links: { self, next, related }`)
  if the client needs to dynamically discover the API - most internal/simple CRUD REST
  APIs do NOT need this level of sophistication; only apply it when there's a clear
  requirement for API self-discoverability.

## Idempotency
- `PUT`/`DELETE` must be naturally idempotent per the HTTP spec.
- `POST` is not naturally idempotent - if the business logic requires it (e.g. creating
  an order, payment), use a client-supplied `Idempotency-Key` header, and have the
  server deduplicate by that key within a reasonable time window.
