# Aula 04 — Query Optimization + EXPLAIN / EXPLAIN ANALYZE 🔥 EXTREMELY HIGH PRIORITY

> "A query used to take 200ms and now takes 10 seconds. How would you investigate?" — esta aula é o framework para responder isso como senior. Inclui também N+1/ORM e os 10 cenários de troubleshooting.

---

# PARTE A — O framework de troubleshooting (DECORE — vai repetir em voz alta)

## Problem

Resposta de mid-level: "I'd add an index." Resposta de senior: um **processo estruturado** que funciona para qualquer query lenta.

## Concept — os 11 passos

1. **Measure** — confirme com dados: qual query, quanto tempo, desde quando, sempre ou às vezes? (APM, `pg_stat_statements`, logs de slow query.)
2. **Reproduce** — rode a query real, com os **parâmetros reais** (parâmetros diferentes = planos diferentes!), idealmente numa réplica.
3. **EXPLAIN** — veja o plano estimado sem executar.
4. **EXPLAIN ANALYZE** — execute e compare estimado × real.
5. **Find expensive nodes** — onde está o tempo? (o nó com maior `actual time` exclusivo.)
6. **Analyze cardinality** — `rows` estimado × `rows` real. Misestimate grande = raiz de quase tudo (join errado, sort em disco).
7. **Check indexes** — o índice esperado existe? É usado? É usável (sargability)?
8. **Check joins/sorts** — Nested Loop sobre milhões? Sort em disco (`external merge`)? Hash sem memória?
9. **Check contention** — locks, `pg_locks`, `pg_stat_activity`; a query está lenta ou **esperando**?
10. **Change ONE thing** — um índice, um rewrite, um `ANALYZE`. Uma mudança por vez.
11. **Benchmark again** — compare com a medição do passo 1.

### As causas mais comuns (checklist mental para "what would you investigate?")

- **Table growth** — a query sempre foi O(n) e n cresceu (Seq Scan que era barato).
- **Stale statistics** — tabela mudou muito, `ANALYZE` não rodou → misestimates → plano ruim.
- **Missing/unusable index** — nunca existiu, ou expressão/cast impede o uso (sargability).
- **Parameter differences** — o mesmo SQL é rápido para o customer médio e lento para o customer com 2M orders (data skew).
- **N+1** — a "query lenta" na verdade são 500 queries rápidas (ver Parte C).
- **Locks/contention** — a query espera um lock (migração rodando? transação longa aberta?).
- **Resource pressure** — CPU/IO/memória do banco; connection pool esgotado.
- **Não é o banco** — latência de rede, serialização, app. Sempre separe "DB time" de "end-to-end time".

## Interview answer (English) — a resposta de 60 segundos

> **"First I'd measure — confirm what changed and when, using pg_stat_statements or APM, and check whether it's slow for all parameters or specific ones. Then I'd reproduce it and run EXPLAIN ANALYZE. I'm looking for three things: where the time actually goes, whether estimated rows match actual rows — because a bad estimate leads the planner to a bad join strategy — and whether the expected index is being used. Common culprits are table growth turning a seq scan expensive, stale statistics, a filter that's not sargable, or lock contention rather than the query itself. Then I change one thing at a time and re-benchmark."**

---

# PARTE B — Lendo EXPLAIN / EXPLAIN ANALYZE

## Concept — os nós que você precisa reconhecer

### Nós de acesso a dados

| Nó | O que é | Quando é suspeito |
|---|---|---|
| **Seq Scan** | lê a tabela inteira | quando a query é seletiva e existe índice utilizável |
| **Index Scan** | desce o B-tree, visita o heap por row | com `loops` alto ou milhões de rows (random IO) |
| **Index Only Scan** | responde só com o índice | `Heap Fetches` alto = visibility map desatualizado (VACUUM) |
| **Bitmap Index Scan + Bitmap Heap Scan** | marca as páginas pelo índice, depois lê o heap em ordem física | meio-termo entre Index e Seq Scan; normal para seletividade média |

### Nós de JOIN — e por que cardinality estimation importa

| Nó | Ideal para | Falha típica |
|---|---|---|
| **Nested Loop** | outer **pequeno** + inner com índice | planner estimou 100 rows no outer, vieram 2M → 2M index scans |
| **Hash Join** | conjuntos grandes, sem ordem, equality join | hash não cabe em `work_mem` → spill para disco (batches) |
| **Merge Join** | ambos os lados já ordenados (índice/sort) | precisa de sort caro antes |

**Este é O insight da aula:** o planner escolhe a estratégia de join **com base nas estimativas**. `estimated rows = 100, actual = 2,000,000` → ele escolheu Nested Loop achando que faria 100 lookups, fez 2 milhões. A query não está "lenta" — está **mal planejada por estatísticas erradas**. Solução: `ANALYZE`, aumentar `default_statistics_target` da coluna, ou `CREATE STATISTICS` para colunas correlacionadas.

### Outros nós

- **Sort** — atenção a `Sort Method: external merge Disk: ...` = não coube em `work_mem`.
- **Aggregate / HashAggregate / GroupAggregate** — agregações; HashAggregate também pode spillar.

