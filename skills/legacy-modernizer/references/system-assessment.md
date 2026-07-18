# System Assessment

## Method

Assessing a legacy system means answering a fixed set of questions before any migration plan is
written, regardless of what the system is built with.

**Codebase analysis.** Establish baseline size (files, lines of code), external and internal
dependency count, and code smells that signal risk — functions that have grown too long to reason
about safely, tight coupling (business logic mixed directly with data-access/query code instead of
being separated behind a boundary), and global/shared mutable state that makes behavior
context-dependent and hard to characterize. Estimate existing test coverage as a proxy for how much
safety net already exists before any change is made.

**Dependency analysis.** Map which internal modules depend on which others, and specifically look for
circular dependencies — a module graph with cycles is a structural signal that clean incremental
extraction (strangler fig, extract service) will be harder than it looks, because there's no clean
boundary to cut along yet. Visualizing the graph also surfaces "god modules" with unusually wide
fan-in/fan-out, which are natural first candidates for the Facade or Extract Service refactoring
patterns before any migration is attempted.

**Change-frequency hotspots.** Files or modules that change most often in version-control history are
simultaneously higher business value (people keep needing to touch them, meaning they matter) and
higher risk (frequent change means frequent opportunity to introduce regressions). Prioritize
assessment depth and test-coverage investment on hotspots first, not on whatever code happens to be
easiest to analyze.

**Technical debt calculation.** Assign each category of issue found (long functions, circular
dependencies, missing tests, known vulnerabilities, deprecated dependencies, duplication) a
severity-weighted effort estimate — commonly expressed as remediation days per severity tier
(critical/major/minor/informational). Summing across all found issues produces a total estimated
remediation effort. This turns "the codebase is bad" into a size-of-effort number stakeholders can
actually plan around.

**Risk assessment matrix.** For each area under consideration for modernization, score risk as impact
× probability, and rank areas by the resulting severity. Critically, every risk entry must be paired
with an explicit mitigation — a risk list with no mitigations attached is just a list of things to
worry about, not an input to planning.

**Modernization roadmap.** Sequence the work into phases, where each phase explicitly states its
duration estimate, its dependencies on prior phases, the success metrics that must be met before the
next phase begins, and — non-negotiably — its own rollback plan. A phase with no stated rollback plan
is not ready to be scheduled.

**Stakeholder communication.** A recurring, structured status update (progress percentage, on-track/
blocked status, what completed, what's in progress, current blockers/risks, key metrics, next
goals) keeps non-technical stakeholders correctly informed without requiring them to read the
underlying technical assessment. Consistency of structure across updates matters more than detail —
stakeholders are tracking trend and risk, not implementation specifics.

## Boundary

- Assessment produces the *input* to planning (the roadmap's contents) — it does not itself choose the
  migration approach. A high risk score or large debt estimate doesn't automatically imply strangler
  fig over a different strategy; that judgment happens during planning, informed by but not dictated by
  the assessment numbers.
- Effort-day and cost estimates from the debt calculation are ballpark inputs for a roadmap discussion,
  not commitments — treat them as a starting point for negotiation with stakeholders, not as a
  contract to be held to precisely.
- Assessment describes the system as it is; it does not evaluate whether the original design decisions
  were reasonable given the constraints at the time. The goal is an accurate present-state picture to
  plan from, not a retrospective judgment of past engineering choices.
