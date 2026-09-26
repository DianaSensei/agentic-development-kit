# MySQL (InnoDB) Tuning

Only tune when you have measured evidence - the values below are reference starting points for a dedicated 16GB RAM server.

## InnoDB Buffer Pool - the most important setting, equivalent to Postgres's `shared_buffers`

```sql
-- Recommended: 70-80% of RAM for a dedicated MySQL server
SET GLOBAL innodb_buffer_pool_size = 12884901888;  -- 12GB for a 16GB server
SET GLOBAL innodb_buffer_pool_instances = 8;        -- 1 instance per 1GB, max 64, reduces contention on multi-core systems

-- Target hit ratio >99%
SELECT (1 - (r.v / q.v)) * 100 AS hit_ratio FROM
  (SELECT VARIABLE_VALUE AS v FROM performance_schema.global_status WHERE VARIABLE_NAME = 'Innodb_buffer_pool_reads') r,
  (SELECT VARIABLE_VALUE AS v FROM performance_schema.global_status WHERE VARIABLE_NAME = 'Innodb_buffer_pool_read_requests') q;
```

## Log & I/O

```ini
innodb_log_file_size = 1G           # larger = better write performance but longer crash recovery - balance against write load
innodb_flush_log_at_trx_commit = 1  # 1 = full ACID (default, safest)
                                      # 2 = write to OS cache, flush every second (trades safety for speed - acceptable for replicas/analytics)
innodb_flush_method = O_DIRECT      # avoids double buffering
innodb_io_capacity = 10000          # IOPS the storage can handle - SSDs are typically 5000-20000
```

## Slow Query Log & Performance Schema

```sql
SET GLOBAL slow_query_log = 'ON';
SET GLOBAL long_query_time = 1.0;               -- log queries > 1s
SET GLOBAL log_queries_not_using_indexes = 'ON';

-- Top queries by total execution time
SELECT DIGEST_TEXT, COUNT_STAR AS exec_count,
       ROUND(SUM_TIMER_WAIT / 1e12, 3) AS total_time_sec
FROM performance_schema.events_statements_summary_by_digest
ORDER BY SUM_TIMER_WAIT DESC LIMIT 20;

-- Full table scans - a sign of missing indexes
SELECT * FROM sys.statements_with_full_table_scans ORDER BY exec_count DESC LIMIT 10;
```

## Index & Covering Index

```sql
CREATE INDEX idx_orders_user_covering ON orders(user_id, status, created_at, total);
EXPLAIN SELECT status, created_at, total FROM orders WHERE user_id = 123;
-- Expected: "Using index" in the Extra column → covering index, no need to read the base table

-- Find duplicate/redundant indexes
SELECT a.table_name, a.index_name AS index1, b.index_name AS index2
FROM information_schema.statistics a
JOIN information_schema.statistics b
    ON a.table_schema = b.table_schema AND a.table_name = b.table_name
    AND a.seq_in_index = b.seq_in_index AND a.column_name = b.column_name AND a.index_name != b.index_name;
```

## Partitioning (Range/List)

```sql
CREATE TABLE events (
    id BIGINT NOT NULL AUTO_INCREMENT, created_at DATETIME NOT NULL,
    PRIMARY KEY (id, created_at)
) PARTITION BY RANGE (YEAR(created_at)) (
    PARTITION p2024 VALUES LESS THAN (2025),
    PARTITION p2025 VALUES LESS THAN (2026),
    PARTITION pmax VALUES LESS THAN MAXVALUE
);
-- Dropping an old partition = fast delete, no need for a bulk DELETE
ALTER TABLE events DROP PARTITION p2024;
```

## Replication

```sql
SET GLOBAL binlog_format = 'ROW';   -- ROW is safest for replication (vs STATEMENT/MIXED)
SET GLOBAL sync_binlog = 1;         -- safest; 0 is faster but risks data loss on crash

-- On the replica: check lag
SELECT Seconds_Behind_Master FROM (SHOW SLAVE STATUS) s;
```

## Table Maintenance

```sql
ANALYZE TABLE users;   -- refresh statistics - run after a bulk data change
OPTIMIZE TABLE users;  -- rebuild, reduces fragmentation (equivalent to Postgres's VACUUM FULL - also locks the table, be careful in production)
```

## Reference config (16GB RAM, production)

```ini
[mysqld]
innodb_buffer_pool_size = 12G
innodb_buffer_pool_instances = 8
innodb_log_file_size = 1G
innodb_flush_log_at_trx_commit = 1
innodb_flush_method = O_DIRECT
innodb_io_capacity = 10000
max_connections = 200
thread_cache_size = 100
slow_query_log = ON
long_query_time = 1
log_queries_not_using_indexes = ON
binlog_format = ROW
sync_binlog = 1
performance_schema = ON
character_set_server = utf8mb4
```

## Key differences from PostgreSQL to remember

- Default isolation level is `REPEATABLE READ` (Postgres/Oracle default to `READ COMMITTED`) - see the main SKILL.md, Transaction Isolation section.
- No full `EXPLAIN ANALYZE` like Postgres until MySQL 8.0 - before that only `EXPLAIN` was available (estimates, not actual runtime).
- The query cache was completely removed as of MySQL 8.0 - `query_cache_type`/`query_cache_size` no longer exist.
