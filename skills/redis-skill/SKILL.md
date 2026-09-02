---
name: redis-skill
description: In-depth Redis knowledge - caching, distributed locks, lightweight queues, ranking/leaderboards. Use when the feature needs a cache, a distributed lock, a queue that can tolerate minimal loss, or a leaderboard. If strong durability/delivery guarantees are needed (retry, dead-letter, replay), see `kafka-skill`/`rabbitmq-skill` instead of Redis.
metadata:
  domain: database
  triggers: Redis, cache, caching, cache invalidation, cache-aside, TTL, distributed lock, Redlock, leaderboard, sorted set, session store, rate limiting, hot key, eviction policy, Redis Streams
  role: specialist
  scope: implementation
  output-format: code
  related-skills: database-skill, java-spring-skill, kafka-skill, rabbitmq-skill, testcontainers-skill, monitoring-expert
---

# Redis - Multi-Purpose by Use Case

## Discover
Confirm the project already uses Redis via its dependency (`spring-boot-starter-data-redis`, `lettuce`/`jedis`), read the existing cluster/standalone config and the TTL convention already in use.

## When It Fits / When It Doesn't
Fits: caching, sessions, short-lived distributed locks, lightweight queues that can tolerate minimal loss, high-speed leaderboards/counters. **Does NOT fit** as the primary source of truth for important data that needs strong durability - even with AOF/RDB enabled, Redis is still "best-effort": RDB loses data between snapshots, and AOF (`appendfsync everysec`, the default) can lose up to ~1s of data on a crash. If the business can't accept that loss, that data belongs in an RDBMS (`database-skill`) - Redis should only be a cache/accelerator layered on top.

## Common Real-World Issues
- **Big keys**: an oversized hash/set/sorted set (hundreds of thousands of fields/members) blocks Redis's single-threaded event loop during an operation on it (e.g. `KEYS *`, `DEL` on a large key) - use `SCAN` instead of `KEYS`, `UNLINK` instead of `DEL` (async deletion, non-blocking).
- **Hot key**: one key gets disproportionately high traffic (viral), concentrating load on a single node even in a multi-node cluster (because a key belongs to exactly one slot) - consider an application-tier cache in front, or splitting the key, if this happens.
- **Wrong eviction policy**: once `maxmemory` is reached, the policy (`allkeys-lru`/`volatile-ttl`/etc.) decides which key gets evicted first - choosing `allkeys-lru` while an important key has NO TTL set means that key can be evicted unintentionally; choose a `volatile-*` policy if TTL-less keys need protection from eviction.
- **Pub/Sub (the `PUBLISH`/`SUBSCRIBE` channel, distinct from Streams)**: has NO persistence - a subscriber offline at publish time loses that message permanently; not suitable when reliable delivery is required (use Streams if durability + replay is needed).

## 1. Caching
- **Key naming**: follows the project's existing convention (e.g. `<domain>:<entity>:<id>`).
- **TTL**: always set an explicit TTL for cache entries - never cache indefinitely unless there's a clear reason and an accompanying active-invalidation mechanism.
- **Invalidation strategy**: write-through (update the cache immediately on DB write), write-behind, or cache-aside (invalidate on write, reload on a read miss) - choose based on how much stale data the business can tolerate (default to cache-aside if there's no other signal - simplest and safest), stating the reasoning briefly. Only ask back if this cache serves sensitive data where staleness could cause a serious business consequence (price, inventory, balance).
- **Cache stampede**: consider a lock or TTL jitter when many requests can miss the cache simultaneously (to avoid all of them hitting the DB at once).

## 2. Distributed Lock
- Use `SET key value NX PX <ttl>` (or the Redisson library) - ALWAYS set a TTL on the lock to avoid a permanent deadlock if the holding process crashes.
- Consider the **Redlock** algorithm only when a lock needs to be reliable across multiple independent Redis instances (not just one instance/cluster) - only use it when reliability truly demands it; there's genuine technical debate about Redlock, so weigh it carefully before applying it to a critical financial operation.
- Release the lock only if owned by the releaser (use a random token/value, check it before deleting - avoid releasing another process's lock by mistake).

## 3. Lightweight Queue
- **List** (`LPUSH`/`BRPOP`) for a simple FIFO queue that doesn't need high reliability.
- **Redis Streams** (`XADD`/`XREADGROUP`) when consumer groups, acks, or replay are needed - closer to Kafka in spirit but lighter weight, useful when new Kafka/RabbitMQ infrastructure isn't worth adding. If the business needs more reliability/durability than Streams provides, consider `kafka-skill`/`rabbitmq-skill` instead of forcing Redis into the role of primary queue.

## 4. Ranking / Leaderboard
- **Sorted Set** (`ZADD`/`ZRANGE`/`ZRANK`) - the standard structure for leaderboards, O(log N) rank lookup.
- Prefer `ZINCRBY` for score updates over a manual read-modify-write (avoids race conditions).

## Cluster & High Availability (note only, don't change infrastructure unprompted)
If the project already uses Redis Cluster, note that some commands don't support multi-key operations across different slots (use a hash tag `{...}` when related keys must share a slot).

## Test
Testcontainers Redis for integration tests - test TTL/invalidation correctness, test that a lock is never held past its TTL, test that a sorted set returns the correct rank.

## Boundary
If the request already makes the purpose clear (e.g. "cache the result of API X", "lock to prevent processing the same order twice") - infer the corresponding use case (cache/lock/queue/ranking) and choose the matching Redis data structure without asking back. Only ask when the description is too vague to infer the right use case (e.g. "temporarily store this in Redis" with no indication of whether TTL is needed, ordered reads are needed, or it's just transient existence).

## Knowledge Reference

Cache-aside/write-through/write-behind invalidation, cache stampede, distributed locking (`SET NX PX`, Redlock), Redis Streams vs. Pub/Sub, sorted sets for leaderboards, eviction policies, big key / hot key issues.
