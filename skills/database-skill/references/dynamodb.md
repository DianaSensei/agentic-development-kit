# DynamoDB (+ ScyllaDB Alternator) - Key-Value / Wide-Column NoSQL

DynamoDB is fundamentally different from RDBMS/MongoDB: there's no JOIN, no flexible ad-hoc queries -
the schema/indexes must be designed AROUND known access patterns, not around the data structure. Getting
the design wrong from the start (not enough GSIs for a needed read pattern) usually can't be fixed without
recreating the table.

**ScyllaDB shares this file** - ScyllaDB has a DynamoDB-compatible API called **Alternator**, which
reimplements the actual DynamoDB API (PutItem/Query/GSI/`ConditionExpression`...) on top of the ScyllaDB
engine. When a project uses ScyllaDB via Alternator (instead of native CQL), everything about data model
design below applies identically to DynamoDB - the only differences are at the infrastructure/operations
layer (see the "ScyllaDB Alternator - operational differences" section at the end of this file). If a
project uses ScyllaDB via native CQL (not through Alternator), that's an entirely different data model -
see `references/cassandra.md` instead of this file.

## Design principle: Access patterns first, then tables

List EVERY query pattern the application needs (e.g. "get orders by customer," "get orders by status
within a date range") BEFORE designing the partition key/sort key - the complete opposite of RDBMS
(normalize first, query later). No pattern can easily be added later once a table already holds a large
amount of data without either creating a new GSI (costly backfill) or redesigning the table.

## Partition Key & Sort Key

```
Table "Orders":
  PK (partition key): CUSTOMER#<customer_id>
  SK (sort key):       ORDER#<order_id>
```

- **Partition key** determines physical data distribution - choose a column with high cardinality, avoid
  "hot partitions" (e.g. using `status` as PK when status only has a few values → all traffic piles onto a
  handful of partitions).
- **Sort key** enables range queries within the same partition (`begins_with`, `between`) - used to pack
  multiple related entity types into the same item collection (**single-table design**).

### Single-Table Design (the most common pattern in production)

```
PK                  | SK                  | Attributes
CUSTOMER#123        | METADATA            | name, email, ...
CUSTOMER#123        | ORDER#2024-01-15-01 | total, status, ...
CUSTOMER#123        | ORDER#2024-02-01-02 | total, status, ...
```

A single `Query` with `PK = CUSTOMER#123` retrieves both the customer profile and all their orders -
replacing an RDBMS JOIN. Trade-off: much harder to read than separate tables, and every access pattern
must be known before designing the keys. Only use single-table design once patterns are confirmed; if
access patterns are still uncertain (early product stage), a simpler multi-table design is easier to
maintain even though it's less cost-optimized.

## Global Secondary Index (GSI) & Local Secondary Index (LSI)

- **GSI**: partition key + sort key DIFFERENT from the base table - used to support a second access
  pattern (e.g. looking up orders by `status` instead of by `customer_id`). Has its own
  `WriteCapacity`/eventual consistency, can be created/deleted after the table already exists (but
  requires a backfill if the table already has data).
- **LSI**: same partition key as the base table, only the sort key differs - MUST be declared at table
  creation time, cannot be added later. Limited to 20GB of data per partition key value when an LSI
  exists. Less flexible than GSI - only use it when you need strongly consistent reads on a secondary
  pattern and are certain about it from the start.

```
GSI "StatusIndex": PK = STATUS#<status>, SK = ORDER#<created_at>
→ Query orders by status, sorted by creation time, without a full-table Scan.
```

## Query vs Scan - ALWAYS prefer Query; Scan is a performance red flag

```
Query: reads by PK (and optionally an SK condition) - efficient, cost scales with the number of items returned.
Scan:  reads the ENTIRE table then filters - cost scales with the ENTIRE table regardless of how many items match the filter.
```

If a `Scan` is needed frequently for one access pattern → that's a sign of a bad key/GSI design, not a
query-optimization problem. A Filter Expression in Query/Scan only reduces the data RETURNED, NOT the read
cost - DynamoDB still charges capacity for the number of items scanned before filtering.

## Capacity Mode

- **On-Demand**: pay per actual request, auto-scales - suits unpredictable traffic or early stages where
  the load pattern isn't clear yet. Higher cost per request than Provisioned when traffic is stable and
  high.
- **Provisioned** (+ Auto Scaling): cheaper when traffic is predictable and stable, but requires watching
  for throttling (`ProvisionedThroughputExceededException`) - traffic that exceeds the set capacity is
  rejected rather than auto-scaling immediately the way On-Demand does.

Default to On-Demand for new features/unclear traffic patterns; switch to Provisioned once stable traffic
has been measured and cost optimization matters - this is an operational decision, not a schema-design
decision, and can be switched back and forth without affecting data.

## Consistency & Concurrency

- Reads default to **eventually consistent** (cheaper) - use `ConsistentRead: true` when the business logic
  needs to read the exact value just written immediately (costs double the read capacity compared to
  eventual).
- **Conditional writes** - an atomic mechanism equivalent to optimistic locking/atomic UPDATE in RDBMS,
  without long-running RDBMS-style transactions:

```
PutItem/UpdateItem with ConditionExpression, e.g.:
  ConditionExpression: "attribute_not_exists(PK)"          -- only insert if it doesn't already exist
  ConditionExpression: "version = :expected_version"        -- version-column-style optimistic locking
  UpdateExpression: "SET stock = stock - :qty"
  ConditionExpression: "stock >= :qty"                       -- equivalent to an atomic conditional UPDATE in RDBMS
```

- **TransactWriteItems**: supports multi-item ACID transactions (up to 100 items, same region) - use when
  you genuinely need atomicity across multiple items/tables, costs double the write capacity of a normal
  write, only use when a `ConditionExpression` on a single item isn't enough to solve the problem.

## Item Size & Design Constraints

- 400KB/item limit - large data (files, blobs) should live in S3, with DynamoDB holding only a
  reference/metadata.
- No `ALTER TABLE`/schema migration in the RDBMS sense - DynamoDB is schemaless at the attribute level
  (each item can have different attributes); only the PK/SK and indexes are fixed at table creation.
  "Migration" really means changing how the application writes/reads attributes, or backfilling a new
  GSI - not DDL.

## DynamoDB Streams & TTL

- **Streams**: captures item changes (INSERT/MODIFY/REMOVE) in real time, triggers Lambda - used for
  asynchronous side effects (audit logs, syncing to other systems, updating aggregates) instead of
  RDBMS-style SQL triggers.
- **TTL**: automatically deletes expired items (based on an epoch timestamp attribute) - used for
  session/cache data; deletion via TTL doesn't consume write capacity (unlike a manual delete).

## DAX (DynamoDB Accelerator)

A dedicated cache layer for DynamoDB (similar to Redis but built in, microsecond latency) - only add it
once you've confirmed a read-heavy workload needs even lower latency and the key design is already
optimized, not as a first response to seeing slowness.

## ScyllaDB Alternator - operational differences from real DynamoDB

- **Self-hosted/multi-cloud**: ScyllaDB isn't locked into AWS the way DynamoDB is - choose Alternator when
  you want DynamoDB's data model/API but need to run your own infrastructure (on-prem, multi-cloud, or you
  already have a ScyllaDB cluster running for other purposes via CQL).
