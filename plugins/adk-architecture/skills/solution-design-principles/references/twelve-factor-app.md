# 12-Factor App

A set of practices for building applications that deploy cleanly and scale predictably on modern
(cloud/container/orchestrated) infrastructure. Originally written for web apps and SaaS backends; apply
with judgment to workloads it wasn't designed for (see caveats at the end).

## The 12 Factors

### I. Codebase
One codebase tracked in version control, many deploys. Multiple apps sharing code should share it via a
declared dependency (a library), not a copy-pasted or symlinked codebase - that's factor VI's
disposability and factor II's dependency isolation working together, not a separate exception.

**Gap symptom**: A "shared utils" folder copy-pasted into three repos, each drifting independently.

### II. Dependencies
Explicitly declare and isolate dependencies - never rely on the existence of system-wide packages.

**Gap symptom**: A build that only works on one developer's machine because it silently relies on a
globally-installed tool version.

### III. Config
Store config that varies between deploys (environment) - credentials, hostnames, feature flags - in
environment variables, not in the codebase.

**Gap symptom**: `application-prod.yml` committed to the repo with production database credentials.

**Why this matters beyond convenience**: config in code means a code change (and a deploy, and a review)
is required to change an environment value, and a security leak the moment the repo is ever exposed.

### IV. Backing Services
Treat backing services (databases, queues, caches, third-party APIs) as attached resources, accessed via
a URL/config, swappable without code changes.

**Gap symptom**: Code that behaves differently depending on whether the database is "the local one" vs.
"the real one," rather than treating both identically through config.

### V. Build, Release, Run
Strictly separate the build stage (compile/bundle), release stage (build + config for one environment),
and run stage (execute that release). A release is immutable; the same build combined with different
config produces different releases.

**Gap symptom**: "Fixing" a production issue by editing a running container's files directly instead of
producing a new release.

### VI. Processes
Execute the app as one or more stateless processes; any persisted state goes to a backing service
(database, cache), never in-process memory or the local filesystem between requests.

**Gap symptom**: Session data stored in server memory - the app breaks the moment there's more than one
instance, or the instance restarts.

### VII. Port Binding
The app is self-contained and exports services via port binding - it does not rely on a runtime-injected
webserver (e.g. Apache/Tomcat) to exist around it.

**Modern reading**: satisfied automatically by most modern frameworks/containers; check this mainly for
older app-server-dependent architectures.

### VIII. Concurrency
Scale out via the process model - add more stateless process instances - rather than scaling up a single
process with internal threading tricks as the primary scaling strategy.

**Gap symptom**: A design that assumes exactly one instance will ever run (in-memory locks, singleton
schedulers with no leader election) - breaks the moment horizontal scaling is needed.

### IX. Disposability
Processes start fast and shut down gracefully - finishing in-flight work, releasing resources - on
`SIGTERM`, so they can be started/stopped/killed by the platform without ceremony.

**Gap symptom**: A worker that drops in-flight jobs with no way to resume them if killed mid-task; a slow
startup that makes autoscaling/rolling-deploys painfully slow.

### X. Dev/Prod Parity
Keep development, staging, and production as similar as possible - same backing service *types*, small
time and personnel gap between writing code and deploying it.

**Gap symptom**: SQLite locally, a different RDBMS in production - bugs specific to the production
database's behavior are invisible until they hit production.

### XI. Logs
Treat logs as an event stream - write to `stdout`, let the execution environment handle routing,
aggregation, and storage; don't manage log files or log routing inside the app itself.

**Gap symptom**: The app writes to a local log file that fills the disk, or manages its own log rotation
and shipping logic.

### XII. Admin Processes
Run admin/management tasks (migrations, one-off scripts, a console) as one-off processes in the same
environment, using the same codebase and config, as the app's regular processes - not via ad hoc scripts
that have drifted from what's actually deployed.

**Gap symptom**: A "run this SQL by hand on prod" migration step instead of a versioned migration run
through the same pipeline as everything else.

## Applying This in Review

Score each factor Addressed/Gap for the service under review. Group findings by root cause where
possible - a service violating both Config (III) and Dev/Prod Parity (X) often has one underlying cause
(environment-specific code paths) rather than two unrelated issues.

## Caveats - Where 12-Factor Doesn't Fully Apply

- **Long-running stateful workloads** (a game server holding session state in memory for latency
  reasons, a database itself) intentionally violate Processes (VI) - that's the correct design for that
  workload, not a gap. Judge against the *intent* (explicit, deliberate state management with a defined
  consistency/failover story) rather than the letter of the rule.
- **Batch/ML training jobs** commonly violate Concurrency's "scale via more processes" framing -
  vertical scaling (bigger machine) is often the right call for a single large training run. The gap to
  actually look for is disposability (IX) and config (III), which still apply.
- **Desktop/CLI/embedded applications** aren't "deploys" in the 12-Factor sense at all - apply only the
  factors that translate (Dependencies, Config, Logs), and don't force-fit the rest.
