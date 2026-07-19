# PostgreSQL Tuning & Operations

Only change production config when you have measured evidence (don't guess) — every value below is a
reference starting point for a dedicated 16GB RAM server and needs to be tuned against real load.

## Memory Configuration

```ini
# postgresql.conf — dedicated 16GB RAM server
shared_buffers = 4GB              # 25% of RAM (up to ~40% for a fully dedicated server)
effective_cache_size = 12GB       # 50-75% of RAM — just a hint for the planner, not actually allocated
work_mem = 40MB                   # per-operation (sort/hash) — reference formula: (RAM*0.25)/max_connections
maintenance_work_mem = 2GB        # for VACUUM/CREATE INDEX — can be set much higher than work_mem
```

Target cache hit ratio >99%:

```sql
SELECT round(sum(heap_blks_hit)::numeric / NULLIF(sum(heap_blks_hit) + sum(heap_blks_read), 0) * 100, 2) AS cache_hit_ratio
FROM pg_statio_user_tables;
```

## Query Planner

```ini
default_statistics_target = 200   # default is 100 — increase for large tables/high-cardinality columns needing more accurate estimates
random_page_cost = 1.1            # SSD (default 4.0 is meant for spinning HDDs)
max_parallel_workers_per_gather = 4
```

```sql
-- Increase statistics for a specific column instead of the whole database
ALTER TABLE users ALTER COLUMN email SET STATISTICS 500;
ANALYZE users;  -- apply immediately, no need to wait for autoanalyze
```

## VACUUM & Autovacuum — NEVER disable autovacuum globally

PostgreSQL uses MVCC: UPDATE/DELETE doesn't remove old rows immediately, it marks them as "dead tuples."
Without VACUUM → table bloat, gradually degrading performance, and eventually transaction ID wraparound
(severe — can cause the DB to refuse writes).

```sql
-- Monitor dead tuple ratio — alert when dead_pct is high and last_autovacuum hasn't run in a while
SELECT relname, n_dead_tup, n_live_tup,
       round(n_dead_tup * 100.0 / NULLIF(n_live_tup + n_dead_tup, 0), 2) AS dead_pct,
       last_autovacuum
FROM pg_stat_user_tables ORDER BY n_dead_tup DESC LIMIT 20;

-- High-churn tables (lots of update/delete): vacuum more aggressively than the default (10% dead tuples)
ALTER TABLE orders SET (autovacuum_vacuum_scale_factor = 0.05, autovacuum_vacuum_cost_delay = 2);

-- Manual VACUUM does not lock the table — use when you need it urgently instead of waiting for autovacuum
VACUUM (ANALYZE, VERBOSE) orders;

-- VACUUM FULL locks the table completely (exclusive lock) — avoid in production, prefer pg_repack (online, non-locking)
```

## Connections & Locks

```sql
-- Long-running queries
SELECT pid, now() - query_start AS duration, query
FROM pg_stat_activity WHERE state = 'active' AND now() - query_start > interval '5 minutes';

-- Idle-in-transaction — holds locks for a long time, blocks VACUUM, usually caused by a bug that forgets to COMMIT/ROLLBACK
SELECT pid, now() - state_change AS idle_duration, query
FROM pg_stat_activity WHERE state = 'idle in transaction' AND now() - state_change > interval '1 minute';

-- Which query is blocking which
SELECT blocked.pid AS blocked_pid, blocking.pid AS blocking_pid,
       blocked.query AS blocked_query, blocking.query AS blocking_query
FROM pg_stat_activity blocked
JOIN pg_locks bl ON bl.pid = blocked.pid AND NOT bl.granted
JOIN pg_locks kl ON kl.locktype = bl.locktype AND kl.database IS NOT DISTINCT FROM bl.database
    AND kl.relation IS NOT DISTINCT FROM bl.relation AND kl.pid != bl.pid AND kl.granted
JOIN pg_stat_activity blocking ON blocking.pid = kl.pid;

-- Automatic timeouts for sessions/statements — avoid a single connection hanging indefinitely and holding a pool slot
ALTER SYSTEM SET idle_in_transaction_session_timeout = '5min';
ALTER SYSTEM SET statement_timeout = '30s';
```

Connection pool exhaustion is usually caused by connections/transactions not being closed properly (a leak
from an exception that skips release) — use pgBouncer (`pool_mode = transaction`) to reduce the number of
real connections hitting Postgres when there are many clients.

## Partitioning — consider when a table exceeds 10M rows or you need to drop old data quickly

```sql
CREATE TABLE events (id BIGSERIAL, created_at TIMESTAMP NOT NULL, data JSONB) PARTITION BY RANGE (created_at);
CREATE TABLE events_2024_01 PARTITION OF events FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
CREATE INDEX idx_events_2024_01_type ON events_2024_01(event_type);  -- separate index per partition

-- Query correctly uses partition pruning if the filter matches the partition key column
EXPLAIN SELECT * FROM events WHERE created_at >= '2024-01-15' AND created_at < '2024-01-20';
-- Expected: only scans the events_2024_01 partition, not the whole table
```

Dropping a partition (e.g. data older than 1 year) is much faster than a bulk `DELETE` — no WAL needs to be
written per row, and no dead tuples are created that would need a later VACUUM.

## Replication (summary — only when the project genuinely needs HA/read replicas)

- **Streaming (physical)**: the replica is a byte-for-byte copy, used for simple failover/read scaling.
  Enable `wal_level = replica`, create a replication slot to avoid losing WAL when the replica temporarily
  disconnects.
- **Logical**: replicates at the row level via publication/subscription, allows selecting specific tables,
  and supports different Postgres versions on each side — use it when you need selective replication or
  are migrating between two clusters.
- ALWAYS monitor lag when a replica exists — high lag that goes undetected leads to reading stale data
  without realizing it:

```sql
-- On the primary
SELECT client_addr, state, pg_wal_lsn_diff(sent_lsn, replay_lsn) AS lag_bytes FROM pg_stat_replication;
-- On the standby
SELECT now() - pg_last_xact_replay_timestamp() AS replication_lag;
```

- Real production HA usually needs Patroni/pg_auto_failover (automatic failover) + PgBouncer/HAProxy
  (routing) on top — this is a major infrastructure decision that needs to be discussed with the user
  separately, don't add it unprompted.

## Backup — Point-in-Time Recovery (PITR)

```ini
archive_mode = on
archive_command = 'cp %p /backup/wal/%f'   # or use pgBackRest for real production
```

```bash
pg_basebackup -h localhost -U postgres -D /backup/base/$(date +%Y%m%d) -Ft -z -P
# Restore: restore the base backup, create recovery.signal, set recovery_target_time in postgresql.conf, restart
```

## Reference config file (16GB RAM, production)

```ini
shared_buffers = 4GB
effective_cache_size = 12GB
work_mem = 40MB
maintenance_work_mem = 2GB
wal_buffers = 16MB
checkpoint_completion_target = 0.9
max_wal_size = 2GB
default_statistics_target = 200
random_page_cost = 1.1
max_parallel_workers_per_gather = 4
max_connections = 200
log_min_duration_statement = 1000   # log queries > 1s
log_lock_waits = on
```

## Maintenance Checklist

- **Daily**: autovacuum activity, long-running queries, replication lag (if applicable), cache hit ratio.
- **Weekly**: slow queries from `pg_stat_statements`, table/index bloat, unused indexes.
- **Monthly**: review autovacuum settings, reindex heavily updated tables, capacity trends.
- **Quarterly**: test an actual backup restore (don't just trust that the backup job succeeded), review version upgrades.
