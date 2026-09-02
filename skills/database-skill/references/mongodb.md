# MongoDB - Document-Oriented NoSQL

MongoDB is much more flexible than DynamoDB/Cassandra (still supports ad-hoc queries, complex aggregation,
arbitrary secondary indexes) but is still NoSQL - there's no real JOIN (only `$lookup`, which simulates one
at a high cost), and the **embed vs reference** decision when designing a document is as important as the
normalization decision in an RDBMS.

## Design principle: Embed vs Reference

- **Embed** (nest child data inside the parent document): a single read is enough (no second round-trip),
  suitable for 1-1 or 1-to-many relationships with a LIMITED number of children that are always read
  together (e.g. `address` inside `user`, `line items` inside an `order`).
- **Reference** (store an `_id` reference, query separately or `$lookup`): use when child data can grow
  WITHOUT BOUND (comments, logs, events), when child data needs to be accessed independently of the
  parent, or when multiple parent documents reference the same child data (avoiding duplication/mismatch
  on update).

```javascript
// Embed - order and line items are always read/written together, item count has a reasonable limit
{
  _id: ObjectId("..."),
  customer_id: ObjectId("..."),
  items: [
    { product_id: ObjectId("..."), name: "Widget", qty: 2, price: 29.99 },
    { product_id: ObjectId("..."), name: "Gadget", qty: 1, price: 49.99 }
  ],
  total: 109.97
}

// Reference - comments can grow unbounded over time, don't embed them in the post
{ _id: ObjectId("..."), post_id: ObjectId("..."), author_id: ObjectId("..."), text: "..." }
```

**16MB/document limit** - embedding an unbounded array (comments, activity logs) is the most common design
mistake; the document will hit this limit as data grows over time even if it starts small. Always ask "does
this array have a clear upper bound?" before embedding.

## Schema Design Patterns

```javascript
// Subset pattern - only embed the N most recent/most important items, query the rest separately when needed
{
  _id: ObjectId("..."),
  name: "Product X",
  recent_reviews: [ /* 5 most recent reviews */ ],   // enough for the product detail page
  review_count: 1204                              // to display the total without loading everything
}

// Extended reference pattern - embed a few commonly used fields from the referenced record to avoid $lookup on frequent reads
{
  _id: ObjectId("..."),
  customer: { _id: ObjectId("..."), name: "Alice", email: "alice@example.com" }, // enough to display, no join needed
  total: 109.97
}
// Trade-off: embedded fields (name/email) can go stale if the customer's info changes later - acceptable
// for rarely changing data, or when this is meant as a snapshot at order-creation time (like the unit_price snapshot in RDBMS).
```

## Indexing

```javascript
db.orders.createIndex({ customer_id: 1, created_at: -1 });  // compound - field order matters just like RDBMS
db.orders.createIndex({ status: 1 }, { partialFilterExpression: { status: "pending" } }); // partial index
db.products.createIndex({ tags: 1 });                         // multikey - automatic when the indexed field is an array
db.posts.createIndex({ title: "text", content: "text" });     // text search
db.locations.createIndex({ coordinates: "2dsphere" });        // geospatial

// Check the plan before claiming an index improved performance - like EXPLAIN in an RDBMS
db.orders.find({ customer_id: ObjectId("...") }).explain("executionStats");
// Look for "COLLSCAN" (full collection scan, equivalent to Seq Scan) vs "IXSCAN" (index used).
```

Compound index: equality fields first, sort/range fields after - the same principle as B-tree composite
indexes in RDBMS (see `references/explain-and-indexing.md`).

## Aggregation Pipeline - optimize stage order

```javascript
db.orders.aggregate([
  { $match: { status: "completed", created_at: { $gte: ISODate("2024-01-01") } } }, // filter as EARLY as possible - reduces data for later stages
  { $project: { customer_id: 1, total: 1 } },   // keep only needed fields - reduces I/O between stages
  { $group: { _id: "$customer_id", total_spent: { $sum: "$total" } } },
  { $sort: { total_spent: -1 } },
  { $limit: 20 }
]);
```

