# Aula 10 — Rapid Fire (revisão de segunda de manhã)

> Objetivo: responder cada pergunta **em inglês, em 30-60 segundos, em voz alta**. Este é o único arquivo com respostas-modelo incluídas — **cubra a seção de respostas e só confira depois de tentar.** Marque ✅ / ⚠️ / ❌ em cada uma.

---

## As perguntas

### SQL
1. WHERE vs HAVING?
2. INNER JOIN vs LEFT JOIN?
3. CTE vs subquery?
4. ROW_NUMBER vs RANK vs DENSE_RANK?
5. GROUP BY vs window function?
6. UNION vs UNION ALL?
7. NOT IN vs NOT EXISTS — which do you prefer and why?
8. COUNT(*) vs COUNT(column)?

### Performance / Postgres
9. Index Scan vs Seq Scan — is a seq scan always bad?
10. Why can too many indexes be harmful?
11. What makes a predicate non-sargable? Give an example.
12. What does ANALYZE do?
13. Why does PostgreSQL need VACUUM?
14. What is MVCC?
15. OFFSET pagination vs keyset pagination?
16. Estimated rows vs actual rows — why does the gap matter?
17. Nested Loop vs Hash Join — when does the planner pick each?

### Concurrency
18. Optimistic vs pessimistic locking?
19. What is a deadlock and how do you prevent it?
20. What's a lost update?

### Migration / Distributed
21. Why is dual-write dangerous?
22. What is CDC?
23. What is the Outbox Pattern?
24. Database-per-service vs shared database?
25. What is the Strangler Fig pattern?
26. Why must consumers be idempotent with at-least-once delivery?
27. How do you prove two databases have the same data?

### Patterns / AWS / DynamoDB
28. Strategy vs Factory?
29. Decorator vs Proxy?
30. Lambda or ECS — how do you decide?
31. SQS vs EventBridge?
32. What causes a hot partition in DynamoDB?
33. When would you choose PostgreSQL over DynamoDB?

---
---
---

## 🔒 Respostas-modelo (NÃO leia antes de tentar todas)

