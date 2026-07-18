# EXPLAIN Analysis & Index Design

## Đọc EXPLAIN — luôn bắt buộc TRƯỚC khi khẳng định 1 query chậm cần index

```sql
-- PostgreSQL: luôn kèm BUFFERS để thấy tỷ lệ cache hit vs disk read
EXPLAIN (ANALYZE, BUFFERS, VERBOSE)
SELECT u.id, u.name, COUNT(o.id) AS order_count
FROM users u LEFT JOIN orders o ON u.id = o.user_id
WHERE u.created_at > NOW() - INTERVAL '30 days'
GROUP BY u.id, u.name
HAVING COUNT(o.id) > 5;

-- MySQL 8.0+
EXPLAIN ANALYZE
SELECT * FROM orders WHERE status = 'pending' AND created_at > NOW() - INTERVAL 7 DAY;
EXPLAIN FORMAT=JSON SELECT ...;  -- chi tiết hơn khi cần
```

**Đọc kết quả — pattern cần chú ý:**

| Pattern | Ý nghĩa | Hướng xử lý |
|---------|---------|-------------|
| `Seq Scan`/table scan trên bảng lớn | Không dùng index | Thêm B-tree index đúng cột filter |
| `rows` ước tính lệch xa `actual rows` | Statistics cũ | `ANALYZE <table>` |
| `Buffers: hit thấp, read cao` | Cache hit ratio thấp | Tăng `shared_buffers`, hoặc thêm covering index |
| `Sort Method: external merge` | Sort tràn ra disk | Tăng `work_mem` cho session đó |
| `Nested Loop` với outer set lớn | Tăng trưởng cấp số nhân | Index đúng cột join của bảng inner |
| `Index Only Scan` | Tốt nhất — không cần đọc heap | Không cần xử lý gì thêm |

Node type từ nhanh → chậm: `Index Only Scan` > `Index Scan` > `Bitmap Index Scan` > `Seq Scan` (chấp nhận được với bảng nhỏ, là vấn đề với bảng lớn).

## B-Tree Index (mặc định)

```sql
CREATE INDEX idx_users_email ON users(email);               -- WHERE
CREATE INDEX idx_orders_user_id ON orders(user_id);          -- JOIN

-- Composite: thứ tự cột quan trọng — equality trước, range sau; cột chọn lọc cao trước
CREATE INDEX idx_orders_status_created ON orders(status, created_at);
-- Tốt cho: WHERE status = 'pending'; WHERE status = 'pending' AND created_at > ...
-- KHÔNG dùng được cho: WHERE created_at > ... (thiếu status ở đầu)
```

## Covering Index — tránh heap fetch, cho phép Index Only Scan

```sql
-- PostgreSQL: INCLUDE cho cột không cần trong điều kiện filter/sort, chỉ cần trong SELECT
CREATE INDEX CONCURRENTLY idx_orders_status_created_covering
    ON orders (status, created_at) INCLUDE (customer_id, total_amount);

-- MySQL: nối thêm cột vào cuối composite index
CREATE INDEX idx_orders_user_covering ON orders(user_id, status, created_at, total);
```

Luôn tạo index bằng `CREATE INDEX CONCURRENTLY` (PostgreSQL) để tránh khóa bảng khi deploy lên production — index thường xây dựng mất thời gian trên bảng lớn, `CONCURRENTLY` cho phép ghi/đọc bình thường song song.

## Partial / Expression Index — nhỏ hơn, nhanh hơn khi chỉ cần 1 tập con dữ liệu

```sql
-- Partial: chỉ index phần dữ liệu thực sự được query
CREATE INDEX idx_orders_active ON orders(status, user_id) WHERE status IN ('pending', 'processing');

-- Expression: khi query luôn áp dụng hàm lên cột (LOWER, DATE...)
CREATE INDEX idx_users_email_lower ON users(LOWER(email));
-- Query PHẢI khớp đúng biểu thức mới dùng được index này:
SELECT * FROM users WHERE LOWER(email) = LOWER('User@Example.com');
```

## Index chuyên biệt (PostgreSQL)

```sql
-- GIN: full-text search, array, JSONB containment
CREATE INDEX idx_posts_search ON posts USING GIN(to_tsvector('english', title || ' ' || content));
CREATE INDEX idx_products_tags ON products USING GIN(tags);        -- WHERE tags @> ARRAY['x']
CREATE INDEX idx_users_metadata ON users USING GIN(metadata);       -- WHERE metadata @> '{"k":"v"}'

-- GiST: geometric (PostGIS), range type
CREATE INDEX idx_events_time_range ON events USING GIST(time_range);

-- BRIN: bảng rất lớn, dữ liệu tự nhiên có thứ tự (time-series insert-only) — index cực nhỏ
CREATE INDEX idx_metrics_time_brin ON metrics USING BRIN(timestamp);
```

## Anti-pattern thường gặp

| Anti-pattern | Vấn đề | Cách sửa |
|-------------|--------|----------|
| Index mọi cột | Overhead ghi, tốn storage | Chỉ index theo query pattern thật |
| Index thừa `(a)` + `(a,b)` | Trùng lặp | Giữ `(a,b)`, xóa `(a)` |
| Sai thứ tự cột composite | `(created_at, user_id)` cho `WHERE user_id = ?` | Đặt cột filter chính xác trước |
| `OR` trong WHERE | Ngăn dùng index | Tách `UNION` hoặc 2 query riêng |
| `LIKE '%term%'` | Full table scan | Full-text search hoặc `pg_trgm` |
| Implicit type conversion | Ngăn dùng index | Match đúng kiểu dữ liệu cột |

## Bảo trì index

```sql
-- PostgreSQL: tìm index không dùng (xóa sau khi xác nhận ổn định ~30 ngày theo dõi)
SELECT schemaname, tablename, indexname, idx_scan,
       pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_stat_user_indexes WHERE idx_scan = 0 AND indexrelname NOT LIKE 'pg_toast%'
ORDER BY pg_relation_size(indexrelid) DESC;

-- Rebuild index bloat mà không khóa bảng
REINDEX INDEX CONCURRENTLY idx_users_email;

-- MySQL: tìm index chưa từng dùng
SELECT object_schema, object_name, index_name
FROM performance_schema.table_io_waits_summary_by_index_usage
WHERE index_name IS NOT NULL AND count_star = 0 AND object_schema = 'your_database';
```

## Checklist thiết kế index

1. Xác định query pattern thật qua `pg_stat_statements`/slow query log — không đoán.
2. Kiểm tra `EXPLAIN` — tìm `Seq Scan` trên bảng lớn.
3. Thiết kế: equality → range → include.
4. Tạo với `CONCURRENTLY` để không khóa bảng production.
5. Xác nhận cải thiện bằng `EXPLAIN` trước/sau.
6. Theo dõi usage, xóa index không dùng sau ~30 ngày.
