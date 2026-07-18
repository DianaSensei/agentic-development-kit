# PostgreSQL Tuning & Operations

Chỉ chỉnh config production khi có bằng chứng đo được (không đoán mò) — mọi giá trị dưới đây là điểm khởi đầu tham khảo cho server 16GB RAM dedicated, cần điều chỉnh theo tải thật.

## Memory Configuration

```ini
# postgresql.conf — server 16GB RAM dedicated
shared_buffers = 4GB              # 25% RAM (tối đa ~40% cho server dedicated hoàn toàn)
effective_cache_size = 12GB       # 50-75% RAM — chỉ là hint cho planner, không cấp phát thật
work_mem = 40MB                   # per-operation (sort/hash) — công thức tham khảo: (RAM*0.25)/max_connections
maintenance_work_mem = 2GB        # cho VACUUM/CREATE INDEX — có thể set cao hơn work_mem nhiều
```

Cache hit ratio mục tiêu >99%:

```sql
SELECT round(sum(heap_blks_hit)::numeric / NULLIF(sum(heap_blks_hit) + sum(heap_blks_read), 0) * 100, 2) AS cache_hit_ratio
FROM pg_statio_user_tables;
```

## Query Planner

```ini
default_statistics_target = 200   # mặc định 100 — tăng cho bảng lớn/cột cardinality cao cần estimate chính xác hơn
random_page_cost = 1.1            # SSD (mặc định 4.0 dành cho HDD quay cơ)
max_parallel_workers_per_gather = 4
```

```sql
-- Tăng statistics riêng cho 1 cột cụ thể thay vì toàn database
ALTER TABLE users ALTER COLUMN email SET STATISTICS 500;
ANALYZE users;  -- áp dụng ngay, không cần đợi autoanalyze
```

## VACUUM & Autovacuum — KHÔNG BAO GIỜ tắt autovacuum toàn cục

PostgreSQL dùng MVCC: UPDATE/DELETE không xóa row cũ ngay mà đánh dấu "dead tuple". Thiếu VACUUM → bloat table, hiệu năng giảm dần, cuối cùng là transaction ID wraparound (nghiêm trọng, có thể khiến DB từ chối ghi).

```sql
-- Theo dõi tỷ lệ dead tuple — cảnh báo khi dead_pct cao mà last_autovacuum lâu chưa chạy
SELECT relname, n_dead_tup, n_live_tup,
       round(n_dead_tup * 100.0 / NULLIF(n_live_tup + n_dead_tup, 0), 2) AS dead_pct,
       last_autovacuum
FROM pg_stat_user_tables ORDER BY n_dead_tup DESC LIMIT 20;

-- Bảng high-churn (nhiều update/delete): vacuum aggressive hơn mặc định (10% dead tuple)
ALTER TABLE orders SET (autovacuum_vacuum_scale_factor = 0.05, autovacuum_vacuum_cost_delay = 2);

-- VACUUM thủ công không khóa bảng — dùng khi cần gấp, không đợi autovacuum
VACUUM (ANALYZE, VERBOSE) orders;

-- VACUUM FULL khóa bảng hoàn toàn (exclusive lock) — tránh dùng trên production, ưu tiên pg_repack (online, không khóa)
```

## Connection & Lock

```sql
-- Query đang chạy lâu
SELECT pid, now() - query_start AS duration, query
FROM pg_stat_activity WHERE state = 'active' AND now() - query_start > interval '5 minutes';

-- Idle-in-transaction — giữ lock lâu, chặn VACUUM, thường do bug quên COMMIT/ROLLBACK
SELECT pid, now() - state_change AS idle_duration, query
FROM pg_stat_activity WHERE state = 'idle in transaction' AND now() - state_change > interval '1 minute';

-- Query nào đang block query nào
SELECT blocked.pid AS blocked_pid, blocking.pid AS blocking_pid,
       blocked.query AS blocked_query, blocking.query AS blocking_query
FROM pg_stat_activity blocked
JOIN pg_locks bl ON bl.pid = blocked.pid AND NOT bl.granted
JOIN pg_locks kl ON kl.locktype = bl.locktype AND kl.database IS NOT DISTINCT FROM bl.database
    AND kl.relation IS NOT DISTINCT FROM bl.relation AND kl.pid != bl.pid AND kl.granted
JOIN pg_stat_activity blocking ON blocking.pid = kl.pid;

-- Timeout tự động cho session/statement — tránh 1 connection treo vô thời hạn chiếm pool
ALTER SYSTEM SET idle_in_transaction_session_timeout = '5min';
ALTER SYSTEM SET statement_timeout = '30s';
```

