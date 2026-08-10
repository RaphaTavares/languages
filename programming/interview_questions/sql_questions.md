# Top 20 SQL Interview Questions

## 1. What is SQL and what are its main sublanguages?

SQL (Structured Query Language) is a standard language for managing relational databases. Sublanguages:

- **DDL** (Data Definition) — `CREATE`, `ALTER`, `DROP`, `TRUNCATE`
- **DML** (Data Manipulation) — `INSERT`, `UPDATE`, `DELETE`, `MERGE`
- **DQL** (Data Query) — `SELECT`
- **DCL** (Data Control) — `GRANT`, `REVOKE`
- **TCL** (Transaction Control) — `COMMIT`, `ROLLBACK`, `SAVEPOINT`

## 2. What are the different types of JOINs?

- **INNER JOIN** — rows where the join condition matches in both tables.
- **LEFT (OUTER) JOIN** — all rows from the left table, matched rows from the right (NULL if no match).
- **RIGHT (OUTER) JOIN** — all rows from the right, matched from the left.
- **FULL (OUTER) JOIN** — all rows from both, with NULLs where no match.
- **CROSS JOIN** — Cartesian product of both tables.
- **SELF JOIN** — a table joined to itself.

```sql
SELECT u.name, o.total
FROM users u
LEFT JOIN orders o ON o.user_id = u.id;
```

## 3. What is the difference between `WHERE` and `HAVING`?

- **`WHERE`** — filters rows **before** grouping. Cannot use aggregate functions.
- **`HAVING`** — filters groups **after** `GROUP BY`. Can use aggregates.

```sql
SELECT department, COUNT(*) AS cnt
FROM employees
WHERE active = true
GROUP BY department
HAVING COUNT(*) > 10;
```

## 4. What is database normalization? Explain 1NF, 2NF, 3NF.

Normalization is the process of organizing data to reduce redundancy and improve integrity.

- **1NF** — atomic values (no repeating groups, no arrays in cells).
- **2NF** — 1NF + no partial dependency on a composite primary key.
- **3NF** — 2NF + no transitive dependencies (non-key attributes depend only on the key).
- **BCNF** — stricter 3NF: every determinant must be a candidate key.

## 5. When would you denormalize a database?

Denormalization introduces redundancy intentionally to improve read performance. Use cases:

- Read-heavy workloads (reporting, analytics).
- Reducing expensive joins.
- Caching computed aggregates.

Trade-offs: harder writes, risk of inconsistency, more storage.

## 6. What is an index and what types exist?

An index is a data structure that speeds up lookups on one or more columns, at the cost of slower writes and extra storage.

- **Clustered** — determines the physical order of rows (one per table).
- **Non-clustered** — separate structure pointing to rows (many per table).
- **Composite** — multiple columns; order matters for prefix matching.
- **Unique** — enforces uniqueness.
- **Partial / filtered** — indexes only rows matching a predicate.
- **Covering** — includes all columns needed by the query (no table lookup).

## 7. What is the difference between a primary key, unique key, and foreign key?

- **Primary key** — uniquely identifies each row; one per table; NOT NULL; automatically indexed.
- **Unique key** — enforces uniqueness on a column/set; allows one NULL (in most engines); can have many per table.
- **Foreign key** — references a primary/unique key in another (or the same) table; enforces referential integrity.

## 8. What are the ACID properties?

- **Atomicity** — a transaction is all-or-nothing.
- **Consistency** — a transaction moves the DB from one valid state to another.
- **Isolation** — concurrent transactions don't interfere.
- **Durability** — committed data survives crashes.

## 9. What are transaction isolation levels?

Four standard levels, from weakest to strongest:

- **READ UNCOMMITTED** — dirty reads allowed.
- **READ COMMITTED** — no dirty reads; non-repeatable reads possible.
- **REPEATABLE READ** — same query returns same rows within a transaction; phantom reads possible.
- **SERIALIZABLE** — full isolation, as if transactions ran sequentially.

Stronger isolation → more locking/versioning → lower concurrency.

## 10. What is the difference between `GROUP BY` and `ORDER BY`?

