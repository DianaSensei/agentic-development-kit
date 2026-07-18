---
name: database-skill
description: "In-depth database design and server-side optimization knowledge — RDBMS (Oracle, PostgreSQL, MySQL) and NoSQL (document: MongoDB; key-value: DynamoDB/ScyllaDB Alternator; column-based: Cassandra/ScyllaDB CQL). Transaction isolation, concurrency control/locking, indexing/EXPLAIN, query optimization, schema/data-model design, advanced PostgreSQL/MySQL tuning (JSONB, extensions, VACUUM, replication), partition/shard key design, migration. Use when a feature needs schema design/changes or query optimization against a server-based database."
metadata:
  domain: database
  triggers: database design, schema design, query optimization, slow query, EXPLAIN ANALYZE, index design, PostgreSQL, MySQL, Oracle, MongoDB, DynamoDB, Cassandra, ScyllaDB, transaction isolation, concurrency, VACUUM, replication, JSONB, partition key, shard key, wide-column, document database, key-value database
  role: specialist
  scope: design-and-optimization
  output-format: analysis-and-code
  related-skills: java-spring-skill, tauri-react-skill, testcontainers-skill, code-review-skill
---

# Database — RDBMS vs. NoSQL (Document / Key-Value / Column-based)

This skill covers two server-side data-management families with fundamentally different design philosophies:

- **RDBMS** (Oracle/PostgreSQL/MySQL): fixed schema, relational normalization, flexible ad-hoc querying via SQL/JOIN.
- **NoSQL**, split by data model — each model has its own trade-offs and design approach; they are NOT interchangeable in mindset:
  - **Document** (MongoDB): flexible schema, still retains relatively flexible querying/aggregation.
  - **Key-Value** (DynamoDB, ScyllaDB via Alternator): extremely fast, scales horizontally well, in exchange for having to know the access pattern before designing.
  - **Column-based/Wide-column** (Cassandra, ScyllaDB via CQL): similar philosophy to key-value (access-pattern-first) but a different data model (partition + clustering key, CQL).

## Discover

Confirm which DB is in use via the concrete dependency/driver/SDK (Oracle JDBC, `postgresql`, `mysql-connector-j`, `spring-data-mongodb`, the AWS SDK `DynamoDbClient`, `cassandra-driver`/`gocql`). If it's ScyllaDB, confirm clearly whether the project uses it via **Alternator** (the DynamoDB SDK, key-value PK/SK data model — see `references/dynamodb.md`) or via **CQL** (`cassandra-driver`, column-based partition/clustering-key data model — see `references/cassandra.md`), since the two usage modes have completely different data models despite both running on ScyllaDB. Read the existing schema/entity/table/collection definitions and the migration tool in use (Flyway/Liquibase for RDBMS). Do NOT assume which family is in use without confirming — RDBMS/document/key-value/column-based have fundamentally different data models (RDBMS/MongoDB still allow flexible querying; DynamoDB/Cassandra/ScyllaDB have no JOIN and are designed around access patterns rather than normalization).

## Reference Guide

Load detail based on the context currently being worked on:

| Family | Topic | Reference | Load When |
|--------|-------|-----------|-----------|
| RDBMS | EXPLAIN & Indexing | `references/explain-and-indexing.md` | Slow query, index design, reading an execution plan |
| RDBMS | Query Patterns | `references/query-patterns.md` | Rewriting a slow query, CTEs, window functions, pagination |
| RDBMS | Schema Design | `references/schema-design.md` | Designing a new table, normalization, constraints, porting between dialects |
| RDBMS | Advanced PostgreSQL | `references/postgres-advanced.md` | JSONB, extensions (PostGIS/pgvector/pg_trgm/pgcrypto) |
| RDBMS | PostgreSQL Tuning & Ops | `references/postgres-tuning-and-ops.md` | Memory/planner config, VACUUM, replication, partitioning, backup |
| RDBMS | MySQL Tuning | `references/mysql-tuning.md` | InnoDB buffer pool, slow query log, MySQL partitioning |
| Both | Monitoring | `references/monitoring.md` | Baselines, health checks, alert thresholds |
| NoSQL — Document | MongoDB | `references/mongodb.md` | Embed vs. reference, aggregation pipeline, sharding, transactions |
| NoSQL — Key-Value | DynamoDB + ScyllaDB (Alternator) | `references/dynamodb.md` | Access-pattern design, PK/SK, GSI/LSI, conditional writes |
| NoSQL — Column-based | Cassandra (+ ScyllaDB via CQL) | `references/cassandra.md` | CQL, partition/clustering key, consistency level, LWT |

## Transaction Isolation Level

