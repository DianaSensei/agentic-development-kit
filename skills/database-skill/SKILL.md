---
name: database-skill
description: "In-depth database design and server-side optimization knowledge - RDBMS (Oracle, PostgreSQL, MySQL) and NoSQL (document: MongoDB; key-value: DynamoDB/ScyllaDB Alternator; column-based: Cassandra/ScyllaDB CQL). Transaction isolation, concurrency control/locking, indexing/EXPLAIN, query optimization, schema/data-model design, advanced PostgreSQL/MySQL tuning (JSONB, extensions, VACUUM, replication), partition/shard key design, migration. Use when a feature needs schema design/changes or query optimization against a server-based database."
metadata:
  domain: database
  triggers: slow query, EXPLAIN ANALYZE, index design, partition key, wide-column, document database, key-value database
  role: specialist
  scope: design-and-optimization
  output-format: analysis-and-code
  related-skills: java-spring-skill, tauri-react-skill, testcontainers-skill, code-review-skill
---

# Database - RDBMS vs. NoSQL (Document / Key-Value / Column-based)

Four data models with genuinely different design mindsets - not interchangeable. RDBMS
(Oracle/PostgreSQL/MySQL) and Document (MongoDB) keep flexible ad-hoc querying; Key-Value (DynamoDB,
ScyllaDB via Alternator) and Column-based (Cassandra, ScyllaDB via CQL) have no JOIN and are designed
around a known access pattern instead of normalization.

**ScyllaDB is two different databases depending on usage mode**: via **Alternator** it's key-value with
the DynamoDB SDK and PK/SK model (`references/dynamodb.md`); via **CQL** it's column-based with
partition/clustering keys (`references/cassandra.md`). Never treat them as one.

## Discover

Confirm the DB from the concrete dependency/driver/SDK (Oracle JDBC, `postgresql`,
`mysql-connector-j`, `spring-data-mongodb`, AWS SDK `DynamoDbClient`, `cassandra-driver`/`gocql`) - never
assume the family. For ScyllaDB, establish which of the two usage modes above the project uses. Then read
the existing schema/entity/collection definitions and the migration tool in play (Flyway/Liquibase).

## Reference Guide

| Family | Topic | Reference | Load When |
|--------|-------|-----------|-----------|
| RDBMS | EXPLAIN & Indexing | `references/explain-and-indexing.md` | Slow query, index design, reading an execution plan |
| RDBMS | Query Patterns | `references/query-patterns.md` | Rewriting a slow query, CTEs, window functions, pagination |
| RDBMS | Schema Design | `references/schema-design.md` | Designing a new table, normalization, constraints, porting between dialects |
| RDBMS | Advanced PostgreSQL | `references/postgres-advanced.md` | JSONB, extensions (PostGIS/pgvector/pg_trgm/pgcrypto) |
| RDBMS | PostgreSQL Tuning & Ops | `references/postgres-tuning-and-ops.md` | Memory/planner config, VACUUM, replication, partitioning, backup |
| RDBMS | MySQL Tuning | `references/mysql-tuning.md` | InnoDB buffer pool, slow query log, MySQL partitioning |
| Both | Monitoring | `references/monitoring.md` | Baselines, health checks, alert thresholds |
| NoSQL - Document | MongoDB | `references/mongodb.md` | Embed vs. reference, aggregation pipeline, sharding, transactions |
| NoSQL - Key-Value | DynamoDB + ScyllaDB (Alternator) | `references/dynamodb.md` | Access-pattern design, PK/SK, GSI/LSI, conditional writes |
| NoSQL - Column-based | Cassandra (+ ScyllaDB via CQL) | `references/cassandra.md` | CQL, partition/clustering key, consistency level, LWT |

## Transaction Isolation

Defaults differ in a way that's easy to mix up: Postgres and Oracle are `READ COMMITTED`, **MySQL/InnoDB
is `REPEATABLE READ`**. So Postgres/Oracle can see non-repeatable and phantom reads by default, while
MySQL blocks non-repeatable reads and (via next-key locking) most phantoms - at the cost of more gap
locking, making it more deadlock-prone than Postgres at its own default. Worth remembering when porting
concurrency logic between the two.