Placing `$match`/`$project` as early as possible in the pipeline is best - MongoDB can use an index for a
`$match` at the start of the pipeline (like `WHERE` before `GROUP BY`), but CANNOT use an index if `$match`
comes after data-transforming stages (`$group`, `$unwind`, etc.).

`$lookup` (simulated JOIN) is significantly more expensive than embedding, especially without an index on
the join field in the target collection - only use it when the reference pattern is genuinely needed (see
Embed vs Reference above), don't overuse it like a regular RDBMS JOIN.

## Transactions & Concurrency

- Multi-document ACID transactions are available from 4.0+ (replica set) / 4.2+ (sharded cluster) - but
  prefer designing SELF-CONTAINED documents (embed) so most operations only need atomicity at the single
  document level (MongoDB naturally guarantees document-level atomicity without needing a transaction);
  reserve multi-document transactions for when you truly need atomicity across multiple
  documents/collections.
- Atomic increment/decrement of a numeric field: use `$inc` - carries the same atomic-conditional-UPDATE
  spirit as RDBMS, without a read-then-write round trip:

```javascript
db.inventory.updateOne(
  { _id: productId, stock: { $gte: qty } },   // condition in the filter - atomic, equivalent to WHERE stock >= :qty
  { $inc: { stock: -qty } }
);
// Check matchedCount === 0 to know whether the operation succeeded (like checking updatedRows == 0 in a SQL UPDATE)
```

- Optimistic locking: add a `version` field, condition it in the filter (`{ _id, version: expectedVersion
  }`), `$inc` the version on a successful update - the same pattern as JPA's `@Version`.

## Sharding - the shard key matters as much as the partition key in DynamoDB/Cassandra

Choose a shard key with high cardinality that distributes traffic evenly - a low-cardinality shard key
creates a **hot shard** (the same hot-partition problem as DynamoDB/Cassandra, see
`references/dynamodb.md`/`references/cassandra.md`). Changing the shard key after the cluster already has
significant data is a heavy operation (requires resharding) - choose carefully up front, especially if you
expect to scale horizontally in the future.

## Migration - schemaless, but document versions still need to be managed

MongoDB has no `ALTER TABLE` DDL, but applications still need to handle older documents missing new fields
(there's NO constraint forcing every document into the same shape). Two common approaches:
1. **One-time migration script**: `updateMany` across the whole collection to add a new field with a
   default - similar to an RDBMS migration, needs a rollback plan and staged rollout if the data is large.
2. **Lazy migration at the code layer**: read the new field with a fallback default if missing, write the
   new value back when the document is naturally updated - avoids a costly one-time bulk write, at the cost
   of multiple document "versions" coexisting for a longer period.

## Testcontainers / Local Testing

Use the `mongo` image via `testcontainers-skill` for integration tests - a replica set (`--replSet`) is
required if testing multi-document transactions, since MongoDB transactions require a replica set even when
running a single node.

## When to choose MongoDB (vs RDBMS and other key-value/column-based NoSQL stores)

- Semi-structured data with a frequently changing schema, but still needing flexible querying (filtering by
  various fields, aggregation - not just by a single fixed key like DynamoDB/Cassandra).
- Naturally document-oriented access (reading/writing a single document covers most use cases), needing
  easier horizontal write scaling than RDBMS, but access patterns aren't YET stable/narrow enough to accept
  the trade-offs of a key-value/column-based store (see
  `references/dynamodb.md`/`references/cassandra.md`).
- NOT a good fit when: data is tightly relational and needs frequent complex JOINs across many tables, or
  strong ACID transactions are central to the design (RDBMS is a better fit).

## Quick Reference

| Concept | Role |
|-----------|---------|
| Embed | Nests child data - single read, for bounded relationships always read together |
| Reference + `$lookup` | Separates child data - used when unbounded or needs independent access |
| Compound Index | Field order: equality first, sort/range after - same as RDBMS B-tree |
| Early `$match`/`$project` | Optimizes the aggregation pipeline, leverages indexes |
| `$inc` + conditional filter | Atomic conditional update - equivalent to SQL's `WHERE x >= :y` |
| Shard Key | Physical data distribution - low cardinality causes a hot shard |
| 16MB/document | Hard limit - a sign you need to move from embed to reference |
