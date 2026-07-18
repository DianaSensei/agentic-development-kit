# Monitoring & Alert Thresholds

Setup container test (Testcontainers) xem `testcontainers-skill`. File này là truy vấn theo dõi sức khỏe DB **thật** (staging/production), không phải test.

## Baseline trước khi tối ưu — LUÔN đo trước/sau mỗi thay đổi, không đổi nhiều thứ cùng lúc

```sql
-- PostgreSQL: top query theo tổng thời gian (cần pg_stat_statements)
SELECT substring(query, 1, 100) AS short_query, calls,
       round(mean_exec_time::numeric, 2) AS mean_ms,
       round((100 * total_exec_time / sum(total_exec_time) OVER ())::numeric, 2) AS pct_total
FROM pg_stat_statements ORDER BY total_exec_time DESC LIMIT 20;

-- MySQL: tương đương qua performance_schema
SELECT DIGEST_TEXT, COUNT_STAR AS exec_count, ROUND(SUM_TIMER_WAIT / 1e12, 3) AS total_sec
FROM performance_schema.events_statements_summary_by_digest ORDER BY SUM_TIMER_WAIT DESC LIMIT 20;
```

## Health Check nhanh (chạy định kỳ hoặc khi nghi ngờ sự cố)

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

## Alert Threshold tham khảo (điều chỉnh theo baseline thật của project, không copy máy móc)

| Metric | WARNING | CRITICAL |
|--------|---------|----------|
| Connection pool usage | >80% max | >90% max |
| Cache hit ratio | <95% | <90% |
| Replication lag | >10s | >60s |
| Dead tuple % (Postgres) | >10% chưa autovacuum | >20% |
| Slow query (>1s) tăng đột biến | tăng >2x baseline | tăng >5x baseline |

```sql
-- PostgreSQL: cảnh báo connection pool
SELECT count(*) AS current, current_setting('max_connections')::int AS max,
    CASE WHEN count(*) > current_setting('max_connections')::int * 0.9 THEN 'CRITICAL'
         WHEN count(*) > current_setting('max_connections')::int * 0.8 THEN 'WARNING'
         ELSE 'OK' END AS status
FROM pg_stat_activity;
```

## Sequential scan trên bảng lớn — dấu hiệu sớm nhất của thiếu index (kiểm tra định kỳ, không chỉ 1 lần lúc launch)

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

1. Ghi lại baseline khi hệ thống chạy bình thường — không có baseline thì không biết "chậm hơn bình thường" nghĩa là gì.
2. Theo dõi xu hướng (daily/weekly), không chỉ nhìn giá trị tức thời.
3. Alert tự động (Prometheus/Grafana/Datadog) thay vì kiểm tra thủ công — tool cụ thể xem `monitoring-expert` skill.
4. Test optimization ở staging trước, revert ngay nếu write performance/replication lag xấu đi sau khi áp dụng production.
