# PostgreSQL Advanced — JSONB & Extensions

## JSONB — luôn dùng JSONB thay vì JSON (binary, indexable, nhanh hơn); chỉ dùng `json` khi cần giữ nguyên format/whitespace gốc

### Operators

```sql
-- Retrieval: -> trả JSONB, ->> trả text
SELECT data -> 'user' ->> 'name' FROM documents;        -- text
SELECT data #> '{user,address,city}' FROM documents;     -- nested path, JSONB
SELECT data #>> '{user,address,city}' FROM documents;    -- nested path, text

-- Containment (dùng được với GIN index — hiệu năng tốt nhất)
SELECT * FROM documents WHERE data @> '{"status": "active"}';
SELECT * FROM documents WHERE data ? 'email';             -- key tồn tại
SELECT * FROM documents WHERE data ?& ARRAY['email', 'phone']; -- tất cả key tồn tại

-- Modification
UPDATE documents SET data = data || '{"updated_at": "2024-01-01"}'::jsonb;  -- merge nông
UPDATE documents SET data = jsonb_set(data, '{user,email}', '"new@example.com"'::jsonb); -- update sâu
```

### Indexing JSONB — chọn đúng loại theo pattern truy vấn

```sql
-- GIN mặc định: hỗ trợ @>, ?, ?&, ?|
CREATE INDEX idx_documents_data ON documents USING GIN(data);

-- GIN + jsonb_path_ops: nhỏ hơn ~20%, nhanh hơn CHO RIÊNG @> — không hỗ trợ ?
CREATE INDEX idx_documents_path_ops ON documents USING GIN(data jsonb_path_ops);

-- B-tree trên giá trị extract: khi chỉ cần query 1 path cụ thể thường xuyên (nhanh nhất cho equality/range)
CREATE INDEX idx_documents_status_btree ON documents((data ->> 'status'));

-- Generated column + B-tree: khi path được query CỰC kỳ thường xuyên, đáng tách hẳn ra cột riêng
ALTER TABLE documents ADD COLUMN status TEXT GENERATED ALWAYS AS (data ->> 'status') STORED;
CREATE INDEX idx_docs_status_col ON documents(status);
```

### DO / DON'T

```sql
-- DO: dùng @> cho query có index GIN hỗ trợ
WHERE data @> '{"status": "active"}'

-- DON'T: trộn ->> (text) với so sánh kiểu khác — không dùng được index đúng cách
WHERE data @> '{"score": "100"}'              -- sai, "100" là string trong khi score là number
WHERE CAST(data ->> 'score' AS INTEGER) = 100  -- đúng

-- DON'T: JSONB cho mảng cực lớn (10k+ phần tử) — tách bảng riêng thay vì nhồi vào 1 document
-- DON'T: JSONB cho field bị UPDATE thường xuyên — tách cột riêng, JSONB tối ưu cho đọc nhiều/ghi ít hơn
```

## Extension quan trọng — cài khi thực sự cần, không cài "phòng khi"

| Extension | Dùng khi | Ví dụ |
|-----------|----------|-------|
| `pg_stat_statements` | Luôn nên có — theo dõi query chậm | `SELECT query, mean_exec_time FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 20;` |
| `uuid-ossp` / `pgcrypto` (`gen_random_uuid()`) | Cần UUID làm PK | `id UUID PRIMARY KEY DEFAULT gen_random_uuid()` |
| `pg_trgm` | Fuzzy search, tối ưu `LIKE '%x%'` | `CREATE INDEX ... USING GIN(email gin_trgm_ops);` |
| `postgis` | Dữ liệu địa lý/không gian | `ST_Distance`, `ST_DWithin`, `ST_Contains` |
| `pgvector` | Vector similarity search (semantic search, RAG) | `embedding vector(1536)`, index `hnsw`/`ivfflat` |
| `pgcrypto` | Hash password, encrypt field nhạy cảm | `crypt('pw', gen_salt('bf', 10))` |
| `postgres_fdw` | Query xuyên database Postgres khác | `CREATE FOREIGN TABLE ...` |
| `pg_repack` | Reclaim bloat không khóa bảng (thay `VACUUM FULL`) | chạy qua CLI, không phải SQL |

### pgcrypto — hash password đúng cách (bcrypt, KHÔNG tự viết hash)

```sql
INSERT INTO users (email, password_hash) VALUES ('user@example.com', crypt('password123', gen_salt('bf', 10)));
SELECT * FROM users WHERE email = 'user@example.com' AND password_hash = crypt('password123', password_hash);
```

### pgvector — vector similarity

```sql
CREATE TABLE embeddings (id SERIAL PRIMARY KEY, content TEXT, embedding vector(1536));
CREATE INDEX ON embeddings USING hnsw (embedding vector_cosine_ops);  -- hnsw: recall tốt hơn ivfflat, tốn RAM hơn

SELECT content, 1 - (embedding <=> :query_vector) AS similarity
FROM embeddings ORDER BY embedding <=> :query_vector LIMIT 10;
```

### PostGIS — cơ bản

```sql
CREATE TABLE locations (id SERIAL PRIMARY KEY, geom GEOMETRY(Point, 4326));
CREATE INDEX idx_locations_geom ON locations USING GIST(geom);

SELECT name FROM locations
WHERE ST_DWithin(geom::geography, ST_SetSRID(ST_MakePoint(-74.0060, 40.7128), 4326)::geography, 1000); -- trong bán kính 1km
```
