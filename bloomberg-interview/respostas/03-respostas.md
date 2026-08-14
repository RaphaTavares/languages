# 🔒 Gabarito — Aula 03 (Indexes)

> **Só abra depois de tentar.** Nos exercícios de índice não existe UMA resposta certa — o que é avaliado é a justificativa. Compare seu raciocínio, não só a resposta final.

---

## Exercício 1 — equality + equality + sort

**Índice:** `CREATE INDEX ON orders (customer_id, status, created_at DESC);`

**Modelo em inglês:**

> *"Both customer_id and status are equality predicates, so they go first — together they narrow the scan to one small contiguous range of the index. created_at goes last so the index delivers rows already in the ORDER BY order; combined with LIMIT 20, the scan reads exactly 20 entries and stops. The plan goes from seq scan + sort to an index scan with no sort node. The order between the two equality columns barely matters for this query — I'd pick the one that lets the leftmost prefix serve other queries too."*

**O que derruba a resposta:** propor `(created_at, customer_id, status)` "porque ordena por data" — com `created_at` primeiro, o índice não consegue afunilar por customer; ele varreria por data filtrando row a row.

---

## Exercício 2 — equality + range

**Resposta: `(account_id, created_at)`.**

- `account_id` é **equality** → primeiro: desce direto para o bloco daquela conta; dentro dele, as entries já estão ordenadas por `created_at` → o range do mês é uma **fatia contígua**. Lê exatamente o que precisa.
- `(created_at, account_id)` inverso: o range de `created_at` vem primeiro → o índice varre **o mês inteiro de TODAS as contas** e filtra `account_id` row a row.

**Regra que este exercício prova:** depois de uma coluna usada como **range**, as colunas seguintes do índice não afinam mais a busca — só filtram. Por isso: equality primeiro, range/sort depois.

---

## Exercício 3 — status pending (1%)

**Melhor resposta: partial index.**

```sql
CREATE INDEX idx_orders_pending ON orders (created_at DESC)
WHERE status = 'pending';
```

- A query sempre filtra `status = 'pending'` (1% das rows) → o índice contém **só** esse 1%: minúsculo, quente em cache, e as entries já saem ordenadas por `created_at DESC` → `LIMIT 50` lê 50 entries e para.
- Bônus enorme de escrita: os 99% de orders que nunca são pending **não pagam** manutenção deste índice (updates de completed/cancelled não o tocam).

**Alternativa aceitável:** composite `(status, created_at DESC)` — serve também a queries de outros status. Trade-off honesto: índice ~100× maior, manutenção em toda escrita. Se só o fluxo de pendings importa, o partial vence; se há queries iguais para outros status, o composite. **Dizer esse trade-off em voz alta é a resposta de senior.**

---

## Exercício 4 — LOWER(email)

O índice em `email` indexa o **valor original**; o predicado é sobre `LOWER(email)` — uma expressão — então o índice não serve para navegar (não-sargable). Soluções:

1. **Expression index:** `CREATE INDEX ON users (LOWER(email));` → o predicado `LOWER(email) = LOWER(?)` vira sargable.
2. **`citext`** para a coluna (case-insensitive por tipo) — mais invasivo, mas resolve na raiz.
3. Normalizar no write (armazenar sempre lowercase + constraint) — resolve para sempre, exige migração dos dados.

Em entrevista, cite a 1 como fix imediato e a 3 como fix estrutural.

---

## Exercício 5 — "why is Postgres ignoring the index?" (modelo)

> *"It's not a bug — it's the cost model working correctly. The predicate matches 92% of a 50-million-row table. Following the index would mean ~46 million random heap accesses, while a sequential scan reads the table in order, which is far cheaper per page. An index only pays off when the predicate is selective. If the queries we actually care about are the rare statuses, I'd create a partial index for those — `WHERE status IN ('pending', 'failed')` — instead of a full index on status, which is mostly dead weight and write overhead."*

---

## Exercício 6 — DELETE lento no pai

**Suspeita:** `orders.customer_id` é FK **sem índice**. O Postgres não indexa FKs automaticamente — ao deletar um customer, a verificação referencial (ou o `ON DELETE CASCADE`) precisa achar as orders daquele customer → **Seq Scan em orders a cada delete**.

**Como confirmar:**
1. `EXPLAIN ANALYZE` do DELETE — o tempo aparece nos **triggers de FK** (`Trigger for constraint ... time=...`).
2. Conferir índices: `\d orders` / consultar `pg_indexes` — não haverá índice começando por `customer_id`.

**Fix:** `CREATE INDEX CONCURRENTLY ON orders (customer_id);` (CONCURRENTLY para não travar escrita em produção — mencionar isso vale ponto).

---

## Exercício 7 — 5 índices numa tabela de ingestão (modelo)

> *"I'd push back on the write cost: at 20k inserts per second, five extra indexes mean five extra index maintenances per insert, plus WAL — that can easily halve ingestion throughput, and the reports run once a day. Alternatives, in order: run the reports on a read replica, so the primary keeps zero extra indexes; build a nightly pre-aggregated summary table — reports read that instead of raw events; if the reports filter by time on an append-only table, a BRIN index on the timestamp is nearly free to maintain and tiny; and if some index does prove necessary, create it CONCURRENTLY and measure ingestion impact before and after. I'd only accept the B-tree indexes that a measured, recurring query justifies."*

Elementos esperados: custo de escrita quantificado, réplica, pré-agregação, BRIN (diferencial), medir antes/depois.
