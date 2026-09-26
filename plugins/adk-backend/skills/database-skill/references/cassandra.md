# Cassandra - Wide-Column NoSQL (CQL)

Note the distinction: **ScyllaDB with the DynamoDB-compatible API (Alternator)** is covered together with
DynamoDB in `references/dynamodb.md`. This file is only for **native Cassandra via CQL** - if a project
uses ScyllaDB via plain CQL (not through Alternator), the data model/CQL in this file applies almost
identically (ScyllaDB is protocol/CQL-compatible with Cassandra), differing only at the operational layer:
ScyllaDB is written in C++ (no GC pauses like Cassandra's JVM), and its shard-per-core architecture makes
more effective use of multiple cores/nodes without needing to manually tune JVM heap.

## Design principle: Access patterns first, tables second

Cassandra does NOT support JOINs and has no flexible ad-hoc querying like an RDBMS. A single table serves
EXACTLY 1 (or a few) known access patterns well - a different access pattern requires a different table
holding the same data with a different key (**query-driven denormalization**, the same "query-first"
spirit as DynamoDB, see `references/dynamodb.md`).

## Partition Key & Clustering Key

```sql
CREATE TABLE orders_by_customer (
    customer_id  UUID,
    order_date   TIMESTAMP,
    order_id     UUID,
    status       TEXT,
    total        DECIMAL,
    PRIMARY KEY ((customer_id), order_date, order_id)
    -- (customer_id) = partition key - determines which node/replica holds the data
    -- order_date, order_id = clustering key - determines the sort order WITHIN the partition
) WITH CLUSTERING ORDER BY (order_date DESC);
```

- **Partition key**: must be present in the `WHERE` clause of every efficient query - determines which
  node the data lives on. Low cardinality (e.g. using `status` as the partition key when there are only a
  few values) creates a **hot partition** - one node takes all the read/write traffic while others sit
  idle.
- **Clustering key**: physically sorts data within the partition, enabling efficient range queries
  (`order_date > ?`) without reading the whole partition.

**Denormalize per query** - a separate table per access pattern, synced on write (no JOIN at read time):

```sql
-- Access pattern 1: look up orders by customer → table above
-- Access pattern 2: look up orders by status → separate table, different PK
CREATE TABLE orders_by_status (
    status      TEXT,
    order_date  TIMESTAMP,
    order_id    UUID,
    customer_id UUID,
    total       DECIMAL,
    PRIMARY KEY ((status), order_date, order_id)
);
-- The application must write to BOTH tables when creating an order - trade-off: 2x the writes, but reads stay fast (no JOIN)
```

## CQL - looks like SQL but deliberately restricted

```sql
-- Efficient query: ALWAYS include the partition key in WHERE
SELECT * FROM orders_by_customer WHERE customer_id = ? AND order_date > '2024-01-01';

-- NOT ALLOWED: filtering by a column that isn't a partition/clustering key without ALLOW FILTERING
SELECT * FROM orders_by_customer WHERE total > 1000;  -- error, unless ALLOW FILTERING is added

-- ALLOW FILTERING = a performance red flag - scans everything then filters; CQL blocks this by default on
-- purpose, to force developers to notice a badly designed query instead of it silently getting slower as data grows.
```

No JOINs, no subqueries, no flexible `GROUP BY` like SQL - any complex aggregation should be handled at the
application layer or via the Spark connector, not forced into CQL.

## Consistency Level - tunable, chosen per query

Cassandra uses an eventually-consistent model with a consistency level (CL) selectable PER QUERY, unlike a
fixed RDBMS replica setup:

| CL | Meaning | Use when |
|----|---------|----------|
| `ONE` | 1 replica acknowledges | Fastest read/write, tolerates temporarily stale data |
| `QUORUM` | Majority of replicas acknowledge (e.g. 2/3) | Balances consistency/latency - a sensible default for most use cases |
| `ALL` | Every replica acknowledges | Need the strongest consistency, accept the highest latency, reduces availability if 1 replica is down |

**Read + Write CL both set to QUORUM** → guarantees read-your-write consistency (R + W > Replication
Factor) - the most important formula to remember when you need to read a value immediately after writing
it without using CL=ALL.

## Replication Factor & Multi-Datacenter

```sql
CREATE KEYSPACE ecommerce WITH replication = {
    'class': 'NetworkTopologyStrategy',
    'datacenter1': 3   -- 3 copies in this DC - RF=3 is the common production baseline
};
```

RF=3 + CL=QUORUM is a sensible default combo for production - tolerates 1 node going down without losing
availability or consistency. Multi-datacenter replication (`NetworkTopologyStrategy` with multiple DCs) is
used when you need disaster recovery or reduced read/write latency by geographic region - this is a major
infrastructure decision that needs to be discussed with the user separately, don't add it unprompted.

## Lightweight Transaction (LWT) - conditional write, equivalent to DynamoDB's ConditionExpression

```sql
INSERT INTO orders (order_id, status) VALUES (?, 'pending') IF NOT EXISTS;
UPDATE inventory SET stock = stock - :qty WHERE product_id = ? IF stock >= :qty;
```

LWT uses the Paxos protocol internally - significantly more expensive than a normal write (more
round-trips), only use it when you genuinely need conditional atomicity, not as the default for every
write.

## Ops & Tuning

- **Compaction strategy**: `SizeTieredCompactionStrategy` (default, good for write-heavy workloads) vs
  `LeveledCompactionStrategy` (good for read-heavy workloads, reduces the number of SSTables that need to
  be read) - choose based on real load, don't change the default unless you've measured a specific
  problem.
- **JVM heap & GC**: Cassandra runs on the JVM - heap size needs tuning, and GC pauses need monitoring. Long
  GC pauses are the most common cause of sudden latency spikes. (ScyllaDB via CQL skips this tuning step -
  it's C++, with a shard-per-core architecture that self-allocates across CPU cores, but hot-partition
  monitoring is still needed the same way.)
- **Tombstones**: `DELETE` doesn't remove data immediately, it marks a tombstone (similar to Postgres's
  MVCC dead tuples) - too many tombstones in one partition (a frequent-delete pattern) significantly slows
  down reads; needs periodic `nodetool compact` or a TTL-based design instead of manual DELETE where
  possible.