- Defaults: Postgres = `READ COMMITTED`, Oracle = `READ COMMITTED`, **MySQL (InnoDB) = `REPEATABLE READ`** (different from Postgres/Oracle — easy to mix up). Understand what can happen at the default level: Postgres/Oracle (`READ COMMITTED`) can see non-repeatable reads and phantom reads; MySQL (`REPEATABLE READ`) blocks non-repeatable reads on its own and (via next-key locking) most phantom reads within the same transaction, but uses more gap locking so it's more prone to deadlocks/blocking at its default level than Postgres — worth keeping in mind when porting concurrency logic between these two databases.
- Raise to `REPEATABLE READ`/`SERIALIZABLE` (Postgres/Oracle) only when the business genuinely needs it (keep this to a minimum) (e.g. a check-then-write within one transaction that must not allow data to change mid-way) — the trade-off is reduced throughput from a higher chance of conflict/rollback. For a NEW transaction/method, choose the right isolation level based on the business requirement and state the reasoning briefly. Only ask back when a proposed isolation-level increase affects a transaction/table ALREADY RUNNING in production at scale (risk of reducing throughput for the existing system, not just the new feature).

## Concurrency Control

- **Optimistic locking** (a version column/JPA `@Version`): fits when conflicts are rare, avoids holding locks for long — requires handling `OptimisticLockException` (retry or surface to the user).
- **Pessimistic locking** (`SELECT ... FOR UPDATE`): (keep usage to a minimum) fits when conflicts are frequent and strict sequencing is required — watch for deadlocks if multiple transactions lock in different orders (always lock in a consistent order to avoid deadlock).
- **Atomic conditional UPDATE** (e.g. `UPDATE product SET stock = stock - :qty WHERE id = :id AND stock >= :qty`, checking `updatedRows == 0` to know whether the operation succeeded): the BEST fit for conditional increment/decrement operations (deducting stock, deducting balance, enforcing a quota) — Postgres/MySQL/Oracle lock the row within the UPDATE statement itself, no separate round trip needed to acquire a lock (faster than pessimistic locking), and no app-level retry loop needed (simpler than optimistic locking). This is usually the BEST choice whenever the check condition (`stock >= :qty`) can be expressed directly in the UPDATE's `WHERE` clause — only reach for optimistic/pessimistic locking when the logic is too complex to fit into a single UPDATE statement (e.g. needing to read and validate several dependent conditions before deciding whether to write).
- **NoSQL — same spirit as the atomic conditional UPDATE above, but syntax differs per system**: MongoDB uses `$inc` + a filter condition (multi-document transactions only when truly needed — prefer embedding to avoid needing one); DynamoDB/ScyllaDB (Alternator) use `ConditionExpression` (`TransactWriteItems` when atomicity across multiple items is needed, at roughly double the capacity cost); Cassandra (+ ScyllaDB via CQL) uses a Lightweight Transaction (`IF NOT EXISTS`/`IF ...`, expensive due to Paxos). See `references/mongodb.md`, `references/dynamodb.md`, `references/cassandra.md` for details per system.

## Indexing

- Index columns actually used frequently in `WHERE`/`JOIN`/`ORDER BY` — don't over-index (every index costs write overhead, increasing INSERT/UPDATE time).
- Composite index: column order matters (equality-filter columns first, range columns after).
- Check the query plan (`EXPLAIN ANALYZE` in Postgres, `EXPLAIN` in MySQL, an execution plan in Oracle) before asserting that an index will improve performance — don't guess. For reading EXPLAIN output and index types (covering/partial/GIN/GiST/BRIN), see `references/explain-and-indexing.md`.
- **MongoDB**: single/compound indexing follows the same principles as RDBMS (equality first, range/sort after), plus multikey (an index on an array field)/text/geospatial indexes — see `references/mongodb.md`.
- **DynamoDB/ScyllaDB/Cassandra**: "index" here means the partition key/sort key (DynamoDB, ScyllaDB Alternator) or partition/clustering key (Cassandra, ScyllaDB via CQL) — decided AT TABLE-DESIGN TIME based on the access pattern, not added arbitrarily like an RDBMS index. A `Scan` (DynamoDB) or `ALLOW FILTERING` (CQL) is a sign of a wrong key design, not a problem to patch by adding an index — see `references/dynamodb.md`/`references/cassandra.md`.

## Query Optimization

- Avoid `SELECT *` when only a few columns are needed (reduces I/O, avoids unnecessary locking).
- Pagination: `LIMIT/OFFSET` is simple but slow with a large offset — consider keyset pagination (`WHERE id > last_id`) for large datasets with deep pagination.
- **MongoDB**: place `$match`/`$project` early in the aggregation pipeline to reduce the data processed in later stages and take advantage of indexes — see `references/mongodb.md`.
- Rewrite patterns for slow queries (subquery→JOIN, IN→EXISTS), CTEs, window functions, dialect differences: see `references/query-patterns.md` and `references/schema-design.md`.

