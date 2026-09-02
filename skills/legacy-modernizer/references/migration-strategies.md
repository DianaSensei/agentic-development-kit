# Migration Strategies

## Method

Six migration scenarios. Each defines *how* to move state or traffic from an old system to a new one
safely - the mechanism, not the target design.

**Database migration - dual-write.** During the transition, the new database is treated as the source
of truth: writes land there first, in the request path. A write to the legacy database happens as a
best-effort, non-blocking sync - if it fails, that failure is logged, not propagated, because the new
database is already authoritative. Reads try the new database first; if a record isn't there yet, fall
back to the legacy database and lazily migrate that record into the new one at read time. Once
everything has been touched (all records have flowed through at least one read or been backfilled),
dual-write stops and the legacy database is no longer written to.

**Database migration - schema evolution (Expand-Contract).** Changing a schema without downtime
follows a fixed sequence: **Expand** (add the new column/field, nullable or with a default, so nothing
breaks) → **Write Both** (application code writes to both the old and new field simultaneously) →
**Backfill** (migrate existing rows so the new field is populated everywhere) → **Read New**
(application code reads the new field, falling back to the old one only if it's ever missing) →
**Contract** (drop the old field, once every deployed version of the application has moved past the
"Write Both" step). Skipping straight from Expand to Contract is what causes downtime or data loss -
each step exists specifically to keep the system consistent while different versions of the
application may be running simultaneously.

**API versioning migration.** Run the old and new response shapes concurrently behind version
negotiation (a version header, path segment, or Accept-header convention). Add deprecation/sunset
signaling to the old version's responses so consumers have a concrete timeline. Migrate clients over
that timeline, and only remove the old version once nothing is calling it anymore - verified by
monitoring actual traffic to the old version, not by assumption.

**Framework/runtime migration.** Run the old and new frameworks side by side (different ports or
processes during the transition). Build new endpoints/features in the new framework going forward. A
proxy/routing layer sits in front of both and forwards each request to whichever framework currently
owns that endpoint. Migrate endpoint by endpoint, updating the proxy's routing table each time, and
retire the old framework only once the routing table sends it nothing.

**Frontend UI migration.** Load both the old and new UI stacks together temporarily. Wrap legacy UI
components so the new framework can mount and unmount them without the legacy code needing to know
it's being embedded. Replace components incrementally, each behind its own flag, and bridge shared
state across the old/new boundary (a single source of truth both stacks read from) until nothing
depends on the legacy stack anymore.

**Microservices extraction.** Identify a bounded context that's tightly coupled inside a monolith
(a cohesive piece of business capability, e.g. "payments"). Stand up a new, independently deployable
service for it. Change the monolith to call the new service instead of running that logic locally -
this is itself an Adapter-shaped change (see refactoring-patterns). Once dependents no longer need a
synchronous response, move the integration from direct request/response coupling to event-driven
communication, so the extracted service and the monolith no longer need to be available
simultaneously to function. The monolith increasingly becomes an orchestrator of events rather than an
owner of the logic it extracted.

**Language/runtime version upgrade.** Introduce a compatibility layer that lets code run correctly
under both the old and new runtime/language version during the transition. Adopt new-version idioms
gradually, module by module, rather than all at once. Remove the compatibility layer only once nothing
in the codebase still depends on old-version behavior.

## Boundary

- Every strategy here chooses *how* to move state or traffic; none of them chooses the *target*
  architecture - deciding what the new database schema, API shape, or service boundaries should look
  like is a separate design decision that happens before the migration strategy is selected.
- Every migration step needs an explicit, stated trigger for advancing and an explicit rollback path.
  Dual-write's entire value is that the source of truth is unambiguous at every point specifically so
  rollback is unambiguous too - a migration step with no defined rollback is a big-bang cutover wearing
  an incremental label.
- These strategies assume the legacy system keeps functioning correctly throughout the migration - if
  the legacy system itself needs behavior changes first, do that as a separate, tested refactor (see
  refactoring-patterns) before layering a migration on top of it.