- **`nodetool repair`**: run periodically (typically weekly) to resync data across replicas after a network
  partition/node outage - skipping it for a long time increases the risk of reading inconsistent data.

## Testcontainers / Local Testing

Use the `cassandra` image (or `scylladb/scylla` if the project uses ScyllaDB via CQL) through
`test-master/references/testcontainers.md` - this tests real CQL/consistency-level behavior accurately, which is especially
important for catching queries missing a partition key early (they fail immediately when running CQL).

## When to choose Cassandra (vs DynamoDB/ScyllaDB Alternator/RDBMS/MongoDB - see the main SKILL.md)

- Extremely high write volume, distributed across multiple datacenters, needing infrastructure control
  (self-hosted) rather than a managed service.
- Access patterns are already numerous and well understood, and you accept denormalizing/writing to
  multiple tables in exchange for fast reads.
- Want the traditional CQL ecosystem/tooling (stable multi-language drivers, Spark connector) - if you just
  want the same data model with better performance on the same hardware and don't want to tune the JVM,
  consider ScyllaDB via CQL instead of Cassandra (the content of this file applies almost unchanged, see
  the Ops notes above).
- NOT a good fit when: query patterns aren't stable yet, you need JOINs/complex ad-hoc queries, or the team
  lacks experience operating distributed systems (self-hosted operational cost is significant) - consider
  DynamoDB/ScyllaDB Alternator if you want managed, or RDBMS/MongoDB if access patterns aren't finalized.

## Quick Reference

| Concept | Role |
|-----------|---------|
| Partition Key | Physical data distribution, required in WHERE |
| Clustering Key | Sort order within a partition, enables range queries |
| `ALLOW FILTERING` | Red flag - scans without using an index, avoid |
| Consistency Level (CL) | Chosen per query: ONE/QUORUM/ALL |
| Replication Factor (RF) | Number of copies - RF=3 + CL=QUORUM is the common baseline |
| Lightweight Transaction (LWT) | Conditional write (`IF NOT EXISTS`/`IF ...`), costs Paxos overhead |
| Tombstone | `DELETE` marker - many tombstones slow down reads |
| `nodetool repair` | Periodic replica resync |