- **No On-Demand/Provisioned capacity concept in the AWS billing sense** - throughput is limited by the
  actual cluster resources (node CPU/RAM/disk), requiring self-managed capacity planning like any
  self-hosted system, and it does not auto-scale per request the way real DynamoDB On-Demand does.
- **No DAX, more limited Streams** - some AWS managed-only features (the DAX cache layer, Lambda-integrated
  Streams) aren't available or need a self-built equivalent; check ScyllaDB's current Alternator
  documentation before assuming a feature is available.
- **Cluster operations** (compaction, repair, GC-less shard-per-core) are identical to ScyllaDB's Ops
  section when used via CQL - see the end of `references/cassandra.md` to understand the shard-per-core
  architecture, even though here it's accessed via the Alternator API rather than CQL.

## Testcontainers / Local Testing

Use the `amazon/dynamodb-local` image (real DynamoDB) or `scylladb/scylla` with the Alternator flag enabled
(ScyllaDB) via `testcontainers-skill` for integration tests - Query/GSI/conditional-write behavior
reproduces production accurately, unlike a pure SDK mock (mocks don't catch key/GSI design mistakes).

## When to choose DynamoDB vs ScyllaDB Alternator (vs RDBMS/MongoDB/Cassandra - see the main SKILL.md)

- Access patterns are already clear, stable, and can be fully enumerated before design - a shared
  prerequisite for both.
- Need near-unlimited horizontal read/write scaling with stable single-digit millisecond latency.
- **Real DynamoDB**: already on AWS, want fully managed, don't want to operate a cluster.
- **ScyllaDB via Alternator**: want to keep DynamoDB's familiar data model/API but need to run your own
  infrastructure (self-hosted/multi-cloud), or already have a ScyllaDB cluster.
- NOT a good fit (both) when: you need flexible ad-hoc queries (reporting, multi-dimensional analytics),
  complex JOINs, or access patterns that are still changing frequently in an early product stage -
  RDBMS/MongoDB are far more flexible for these cases.

## Quick Reference

| Concept | Role |
|-----------|---------|
| Partition Key (PK) | Physical data distribution, required in every Query |
| Sort Key (SK) | Range queries within a partition, enables single-table design |
| GSI | Secondary access pattern, different key from the base table, can be added later |
| LSI | Secondary access pattern, same PK, declared at table creation, cannot change later |
| Query | Efficient read by PK - always prefer |
| Scan | Full-table read - red flag, avoid for frequent access patterns |
| ConditionExpression | Conditional atomic write - equivalent to optimistic lock/atomic UPDATE |
| TransactWriteItems | ACID across multiple items, double capacity cost |
| On-Demand / Provisioned | Capacity billing mode - On-Demand is the default when traffic is unclear |
