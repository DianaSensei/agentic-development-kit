# Schema Design - Normalization, Constraints, Dialect Differences

## Normalization - apply up to 3NF, denormalize deliberately afterward

```sql
-- 1NF: atomic values, don't cram multiple values into 1 column
-- Wrong: phones VARCHAR "555-1234,555-5678"  →  Right: a separate customer_phones child table

-- 2NF: non-key columns must depend on the ENTIRE key, not on part of a composite key
-- Wrong: order_items(order_id, product_id, product_name, product_price, quantity)
--        product_name/product_price only depend on product_id, not on the full (order_id, product_id)
-- Right: move product_name/price to a products table, order_items only keeps unit_price (a snapshot at order time)

-- 3NF: no transitive dependencies (column A depends on column B, and B depends on the primary key)
-- Wrong: addresses(zip_code, city, state) - city/state depend on zip_code, not on address_id
-- Right: split into a zip_codes(zip_code PK, city, state) table, addresses just keeps the zip_code FK
```

Normalizing to 3NF is a reasonable baseline for OLTP; deliberate denormalization (e.g. storing a snapshot
`unit_price` in `order_items` instead of always joining `products`) should only happen for a specific
reason (avoiding historical values changing along with current prices, or a measured performance need).

## Keys & Constraints

```sql
-- Surrogate key (auto-increment/UUID) kept separate from the natural key (business meaning)
CREATE TABLE customers (
    customer_id SERIAL PRIMARY KEY,        -- surrogate
    email VARCHAR(255) NOT NULL UNIQUE,    -- natural candidate key
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- FK with a cascading action - choose the right behavior based on business semantics
FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE;   -- deleting an order deletes its line items too
FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE RESTRICT; -- block deleting a product if orders still reference it

-- CHECK constraint - enforce the rule at the DB level, not just the app layer
CONSTRAINT chk_salary_positive CHECK (salary > 0),
CONSTRAINT chk_hire_not_future CHECK (hire_date <= CURRENT_DATE)

-- Composite UNIQUE
CONSTRAINT uq_user_preference UNIQUE (user_id, preference_key)

-- Exclusion constraint (PostgreSQL) - prevents overlap, e.g. no 2 bookings for the same room at overlapping times
EXCLUDE USING GIST (room_id WITH =, booked_during WITH &&)
```

Always index FK columns - an FK column is not automatically indexed the way a PK is; a missing FK index is
the single most common cause of slow JOINs on large tables.

## Common Design Patterns

```sql
-- Soft delete - preserves history, filter via WHERE deleted_at IS NULL
ALTER TABLE posts ADD COLUMN deleted_at TIMESTAMP;
CREATE INDEX idx_posts_active ON posts(created_at DESC) WHERE deleted_at IS NULL;

-- Many-to-many with attributes - the junction table has extra columns of its own (not just the 2 FKs)
CREATE TABLE enrollments (
    student_id INT REFERENCES students(student_id),
    course_id INT REFERENCES courses(course_id),
    grade CHAR(2), status VARCHAR(20) DEFAULT 'active',
    UNIQUE (student_id, course_id)
);

-- Self-referencing hierarchy (adjacency list - simple, sufficient for most use cases; see the recursive CTE in query-patterns.md for querying it)
CREATE TABLE categories (
    category_id SERIAL PRIMARY KEY,
    parent_category_id INT REFERENCES categories(category_id)
);

-- Audit trail - a trigger automatically records old/new values on every INSERT/UPDATE/DELETE
CREATE TABLE audit_log (
    table_name VARCHAR(100), record_id BIGINT, action VARCHAR(10),
    old_values JSONB, new_values JSONB, changed_by INT, changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

Avoid polymorphic associations (`commentable_type` + `commentable_id` instead of a real FK) unless truly
necessary - referential integrity can't be enforced at the DB level, which makes it easy to end up with
orphaned data (records pointing at entities that don't exist) without the DB raising an error.

## Dialect Differences - when porting between RDBMS engines

| Concept | PostgreSQL | MySQL | SQL Server | Oracle |
|---------|-----------|-------|-------------|--------|
| Auto-increment | `SERIAL`/`GENERATED ALWAYS AS IDENTITY` | `AUTO_INCREMENT` | `IDENTITY(1,1)` | `GENERATED ALWAYS AS IDENTITY` |
| String concatenation | `\|\|` or `CONCAT()` | `CONCAT()` (`+` causes an error) | `+` or `CONCAT()` | `\|\|` |
| Current date | `NOW()`/`CURRENT_DATE` | `NOW()`/`CURDATE()` | `GETDATE()` | `SYSDATE` |
| Pagination | `LIMIT n OFFSET m` | `LIMIT n OFFSET m` | `OFFSET m ROWS FETCH NEXT n ROWS ONLY` | `OFFSET m ROWS FETCH NEXT n ROWS ONLY` (12c+) |
| Boolean | `BOOLEAN` (native) | `TINYINT(1)` | `BIT` | `NUMBER(1)` (no true boolean type) |
| UPSERT | `ON CONFLICT ... DO UPDATE` | `ON DUPLICATE KEY UPDATE` | `MERGE` | `MERGE` |
| String comparison | Case-sensitive by default | Case-insensitive by default (`_ci` collation) | Depends on collation | Case-sensitive by default |
| JSON | `JSONB` (indexable, binary) | `JSON` (8.0+) | `NVARCHAR(MAX)` + `ISJSON()` | `CLOB` + `IS JSON` |

The most bug-prone mismatch when porting: **string comparison case-sensitivity** (MySQL defaults to
case-insensitive, Postgres/Oracle are case-sensitive - code that works correctly on MySQL can fail on
Postgres without explicit `LOWER()`/`ILIKE`) and **NULL handling in `NOT IN`** (see `query-patterns.md` -
use `NOT EXISTS` instead of `NOT IN` to avoid this issue across every dialect).

## Schema Design Checklist

1. Choose the smallest appropriate data type (INT vs BIGINT, VARCHAR(n) vs TEXT).
2. Index every FK column.
3. Use `NOT NULL` + an explicit default, avoid NULL where avoidable.
4. Enforce integrity with DB constraints, not just app-layer validation.
5. Normalize to 3NF first, denormalize deliberately later only with evidence it's needed.
6. Use version-controlled migrations (Flyway/Liquibase) - see the main SKILL.md.
