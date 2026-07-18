# MySQL (InnoDB) Tuning

Chỉ chỉnh khi có bằng chứng đo được — các giá trị dưới đây là điểm khởi đầu tham khảo cho server 16GB RAM dedicated.

## InnoDB Buffer Pool — quan trọng nhất, tương đương `shared_buffers` của Postgres

```sql
-- Khuyến nghị: 70-80% RAM cho server dedicated MySQL
SET GLOBAL innodb_buffer_pool_size = 12884901888;  -- 12GB cho server 16GB
SET GLOBAL innodb_buffer_pool_instances = 8;        -- 1 instance/1GB, tối đa 64, giúp giảm contention trên multi-core

-- Hit ratio mục tiêu >99%
SELECT (1 - (r.v / q.v)) * 100 AS hit_ratio FROM
  (SELECT VARIABLE_VALUE AS v FROM performance_schema.global_status WHERE VARIABLE_NAME = 'Innodb_buffer_pool_reads') r,
  (SELECT VARIABLE_VALUE AS v FROM performance_schema.global_status WHERE VARIABLE_NAME = 'Innodb_buffer_pool_read_requests') q;
```

## Log & I/O

```ini
innodb_log_file_size = 1G           # lớn hơn = write performance tốt hơn nhưng crash recovery lâu hơn — cân bằng theo write load
innodb_flush_log_at_trx_commit = 1  # 1 = ACID đầy đủ (mặc định, an toàn nhất)
                                      # 2 = ghi OS cache, flush mỗi giây (đánh đổi an toàn lấy tốc độ — chấp nhận được cho replica/analytics)
innodb_flush_method = O_DIRECT      # tránh double buffering
innodb_io_capacity = 10000          # IOPS storage chịu được — SSD thường 5000-20000
```

## Slow Query Log & Performance Schema

```sql
SET GLOBAL slow_query_log = 'ON';
SET GLOBAL long_query_time = 1.0;               -- log query > 1s
SET GLOBAL log_queries_not_using_indexes = 'ON';

-- Top query theo tổng thời gian thực thi
SELECT DIGEST_TEXT, COUNT_STAR AS exec_count,
       ROUND(SUM_TIMER_WAIT / 1e12, 3) AS total_time_sec
FROM performance_schema.events_statements_summary_by_digest
ORDER BY SUM_TIMER_WAIT DESC LIMIT 20;

-- Full table scan — dấu hiệu thiếu index
SELECT * FROM sys.statements_with_full_table_scans ORDER BY exec_count DESC LIMIT 10;
```

## Index & Covering Index

```sql
CREATE INDEX idx_orders_user_covering ON orders(user_id, status, created_at, total);
EXPLAIN SELECT status, created_at, total FROM orders WHERE user_id = 123;
-- Kỳ vọng: "Using index" trong cột Extra → covering index, không cần đọc bảng gốc

-- Tìm index trùng lặp/thừa
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
-- Drop partition cũ = xóa nhanh, không cần DELETE hàng loạt
ALTER TABLE events DROP PARTITION p2024;
```

## Replication

```sql
SET GLOBAL binlog_format = 'ROW';   -- ROW an toàn nhất cho replication (so với STATEMENT/MIXED)
SET GLOBAL sync_binlog = 1;         -- an toàn nhất; 0 nhanh hơn nhưng rủi ro mất data khi crash

-- Trên replica: check lag
SELECT Seconds_Behind_Master FROM (SHOW SLAVE STATUS) s;
```

## Table Maintenance

```sql
ANALYZE TABLE users;   -- refresh statistics — chạy sau bulk data change
OPTIMIZE TABLE users;  -- rebuild, giảm fragmentation (tương đương VACUUM FULL của Postgres — cũng khóa bảng, cẩn thận trên production)
```

## Config tham khảo (16GB RAM, production)

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

## Khác biệt cần nhớ so với PostgreSQL

- Isolation level mặc định là `REPEATABLE READ` (Postgres/Oracle là `READ COMMITTED`) — xem SKILL.md chính, mục Transaction Isolation.
- Không có `EXPLAIN ANALYZE` đầy đủ như Postgres tới MySQL 8.0 — trước đó chỉ có `EXPLAIN` (ước tính, không phải actual runtime).
- Query cache đã bị loại bỏ hoàn toàn từ MySQL 8.0 — không còn `query_cache_type`/`query_cache_size`.
