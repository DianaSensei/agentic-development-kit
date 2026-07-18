# Query Patterns — Rewrite, CTE, Window Function

## Query Rewrite phổ biến (before → after)

```sql
-- Subquery tương quan → JOIN với window function
-- BEFORE (chậm — chạy subquery cho từng row)
SELECT * FROM orders o
WHERE total > (SELECT AVG(total) FROM orders WHERE user_id = o.user_id);

-- AFTER (nhanh — 1 lần quét)
SELECT * FROM (
    SELECT *, AVG(total) OVER (PARTITION BY user_id) AS avg_total FROM orders
) x WHERE total > avg_total;
```

```sql
-- IN (subquery) → EXISTS — short-circuit ngay khi match đầu tiên, không cần materialize hết subquery
SELECT * FROM users u
WHERE EXISTS (SELECT 1 FROM orders o WHERE o.user_id = u.id AND o.total > 1000);

-- NOT IN (có rủi ro NULL) → NOT EXISTS (an toàn hơn, không bị NULL trong subquery làm sai kết quả)
SELECT * FROM customers c
WHERE NOT EXISTS (SELECT 1 FROM orders o WHERE o.customer_id = c.customer_id);
```

```sql
-- Pagination offset lớn → keyset pagination (cursor-based)
-- BEFORE: chậm dần khi OFFSET lớn (DB vẫn phải quét qua hết các row bị bỏ)
SELECT * FROM products ORDER BY created_at DESC LIMIT 20 OFFSET 10000;

-- AFTER: luôn nhanh bất kể đang ở trang nào
SELECT * FROM products
WHERE created_at < :last_seen_created_at
   OR (created_at = :last_seen_created_at AND id < :last_seen_id)
ORDER BY created_at DESC, id DESC LIMIT 20;
-- Cần index hỗ trợ: CREATE INDEX idx_products_pagination ON products (created_at DESC, id DESC);
```

**Bảng red-flag nhanh:**

| Pattern | Vấn đề | Giải pháp |
|---------|--------|-----------|
| `SELECT *` | Lấy thừa cột, I/O thừa | Chỉ select cột cần |
| Scalar subquery trong `SELECT` | N+1 | JOIN + GROUP BY |
| `WHERE DATE(col) = ...` | Hàm trên cột chặn index | Đổi thành range: `col >= 'x' AND col < 'y'` |
| `IN` list lớn (>100) | Kém hiệu quả | Temp table hoặc JOIN |
| `SELECT DISTINCT` chỉ để dedup theo tồn tại | Sort/dedup thừa | `EXISTS` |

## CTE

```sql
WITH active_users AS (
    SELECT user_id, username FROM users WHERE is_active = true
),
user_orders AS (
    SELECT user_id, COUNT(*) AS order_count, SUM(total) AS total_spent
    FROM orders WHERE status = 'completed' GROUP BY user_id
)
SELECT u.username, COALESCE(o.order_count, 0) AS orders
FROM active_users u LEFT JOIN user_orders o ON u.user_id = o.user_id;
```

PostgreSQL 12+ mặc định materialize CTE dùng 1 lần cũng như nhiều lần — dùng `AS NOT MATERIALIZED` để ép inline (tối ưu hơn khi CTE chỉ dùng 1 lần và optimizer có thể đẩy filter vào trong), hoặc `AS MATERIALIZED` để ép tính 1 lần rồi tái sử dụng (tối ưu khi CTE được reference nhiều lần và tính toán nặng).

### Recursive CTE — traversal hierarchy

```sql
WITH RECURSIVE org_hierarchy AS (
    SELECT employee_id, name, manager_id, 1 AS level, ARRAY[employee_id] AS path
    FROM employees WHERE manager_id IS NULL
    UNION ALL
    SELECT e.employee_id, e.name, e.manager_id, h.level + 1, h.path || e.employee_id
    FROM employees e
    JOIN org_hierarchy h ON e.manager_id = h.employee_id
    WHERE NOT e.employee_id = ANY(h.path)   -- luôn cần điều kiện chặn cycle
)
SELECT employee_id, REPEAT('  ', level - 1) || name AS indented_name, level
FROM org_hierarchy ORDER BY path;
```

## JOIN nâng cao

```sql
-- LATERAL (PostgreSQL): "top N per group" hiệu quả, tránh window function + subquery lồng
SELECT c.customer_id, recent.order_date, recent.total
FROM customers c
CROSS JOIN LATERAL (
    SELECT order_date, total FROM orders o
    WHERE o.customer_id = c.customer_id
    ORDER BY order_date DESC LIMIT 3
) recent;

-- Anti-join: record ở A không có ở B
SELECT u.user_id FROM users u
LEFT JOIN orders o ON u.user_id = o.user_id
WHERE o.order_id IS NULL;
```

## Window Function

```sql
-- Ranking: khác biệt quan trọng giữa 3 hàm khi có giá trị trùng nhau
SELECT student_id, score,
    RANK()       OVER (ORDER BY score DESC) AS rnk,        -- có gap: 1,1,3
    DENSE_RANK() OVER (ORDER BY score DESC) AS dense_rnk,  -- không gap: 1,1,2
    ROW_NUMBER() OVER (ORDER BY score DESC) AS row_num     -- luôn duy nhất: 1,2,3
FROM exam_results;

-- Top-N per group — pattern rất hay dùng
SELECT * FROM (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY order_date DESC) AS rn
    FROM orders
) ranked WHERE rn = 1;

-- Running total & rolling average
SELECT order_date, daily_revenue,
    SUM(daily_revenue) OVER (ORDER BY order_date) AS cumulative_revenue,
    AVG(daily_revenue) OVER (ORDER BY order_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS rolling_7day_avg
FROM daily_sales;

-- LAG/LEAD — so sánh với row trước/sau (day-over-day, phát hiện gap thời gian)
SELECT order_date, total,
    total - LAG(total) OVER (ORDER BY order_date) AS day_over_day_change
FROM daily_orders;

-- Percentile
SELECT employee_id, salary,
    PERCENT_RANK() OVER (ORDER BY salary) AS pct_rank,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY salary) OVER () AS median_salary
FROM employees;
```

`ROWS` (offset vật lý theo row) khác `RANGE` (offset theo giá trị logic, VD khoảng thời gian) trong frame specification — dùng `RANGE BETWEEN INTERVAL '7 days' PRECEDING AND CURRENT ROW` khi cần "7 ngày gần nhất" đúng nghĩa lịch, không phải "7 row gần nhất" (2 cái khác nhau nếu có ngày thiếu dữ liệu).

**Tránh multiple window pass**: gộp nhiều `OVER()` cùng frame vào 1 lần quét thay vì nhiều subquery riêng — `SELECT DISTINCT AVG(price) OVER (), MAX(price) OVER () FROM products` nhanh hơn 2 scalar subquery riêng.

## Set Operations

```sql
SELECT product_id FROM active_products
UNION                                    -- dedup, chậm hơn UNION ALL
SELECT product_id FROM featured_products;

SELECT user_id, 'signup' FROM signups
UNION ALL                                -- không dedup, nhanh hơn — dùng khi chắc chắn không trùng hoặc trùng chấp nhận được
SELECT user_id, 'purchase' FROM purchases;
```
