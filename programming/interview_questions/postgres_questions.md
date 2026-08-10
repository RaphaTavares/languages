# Top 20 PostgreSQL Interview Questions

## 1. What is PostgreSQL and what makes it different from other RDBMS?

PostgreSQL is a powerful, open-source object-relational database (ORDBMS) known for standards compliance, extensibility, and advanced features. Distinguishing traits:

- Rich type system (arrays, JSONB, ranges, geometric, UUID, hstore)
- Full ACID compliance with MVCC
- Extensible: custom types, operators, functions, and languages (PL/pgSQL, PL/Python)
- Powerful indexing (GIN, GiST, BRIN, hash, B-tree)
- Strong support for complex queries, CTEs, and window functions

## 2. What is MVCC (Multi-Version Concurrency Control)?

MVCC allows concurrent reads and writes without blocking each other. Each transaction sees a consistent snapshot of the database:

- Writers don't block readers, and readers don't block writers.
- Each row can have multiple versions; visibility is determined by transaction IDs (xmin/xmax).
- Old row versions are cleaned up by `VACUUM`.

## 3. What is the difference between JSON and JSONB?

- **`JSON`** — stored as text, preserves whitespace and key order, faster to insert, slower to query.
- **`JSONB`** — stored in a decomposed binary format, supports indexing (GIN), faster queries, no duplicate keys, no preserved order.

Use `JSONB` in almost every case unless you need to preserve exact input.

```sql
SELECT data->>'name' FROM users WHERE data @> '{"active": true}';
```

## 4. What index types does PostgreSQL support and when to use each?

- **B-tree** (default) — equality and range queries on ordered data.
- **Hash** — equality only; rarely worth choosing over B-tree.
- **GIN** (Generalized Inverted Index) — arrays, JSONB, full-text search.
- **GiST** (Generalized Search Tree) — geometric, full-text, custom types.
- **SP-GiST** — non-balanced data (e.g., phone directories, IP ranges).
- **BRIN** (Block Range Index) — very large tables where data is naturally ordered (time-series). Tiny footprint.

## 5. What is `VACUUM` and why is it needed?

MVCC leaves behind dead row versions after `UPDATE`/`DELETE`. `VACUUM` reclaims that space.

- **`VACUUM`** — reclaims space for reuse, doesn't return it to the OS.
- **`VACUUM FULL`** — rewrites the table, returns space to the OS, requires an exclusive lock.
- **`autovacuum`** — background daemon that runs `VACUUM` and `ANALYZE` automatically based on thresholds.

Neglected vacuuming leads to bloat and transaction ID wraparound.

## 6. What are schemas in PostgreSQL?

A schema is a namespace inside a database, containing tables, views, functions, etc. They let you:

- Group related objects.
- Grant permissions at the schema level.
- Allow multiple users/apps to share a database without name collisions.

The default is `public`. The `search_path` controls how unqualified names are resolved.

## 7. What are sequences and how do `SERIAL` and `IDENTITY` differ?

A **sequence** is an object that generates monotonically increasing numeric values (used for auto-incrementing PKs).

- **`SERIAL`** — legacy shortcut; creates a sequence + integer column. Ownership can be lost on schema changes.
- **`GENERATED ... AS IDENTITY`** (SQL standard, Postgres 10+) — preferred. Two modes:
  - `BY DEFAULT` — user can override.
  - `ALWAYS` — user cannot override (safer).

## 8. What are CTEs and recursive CTEs?

A **CTE** (`WITH ... AS`) defines a temporary named result set within a query.

**Recursive CTEs** enable tree/graph traversal:

```sql
WITH RECURSIVE org_chart AS (
  SELECT id, name, manager_id, 1 AS level
  FROM employees WHERE manager_id IS NULL
  UNION ALL
  SELECT e.id, e.name, e.manager_id, oc.level + 1
  FROM employees e JOIN org_chart oc ON e.manager_id = oc.id
)
SELECT * FROM org_chart;
```

Note: Postgres 12+ inlines non-recursive CTEs by default (previously they were optimization fences).

## 9. What is a materialized view and how is it different from a regular view?

- **View** — a stored query; runs every time it's referenced.
- **Materialized view** — stores the result physically; must be refreshed with `REFRESH MATERIALIZED VIEW`.

Materialized views trade freshness for speed. Use `REFRESH ... CONCURRENTLY` to avoid locking (requires a unique index).

## 10. What are the transaction isolation levels in PostgreSQL?

Postgres supports all four standard levels, but behaves as follows:

- **READ UNCOMMITTED** — treated as READ COMMITTED (no dirty reads ever).
- **READ COMMITTED** (default) — each statement sees a fresh snapshot.
- **REPEATABLE READ** — snapshot fixed at the first statement; prevents non-repeatable reads and phantom reads (thanks to MVCC).
- **SERIALIZABLE** — uses Serializable Snapshot Isolation (SSI); may abort transactions on conflicts.

