# Well-Architected Pillars

A technology/cloud-agnostic distillation of the pillars shared by AWS, Azure, and Google Cloud's
Well-Architected/Architecture frameworks. Use to assess whether a *design* (not yet built) or an
*existing system* has addressed each operational concern — not to pick specific cloud services.

Score each pillar as: **Addressed** (a concrete decision exists), **Deferred** (explicitly not a
priority yet, with a stated trigger to revisit), or **Gap** (not considered — this is the finding to
raise).

## 1. Operational Excellence

Can the system be run, deployed, and changed safely and repeatably?

**Guiding questions**:
- Is deployment automated and repeatable (not a manual runbook with room for human error)?
- Can a change be rolled back quickly if it causes a problem?
- Are operational procedures (deploy, rollback, scale, incident response) documented and, where
  possible, codified rather than tribal knowledge?
- Does the team get feedback (metrics, logs, alerts) fast enough to catch a regression before it
  compounds?

**Concrete practices**: CI/CD pipelines, infrastructure as code, feature flags for safe rollout,
runbooks, blameless post-incident review, small/frequent deploys over large/rare ones.

**Common gap**: A system with excellent code quality but a deploy process that's a manual, undocumented
sequence of steps one person remembers.

## 2. Security

Is data and access to the system protected commensurate with what it's worth to an attacker?

**Guiding questions**:
- Is authentication/authorization enforced at every entry point, not just the "front door"?
- Is sensitive data encrypted in transit and at rest?
- Is the principle of least privilege applied to every service identity and human role?
- Is there a plan for detecting and responding to a security event, not just preventing one?

**Concrete practices**: Defense in depth, least-privilege IAM, secrets management (not hardcoded
credentials), input validation at trust boundaries, dependency vulnerability scanning, audit logging of
sensitive actions.

**Boundary**: This pillar's design-level check is this skill's job — the actual secure-coding
implementation is `secure-code-guardian`'s job, and a vulnerability audit of existing code is
`security-reviewer`'s job.

**Common gap**: Authorization checked at the API gateway but not re-checked at the service that actually
performs a sensitive action, reachable via an internal call that skips the gateway.

## 3. Reliability

Does the system perform its intended function correctly and consistently, including when parts of it
fail?

**Guiding questions**:
- What is the failure mode of every external dependency (network call, database, third-party API), and
  is it handled explicitly (timeout, retry, fallback) rather than left to hang or crash?
- Is there a defined recovery objective (how much data loss / downtime is acceptable) and does the design
  actually meet it?
- Does the system degrade gracefully under partial failure, or does one failing dependency take down
  everything?
- Is capacity planned for realistic peak load, with headroom for growth?

**Concrete practices**: Health checks, redundancy for critical paths, backup and tested restore
procedures, chaos/failure testing, defined RTO/RPO, circuit breakers and bulkheads for distributed calls
(see `architecture-designer`'s `resilience-patterns.md` for the distributed-systems-specific patterns).

**Common gap**: Backups exist but restoration has never actually been tested — the recovery plan is
theoretical.

## 4. Performance Efficiency

Does the system use computing resources efficiently, and does that efficiency hold as load changes?

**Guiding questions**:
- Is the system's resource usage matched to actual load (not permanently over-provisioned "to be safe,"
  and not under-provisioned to fail under normal peak)?
- Are the expensive operations (N+1 queries, unindexed scans, synchronous chains of remote calls)
  identified and either avoided or explicitly accepted as a trade-off?
- Does performance degrade predictably (linearly) under increasing load, or does it fall off a cliff past
  some threshold that hasn't been tested?
- Is there a defined performance target (latency/throughput SLO), or is "fast enough" undefined?

**Concrete practices**: Load/performance testing before launch, caching where reads dominate writes,
async processing for non-blocking work, database indexing matched to actual query patterns, monitoring
that surfaces degradation before users notice.

**Common gap**: No load testing was ever done; the first time real concurrent load is seen is in
production.

## 5. Cost Optimization

Does the system deliver its value at a cost proportionate to that value, without cost being either
ignored or over-optimized at the expense of the other pillars?

**Guiding questions**:
- Are always-on resources actually needed 24/7, or would on-demand/scheduled scaling fit the real usage
  pattern?
- Is data retained longer, or replicated more redundantly, than the actual requirement demands?
- Is a cheaper, simpler solution being passed over only because a more expensive one is more familiar or
  more impressive, without the extra cost being justified by a requirement?
- Conversely: is a critical path being under-resourced to save cost in a way that undermines Reliability
  or Performance the business actually needs?

**Concrete practices**: Right-sizing based on measured usage, autoscaling matched to real traffic
patterns, storage tiering (hot/cold) matched to access frequency, tagging/attribution so cost is visible
per team or feature.

**Scope note**: This skill flags cost-*relevant design choices* (e.g. "this always-on worker could be
event-triggered") — actual dollar-cost modeling and cloud-provider pricing comparisons are out of scope.

**Common gap**: A batch job that runs for 5 minutes a day on an instance that's provisioned and billed
24/7.

## 6. Sustainability (where applicable)

Is the system designed to minimize its resource footprint, not just its dollar cost? (Most cost-optimal
choices are also sustainability-optimal, since both track actual resource consumption — treat this as a
secondary lens on the Cost Optimization findings rather than a separate analysis, unless environmental
impact is an explicit stated requirement.)

## Using the Pillars in Review

1. Go through all six pillars for every system-level review — don't skip a pillar silently.
2. For each, land on **Addressed / Deferred / Gap**. A **Deferred** verdict must state the trigger that
   would make it a priority (e.g. "revisit autoscaling once traffic exceeds current single-instance
   capacity" — not just "later").
3. Weight the pillars by what the system actually is: an internal admin tool over-indexing on
   auto-scaling Cost Optimization is itself a design smell (effort spent where it doesn't pay for the
   system's actual risk profile); a payments system treating Security as **Deferred** is a Gap, not a
   legitimate deferral, regardless of stage.
4. Pillars trade off against each other (more redundancy improves Reliability but costs more; more
   caching improves Performance but adds a consistency/staleness risk to Reliability). Name the tension
   explicitly rather than presenting a pillar improvement as free.