- **`GROUP BY`** — groups rows sharing a value; used with aggregates (`COUNT`, `SUM`, `AVG`).
- **`ORDER BY`** — sorts the result set.

`ORDER BY` runs after `GROUP BY` in logical query processing.

## 11. What are subqueries and CTEs?

- **Subquery** — a query nested inside another query. Can be scalar, row, table, or correlated.
- **CTE (Common Table Expression)** — a named temporary result defined with `WITH`. Improves readability, supports recursion.

```sql
WITH recent_orders AS (
  SELECT * FROM orders WHERE created_at > NOW() - INTERVAL '7 days'
)
SELECT user_id, COUNT(*) FROM recent_orders GROUP BY user_id;
```

## 12. What are window functions?

Window functions perform calculations across a set of rows related to the current row, **without collapsing the result set** (unlike aggregates with `GROUP BY`).

```sql
SELECT
  employee_id,
  salary,
  RANK() OVER (PARTITION BY department ORDER BY salary DESC) AS rank,
  AVG(salary) OVER (PARTITION BY department) AS dept_avg
FROM employees;
```

Common ones: `ROW_NUMBER`, `RANK`, `DENSE_RANK`, `LAG`, `LEAD`, `SUM/AVG OVER`.

## 13. What is the difference between `UNION` and `UNION ALL`?

- **`UNION`** — combines results and removes duplicates (more expensive).
- **`UNION ALL`** — combines results, keeps duplicates (faster).

Both require the same number of columns with compatible types.

## 14. What is the difference between `DELETE`, `TRUNCATE`, and `DROP`?

- **`DELETE`** — DML; removes rows matching a `WHERE` clause; logged per row; triggers fire; rollback-able.
- **`TRUNCATE`** — DDL; removes all rows quickly; resets identity; minimal logging; usually no triggers.
- **`DROP`** — DDL; removes the entire table (schema + data).

## 15. What is a view? What is a materialized view?

- **View** — a stored query treated like a virtual table. Executed every time it's queried. No storage of data.
- **Materialized view** — stores the query result physically; must be refreshed. Trades staleness for speed.

## 16. What is the difference between a stored procedure and a function?

- **Stored procedure** — a routine that can perform actions (DML), return zero or more result sets, doesn't have to return a value. Called via `CALL` / `EXEC`.
- **Function** — must return a value (scalar or table); usually side-effect-free; can be used inside SQL expressions.

## 17. What is a trigger?

A trigger is a stored procedure that fires automatically in response to an event on a table (`INSERT`, `UPDATE`, `DELETE`). Can be `BEFORE`, `AFTER`, or `INSTEAD OF`.

Use for audit logs, cascading rules, and derived data. Overuse hurts maintainability and performance — prefer application logic when possible.

## 18. How do you optimize a slow query?

- Read the **query plan** (`EXPLAIN` / `EXPLAIN ANALYZE`).
- Add or refine **indexes** (especially on JOIN and WHERE columns).
- Avoid `SELECT *`; select only needed columns.
- Rewrite correlated subqueries as joins or CTEs.
- Look for **sequential scans** on large tables.
- Update **statistics** (`ANALYZE`).
- Consider **partitioning** or **materialized views** for hot aggregates.

## 19. What is the N+1 query problem?

Firing one query for the parent and N follow-up queries for each child, instead of joining or batching.

```sql
-- Bad: 1 + N queries
SELECT * FROM users;                          -- 1
SELECT * FROM orders WHERE user_id = ?;       -- N times

-- Good: 1 query
SELECT u.*, o.* FROM users u LEFT JOIN orders o ON o.user_id = u.id;
```

ORMs are the most common source. Fix with eager loading / `JOIN` / batching.

## 20. What is the difference between OLTP and OLAP?

- **OLTP (Online Transaction Processing)** — day-to-day operational systems. Many small, fast transactions. Normalized. Row-oriented storage.
- **OLAP (Online Analytical Processing)** — analytical/reporting workloads. Fewer, complex, aggregating queries over large datasets. Denormalized / star schema. Often columnar storage (Snowflake, BigQuery, Redshift).
