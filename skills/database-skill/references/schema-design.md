# Schema Design — Normalization, Constraints, Dialect Differences

## Normalization — áp dụng tới 3NF, denormalize có chủ đích sau đó

```sql
-- 1NF: giá trị nguyên tử, không nhét nhiều giá trị vào 1 cột
-- Sai: phones VARCHAR "555-1234,555-5678"  →  Đúng: bảng con customer_phones riêng

-- 2NF: cột không-khóa phải phụ thuộc TOÀN BỘ khóa, không phụ thuộc 1 phần khóa composite
-- Sai: order_items(order_id, product_id, product_name, product_price, quantity)
--      product_name/product_price chỉ phụ thuộc product_id, không phụ thuộc cả (order_id, product_id)
-- Đúng: tách product_name/price sang bảng products, order_items chỉ giữ unit_price (snapshot tại thời điểm order)

-- 3NF: không có phụ thuộc bắc cầu (cột A phụ thuộc cột B, B lại phụ thuộc khóa chính)
-- Sai: addresses(zip_code, city, state) — city/state phụ thuộc zip_code chứ không phụ thuộc address_id
-- Đúng: tách bảng zip_codes(zip_code PK, city, state), addresses chỉ giữ FK zip_code
```

Normalize tới 3NF là baseline hợp lý cho OLTP; denormalize có chủ đích (VD lưu snapshot `unit_price` trong `order_items` thay vì luôn join `products`) chỉ khi có lý do cụ thể (tránh giá trị lịch sử bị đổi theo giá hiện tại, hoặc đo được hiệu năng cần).

## Khóa & Constraint

```sql
-- Surrogate key (auto-increment/UUID) tách biệt khỏi natural key (business meaning)
CREATE TABLE customers (
    customer_id SERIAL PRIMARY KEY,        -- surrogate
    email VARCHAR(255) NOT NULL UNIQUE,    -- natural candidate key
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- FK với cascading action — chọn đúng hành vi theo ngữ nghĩa nghiệp vụ
FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE;   -- xóa order thì xóa luôn item con
FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE RESTRICT; -- chặn xóa product nếu đang có order dùng

-- CHECK constraint — enforce rule ở tầng DB, không chỉ ở tầng app
CONSTRAINT chk_salary_positive CHECK (salary > 0),
CONSTRAINT chk_hire_not_future CHECK (hire_date <= CURRENT_DATE)

-- Composite UNIQUE
CONSTRAINT uq_user_preference UNIQUE (user_id, preference_key)

-- Exclusion constraint (PostgreSQL) — chặn overlap, VD không cho 2 booking cùng phòng trùng giờ
EXCLUDE USING GIST (room_id WITH =, booked_during WITH &&)
```

Luôn index cột FK — không tự động có index chỉ vì là FK (khác PK), thiếu index FK là nguyên nhân phổ biến nhất khiến JOIN chậm trên bảng lớn.

## Pattern thiết kế thường dùng

```sql
-- Soft delete — giữ lịch sử, filter qua WHERE deleted_at IS NULL
ALTER TABLE posts ADD COLUMN deleted_at TIMESTAMP;
CREATE INDEX idx_posts_active ON posts(created_at DESC) WHERE deleted_at IS NULL;

-- Many-to-many với attribute — bảng junction có thêm cột riêng (không chỉ 2 FK)
CREATE TABLE enrollments (
    student_id INT REFERENCES students(student_id),
    course_id INT REFERENCES courses(course_id),
    grade CHAR(2), status VARCHAR(20) DEFAULT 'active',
    UNIQUE (student_id, course_id)
);

-- Self-referencing hierarchy (adjacency list — đơn giản, đủ cho hầu hết use case; xem CTE đệ quy ở query-patterns.md để truy vấn)
CREATE TABLE categories (
    category_id SERIAL PRIMARY KEY,
    parent_category_id INT REFERENCES categories(category_id)
);

-- Audit trail — trigger tự ghi old/new value mỗi lần INSERT/UPDATE/DELETE
CREATE TABLE audit_log (
    table_name VARCHAR(100), record_id BIGINT, action VARCHAR(10),
    old_values JSONB, new_values JSONB, changed_by INT, changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

Tránh polymorphic association (`commentable_type` + `commentable_id` thay vì FK thật) trừ khi thực sự cần — không enforce được referential integrity ở tầng DB, dễ sinh dữ liệu rác (record trỏ tới entity không tồn tại) mà DB không báo lỗi.

## Dialect Differences — khi cần port giữa các RDBMS

| Concept | PostgreSQL | MySQL | SQL Server | Oracle |
|---------|-----------|-------|-------------|--------|
| Auto-increment | `SERIAL`/`GENERATED ALWAYS AS IDENTITY` | `AUTO_INCREMENT` | `IDENTITY(1,1)` | `GENERATED ALWAYS AS IDENTITY` |
| Nối chuỗi | `\|\|` hoặc `CONCAT()` | `CONCAT()` (`+` gây lỗi) | `+` hoặc `CONCAT()` | `\|\|` |
| Ngày hiện tại | `NOW()`/`CURRENT_DATE` | `NOW()`/`CURDATE()` | `GETDATE()` | `SYSDATE` |
| Pagination | `LIMIT n OFFSET m` | `LIMIT n OFFSET m` | `OFFSET m ROWS FETCH NEXT n ROWS ONLY` | `OFFSET m ROWS FETCH NEXT n ROWS ONLY` (12c+) |
| Boolean | `BOOLEAN` (native) | `TINYINT(1)` | `BIT` | `NUMBER(1)` (không có boolean thật) |
| UPSERT | `ON CONFLICT ... DO UPDATE` | `ON DUPLICATE KEY UPDATE` | `MERGE` | `MERGE` |
| So sánh chuỗi | Case-sensitive mặc định | Case-insensitive mặc định (collation `_ci`) | Tùy collation | Case-sensitive mặc định |
| JSON | `JSONB` (indexable, binary) | `JSON` (8.0+) | `NVARCHAR(MAX)` + `ISJSON()` | `CLOB` + `IS JSON` |

Sai lệch dễ gây bug nhất khi port: **case-sensitivity so sánh chuỗi** (MySQL mặc định case-insensitive, Postgres/Oracle case-sensitive — code chạy đúng ở MySQL có thể fail ở Postgres nếu không `LOWER()`/`ILIKE` tường minh) và **NULL handling trong `NOT IN`** (xem `query-patterns.md` — dùng `NOT EXISTS` thay vì `NOT IN` để tránh vấn đề này ở mọi dialect).

## Checklist thiết kế schema

1. Chọn kiểu dữ liệu nhỏ nhất phù hợp (INT vs BIGINT, VARCHAR(n) vs TEXT).
2. Index mọi cột FK.
3. `NOT NULL` + default rõ ràng, tránh NULL khi có thể tránh được.
4. Enforce integrity bằng constraint ở DB, không chỉ validate ở app.
5. Normalize tới 3NF trước, denormalize có chủ đích sau nếu có bằng chứng cần.
6. Migration có version control (Flyway/Liquibase) — xem SKILL.md chính.