## Migration

- Prefer backward-compatible changes: add a nullable column, don't change the type of a column already in direct use (add a new column, migrate the data, then drop the old column in a later pass).
- For large migrations (changing a data type, changing an index on a large table), consider running outside peak hours with a clear rollback plan — always requires user approval before applying to production (real data, hard/impossible to reverse if wrong). A migration for a new table with no real data yet can be written and run normally, no separate approval needed.
- **MongoDB**: schemaless, but old documents missing a new field still need to be handled — a one-time migration script (`updateMany`) or lazy migration at the code layer (a fallback default, written back when the document is naturally updated). See `references/mongodb.md`.
- **DynamoDB/ScyllaDB/Cassandra**: there's no `ALTER TABLE`-style DDL to change structure like an RDBMS — the schema is only fixed at the PK/SK (DynamoDB, ScyllaDB Alternator) or partition/clustering key (Cassandra, ScyllaDB via CQL) level; the remaining attributes are schemaless. "Migration" here actually means (1) changing how the application writes/reads a new attribute, with a code-level default for old items that don't have it yet, or (2) backfilling a new GSI/table when a new access pattern is needed — not an instant DDL operation; it needs a clear backfill plan and always requires user approval once the data is already large.

## Choosing RDBMS vs. NoSQL (Document/Key-Value/Column-based) — for a new, unconstrained decision

The most important decision criterion: **how stable the access pattern already is**. The more flexible/ad-hoc the querying needs to be → the more it leans toward RDBMS/Document. The more precisely the read/write pattern is already known → the more it leans toward Key-Value/Column-based (trading that flexibility for better scale/latency).

- **RDBMS**: data has clear relationships needing joins, needs strong ACID transactions across multiple tables, the schema is relatively stable, but the access pattern can still change (the most flexible ad-hoc querying of the four options).
- **NoSQL — Document (MongoDB)**: semi-structured data with a frequently changing schema, naturally accessed per-document (reading/writing one document is usually enough, joins are rarely needed), needs easier horizontal write scaling than RDBMS but the access pattern is NOT yet stable enough to justify Key-Value/Column-based — still keeps relatively flexible querying/aggregation. See `references/mongodb.md`.
- **NoSQL — Key-Value (DynamoDB, ScyllaDB via Alternator)**: the access pattern is CLEAR and STABLE from the start, and near-unlimited read/write scale with stable single-digit-millisecond latency is required. Trade-off: loses ad-hoc query capability — every new access pattern requires a redesign/backfill. Real DynamoDB when already on AWS and wanting a fully managed service; ScyllaDB via Alternator when wanting DynamoDB's familiar data model/API but needing self-hosted/multi-cloud. See `references/dynamodb.md`.
- **NoSQL — Column-based (Cassandra, ScyllaDB via CQL)**: same access-pattern-first philosophy as Key-Value, but a different data model (partition + clustering key, CQL, denormalized per query). Very high write volume, distributed across multiple datacenters, needs self-hosted infrastructure control. Cassandra when the long-established, traditional CQL ecosystem/tooling is needed (accepting JVM/GC tuning); ScyllaDB via CQL when wanting the same data model with better performance on the same hardware, without JVM tuning. See `references/cassandra.md`.
- This is a foundational architectural decision — for a brand-new project, ALWAYS present the trade-offs and wait for the user's decision (see Boundary), never choose unilaterally.

## Common Real-World Issues

