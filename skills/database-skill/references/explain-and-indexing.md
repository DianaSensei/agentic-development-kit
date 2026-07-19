# EXPLAIN Analysis & Index Design

## Reading EXPLAIN — always mandatory BEFORE claiming a slow query needs an index

```sql
-- PostgreSQL: always include BUFFERS to see the cache-hit vs disk-read ratio
EXPLAIN (ANALYZE, BUFFERS, VERBOSE)
SELECT u.id, u.name, COUNT(o.id) AS order_count
FROM users u LEFT JOIN orders o ON u.id = o.user_id
WHERE u.created_at > NOW() - INTERVAL '30 days'
GROUP BY u.id, u.name
HAVING COUNT(o.id) > 5;

-- MySQL 8.0+
EXPLAIN ANALYZE
SELECT * FROM orders WHERE status = 'pending' AND created_at > NOW() - INTERVAL 7 DAY;
EXPLAIN FORMAT=JSON SELECT ...;  -- more detail when needed
```

**Reading the results — patterns to watch for:**

| Pattern | Meaning | Fix direction |
|---------|---------|-------------|
| `Seq Scan`/table scan on a large table | Not using an index | Add a B-tree index on the filtered column |
| Estimated `rows` far off from `actual rows` | Stale statistics | `ANALYZE <table>` |
| `Buffers: hit low, read high` | Low cache hit ratio | Increase `shared_buffers`, or add a covering index |
| `Sort Method: external merge` | Sort spilled to disk | Increase `work_mem` for that session |
| `Nested Loop` with a large outer set | Exponential growth | Index the join column of the inner table |
| `Index Only Scan` | Best case — no heap read needed | No further action needed |

Node type from fastest to slowest: `Index Only Scan` > `Index Scan` > `Bitmap Index Scan` > `Seq Scan`
(acceptable for small tables, a problem for large ones).

## B-Tree Index (default)

```sql
CREATE INDEX idx_users_email ON users(email);               -- WHERE
CREATE INDEX idx_orders_user_id ON orders(user_id);          -- JOIN

-- Composite: column order matters — equality columns first, range columns after; most selective column first
CREATE INDEX idx_orders_status_created ON orders(status, created_at);
-- Good for: WHERE status = 'pending'; WHERE status = 'pending' AND created_at > ...
-- NOT usable for: WHERE created_at > ... (missing status at the front)
```

## Covering Index — avoids heap fetches, enables Index Only Scan

```sql
-- PostgreSQL: INCLUDE for columns not needed in the filter/sort condition, only needed in the SELECT
CREATE INDEX CONCURRENTLY idx_orders_status_created_covering
    ON orders (status, created_at) INCLUDE (customer_id, total_amount);

-- MySQL: append columns to the end of a composite index
CREATE INDEX idx_orders_user_covering ON orders(user_id, status, created_at, total);
```

Always create indexes with `CREATE INDEX CONCURRENTLY` (PostgreSQL) to avoid locking the table when
deploying to production — index builds often take a while on large tables, and `CONCURRENTLY` allows
normal reads/writes to continue in parallel.

## Partial / Expression Index — smaller, faster when you only need a subset of the data

```sql
-- Partial: only index the portion of data that's actually queried
CREATE INDEX idx_orders_active ON orders(status, user_id) WHERE status IN ('pending', 'processing');

-- Expression: when the query always applies a function to a column (LOWER, DATE...)
CREATE INDEX idx_users_email_lower ON users(LOWER(email));
-- The query MUST match the expression exactly for this index to be used:
SELECT * FROM users WHERE LOWER(email) = LOWER('User@Example.com');
```

## Specialized Indexes (PostgreSQL)

```sql
-- GIN: full-text search, arrays, JSONB containment
CREATE INDEX idx_posts_search ON posts USING GIN(to_tsvector('english', title || ' ' || content));
CREATE INDEX idx_products_tags ON products USING GIN(tags);        -- WHERE tags @> ARRAY['x']
CREATE INDEX idx_users_metadata ON users USING GIN(metadata);       -- WHERE metadata @> '{"k":"v"}'

-- GiST: geometric (PostGIS), range types
CREATE INDEX idx_events_time_range ON events USING GIST(time_range);

-- BRIN: very large tables, naturally ordered data (time-series insert-only) — extremely small index
CREATE INDEX idx_metrics_time_brin ON metrics USING BRIN(timestamp);
```

## Common Anti-patterns

| Anti-pattern | Problem | Fix |
|-------------|--------|----------|
| Indexing every column | Write overhead, storage cost | Only index based on actual query patterns |
| Redundant `(a)` + `(a,b)` | Duplication | Keep `(a,b)`, drop `(a)` |
| Wrong composite column order | `(created_at, user_id)` for `WHERE user_id = ?` | Put the filtered column first |
| `OR` in WHERE | Prevents index usage | Split into `UNION` or two separate queries |
| `LIKE '%term%'` | Full table scan | Full-text search or `pg_trgm` |
| Implicit type conversion | Prevents index usage | Match the column's data type exactly |

## Index Maintenance

```sql
-- PostgreSQL: find unused indexes (drop after confirming stability over ~30 days of monitoring)
SELECT schemaname, tablename, indexname, idx_scan,
       pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_stat_user_indexes WHERE idx_scan = 0 AND indexrelname NOT LIKE 'pg_toast%'
ORDER BY pg_relation_size(indexrelid) DESC;

-- Rebuild a bloated index without locking the table
REINDEX INDEX CONCURRENTLY idx_users_email;

-- MySQL: find never-used indexes
SELECT object_schema, object_name, index_name
FROM performance_schema.table_io_waits_summary_by_index_usage
WHERE index_name IS NOT NULL AND count_star = 0 AND object_schema = 'your_database';
```

## Index Design Checklist

1. Identify real query patterns via `pg_stat_statements`/slow query log — don't guess.
2. Check `EXPLAIN` — look for `Seq Scan` on large tables.
3. Design order: equality → range → include.
4. Create with `CONCURRENTLY` to avoid locking the production table.
5. Confirm the improvement with `EXPLAIN` before/after.
6. Monitor usage, drop unused indexes after ~30 days.