## 11. What kinds of locks does PostgreSQL use?

- **Row-level locks** — acquired by `SELECT ... FOR UPDATE`, `UPDATE`, `DELETE`.
- **Table-level locks** — 8 modes from `ACCESS SHARE` to `ACCESS EXCLUSIVE`; taken by DDL, VACUUM FULL, etc.
- **Advisory locks** — application-defined locks (`pg_advisory_lock`) not tied to any row/table.

Check active locks with `pg_locks` and blocking queries with `pg_stat_activity`.

## 12. What is table partitioning in PostgreSQL?

Splits a large table into smaller physical pieces while presenting a single logical table. Types:

- **RANGE** — by ranges of values (e.g., date ranges).
- **LIST** — by discrete values (e.g., country codes).
- **HASH** — by hash of a column, for even distribution.

Benefits: faster queries via partition pruning, easier maintenance (drop old partitions), better vacuum behavior.

## 13. What replication options does PostgreSQL provide?

- **Streaming (physical) replication** — byte-for-byte copy of WAL to standbys. All-or-nothing per cluster.
- **Logical replication** — publishes changes at the row level; can replicate individual tables, across major versions, or into different schemas.
- **Synchronous vs asynchronous** — trade latency for durability.

Standbys can be **hot** (accept read queries) or **warm** (standby only).

## 14. What is the WAL (Write-Ahead Log)?

The WAL is the append-only log where changes are written **before** they're applied to data files. It provides:

- **Durability** (part of ACID)
- **Crash recovery** — replay WAL from the last checkpoint.
- **Replication** — WAL is streamed to standbys.
- **Point-in-time recovery (PITR)** via archived WAL segments.

## 15. What is the difference between `EXPLAIN` and `EXPLAIN ANALYZE`?

- **`EXPLAIN`** — shows the query plan **without** running the query. Displays estimated costs and row counts.
- **`EXPLAIN ANALYZE`** — actually **executes** the query and reports real timings and row counts.

Use `EXPLAIN (ANALYZE, BUFFERS, VERBOSE)` for deep analysis. Compare estimated vs actual rows — big divergence means stale statistics (`ANALYZE`).

## 16. What are Foreign Data Wrappers (FDW)?

FDWs let PostgreSQL query external data sources (other Postgres instances, MySQL, files, MongoDB, REST APIs) as if they were local tables.

```sql
CREATE EXTENSION postgres_fdw;
CREATE SERVER remote_db FOREIGN DATA WRAPPER postgres_fdw
  OPTIONS (host 'other.db', dbname 'app');
CREATE FOREIGN TABLE remote_users (...) SERVER remote_db;
```

## 17. How does full-text search work in PostgreSQL?

Postgres has built-in full-text search using `tsvector` (indexed documents) and `tsquery` (search terms), with a GIN index for speed.

```sql
CREATE INDEX idx_docs_fts ON docs USING GIN (to_tsvector('english', body));

SELECT * FROM docs
WHERE to_tsvector('english', body) @@ plainto_tsquery('english', 'postgres index');
```

Supports stemming, ranking (`ts_rank`), and multiple languages.

## 18. What are common useful extensions?

- **`pg_stat_statements`** — track query performance across the server.
- **`pgcrypto`** — cryptographic functions (hashing, encryption).
- **`uuid-ossp` / `pgcrypto`** — UUID generation.
- **`PostGIS`** — geospatial data and queries.
- **`hstore`** — key-value store column type.
- **`pg_trgm`** — trigram-based similarity search (great for fuzzy matching).

Enable with `CREATE EXTENSION extension_name;`.

## 19. How does `UPSERT` work in PostgreSQL?

`INSERT ... ON CONFLICT` provides atomic upsert:

```sql
INSERT INTO users (id, name, email)
VALUES (1, 'Alice', 'a@x.com')
ON CONFLICT (id) DO UPDATE
  SET name = EXCLUDED.name,
      email = EXCLUDED.email;

-- Or do nothing on conflict:
INSERT INTO events (id, ...) VALUES (...)
ON CONFLICT (id) DO NOTHING;
```

`EXCLUDED` refers to the row that would have been inserted.

## 20. What's the difference between `NULL`, empty string, and `DEFAULT` in PostgreSQL?

- **`NULL`** — absence of a value; never equals anything (use `IS NULL`).
- **Empty string `''`** — a real value, distinct from `NULL`. In Postgres, `''` is **not** treated as `NULL` (unlike Oracle).
- **`DEFAULT`** — the value assigned by the column definition when not specified.

Three-valued logic: `NULL AND FALSE` → `FALSE`; `NULL AND TRUE` → `NULL`. Use `COALESCE()` to substitute defaults.
