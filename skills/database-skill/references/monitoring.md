# Monitoring & Alert Thresholds

For container-based testing (Testcontainers), see `testcontainers-skill`. This file covers health-monitoring
queries for a **real** database (staging/production), not tests.

## Baseline before optimizing — ALWAYS measure before/after every change, don't change multiple things at once

```sql
-- PostgreSQL: top queries by total time (requires pg_stat_statements)
SELECT substring(query, 1, 100) AS short_query, calls,
       round(mean_exec_time::numeric, 2) AS mean_ms,
       round((100 * total_exec_time / sum(total_exec_time) OVER ())::numeric, 2) AS pct_total
FROM pg_stat_statements ORDER BY total_exec_time DESC LIMIT 20;

-- MySQL: equivalent via performance_schema
SELECT DIGEST_TEXT, COUNT_STAR AS exec_count, ROUND(SUM_TIMER_WAIT / 1e12, 3) AS total_sec
FROM performance_schema.events_statements_summary_by_digest ORDER BY SUM_TIMER_WAIT DESC LIMIT 20;
```

## Quick Health Check (run periodically or when you suspect an incident)

```sql
-- PostgreSQL
SELECT 'connections' AS metric, count(*) AS current, current_setting('max_connections')::int AS max
FROM pg_stat_activity
UNION ALL
SELECT 'cache_hit_ratio', round((sum(heap_blks_hit)::numeric / NULLIF(sum(heap_blks_hit)+sum(heap_blks_read),0))*100, 2), 95
FROM pg_statio_user_tables;

-- MySQL
SELECT 'connections' AS metric, (SELECT COUNT(*) FROM information_schema.processlist) AS current, @@max_connections AS max;
```

## Reference Alert Thresholds (adjust to the project's real baseline, don't copy blindly)

| Metric | WARNING | CRITICAL |
|--------|---------|----------|
| Connection pool usage | >80% of max | >90% of max |
| Cache hit ratio | <95% | <90% |
| Replication lag | >10s | >60s |
| Dead tuple % (Postgres) | >10% and autovacuum hasn't run | >20% |
| Sudden spike in slow queries (>1s) | >2x baseline | >5x baseline |

```sql
-- PostgreSQL: connection pool alert
SELECT count(*) AS current, current_setting('max_connections')::int AS max,
    CASE WHEN count(*) > current_setting('max_connections')::int * 0.9 THEN 'CRITICAL'
         WHEN count(*) > current_setting('max_connections')::int * 0.8 THEN 'WARNING'
         ELSE 'OK' END AS status
FROM pg_stat_activity;
```

## Sequential scans on large tables — the earliest sign of a missing index (check regularly, not just once at launch)

```sql
-- PostgreSQL
SELECT schemaname, tablename, seq_scan, seq_tup_read, n_live_tup
FROM pg_stat_user_tables
WHERE seq_scan > 0 AND n_live_tup > 10000 AND seq_tup_read / NULLIF(seq_scan, 0) > 10000
ORDER BY seq_tup_read DESC;

-- MySQL
SELECT OBJECT_SCHEMA, OBJECT_NAME, SUM_NO_INDEX_USED AS full_scans
FROM performance_schema.table_io_waits_summary_by_index_usage
WHERE INDEX_NAME IS NULL AND COUNT_STAR > 0 ORDER BY SUM_NO_INDEX_USED DESC;
```

## Monitoring Best Practices

1. Record a baseline while the system is running normally — without a baseline, "slower than normal" is meaningless.
2. Track trends (daily/weekly), not just point-in-time values.
3. Use automated alerting (Prometheus/Grafana/Datadog) instead of manual checks — for specific tooling, see the `monitoring-expert` skill.
4. Test optimizations in staging first, revert immediately if write performance/replication lag worsens after applying to production.
