---
name: testcontainers-skill
description: In-depth Testcontainers setup/operation knowledge for integration tests — dependencies, container lifecycle (singleton pattern, reuse, cleanup), wait strategies, multi-container networking, CI integration. Does NOT cover infrastructure-specific test scenarios (see `database-skill`/`kafka-skill`/`rabbitmq-skill`/`redis-skill`/`elasticsearch-skill`). Use when an integration test needs real infrastructure via containers instead of a mock.
---

# Testcontainers — Container Setup & Execution for Integration Tests

## Discover Before Setting Up
Read `pom.xml`/`build.gradle` (or `package.json` if using the Node binding) to check whether a Testcontainers dependency already exists, and which modules are already used (postgresql/kafka/rabbitmq/elasticsearch/...). Confirm the Docker daemon is running on the machine/CI (`docker info`). Read any existing test config (`application-test.yml`, `docker-compose.test.yml` if present) before adding anything new — don't create a duplicate mechanism for something that already exists.

## When to Use Testcontainers / When Not To
Use it when an integration test needs the infrastructure's **real** behavior (real SQL dialect, real Kafka delivery semantics, real Redis TTL, etc.) that a mock/in-memory substitute (H2, embedded Kafka) can't faithfully reproduce — especially if the project has previously hit bugs caused by a mock/prod behavior gap. Do NOT use it for pure business-logic unit tests (mock the dependency per the relevant language/framework skill) — Testcontainers belongs strictly at the integration-test layer; it's slower, so don't overuse it for every test case.

## Basic Setup (JVM/JUnit5)
1. Add the `testcontainers-bom` + the matching module (`postgresql`, `kafka`, `rabbitmq`, `elasticsearch`, etc.) — pick the latest version compatible with the other test dependencies already in the project (no need to ask, this is a test-scope-only dependency). Only ask back if the new version forces a build-tool/JDK version bump outside the task's scope.
2. Use `@Testcontainers` + `@Container` (the JUnit5 extension) instead of manually managing lifecycle with scattered `start()`/`stop()` calls — the extension guarantees cleanup even when a test fails.
3. Pin a specific image version (e.g. `postgres:15.4`); do NOT use the `latest` tag — avoids flaky, non-reproducible tests when the image's behavior changes between runs.

## Lifecycle & Performance — the Most Common Issue
- **Restarting a container for every test class** is the leading cause of a slow test suite (each container takes several seconds to tens of seconds to become healthy). Prefer the **singleton container pattern**: one static container shared across the whole test suite (a base test class or a dedicated JUnit5 extension), started once, never `stop()`-ed between test classes — let Ryuk (below) clean it up when the test JVM exits.
- **Container reuse across local test runs** (not CI): enable `testcontainers.reuse.enable=true` in `~/.testcontainers.properties` and call `.withReuse(true)` for fast repeated local runs during development — do NOT enable reuse by default in CI, since a reused container can carry stale state across builds.
- **Ryuk (the resource reaper)**: Testcontainers automatically runs a Ryuk container to clean up orphaned containers/networks/volumes if the test JVM process dies unexpectedly — don't disable Ryuk (`TESTCONTAINERS_RYUK_DISABLED=true`) unless the CI runner doesn't allow container-managing-container (privileged) access, since disabling it tends to leave orphaned containers accumulating on the CI machine.

## Wait Strategy — Avoiding Flaky "Container Not Ready Yet" Failures
A container in the "running" state doesn't mean the service inside it is ready to accept connections — always declare a proper wait strategy instead of relying on a fixed delay (`Thread.sleep`):
- `Wait.forListeningPort()` for a service that just needs its port open (weak — prone to false positives if the app opens the port before it's actually finished initializing).
- `Wait.forLogMessage(...)` matching a log line that signals readiness (e.g. "database system is ready to accept connections") — more accurate than `forListeningPort`.
- `Wait.forHealthcheck()` if the image already has a healthcheck defined in its Dockerfile.
- Increase `startupTimeout` when running on a CI runner that's weaker/slower than the dev machine, to avoid a false timeout caused by a slow machine rather than a genuinely broken container.

## Networking Between Multiple Containers
When a test needs multiple containers to talk to each other (e.g. an app container calling Kafka + Zookeeper, or service A calling service B) — share a `Network.newNetwork()` and set `.withNetworkAliases(...)` on each container; do NOT use `localhost` or a mapped port from one container to reach another (only the host test JVM can see the externally mapped port via `getMappedPort()`).

## CI Integration
- The CI runner needs the Docker daemon available (Docker-in-Docker, or mounting `/var/run/docker.sock`). This is a shared CI configuration change affecting every other job/pipeline on the same runner — don't change it without flagging it; propose the specific configuration with reasoning and wait for confirmation from the user (or whoever owns CI) before applying it.
- Check CI resource limits (RAM/CPU) are sufficient for however many containers run in parallel — several Testcontainers modules at once (Postgres + Kafka + Elasticsearch, etc.) on a small runner easily times out from resource starvation, not a code bug.
- If CI runs multiple test jobs in parallel, check for port conflicts — Testcontainers maps to a random host port by default so conflicts are rare, but if the project pins a fixed port, double-check it.

## Common Real-World Issues
- **Passes locally, fails in CI**: usually a weak wait strategy (`forListeningPort`) or a default `startupTimeout` too short for a CI runner slower than the dev machine.
- **Orphaned containers accumulating on CI/dev machines**: caused by disabling Ryuk, or `kill -9`-ing the test process mid-run so cleanup never finishes — clean up periodically with `docker system prune` if noticed; not a code bug to fix.
- **Slow/timing-out image pull on first CI run**: consider pre-pulling the image in a dedicated cache step of the CI pipeline if this noticeably affects build time.

## Boundary
This skill only covers **the mechanics of setting up/running containers** (dependencies, lifecycle, wait strategy, networking, CI). The actual test scenarios per infrastructure type (which SQL dialect to test, which Kafka delivery semantics, how to test Redis TTL, what Elasticsearch mapping to test) → coordinate with the matching skill: `database-skill`, `kafka-skill`, `rabbitmq-skill`, `redis-skill`, `elasticsearch-skill`. Pure unit tests (mocked, no container) → the relevant language/framework skill (e.g. `java-spring-skill`).

## Knowledge Reference

Singleton container pattern, `@Testcontainers`/`@Container` (JUnit5), container reuse (`testcontainers.reuse.enable`), Ryuk resource reaper, wait strategies (`forListeningPort`, `forLogMessage`, `forHealthcheck`), multi-container networking (`Network.newNetwork()`, network aliases), CI Docker-in-Docker integration, image version pinning.