Connection pool cạn thường do connection/transaction không đóng đúng (leak do exception không release) — dùng pgBouncer (`pool_mode = transaction`) để giảm tải connection thật tới Postgres khi có nhiều client.

## Partitioning — cân nhắc khi bảng >10M row hoặc cần drop dữ liệu cũ nhanh

```sql
CREATE TABLE events (id BIGSERIAL, created_at TIMESTAMP NOT NULL, data JSONB) PARTITION BY RANGE (created_at);
CREATE TABLE events_2024_01 PARTITION OF events FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
CREATE INDEX idx_events_2024_01_type ON events_2024_01(event_type);  -- index riêng cho từng partition

-- Query dùng đúng partition pruning nếu filter khớp cột partition key
EXPLAIN SELECT * FROM events WHERE created_at >= '2024-01-15' AND created_at < '2024-01-20';
-- Kỳ vọng: chỉ scan partition events_2024_01, không scan toàn bộ bảng
```

Drop 1 partition (VD dữ liệu >1 năm) nhanh hơn `DELETE` hàng loạt rất nhiều — không cần ghi WAL cho từng row, không tạo dead tuple cần VACUUM sau đó.

## Replication (tóm tắt — chỉ khi project thực sự cần HA/read-replica)

- **Streaming (physical)**: replica là bản sao byte-for-byte, dùng cho failover/read scaling đơn giản. Bật `wal_level = replica`, tạo replication slot để tránh mất WAL khi replica tạm ngắt kết nối.
- **Logical**: replicate theo publication/subscription ở mức row, cho phép chọn bảng cụ thể, khác version Postgres giữa 2 bên — dùng khi cần selective replication hoặc migrate giữa 2 cluster.
- Theo dõi lag LUÔN LUÔN khi có replica — lag cao mà không phát hiện sớm dẫn tới đọc dữ liệu cũ mà không biết:

```sql
-- Trên primary
SELECT client_addr, state, pg_wal_lsn_diff(sent_lsn, replay_lsn) AS lag_bytes FROM pg_stat_replication;
-- Trên standby
SELECT now() - pg_last_xact_replay_timestamp() AS replication_lag;
```

- Production HA thật thường cần thêm Patroni/pg_auto_failover (tự động failover) + PgBouncer/HAProxy (routing) — đây là quyết định hạ tầng lớn, cần bàn riêng với user, không tự thêm.

## Backup — Point-in-Time Recovery (PITR)

```ini
archive_mode = on
archive_command = 'cp %p /backup/wal/%f'   # hoặc dùng pgBackRest cho production thật
```

```bash
pg_basebackup -h localhost -U postgres -D /backup/base/$(date +%Y%m%d) -Ft -z -P
# Restore: khôi phục base backup, tạo recovery.signal, set recovery_target_time trong postgresql.conf, start lại
```

## Config file tham khảo (16GB RAM, production)

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
log_min_duration_statement = 1000   # log query > 1s
log_lock_waits = on
```

## Maintenance Checklist

- **Hàng ngày**: autovacuum activity, query chạy lâu, replication lag (nếu có), cache hit ratio.
- **Hàng tuần**: slow query từ `pg_stat_statements`, table/index bloat, index không dùng.
- **Hàng tháng**: review autovacuum setting, reindex bảng update nhiều, capacity trend.
- **Hàng quý**: test restore backup thật (không chỉ tin backup chạy thành công), review version upgrade.
