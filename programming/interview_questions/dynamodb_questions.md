# Top 20 AWS DynamoDB Interview Questions

## 1. What is DynamoDB?

DynamoDB is a fully managed, serverless, NoSQL key-value and document database from AWS. It offers single-digit millisecond latency at any scale, automatic sharding, built-in replication, and pay-per-use or provisioned capacity.

## 2. What is the difference between a partition key and a sort key?

- **Partition key (hash key)** — determines the physical partition where the item is stored. Required.
- **Sort key (range key)** — orders items within the same partition. Optional; when present, the primary key is composite.

Together they form the **primary key**, which must be unique.

## 3. What are the two types of primary keys in DynamoDB?

- **Simple primary key** — partition key only. Each item must have a unique partition key.
- **Composite primary key** — partition key + sort key. Multiple items can share a partition key if their sort keys differ.

## 4. What is the difference between a GSI and an LSI?

- **LSI (Local Secondary Index)** — same partition key as the base table, different sort key. Must be created at table creation. Shares capacity with the base table.
- **GSI (Global Secondary Index)** — different partition key (and optionally different sort key). Can be created anytime. Has its own capacity settings. Eventually consistent only.

Limit: 5 LSIs and 20 GSIs per table (default).

## 5. What are the read consistency models in DynamoDB?

- **Eventually consistent reads** (default) — may return stale data; cheapest and fastest.
- **Strongly consistent reads** — return the most recent data; cost 2× and slightly higher latency; not supported on GSIs.
- **Transactional reads** — consistent, isolated multi-item reads; cost 2× strongly consistent.

## 6. What are the two capacity modes?

- **On-demand** — pay per request, no capacity planning, scales instantly. Good for unpredictable or spiky workloads.
- **Provisioned** — pre-allocate RCUs and WCUs; cheaper for predictable workloads. Auto-scaling can adjust based on utilization.

You can switch modes (once every 24 hours).

## 7. How are RCUs and WCUs calculated?

- **1 RCU** = 1 strongly consistent read/s for an item up to 4 KB, or 2 eventually consistent reads/s.
- **1 WCU** = 1 write/s for an item up to 1 KB.

Transactional operations cost **2×**. Rounded up to the nearest chunk (e.g., a 5 KB read = 2 RCUs).

## 8. What are DynamoDB Streams?

A time-ordered log of item-level changes (INSERT/MODIFY/REMOVE), retained for 24 hours. Consumers can process changes in near real time.

Common use: trigger a Lambda for replication, auditing, aggregations, or cache invalidation. Supersets: **Kinesis Data Streams** integration for longer retention.

## 9. What is single-table design?

A pattern where multiple entity types (users, orders, products) live in **one** DynamoDB table, differentiated by prefixed keys (e.g., `USER#123`, `ORDER#456`). Benefits:

- Fewer requests to fetch related data (one query returns multiple entity types).
- Better use of GSIs.
- Lower operational overhead.

Trade-off: less flexibility, harder to model without upfront access-pattern analysis.

## 10. What is the hot partition problem and how do you avoid it?

A **hot partition** occurs when one partition receives disproportionate traffic, hitting throughput limits while other partitions sit idle.

Mitigations:

- Design partition keys with high cardinality.
- Add a **write sharding** suffix (e.g., `USER#123#0`, `USER#123#1`).
- Use **adaptive capacity** (automatic in Dynamo).
- Cache hot reads (DAX, ElastiCache).

## 11. What is the difference between `Query` and `Scan`?

- **`Query`** — retrieves items with a specific partition key (and optionally sort key condition). Efficient — only reads matching items.
- **`Scan`** — reads every item in the table or index. Slow, expensive, and hits throughput. Use only for one-off ops or small tables.

Prefer `Query` (or `GetItem`) whenever possible.

## 12. What are conditional writes?

Writes that succeed only if a condition is met, evaluated atomically on the server:

```json
{
  "ConditionExpression": "attribute_not_exists(id) AND price > :min",
  "ExpressionAttributeValues": { ":min": 0 }
}
```

Used for optimistic concurrency, uniqueness enforcement, and idempotency. Failed conditions still consume WCUs.

## 13. Do transactions exist in DynamoDB?

Yes. `TransactWriteItems` and `TransactGetItems` support ACID transactions across up to **100 items** (or 4 MB) in one or more tables in the same region.

- Atomic all-or-nothing.
- Cost **2×** normal writes/reads.
- Cannot span AWS accounts or regions.

## 14. What is TTL (Time to Live)?

An attribute (of Number type, Unix epoch seconds) that DynamoDB uses to automatically delete items after their expiration time. Deletions:

- Happen in the background (typically within 48 hours of expiration).
- Are free (no WCU cost).
- Appear in DynamoDB Streams (marked as `REMOVE` by `dynamodb`).

Useful for session data, ephemeral records, and cache-like items.

## 15. What is DAX?

**DynamoDB Accelerator** — a fully managed, in-memory write-through cache for DynamoDB. Provides microsecond read latency for cached items.

- Runs as a cluster inside your VPC.
- API-compatible with DynamoDB (minimal code changes).
- Only caches eventually consistent reads; strongly consistent reads pass through.

## 16. What is Point-in-Time Recovery (PITR)?

Continuous backup that lets you restore a table to any second within the last **35 days**. Enabled with a toggle.

Also available: **on-demand backups** (kept until you delete them, cross-account/region copyable).

## 17. What are Global Tables?

Multi-region, multi-active replication of a DynamoDB table. Writes to any region propagate to all others (typically within a second). Provides:

- Low-latency reads/writes globally.
- Disaster recovery.
- Last-writer-wins conflict resolution.

Requires DynamoDB Streams enabled with `NEW_AND_OLD_IMAGES`.

## 18. What are the size limits in DynamoDB?

- **Item size** — max 400 KB (including attribute names).
- **Attribute name** — up to 64 KB.
- **Partition key value** — up to 2048 bytes; sort key up to 1024 bytes.
- **Query/Scan result** — max 1 MB per page (paginate for more).

For larger blobs, store in S3 and reference the S3 key from DynamoDB.

## 19. What are batch operations?

- **`BatchGetItem`** — retrieves up to 100 items or 16 MB across tables.
- **`BatchWriteItem`** — puts or deletes up to 25 items or 16 MB across tables. No updates, no conditions.

Batches are **not atomic** — individual failures are returned in `UnprocessedItems` (must be retried with backoff).

## 20. What is the difference between a `KeyCondition` and a `FilterExpression`?

- **`KeyConditionExpression`** — applied on the server against the primary key (partition + sort). Determines which items are read → cheaper.
- **`FilterExpression`** — applied **after** the read, before results are returned. You still pay RCUs for filtered-out items.

Design your keys and indexes so most filtering can be done via `KeyCondition`, not `FilterExpression`.
