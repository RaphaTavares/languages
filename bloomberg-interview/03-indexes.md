# Aula 03 — Indexes 🔥 EXTREMELY HIGH PRIORITY

> A pergunta "which index would you create, and why?" é quase garantida. O objetivo desta aula é você ter um **framework de raciocínio**, não regras decoradas.

---

## Problem

```sql
SELECT * FROM orders WHERE customer_id = 42;
```

Sem índice, o Postgres lê **a tabela inteira** (Seq Scan) — 50 milhões de rows para achar 20. Índice = estrutura auxiliar ordenada que permite pular direto para as rows relevantes.

## Concept

### B-tree (o índice default e o único que importa dominar)

- Árvore balanceada ordenada pelas colunas do índice. Busca = descer a árvore (~3-4 níveis mesmo com milhões de rows), depois ler as rows correspondentes na tabela (heap).
- Serve para: `=`, `<`, `>`, `BETWEEN`, `IN`, `ORDER BY` compatível, `LIKE 'abc%'` (prefixo).
- Cada entrada do índice aponta para a row no heap → um Index Scan faz **2 leituras lógicas**: índice + heap. Por isso índice não é grátis.

### Seq Scan não é sempre ruim (resposta de senior)

Se a query vai retornar **30% da tabela**, seguir o índice significa milhões de saltos aleatórios no heap — ler tudo sequencialmente é mais barato. O planner decide por custo estimado. **Seq Scan em query seletiva = suspeito. Seq Scan em query que lê a tabela quase toda = correto.**

### Selectivity e cardinality

- **Cardinality**: quantos valores distintos a coluna tem (`status` → 3; `customer_id` → milhões).
- **Selectivity**: fração de rows que o predicado retorna. `WHERE id = 42` → altíssima seletividade. `WHERE status = 'completed'` quando 90% é completed → péssima.
- Índice vale a pena quando o predicado é **seletivo**. Índice em coluna booleana quase nunca ajuda sozinho (mas veja partial index abaixo).

### Composite index — o coração da pergunta de entrevista

`CREATE INDEX ON orders (customer_id, created_at)` = entradas ordenadas por `customer_id`, e **dentro de cada customer_id**, por `created_at`. Como uma lista telefônica: sobrenome, depois nome.

**Regra do leftmost prefix:** o índice serve para `(customer_id)` e `(customer_id, created_at)`, mas **não** serve (bem) para busca só por `created_at`.

### Framework para "which index?" (DECORE ESTE RACIOCÍNIO)

Para cada query, liste na ordem:

1. **Equality predicates** (`col = ?`) → candidatas às **primeiras** posições do índice.
2. **Range predicates** (`>, <, BETWEEN`) → depois das equalities. ⚠️ Após uma coluna usada em range, as colunas seguintes do índice **não afinam mais a busca** (só filtram).
3. **ORDER BY / sort** → se as colunas de ordenação vierem logo após as equalities, o índice entrega as rows **já ordenadas** e elimina o Sort — crucial com `LIMIT` (para de ler após N rows!).
4. **Selectivity real** dos predicados — vale colocar uma coluna pouco seletiva primeiro? Às vezes sim, se ela é equality e permite que a próxima coluna sirva ao ORDER BY.
5. **Query frequency e write load** — índice perfeito para query rara numa tabela com escrita pesada pode ser um mau negócio.
6. **Índices existentes** — dá para estender um em vez de criar outro?

**Exemplo canônico:**

```sql
SELECT * FROM orders
WHERE customer_id = ? AND status = ?
ORDER BY created_at DESC
LIMIT 20;
```

Índice forte: `(customer_id, status, created_at DESC)` — equalities primeiro (a ordem entre `customer_id` e `status` aqui importa pouco, ambas são equality), e `created_at` por último serve ao ORDER BY: o Postgres desce até o grupo `(customer_id, status)`, lê **20 entradas já ordenadas** e para. Sem sort, sem ler rows extras.

> ⚠️ **Anti-regra:** "always put the highest-cardinality column first" é simplista. A ordem certa vem de: equality → range/sort, e do conjunto de queries que o índice precisa servir (leftmost prefix reutilizável).

### Variações que valem pontos na entrevista