1. **WHERE vs HAVING** — "WHERE filters rows before grouping, HAVING filters groups after aggregation. Aggregate conditions can only live in HAVING; everything else belongs in WHERE, which is also cheaper because fewer rows reach the aggregation."
2. **INNER vs LEFT** — "INNER keeps only matching rows; LEFT keeps every left row, with NULLs when there's no match. Practical tell: 'customers without orders' needs LEFT JOIN plus an IS NULL check, or NOT EXISTS."
3. **CTE vs subquery** — "Mostly readability — modern Postgres inlines simple CTEs, so performance is the same. A CTE referenced twice or marked MATERIALIZED is computed once but becomes an optimization fence: outer filters don't push down into it."
4. **ROW_NUMBER vs RANK vs DENSE_RANK** — "ROW_NUMBER is always unique — ties broken arbitrarily. RANK shares the number on ties and skips (1,2,2,4); DENSE_RANK shares and doesn't skip (1,2,2,3). For 'latest row per entity' I want ROW_NUMBER, so ties can't return two rows."
5. **GROUP BY vs window** — "GROUP BY collapses rows to one per group; a window function keeps every row and adds a computed column over its partition. 'Total per customer' → GROUP BY; 'each order with its customer's total' or 'rank within group' → window."
6. **UNION vs UNION ALL** — "UNION deduplicates, which costs a sort or hash; UNION ALL just concatenates. If duplicates are impossible or acceptable, UNION ALL — it's free."
7. **NOT IN vs NOT EXISTS** — "NOT EXISTS. If the NOT IN subquery returns a single NULL, three-valued logic makes the whole predicate return no rows — a classic silent bug."
8. **COUNT(*) vs COUNT(col)** — "COUNT(*) counts rows; COUNT(col) counts rows where col is not null. After a LEFT JOIN, COUNT(*) gives 1 for a customer with no orders, COUNT(o.id) gives the correct 0."
9. **Seq Scan always bad?** — "No. If the query reads a large fraction of the table, sequential IO beats millions of random index lookups; the planner chooses by cost. A seq scan is suspicious only when the predicate is selective and a usable index exists."
10. **Too many indexes** — "Every insert, update and delete maintains every index — write amplification plus storage plus vacuum work. Updates to indexed columns also lose HOT optimization. Indexes are paid for on every write and only redeemed on the reads that use them."
11. **Non-sargable** — "Any expression wrapped around the column: WHERE DATE(created_at) = X can't navigate the index because the index stores created_at. Rewrite as a half-open range, or index the expression if the pattern is legitimate, like LOWER(email)."
12. **ANALYZE** — "Collects table statistics — histograms, distinct counts — that the planner uses to estimate row counts. Stale stats produce misestimates, and misestimates produce bad join strategies."
13. **VACUUM** — "MVCC never overwrites rows — updates and deletes leave dead tuples behind. VACUUM reclaims them and maintains the visibility map that enables index-only scans. If it falls behind, tables bloat and everything degrades; a long-open transaction can block cleanup entirely."
14. **MVCC** — "Multi-Version Concurrency Control: each transaction sees a consistent snapshot of row versions, so readers never block writers and vice versa. The cost is dead tuples, which is why VACUUM exists."
15. **OFFSET vs keyset** — "OFFSET reads and throws away all skipped rows — page 2000 scans 100k rows and shifts under concurrent inserts. Keyset filters WHERE (created_at, id) < last-seen and limits — constant cost at any depth, needs a matching index, but no random page jumps."
16. **Estimated vs actual rows** — "The planner picks join strategies and memory from estimates. If it expects 100 rows and gets 2 million, it may have chosen a nested loop that now does 2 million lookups. Big gaps point to stale stats, correlated columns, or skew."
17. **Nested Loop vs Hash Join** — "Nested loop: small outer side, indexed inner side — few probes. Hash join: both sides large, equality condition — build a hash table once. The planner decides from cardinality estimates, which is why misestimates flip this choice badly."
18. **Optimistic vs pessimistic** — "Optimistic: version column, conditional update, retry on conflict — best when conflicts are rare or there's user think-time. Pessimistic: SELECT FOR UPDATE holds the row — best for frequent conflicts with short critical sections. And when it fits in one atomic UPDATE, do that instead."
19. **Deadlock** — "Two transactions each hold a lock the other wants; Postgres detects the cycle and kills one. Prevent by acquiring locks in a consistent order and keeping transactions short; the app retries the victim."
20. **Lost update** — "Two transactions read the same value, both compute and write back — the second write silently overwrites the first. Fix with an atomic UPDATE, optimistic versioning, or FOR UPDATE."
21. **Dual-write** — "No atomic transaction spans two systems: one write commits, the other fails, and they diverge silently. Timeouts make retries unsafe, and concurrent writers can apply in different orders. Keep one source of truth and derive the second via CDC or an outbox."
22. **CDC** — "Change Data Capture: read the database's transaction log and stream every committed change, in order, to another system — replication without touching application code. Debezium is the standard tooling."
23. **Outbox** — "Write the state change and the event into the same local transaction — the event goes to an outbox table — and a relay publishes it afterwards. Solves the dual-write between database and broker; delivery becomes at-least-once, so consumers must be idempotent."
24. **DB-per-service vs shared** — "Own database: autonomy, independent deploys and migrations; cost: no cross-service joins — compose via APIs, events, or read models. Shared database couples services through the schema — one ALTER TABLE can break five teams — which is exactly what this migration should start undoing."
25. **Strangler Fig** — "Incrementally route traffic away from a legacy system, domain by domain, until nothing is left — instead of a big-bang rewrite. A service-by-service database migration is the data-layer version of it."
26. **Idempotency with at-least-once** — "Retries mean duplicates are guaranteed eventually. Consumers dedupe by a message or business key — insert with ON CONFLICT DO NOTHING, or a conditional write — so a duplicate becomes a no-op."
27. **Prove two DBs match** — "Layers: row counts per time window to localize drift, business aggregates like daily SUMs, block-level checksums over normalized rows, random-sample deep comparison, and business invariants run on both sides — as a continuous reconciliation job with mismatch metrics, not a one-off check."
28. **Strategy vs Factory** — "Strategy is about interchangeable behavior behind one interface; Factory is about centralizing creation. They pair: the factory picks which strategy to hand you."
29. **Decorator vs Proxy** — "Same shape — wrap the same interface — different intent: decorator adds behavior like caching or retries; proxy controls access — laziness, authorization, remoteness."
30. **Lambda or ECS** — "Lambda for spiky, event-driven, short-lived work — pay per invocation, zero idle cost, but 15-minute limit, cold starts, limited runtime control. ECS for steady traffic, long-lived processes, custom runtimes, or when per-request cost at high volume beats it. I'd start from traffic shape and execution time."
31. **SQS vs EventBridge** — "SQS is a queue: one consumer group, buffering, retries, DLQs — work distribution. EventBridge is an event bus: many subscribers, content-based routing, third-party integrations — fan-out of facts. They compose: EventBridge routes, SQS buffers each consumer."
32. **Hot partition** — "All traffic hashing to one partition key value — a celebrity customer, or a date as partition key so today gets everything. Each partition has fixed throughput, so it throttles while the table looks underutilized. Fix by choosing a higher-cardinality key or sharding the key with a suffix."
33. **Postgres over DynamoDB** — "When access patterns are varied or unknown, when I need ad-hoc queries, joins, aggregations, and multi-row transactions — relational flexibility. DynamoDB wins for a handful of known key-based access patterns needing single-digit-millisecond latency at massive scale. The honest answer: I choose per workload, and query flexibility is usually the deciding factor."

---

## Auto-avaliação

| # | ✅/⚠️/❌ | Nota |
|---|---|---|
| ... | | |

*(Repita as ❌ em voz alta até virarem ✅.)*
