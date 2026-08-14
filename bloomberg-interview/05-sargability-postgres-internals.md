# Aula 05 — Sargability + PostgreSQL Internals + Transactions

> Bloco noturno de sexta. Três temas médios num arquivo: (A) sargability, (B) internals que caem em entrevista, (C) transactions e concurrency.

---

# PARTE A — SARGABILITY

## Problem

O índice existe, a query filtra pela coluna indexada... e o plano mostra Seq Scan.

## Concept

**Sargable** (Search ARGument-able) = o predicado pode usar o índice para **navegar** na árvore. Regra prática:

> **Coluna "nua" de um lado, valor/expressão do outro.** Qualquer função, cast ou aritmética **em cima da coluna** impede o uso direto do índice, porque o índice guarda a coluna original, não o resultado da expressão.

### A galeria de crimes (reconheça todos)

```sql
-- ❌ função na coluna                          ✅ range na coluna nua
WHERE DATE(created_at) = '2026-08-13'           WHERE created_at >= '2026-08-13'
                                                  AND created_at <  '2026-08-14'

-- ❌ aritmética na coluna                      ✅ mova para o outro lado
WHERE amount * 1.1 > 100                        WHERE amount > 100 / 1.1

-- ❌ leading wildcard (não há prefixo)         ✅ prefixo usa B-tree
WHERE name LIKE '%silva'                        WHERE name LIKE 'silva%'
   (full-text / trigram index se precisar)

-- ❌ cast implícito na coluna                  ✅ tipos compatíveis
WHERE customer_code = 12345                     WHERE customer_code = '12345'
   (coluna é varchar → vira cast na coluna!)

-- ❌ função na coluna                          ✅ expression index OU coluna nua
WHERE LOWER(email) = 'x@y.com'                  CREATE INDEX ON users (LOWER(email));
                                                -- agora o predicado com LOWER() é sargable
```

**Nuance de senior:** a expressão não-sargable não quebra a query — ela quebra o **uso do índice**. E a solução nem sempre é reescrever: **expression index** transforma o predicado "criminoso" em sargable. Escolha: reescrever a query (melhor se possível) vs indexar a expressão (quando o padrão é frequente e legítimo, ex: case-insensitive email).

### Interview answer (English)

> **"Sargability is whether a predicate can use an index to navigate, rather than evaluate an expression on every row. The rule of thumb: keep the column bare on one side. `WHERE DATE(created_at) = X` forces a seq scan because the index stores created_at, not DATE(created_at) — I'd rewrite it as a half-open range. When the expression is legitimate and frequent, like LOWER(email), an expression index makes it sargable."**

---

# PARTE B — POSTGRESQL INTERNALS (nível entrevista, não DBA)

## MVCC — o conceito que explica metade do Postgres

**Problema que resolve:** leitores e escritores não se bloquearem.

**Como:** UPDATE/DELETE **nunca sobrescrevem** a row — criam uma **nova versão** e marcam a antiga com o id da transação. Cada transação enxerga o "snapshot" de versões válidas para ela. Resultado: **readers don't block writers, writers don't block readers.**

**O preço:** as versões antigas (**dead tuples**) ficam no heap ocupando espaço.

### VACUUM / autovacuum / ANALYZE (trio de rapid fire)

- **VACUUM** — recolhe dead tuples para reuso de espaço (não devolve ao SO) e atualiza o **visibility map** (que habilita Index Only Scan). Sem vacuum → **bloat**: tabela de 1M rows "vivas" ocupando espaço de 10M → tudo fica lento.
- **autovacuum** — roda VACUUM/ANALYZE automaticamente por thresholds. Cenário clássico de entrevista: tabela com **update pesado** onde o autovacuum não acompanha → bloat crescente, queries degradando lentamente. Outro: **transação longa aberta** impede o vacuum de limpar (as versões antigas ainda podem ser vistas por ela).
- **ANALYZE** — coleta **estatísticas** (histogramas, n_distinct, MCVs) que alimentam o **planner**. Estatísticas velhas = misestimates = plano ruim (conexão direta com a aula 04). Após grande carga de dados: `ANALYZE` manual.

### IDs: sequences, identity, UUID

- `GENERATED ALWAYS AS IDENTITY` = forma moderna (padrão SQL) de auto-incremento; `SERIAL` é o legado. Sequences **não são transacionais**: rollback deixa **gaps** — normal, não é bug (pergunta pegadinha comum).
- **UUID como PK:** prós — gerável no client, sem coordenação, bom para sistemas distribuídos/merge de dados. Contras — 16 bytes, e **UUIDv4 é aleatório**: inserts espalham pelo B-tree inteiro (cache ruim, páginas fragmentadas). Mitigação moderna: **UUIDv7** (ordenado por tempo). Resposta equilibrada: *"UUIDs for distributed generation, but time-ordered ones to keep index locality."*

### JSONB + GIN

- **JSONB** = JSON binário, indexável. Uso certo: atributos **semi-estruturados/esparsos** (metadata, payloads de integração). Uso errado: jogar o modelo relacional inteiro dentro de um JSONB ("schemaless por preguiça").
- **GIN index** = índice invertido para "contém": JSONB (`@>`), arrays, full-text. Trade-off: escrita mais cara que B-tree.
- Frase de entrevista: *"Relational columns for what I query and join on; JSONB for the flexible tail of attributes."*

