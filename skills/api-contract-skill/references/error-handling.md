# Error Handling — RFC 7807 (Problem Details)

## General Principle
Use a single shared error schema for the ENTIRE API — don't let each endpoint invent
its own format (one endpoint returning `{error: "..."}`, another returning `{message:
"...", code: ...}` is a sign of missing standardization).

## RFC 7807 — the recommended standard if the project has no convention of its own
Every error response returns `Content-Type: application/problem+json` with the
following fields:

| Field | Meaning | Required |
|-------|---------|----------|
| `type` | Stable URI identifying the error type (NOT a generic string like `"error"`) | Yes |
| `title` | Short, fixed summary for this error type | Yes |
| `status` | HTTP status code, matching the response's actual status | Yes |
| `detail` | DETAILED, actionable description specific to this occurrence (not a static template) | Recommended |
| `instance` | URI of the specific request that caused the error (used for tracing) | Recommended |
| `errors[]` | Extension for per-field validation errors | When needed |

### Example
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

## Application rules
- `type` must be a stable, documented URI — don't change this value between different
  responses for the same error type (clients may compare `type` for conditional
  handling).
- `detail` must be actionable — state clearly WHAT is wrong and (if possible) HOW to
  fix it, not just "Invalid input".
- Do NOT expose sensitive information in `detail` (stack traces, SQL statements,
  internal file paths) — this is a common security mistake.
- The status code in the body MUST match the actual HTTP status code — don't return
  `200 OK` with an error body inside (this makes it hard for clients that rely on HTTP
  status to handle responses).

## When the project already has its own error convention
Do NOT impose RFC 7807 if the project already has a consistent error standard in use —
keep the existing convention, and just ensure NEW endpoints follow that same
convention instead of inventing a different format.

## Request ID — always include one for debuggability
Every error response (especially `5xx`) should include an ID identifying that specific
request (e.g. a `request_id`/`instance` field, or an `X-Request-ID` header) — without
one, the user/support team has no way to look up the exact log entry for that specific
error in the system. Don't add new tracing infrastructure just for this if the project
doesn't already have one — reuse the existing correlation ID mechanism if a
logging/tracing setup already exists.

## Retryable vs Non-retryable — helps clients know whether to retry automatically
Declare clearly (via standard status codes, no need for a separate field) which errors
the client SHOULD automatically retry and which it should NOT:
- **Should retry** (usually transient errors): `408` Request Timeout, `429` Too Many
  Requests (with a `Retry-After` header), `502`/`503`/`504` (temporary infrastructure
  errors).
- **Should NOT retry** (errors caused by an invalid request, retrying will fail the
  same way): `400`, `401`, `403`, `404`, `409`, `422`.
- For `429`/`503`, ALWAYS return a `Retry-After` header (seconds or HTTP-date) so the
  client knows how long to wait before retrying — don't let the client guess/retry
  immediately, which would add extra load.
