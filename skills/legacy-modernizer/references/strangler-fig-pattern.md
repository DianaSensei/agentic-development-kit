# Strangler Fig Pattern

## Method

The strangler fig pattern gradually replaces a legacy system by building new functionality around it
behind a routing layer, then shifting traffic to the new implementation in increments until the legacy
path is unused and can be removed.

```
Legacy System → Facade/Router → New System
     ↓              ↓               ↓
  Old Code    Feature Flags    Modern Code
     ↓              ↓               ↓
  Phase 1:    Route 10%       Validate New
  Phase 2:    Route 50%       Monitor Metrics
  Phase 3:    Route 100%      Remove Legacy
```

**The facade/router.** A thin layer sits in front of both the legacy and new implementations and
decides, per request, which one handles it. The decision can be a simple on/off flag, a percentage
rollout, or a consistent-hash routing key (e.g. hash the user or entity ID) so that a given
request/user routes to the same implementation across retries - this matters because inconsistent
routing makes logs, retries, and support investigations far harder to reason about. Callers of the
facade never know which implementation actually served them; that's what makes the routing layer safe
to change independently of everything around it.

**Where the pattern applies**, at different granularities of the same idea:
- **API/service routing** - a gateway or top-level handler routes each request to legacy or new
  service logic based on the flag/percentage.
- **Service extraction with an adapter** - before the new implementation exists, wrap the legacy
  service behind the same interface the new one will eventually implement, so the facade can already
  route through a uniform interface from day one.
- **Database strangler** - the read/write layer itself is strangled: writes go to the new
  system (source of truth) with a best-effort, non-blocking sync to legacy; reads try the new system
  first and fall back to legacy with a lazy migration-on-read when a record hasn't moved over yet.
- **UI component strangling** - at the level of individual UI components rather than whole pages: a
  wrapper renders either the legacy component or the new one based on the same kind of flag, allowing
  incremental replacement without a full-page rewrite.
- **Event interception** - legacy event handlers keep running unmodified, but each event is also
  translated and republished onto a new event bus, letting new subscribers build against the modern
  event shape without touching the legacy publisher/handler at all.

**Migration phases and validation.** Each traffic increment (e.g. 0% → 10% → 50% → 100%) is a
checkpoint, not an automatic progression: validate error rate and latency against a defined threshold
before advancing to the next percentage, and treat "instant rollback" as the actual mechanism -
lowering the flag/percentage back down, not a redeploy - so a bad increment can be reversed in seconds.
Cleanup (deleting the legacy code path) only happens after the new path has run at 100% traffic and
proven stable for a full release cycle, never immediately upon reaching 100%.

## Boundary

- This pattern only owns the routing/facade layer and the traffic-shifting mechanics - it does not
  decide what the new implementation's business logic should look like, nor does it validate that the
  new implementation is behaviorally correct. That validation is the job of characterization testing
  and parallel-run/shadow testing (see the testing reference) *before* traffic is shifted toward it.
- It assumes the legacy code being wrapped is left functionally unchanged during the strangling
  process - if the legacy behavior itself needs to change first, that's a refactoring task (see the
  refactoring-patterns reference) to do *before* introducing the facade, not at the same time.
- Database strangling in particular depends on one system being an unambiguous source of truth at
  every point in the migration - a design where both databases are treated as equally authoritative
  produces silent data divergence; pick a source of truth explicitly at each phase.