### Como ler os números

```
Nested Loop (cost=0.86..1245.10 rows=100 width=64)
            (actual time=0.05..3200.44 rows=2000000 loops=1)
```

- `cost=0.86..1245.10` → custo **estimado** (startup..total, unidade abstrata; serve para comparar).
- `rows=100` (primeiro) → **estimativa**; `rows=2000000` (actual) → realidade. **Compare sempre.**
- `actual time=0.05..3200.44` → ms reais (startup..total) **por loop**.
- `loops=847` → ⚠️ o nó executou 847 vezes; **tempo total = actual time × loops**. Inner de Nested Loop sempre tem loops alto — multiplique antes de julgar.

### Exemplo guiado — "what looks suspicious here?"

```
Nested Loop  (cost=... rows=50 ...) (actual time=0.1..9800.2 rows=1200000 loops=1)
  -> Seq Scan on customers c  (rows=50 estimated) (actual rows=48)
       Filter: (country = 'BR')
  -> Index Scan on orders o  (rows=1 estimated) (actual rows=25000 loops=48)
       Index Cond: (customer_id = c.id)
```

Leitura: estimativa do inner era 1 row por customer, vieram **25.000 por customer** (48 loops × 25k = 1.2M). O planner escolheu Nested Loop por causa dessa estimativa; um Hash Join provavelmente venceria. Investigar: estatísticas de `orders.customer_id` desatualizadas ou skew (poucos customers com milhões de orders).

---

# PARTE C — N+1 e ORM performance (Entity Framework)

## Problem

API lenta, mas cada SQL individual parece rápido. Clássico N+1: 1 query para a lista + 1 query por item.

```csharp
var customers = db.Customers.ToList();          // 1 query
foreach (var c in customers)
    Console.WriteLine(c.Orders.Count);          // N queries (lazy loading)
```

## Concept — o cardápio de soluções em EF

- **Eager loading** — `Include(c => c.Orders)`: 1 query com JOIN. ⚠️ **Why can Include be dangerous?** Fan-out: `Include(Orders).ThenInclude(Items)` multiplica rows (cartesian explosion) — o payload do banco explode. EF Core tem `AsSplitQuery()` exatamente para isso: N JOINs viram queries separadas coordenadas. **Joining everything becomes worse than multiple queries** quando o produto das coleções infla o resultado além do custo de round-trips extras.
- **Projection** — `Select(c => new { c.Name, Count = c.Orders.Count() })`: deixa o banco agregar; geralmente a melhor resposta. Só traga o que precisa.
- **Explicit loading** — `db.Entry(c).Collection(x => x.Orders).Load()`: raro, para carregar sob demanda controlada.
- **AsNoTracking** — leitura sem change tracking; menos memória/CPU para queries read-only.
- **Pagination** — nunca `ToList()` sem `Skip/Take` (e keyset para páginas profundas — aula 05).

## Interview answers (English)

> **"Why can Include be dangerous?"** → *"Because it translates to a JOIN, and joining multiple collections causes a cartesian explosion — the row count is the product of the collections, so you transfer massively duplicated data. In EF Core I'd either project only what I need with Select, or use AsSplitQuery to break it into separate queries."*

---

## ✏️ Exercícios

### Exercício 1 — pratique o framework

Sem olhar acima, escreva (em inglês, como falaria) sua resposta para:
> **"A query used to take 200ms and now takes 10 seconds. How would you investigate?"**

### Exercício 2 — leia o plano

```
Hash Join  (rows=1000 estimated) (actual time=1.2..28000.5 rows=4200000 loops=1)
  Hash Cond: (o.customer_id = c.id)
  -> Seq Scan on orders o (actual rows=4200000)
  -> Hash
      -> Seq Scan on customers c (actual rows=100000)
Sort  (actual time=28000.5..41000.0)
  Sort Method: external merge  Disk: 890MB
```

**What looks suspicious here? What would you check first?** (2 problemas distintos.)

### Exercício 3 — misestimate

> "PostgreSQL estimated 100 rows but actually returned 2 million. Why does that matter, and what would you do about it?"

Responda em inglês, cobrindo: por que a estimativa erra, qual o efeito no plano, e 2 ações concretas.

### Exercício 4 a 13 — os 10 cenários de troubleshooting (Parte 23 do curso)

Para cada um, escreva **"What would you investigate?"** em 3-6 frases (inglês). Um por vez, sem pular.

4. A query increased from 200ms to 8 seconds after the table grew from 500k to 50 million rows.
5. PostgreSQL is doing a sequential scan even though an index exists.
6. A query is using an index but is still slow.
7. CPU utilization is fine, but database latency suddenly increased.
8. A JOIN returns 100x more rows than expected.
9. PostgreSQL estimated 1,000 rows but actually returned 4 million.
10. A report query has several GROUP BY operations and sorts and takes 30 seconds.
11. API latency is high, but individual SQL queries look fast.
12. The same query is fast for most customers but takes 20 seconds for a few specific ones.
13. Query latency spikes every day at the same hour, then returns to normal.

---

## ✅ Respostas / avaliação

*(Preenchido durante a sessão interativa, depois da tentativa.)*