- **Covering index / INCLUDE**: `CREATE INDEX ON orders (customer_id) INCLUDE (amount, status)` → se todas as colunas do SELECT estão no índice, o Postgres faz **Index Only Scan** (não visita o heap). ⚠️ Depende do **visibility map**: em tabela com muitas escritas recentes / sem VACUUM, ainda visita o heap ("Heap Fetches" no plano).
- **Partial index**: `CREATE INDEX ON orders (created_at) WHERE status = 'pending'` → índice pequeno e barato quando as queries sempre filtram um subconjunto (ex: 1% de pendings numa tabela de 50M). Excelente resposta para colunas de baixa cardinalidade.
- **Expression index**: `CREATE INDEX ON users (LOWER(email))` → necessário quando a query filtra por expressão (`WHERE LOWER(email) = ?`). Conecta com sargability (aula 05).
- **Unique index**: constraint + índice num só; é como PK e UNIQUE são implementados.
- **FKs**: ⚠️ **PostgreSQL NÃO cria índice automaticamente em coluna de foreign key** (só no lado da PK/unique). FK sem índice → JOINs lentos e **DELETE no pai faz Seq Scan no filho**. Item de checklist clássico de migração.

### O custo dos índices (sempre mencione — é o que separa senior)

- **Write overhead**: cada INSERT/UPDATE/DELETE atualiza **todos** os índices da tabela. 8 índices = 8 escritas extras + WAL.
- **UPDATE detalhe Postgres**: por MVCC, um UPDATE cria uma nova versão da row; se a nova versão não cabe na mesma página, todos os índices precisam de nova entrada (HOT update evita isso quando nenhuma coluna indexada mudou — motivo para **não indexar colunas que mudam à toa**).
- **Storage**: índices podem ocupar mais que a própria tabela.
- **Maintenance**: bloat com o tempo; `REINDEX CONCURRENTLY` em janelas de manutenção; índices **não usados** (ver `pg_stat_user_indexes`) devem ser removidos.

## Interview answer (English) — resposta-modelo para "how do you decide on an index?"

> **"I start from the actual query patterns, not from the table. I list the predicates: equality filters go first in a composite index, then the range or the ORDER BY columns — because after a range column the index can't narrow further. If the query has ORDER BY + LIMIT, getting the sort order from the index is often the biggest win, since the scan can stop after N rows. Then I sanity-check selectivity — an index that matches half the table won't be used — and I weigh the write overhead, because every index taxes every insert and update. Finally I'd confirm with EXPLAIN ANALYZE before and after."**

---

## ✏️ Exercícios — "Which index would you consider, and why?"

Para cada um: proponha o índice (colunas, ordem, tipo), justifique com o framework, e diga o que mudaria no plano de execução.

### Exercício 1

```sql
SELECT * FROM orders
WHERE customer_id = ?
AND status = ?
ORDER BY created_at DESC
LIMIT 20;
```

(Sim, é o exemplo da aula — reescreva a justificativa **com suas palavras, em inglês**, sem olhar.)

### Exercício 2 — equality + range

```sql
SELECT * FROM transactions
WHERE account_id = ?
AND created_at >= '2026-01-01' AND created_at < '2026-02-01';
```

Índice `(created_at, account_id)` ou `(account_id, created_at)`? Por quê? O que acontece com a coluna que vem **depois** do range?

### Exercício 3 — a pegadinha do ORDER BY global

```sql
SELECT * FROM orders
WHERE status = 'pending'
ORDER BY created_at DESC
LIMIT 50;
```

`status` tem 3 valores; 1% das rows são pending. Considere: composite index? Partial index? Qual e por quê?

### Exercício 4 — busca case-insensitive

```sql
SELECT * FROM users WHERE LOWER(email) = LOWER(?);
```

Existe índice em `email`, mas o plano mostra Seq Scan. Por quê, e o que você faria?

### Exercício 5 — o índice que não é usado

Tabela `orders` com 50M rows, índice em `(status)`. A query `WHERE status = 'completed'` (92% das rows) faz Seq Scan. O entrevistador pergunta: **"the index exists, why is Postgres ignoring it? Is that a bug?"** Responda em inglês.

### Exercício 6 — DELETE lento no pai

`DELETE FROM customers WHERE id = ?` está demorando segundos. `orders.customer_id` é FK para `customers.id`. O que você suspeita e como confirma?

### Exercício 7 — trade-off de escrita

Um colega propõe adicionar 5 índices em `events` (tabela de ingestão com 20k inserts/s) para acelerar relatórios que rodam 1x/dia. Responda em inglês: **what would you push back on, and what alternatives would you offer?**

---

## ✅ Respostas / avaliação

*(Preenchido durante a sessão interativa, depois da tentativa.)*
