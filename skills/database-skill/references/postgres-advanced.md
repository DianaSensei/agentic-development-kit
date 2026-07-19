# PostgreSQL Advanced — JSONB & Extensions

## JSONB — always use JSONB instead of JSON (binary, indexable, faster); only use `json` when you need to preserve the original format/whitespace

### Operators

```sql
-- Retrieval: -> returns JSONB, ->> returns text
SELECT data -> 'user' ->> 'name' FROM documents;        -- text
SELECT data #> '{user,address,city}' FROM documents;     -- nested path, JSONB
SELECT data #>> '{user,address,city}' FROM documents;    -- nested path, text

-- Containment (works with GIN index — best performance)
SELECT * FROM documents WHERE data @> '{"status": "active"}';
SELECT * FROM documents WHERE data ? 'email';             -- key exists
SELECT * FROM documents WHERE data ?& ARRAY['email', 'phone']; -- all keys exist

-- Modification
UPDATE documents SET data = data || '{"updated_at": "2024-01-01"}'::jsonb;  -- shallow merge
UPDATE documents SET data = jsonb_set(data, '{user,email}', '"new@example.com"'::jsonb); -- deep update
```

### Indexing JSONB — choose the right type based on query pattern

```sql
-- Default GIN: supports @>, ?, ?&, ?|
CREATE INDEX idx_documents_data ON documents USING GIN(data);

-- GIN + jsonb_path_ops: ~20% smaller, faster SPECIFICALLY FOR @> — does not support ?
CREATE INDEX idx_documents_path_ops ON documents USING GIN(data jsonb_path_ops);

-- B-tree on an extracted value: when you only ever need to query 1 specific path frequently (fastest for equality/range)
CREATE INDEX idx_documents_status_btree ON documents((data ->> 'status'));

-- Generated column + B-tree: when a path is queried EXTREMELY frequently, it's worth pulling it out into its own column
ALTER TABLE documents ADD COLUMN status TEXT GENERATED ALWAYS AS (data ->> 'status') STORED;
CREATE INDEX idx_docs_status_col ON documents(status);
```

### DO / DON'T

```sql
-- DO: use @> for queries a GIN index can support
WHERE data @> '{"status": "active"}'

-- DON'T: mix ->> (text) with a different-typed comparison — the index can't be used correctly
WHERE data @> '{"score": "100"}'              -- wrong, "100" is a string while score is a number
WHERE CAST(data ->> 'score' AS INTEGER) = 100  -- correct

-- DON'T: JSONB for very large arrays (10k+ elements) — split into a separate table instead of cramming into 1 document
-- DON'T: JSONB for fields that get UPDATEd frequently — split into a separate column, JSONB is optimized for read-heavy/write-light
```

## Important extensions — install only when actually needed, not "just in case"

| Extension | Use when | Example |
|-----------|----------|-------|
| `pg_stat_statements` | Should almost always be on — tracks slow queries | `SELECT query, mean_exec_time FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 20;` |
| `uuid-ossp` / `pgcrypto` (`gen_random_uuid()`) | Need a UUID as PK | `id UUID PRIMARY KEY DEFAULT gen_random_uuid()` |
| `pg_trgm` | Fuzzy search, optimizing `LIKE '%x%'` | `CREATE INDEX ... USING GIN(email gin_trgm_ops);` |
| `postgis` | Geographic/spatial data | `ST_Distance`, `ST_DWithin`, `ST_Contains` |
| `pgvector` | Vector similarity search (semantic search, RAG) | `embedding vector(1536)`, index `hnsw`/`ivfflat` |
| `pgcrypto` | Password hashing, encrypting sensitive fields | `crypt('pw', gen_salt('bf', 10))` |
| `postgres_fdw` | Query across another Postgres database | `CREATE FOREIGN TABLE ...` |
| `pg_repack` | Reclaim bloat without locking the table (replaces `VACUUM FULL`) | run via CLI, not SQL |

### pgcrypto — hashing passwords correctly (bcrypt, do NOT write your own hash)

```sql
INSERT INTO users (email, password_hash) VALUES ('user@example.com', crypt('password123', gen_salt('bf', 10)));
SELECT * FROM users WHERE email = 'user@example.com' AND password_hash = crypt('password123', password_hash);
```

### pgvector — vector similarity

```sql
CREATE TABLE embeddings (id SERIAL PRIMARY KEY, content TEXT, embedding vector(1536));
CREATE INDEX ON embeddings USING hnsw (embedding vector_cosine_ops);  -- hnsw: better recall than ivfflat, uses more RAM

SELECT content, 1 - (embedding <=> :query_vector) AS similarity
FROM embeddings ORDER BY embedding <=> :query_vector LIMIT 10;
```

### PostGIS — basics

```sql
CREATE TABLE locations (id SERIAL PRIMARY KEY, geom GEOMETRY(Point, 4326));
CREATE INDEX idx_locations_geom ON locations USING GIST(geom);

SELECT name FROM locations
WHERE ST_DWithin(geom::geography, ST_SetSRID(ST_MakePoint(-74.0060, 40.7128), 4326)::geography, 1000); -- within a 1km radius
```