- **Long-running transaction**: holds locks for a long time, blocking other transactions; in Postgres it also blocks `VACUUM` from running when it should, causing gradual table bloat — always keep transactions SHORT, never call slow I/O (an HTTP call, heavy processing) inside a transaction boundary.
- **Silent missing index**: no obvious error when an index is missing — it just gets progressively slower as data grows, easy to miss if performance is only checked while data is still small. Monitor via a slow query log/`EXPLAIN` periodically, not just once at feature launch.
- **Exhausted connection pool**: a transaction not closed correctly (a leaked connection from an exception that doesn't release it, or forgetting to close) drains the pool (HikariCP, etc.) — causing timeouts in a COMPLETELY UNRELATED request, easily mistaken for a bug elsewhere.
- **Unbounded embedded array (MongoDB)**: embedding an array with no clear upper bound (comments, logs, activity) into a document — works fine while data is small, then the document hits the 16MB limit as data grows over time; fixed by switching to a reference pattern, but by then there's real data that needs migrating. See `references/mongodb.md`.
- **Hot partition/shard key (DynamoDB/ScyllaDB/Cassandra/sharded MongoDB)**: choosing a low-cardinality partition/shard key (e.g. `status`, `tenant_id` with only a few values) concentrates all traffic onto one partition/shard/node while the rest sit idle — no obvious error at design time, only surfaces when traffic grows and latency/throttling spikes abnormally on one specific slice of data. Always check cardinality before finalizing the design.
- **Scan/ALLOW FILTERING silently ending up on a hot code path**: the same failure mode as an RDBMS's "silent missing index" but with worse consequences — cost scales linearly with the size of the WHOLE table, not the result set, so it can "work" fine in dev/staging (small data) and only surface as a problem in production.

## Test

Testcontainers with the real matching DB (Oracle/Postgres/MySQL/`mongo`/`amazon/dynamodb-local`/`scylladb/scylla`/`cassandra`) for integration tests — test correct transaction rollback on failure, test concurrency (two transactions/writes modifying the same record concurrently) doesn't cause a lost update. For MongoDB, multi-document transaction tests need a replica set enabled (`--replSet`); for DynamoDB/ScyllaDB/Cassandra, also test the partition/shard key/GSI design itself (a Query returns the correct results without accidentally falling back to Scan/ALLOW FILTERING). For container setup/lifecycle, see `testcontainers-skill`.

## Constraints

### MUST DO

- Measure a baseline (`EXPLAIN ANALYZE`/execution plan) BEFORE optimizing, and re-measure AFTER to confirm a real improvement — never optimize by feel.
- Create indexes with `CONCURRENTLY` (PostgreSQL) to avoid locking the production table.
- Run `ANALYZE`/update statistics after a bulk data change.
- Change one thing at a time when optimizing — changing several things at once makes it impossible to tell which change actually helped.
- Test in staging before applying to production; revert immediately if write performance or replication lag gets worse.

### MUST NOT DO

- Never disable autovacuum (PostgreSQL) or skip periodic VACUUM for a high-churn table.
- Never create a redundant/duplicate index just because it "might be needed" — every index costs write overhead.
- Never use `SELECT *` in a production query.
- Never raise the isolation level or change the locking strategy for a transaction/table ALREADY RUNNING in production without first explaining the risk.

## Boundary

If the project already uses a specific RDBMS/NoSQL system, always use that one — never switch unprompted. If this is a COMPLETELY NEW project with no DB chosen yet — this is a foundational architectural decision affecting the whole system long-term, so present the trade-offs (RDBMS vs. NoSQL Document/Key-Value/Column-based, see above) and wait for the user's decision instead of choosing unilaterally. Never raise the isolation level or change the locking strategy affecting data/transactions ALREADY RUNNING in production without first explaining the risk — but for new code/tables within the task's scope, choose the appropriate concurrency strategy without asking.

For NoSQL Key-Value/Column-based (DynamoDB/ScyllaDB/Cassandra), one additional constraint applies: partition/sort/clustering key and GSI/LSI design MUST be based on an access pattern confirmed with the user (or clearly evidenced in the request) — never guess the pattern and lock in a key design. A wrong key in this family is hard/impossible to fix without recreating the table and backfilling, a much heavier consequence than adding/removing the wrong index in RDBMS/MongoDB. If using ScyllaDB, also never unilaterally choose between Alternator and CQL if the project doesn't already have one established — the two usage modes have entirely different data models (Key-Value vs. Column-based), and switching mid-way essentially requires rewriting the whole data-access layer.

For MongoDB, the embed-vs-reference decision for a NEW document within the task's scope can be made without asking, based on the criteria in `references/mongodb.md`; only stop to ask the user when changing the structure of a document that ALREADY has real data depending on it (switching embed to reference or vice versa) — this requires migrating real data, a risk similar to changing an RDBMS schema.

## Knowledge Reference

**RDBMS**: PostgreSQL 12-18, MySQL/InnoDB, Oracle, ANSI SQL, transaction isolation levels, MVCC, B-tree/GIN/GiST/BRIN indexes, EXPLAIN/EXPLAIN ANALYZE, CTEs, window functions, JSONB, VACUUM/autovacuum, streaming/logical replication, partitioning, Flyway/Liquibase.

**NoSQL — Document**: MongoDB, embed vs. reference, aggregation pipeline, multikey/text/geospatial index, sharding, multi-document transactions.

**NoSQL — Key-Value**: DynamoDB (PK/SK, GSI/LSI, `ConditionExpression`, `TransactWriteItems`, Streams, TTL, DAX), ScyllaDB Alternator.

**NoSQL — Column-based**: Cassandra/CQL (partition key, clustering key, tunable consistency level, Lightweight Transactions, compaction), ScyllaDB (shard-per-core).

**Shared**: Testcontainers, connection pooling (HikariCP/PgBouncer), optimistic/pessimistic locking, atomic conditional update.
