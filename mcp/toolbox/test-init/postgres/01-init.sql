-- Sample data + a read-only role, so the bundled postgres_primary_query_data
-- and postgres_primary_list_tables tools have something real to show, and
-- the connection can be tested with genuinely read-only credentials (the
-- real protection layer described in ../README.md's "Why read-only"
-- section).

CREATE TABLE IF NOT EXISTS users (
    id serial PRIMARY KEY,
    email text NOT NULL UNIQUE,
    status text NOT NULL DEFAULT 'active',
    created_at timestamptz NOT NULL DEFAULT now()
);

INSERT INTO users (email, status) VALUES
    ('alice@example.com', 'active'),
    ('bob@example.com', 'active'),
    ('carol@example.com', 'inactive')
ON CONFLICT (email) DO NOTHING;

CREATE ROLE toolbox_ro WITH LOGIN PASSWORD 'toolbox_ro';
GRANT CONNECT ON DATABASE testdb TO toolbox_ro;
GRANT USAGE ON SCHEMA public TO toolbox_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO toolbox_ro;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO toolbox_ro;
