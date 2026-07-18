---
name: code-review-skill
description: Objective code-review checklist to run before reporting work complete — general conventions, clean-code, plus a per-technology checklist for whatever was actually used. This is the SELF-CHECK step Claude ALWAYS proactively runs as the last step before reporting done on any change involving code — no separate user request needed. Do NOT use this when the user actively requests a diff/PR review ("review this", "/code-review") — use the built-in `code-review`/`review` skill for that case.
---

# Code Review Checklist

## Discover

Read `CLAUDE.md`/existing conventions. Determine which technologies are ACTUALLY relevant to the change just made (no need to apply the full checklist below for anything unrelated) based on concrete evidence in the changed files.

## General Checklist (every change)

- Clear naming, consistent with convention.
- No significant duplication (DRY), no function/class carrying too many responsibilities.
- No hardcoded secret/credential/API key.
- Exceptions handled explicitly, no silently swallowed errors.
- Comments where genuinely needed for complex logic, no redundant comments.

## Per-Technology Checklist (only apply the part relevant to the change)

**Java/Spring**: correct transaction boundaries, no N+1, exception handling follows convention, logging placed before/after critical sections for easier tracing/debugging, AOP self-invocation pitfalls avoided, framework abstractions preferred over tight coupling to specific dependencies, configuration externalized instead of hardcoded, no magic values.

**Kafka**: consumer idempotency for important consumers, delivery semantics match what was designed, dead-letter configured if needed, sensible partition key.

**RabbitMQ**: ack/nack handled correctly, DLX configured if needed, sensible prefetch, no connection/channel held open longer than necessary.

**Redis**: TTL set for cache entries (no accidental indefinite caching), lock has a TTL (avoids permanent deadlock), lock released only by its owner.

**Elasticsearch**: field mapping uses the correct type (text vs. keyword), no frequent leading-wildcard queries, no direct mapping edits on a production index.

**Database (RDBMS/Mongo)**: index on the correct filter/join/sort columns, isolation level fits the business need, migration is backward-compatible, no latent deadlock risk (locks acquired in a consistent order).

**Google Pub/Sub**: ack deadline sufficient for actual processing time, subscriber idempotency, dead-letter topic configured if needed.

**API Contract (REST/RPC/Message)**: response/message matches the finalized contract (`api-contract-skill`), no silent breaking change to a schema/proto field.

**Tauri/React**: correct path-handling API (no path traversal), capabilities declared least-privilege for the commands actually used, standard plugin used for dialogs, `#[cfg(target_os)]` covers all 3 OSes, Rust commands never panic (return `Result`), event listeners cleaned up on unmount, React has loading/error/empty states covered.

**Local Data/Storage (Tauri offline)**: SQLite migrations run successfully at app startup with a fallback if they fail (never leaves the app unable to open), key-value TTL/schema stays consistent, no large blobs stored in SQLite when `tauri-plugin-fs` would fit better.

**UI/UX**: consistent with the existing design system, clear error/loading state handling for the user, basic accessibility covered (labels, contrast, keyboard navigation).

## A Note on Objectivity

If this is a self-review (the same agent that just wrote the code), it's inherently less objective than a separate session/agent reviewing it. A severe issue MUST be fixed before reporting done — never skip it just because "this is only a self-review." For more objectivity, suggest the user open a new Claude Code session (no shared context) for an independent review.

## Knowledge Reference

DRY, single responsibility, silent error swallowing, self-review objectivity limits, per-technology
review checklists (transaction boundaries, delivery semantics, cache TTL, index correctness, contract
conformance, capability least-privilege).