### ON CONFLICT (upsert)

```sql
INSERT INTO inventory (sku, qty) VALUES ($1, $2)
ON CONFLICT (sku) DO UPDATE SET qty = inventory.qty + EXCLUDED.qty;
```

Atômico, sem race de "SELECT depois INSERT". Também `DO NOTHING` para **idempotência de consumo de mensagens** (conecta com seu forte: DLQ/retries — *"insert the message id with ON CONFLICT DO NOTHING; duplicates become no-ops"*).

### OFFSET vs keyset pagination 🔥 (favorita de entrevista de performance)

- `OFFSET 100000 LIMIT 20` → o banco **lê e descarta 100.000 rows** — página profunda = lenta; e páginas "andam" com inserts concorrentes.
- **Keyset (seek):**

```sql
SELECT * FROM orders
WHERE (created_at, id) < (:last_created_at, :last_id)   -- cursor da página anterior
ORDER BY created_at DESC, id DESC
LIMIT 20;
```

Custo constante em qualquer profundidade (com índice em `(created_at DESC, id DESC)`), estável sob escrita concorrente. Limitação: sem "pular para a página 47".

---

# PARTE C — TRANSACTIONS E CONCURRENCY

## ACID em uma linha cada

**A**tomicity (tudo ou nada) · **C**onsistency (constraints válidas antes→depois) · **I**solation (transações concorrentes não se corrompem) · **D**urability (commit sobrevive a crash, via WAL).

## Isolation levels e anomalias

| Nível | Dirty read | Non-repeatable read | Phantom | Notas Postgres |
|---|---|---|---|---|
| Read Committed (**default**) | não | sim | sim | cada statement vê snapshot novo |
| Repeatable Read | não | não | **não**\* | snapshot fixo da transação; \*Postgres também evita phantoms aqui |
| Serializable | não | não | não | SSI: pode abortar com serialization error → **app precisa de retry** |

- **Dirty read**: ler dado não commitado (Postgres nunca permite).
- **Non-repeatable read**: reler a mesma row e ela mudou.
- **Phantom**: refazer a mesma busca e aparecerem rows novas.

## O cenário do lost update (cai sempre)

```text
T1 reads balance = 100        T2 reads balance = 100
T1 writes 80  (100 - 20)
                              T2 writes 50  (100 - 50)   ← perdeu o débito do T1!
```

**Soluções (saiba as 4 e quando usar cada):**

1. **Atomic update** — `UPDATE accounts SET balance = balance - 20 WHERE id = ?` — a leitura e escrita viram uma operação; melhor opção quando a lógica cabe no SQL.
2. **Pessimistic** — `SELECT ... FOR UPDATE` → lock na row; T2 espera. Use quando conflito é **frequente** e a transação é curta. Custo: contention, risco de deadlock.
3. **Optimistic** — coluna `version`: `UPDATE ... SET balance = 80, version = version + 1 WHERE id = ? AND version = :read_version` → 0 rows afetadas = conflito → retry. Use quando conflito é **raro** e/ou há "think time" (usuário editando form). Em EF: concurrency token / `xmin`.
4. **Serializable** — deixa o banco detectar; app faz retry no abort.

### Interview answer (English)

> **"Optimistic concurrency assumes conflicts are rare: read a version, write back conditionally, retry on mismatch — cheap, no locks held, ideal with user think-time. Pessimistic locks the row up front with SELECT FOR UPDATE — right when conflicts are frequent and the critical section is short, at the cost of contention. And when the operation is expressible as a single atomic UPDATE, that's simpler than both."**

## Deadlocks

T1 trava row A e quer B; T2 travou B e quer A. Postgres detecta e **mata uma** das transações. Prevenção: **adquirir locks sempre na mesma ordem** (ex: ordenar ids antes de `FOR UPDATE`), transações curtas. App deve tratar o erro com retry.

---

## ✏️ Exercícios

### Exercício 1 — sargability spotting

Para cada predicado, diga: sargable? Se não, corrija (rewrite ou índice):

```sql
a) WHERE YEAR(created_at) = 2026
b) WHERE email LIKE '%@gmail.com'
c) WHERE status = 'pending'
d) WHERE CAST(order_number AS TEXT) = '12345'
e) WHERE created_at + INTERVAL '3 days' < now()
```

### Exercício 2 — VACUUM story

Responda em inglês: **"Why does PostgreSQL need VACUUM, and what happens if it falls behind?"** (30-60s, mencione MVCC, dead tuples, bloat, e o efeito de long-running transactions.)

### Exercício 3 — lost update

Dado o cenário de balance acima, o entrevistador pergunta: **"How would you prevent the lost update?"** Dê as opções com trade-offs e **escolha uma** para um sistema de pagamento com alta concorrência na mesma conta.

### Exercício 4 — pagination

Uma listagem de transactions usa `OFFSET (page-1)*50 LIMIT 50` e a página 2000 demora 12s. Explique o porquê e escreva a versão keyset (com o índice que ela precisa).

### Exercício 5 — upsert idempotente

Escreva o SQL que registra o processamento de uma mensagem SQS (`message_id`, `processed_at`) garantindo que reprocessamento de duplicata seja no-op. Explique em inglês por que isso torna o consumer idempotente.

---

## ✅ Respostas / avaliação

*(Preenchido durante a sessão interativa, depois da tentativa.)*