Raise to `REPEATABLE READ`/`SERIALIZABLE` sparingly, only for a real business need (e.g. a check-then-write
that must not see data change mid-transaction); the cost is throughput lost to conflicts/rollbacks. For a
NEW transaction, pick the level from the requirement and state the reasoning briefly - no need to ask. Ask
only when raising the level on a transaction/table already running in production at scale.

## Concurrency Control

- **Atomic conditional UPDATE** - `UPDATE product SET stock = stock - :qty WHERE id = :id AND stock >= :qty`,
  then check `updatedRows == 0` for success. **Usually the best choice** for conditional
  increment/decrement (stock, balance, quota): the row is locked inside the statement itself - no extra
  round trip (faster than pessimistic), no app-level retry loop (simpler than optimistic). Use it whenever
  the check fits into the `WHERE` clause.
- **Optimistic locking** (version column / JPA `@Version`) - conflicts are rare, holds no long locks;
  requires handling `OptimisticLockException` (retry or surface it).
- **Pessimistic locking** (`SELECT ... FOR UPDATE`) - keep to a minimum; for frequent conflicts needing
  strict sequencing. Always lock in a consistent order across transactions or you get deadlocks.

Reach for optimistic/pessimistic only when the logic is too complex for one UPDATE (several dependent
conditions to read and validate before deciding to write).

**NoSQL equivalents of the atomic conditional UPDATE**: MongoDB `$inc` + filter condition (multi-document
transactions only when truly needed - prefer embedding to avoid them); DynamoDB/Alternator
`ConditionExpression` (`TransactWriteItems` for cross-item atomicity, ~2× capacity cost); Cassandra/CQL
Lightweight Transactions (`IF NOT EXISTS`/`IF ...`, expensive - Paxos).

## Indexing

- Index columns actually used in `WHERE`/`JOIN`/`ORDER BY`, and no more - every index taxes every
  INSERT/UPDATE.
- Composite index column order matters: equality filters first, range columns after.
- Check the plan (`EXPLAIN ANALYZE` Postgres, `EXPLAIN` MySQL, execution plan Oracle) before claiming an
  index helps - never guess. Covering/partial/GIN/GiST/BRIN: `references/explain-and-indexing.md`.
- **MongoDB**: same principles, plus multikey (array field)/text/geospatial.
- **DynamoDB/ScyllaDB/Cassandra**: "index" means the partition/sort (or partition/clustering) key,
  decided **at table-design time** from the access pattern - not added later like an RDBMS index. A `Scan`
  or `ALLOW FILTERING` means the key design is wrong; it is not a gap to patch with another index.

## Query Optimization

- Avoid `SELECT *` when a few columns will do - less I/O, less unnecessary locking.
- Pagination: `LIMIT/OFFSET` degrades badly at large offsets - use keyset pagination
  (`WHERE id > last_id`) for deep pagination over large datasets.
- **MongoDB**: `$match`/`$project` early in the aggregation pipeline, to shrink later stages and let
  indexes apply.
- Rewrites (subquery→JOIN, IN→EXISTS), CTEs, window functions, dialect differences:
  `references/query-patterns.md`, `references/schema-design.md`.

## Migration

- Prefer backward-compatible steps: add a nullable column; never change the type of a column already in
  use - add a new one, migrate the data, drop the old one in a later pass.
- Large migrations (type change, index change on a big table) run outside peak hours with a rollback plan,
  and **always need user approval before production** - real data, hard or impossible to reverse. A new
  table with no real data yet needs no separate approval.
- **MongoDB**: schemaless, but documents predating a new field still need handling - a one-time
  `updateMany`, or lazy migration in code (fallback default, written back on the next natural update).
- **DynamoDB/ScyllaDB/Cassandra**: no `ALTER TABLE`. Only the key is fixed; other attributes are
  schemaless. "Migration" means either changing how the app reads/writes an attribute (with a code-level
  default for older items) or backfilling a new GSI/table for a new access pattern - never instant, needs
  a backfill plan, and needs user approval once data is large.

## Choosing a Family (new, unconstrained decision)

The deciding criterion is **how stable the access pattern already is**. More ad-hoc querying needed →
RDBMS/Document. Pattern already precisely known → Key-Value/Column-based, trading flexibility for
scale and latency.

- **RDBMS** - clear relationships needing joins, strong ACID across tables, relatively stable schema, but
  the access pattern may still change. The most flexible querying of the four.
