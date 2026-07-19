# Query Patterns — Rewrite, CTE, Window Functions

## Common Query Rewrites (before → after)

```sql
-- Correlated subquery → JOIN with window function
-- BEFORE (slow — runs the subquery for every row)
SELECT * FROM orders o
WHERE total > (SELECT AVG(total) FROM orders WHERE user_id = o.user_id);

-- AFTER (fast — single pass)
SELECT * FROM (
    SELECT *, AVG(total) OVER (PARTITION BY user_id) AS avg_total FROM orders
) x WHERE total > avg_total;
```

```sql
-- IN (subquery) → EXISTS — short-circuits on the first match, no need to materialize the whole subquery
SELECT * FROM users u
WHERE EXISTS (SELECT 1 FROM orders o WHERE o.user_id = u.id AND o.total > 1000);

-- NOT IN (has NULL risk) → NOT EXISTS (safer, NULLs in the subquery won't silently produce wrong results)
SELECT * FROM customers c
WHERE NOT EXISTS (SELECT 1 FROM orders o WHERE o.customer_id = c.customer_id);
```

```sql
-- Large offset pagination → keyset pagination (cursor-based)
-- BEFORE: gets progressively slower as OFFSET grows (the DB still has to scan through all skipped rows)
SELECT * FROM products ORDER BY created_at DESC LIMIT 20 OFFSET 10000;

-- AFTER: consistently fast regardless of which page you're on
SELECT * FROM products
WHERE created_at < :last_seen_created_at
   OR (created_at = :last_seen_created_at AND id < :last_seen_id)
ORDER BY created_at DESC, id DESC LIMIT 20;
-- Requires a supporting index: CREATE INDEX idx_products_pagination ON products (created_at DESC, id DESC);
```

**Quick red-flag table:**

| Pattern | Problem | Solution |
|---------|--------|-----------|
| `SELECT *` | Fetches unnecessary columns, wasted I/O | Select only the columns you need |
| Scalar subquery in `SELECT` | N+1 | JOIN + GROUP BY |
| `WHERE DATE(col) = ...` | Function on a column blocks index usage | Rewrite as a range: `col >= 'x' AND col < 'y'` |
| Large `IN` list (>100) | Inefficient | Temp table or JOIN |
| `SELECT DISTINCT` used just to dedup by existence | Unnecessary sort/dedup | `EXISTS` |

## CTEs

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

PostgreSQL 12+ materializes a CTE by default whether it's used once or many times — use `AS NOT
MATERIALIZED` to force inlining (better when the CTE is only used once and the optimizer can push the
filter inside), or `AS MATERIALIZED` to force computing it once and reusing the result (better when the
CTE is referenced multiple times and is expensive to compute).

### Recursive CTE — hierarchy traversal

```sql
WITH RECURSIVE org_hierarchy AS (
    SELECT employee_id, name, manager_id, 1 AS level, ARRAY[employee_id] AS path
    FROM employees WHERE manager_id IS NULL
    UNION ALL
    SELECT e.employee_id, e.name, e.manager_id, h.level + 1, h.path || e.employee_id
    FROM employees e
    JOIN org_hierarchy h ON e.manager_id = h.employee_id
    WHERE NOT e.employee_id = ANY(h.path)   -- always needed to prevent cycles
)
SELECT employee_id, REPEAT('  ', level - 1) || name AS indented_name, level
FROM org_hierarchy ORDER BY path;
```

## Advanced JOINs

```sql
-- LATERAL (PostgreSQL): efficient "top N per group," avoids window function + nested subquery
SELECT c.customer_id, recent.order_date, recent.total
FROM customers c
CROSS JOIN LATERAL (
    SELECT order_date, total FROM orders o
    WHERE o.customer_id = c.customer_id
    ORDER BY order_date DESC LIMIT 3
) recent;

-- Anti-join: records in A that don't exist in B
SELECT u.user_id FROM users u
LEFT JOIN orders o ON u.user_id = o.user_id
WHERE o.order_id IS NULL;
```

## Window Functions

```sql
-- Ranking: an important distinction between these 3 functions when there are tied values
SELECT student_id, score,
    RANK()       OVER (ORDER BY score DESC) AS rnk,        -- leaves gaps: 1,1,3
    DENSE_RANK() OVER (ORDER BY score DESC) AS dense_rnk,  -- no gaps: 1,1,2
    ROW_NUMBER() OVER (ORDER BY score DESC) AS row_num     -- always unique: 1,2,3
FROM exam_results;

-- Top-N per group — a very common pattern
SELECT * FROM (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY order_date DESC) AS rn
    FROM orders
) ranked WHERE rn = 1;

-- Running total & rolling average
SELECT order_date, daily_revenue,
    SUM(daily_revenue) OVER (ORDER BY order_date) AS cumulative_revenue,
    AVG(daily_revenue) OVER (ORDER BY order_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS rolling_7day_avg
FROM daily_sales;

-- LAG/LEAD — comparing to the previous/next row (day-over-day, detecting time gaps)
SELECT order_date, total,
    total - LAG(total) OVER (ORDER BY order_date) AS day_over_day_change
FROM daily_orders;

-- Percentile
SELECT employee_id, salary,
    PERCENT_RANK() OVER (ORDER BY salary) AS pct_rank,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY salary) OVER () AS median_salary
FROM employees;
```

`ROWS` (physical row offset) differs from `RANGE` (logical value offset, e.g. a time interval) in a frame
specification — use `RANGE BETWEEN INTERVAL '7 days' PRECEDING AND CURRENT ROW` when you need a true
calendar "last 7 days," not "the last 7 rows" (these differ when there are days with missing data).

**Avoid multiple window passes**: combine multiple `OVER()` clauses with the same frame into a single scan
instead of separate subqueries — `SELECT DISTINCT AVG(price) OVER (), MAX(price) OVER () FROM products` is
faster than two separate scalar subqueries.

## Set Operations

```sql
SELECT product_id FROM active_products
UNION                                    -- dedups, slower than UNION ALL
SELECT product_id FROM featured_products;

SELECT user_id, 'signup' FROM signups
UNION ALL                                -- no dedup, faster — use when you're sure there's no overlap or overlap is acceptable
SELECT user_id, 'purchase' FROM purchases;
```