- **Document (MongoDB)** - semi-structured, frequently changing schema, naturally accessed per-document
  (joins rare), wants easier horizontal write scaling than RDBMS, but the access pattern isn't stable
  enough yet to justify key-value/column-based. Keeps flexible querying/aggregation.
- **Key-Value (DynamoDB, ScyllaDB Alternator)** - access pattern clear and stable from the start,
  near-unlimited scale at stable single-digit-ms latency required. Trade-off: no ad-hoc querying - each
  new access pattern means redesign/backfill. DynamoDB if already on AWS and wanting fully managed;
  Alternator for that same model self-hosted or multi-cloud.
- **Column-based (Cassandra, ScyllaDB CQL)** - same access-pattern-first philosophy, different model
  (partition + clustering key, denormalized per query). Very high write volume, multi-datacenter,
  self-hosted control. Cassandra for the mature CQL ecosystem (accepting JVM/GC tuning); ScyllaDB CQL for
  the same model with better performance per unit of hardware and no JVM tuning.

## Common Real-World Issues

- **Long-running transaction** - holds locks and blocks others; in Postgres it also stalls `VACUUM`,
  bloating tables gradually. Keep transactions SHORT; never do slow I/O (HTTP call, heavy processing)
  inside one.
- **Silent missing index** - no error, just gradual slowdown as data grows; invisible if performance was
  only checked while data was small. Watch the slow query log/`EXPLAIN` periodically, not once at launch.
- **Exhausted connection pool** - one leaked connection (an exception path that never releases) drains
  the pool and causes timeouts in a completely unrelated request, easily blamed on the wrong code.
- **Unbounded embedded array (MongoDB)** - embedding comments/logs/activity with no upper bound works
  until the document hits 16MB; the fix (switch to references) then requires migrating real data.
- **Hot partition/shard key** - a low-cardinality key (`status`, a `tenant_id` with few values)
  concentrates all traffic on one partition while the rest idle. No error at design time; surfaces as
  latency/throttling spikes on one slice once traffic grows. Check cardinality before finalizing.
- **Scan/ALLOW FILTERING on a hot path** - the "silent missing index" failure mode, but worse: cost scales
  with the whole table, not the result set, so it looks fine on dev/staging data and only bites in prod.

## Test

Testcontainers with the real matching DB
(Oracle/Postgres/MySQL/`mongo`/`amazon/dynamodb-local`/`scylladb/scylla`/`cassandra`): test that a failure
rolls the transaction back, and that two concurrent writers to one record don't produce a lost update.
MongoDB multi-document transaction tests need a replica set (`--replSet`). For
DynamoDB/ScyllaDB/Cassandra, test the key design itself - a Query returns the right rows without silently
falling back to Scan/ALLOW FILTERING. Container setup/lifecycle → `testcontainers-skill`.

## Constraints

- Measure a baseline (`EXPLAIN ANALYZE`/execution plan) BEFORE optimizing and re-measure AFTER - never
  optimize by feel, and change one thing at a time or you can't tell what helped.
- Build indexes `CONCURRENTLY` (PostgreSQL) so production tables aren't locked; run `ANALYZE` after a
  bulk data change.
- Test in staging first; revert immediately if write performance or replication lag degrades.
- Never disable autovacuum or skip VACUUM on a high-churn table.
- Never add a redundant index "in case it's needed."

## Boundary

Already has a DB → use it, never switch unprompted. Brand-new project with none chosen → present the
trade-offs above and wait for the user's decision; this is a foundational architectural call, never made
unilaterally.

Never raise an isolation level or change a locking strategy affecting **data already running in
production** without explaining the risk first. For new code/tables inside the task's scope, choose the
concurrency strategy without asking.

**Key-Value/Column-based**: partition/sort/clustering key and GSI/LSI design must come from an access
pattern the user confirmed (or the request clearly evidences) - never guess and lock one in. A wrong key
here can only be fixed by recreating the table and backfilling, far heavier than a wrong RDBMS index.
Never pick Alternator vs. CQL unilaterally when the project has neither established - switching later
means rewriting the whole data-access layer.

**MongoDB**: decide embed-vs-reference for a NEW document yourself using `references/mongodb.md`'s
criteria. Ask only when restructuring a document that already has real data depending on it - that means
migrating real data, comparable in risk to an RDBMS schema change.
