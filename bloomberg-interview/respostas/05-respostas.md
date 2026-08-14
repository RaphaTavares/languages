# 🔒 Gabarito — Aula 05 (Sargability + Internals + Concurrency)

> **Só abra depois de tentar.**

---

## Exercício 1 — sargability spotting

**a) `WHERE YEAR(created_at) = 2026`** — ❌ não-sargable (função na coluna; em Postgres seria `EXTRACT`/`date_part`, mesmo problema). ✅ Rewrite em range meio-aberto:
```sql
WHERE created_at >= '2026-01-01' AND created_at < '2027-01-01'
```

**b) `WHERE email LIKE '%@gmail.com'`** — ❌ leading wildcard: B-tree navega por prefixo, e não há prefixo. Opções: trigram index (`pg_trgm` + GIN) se a busca for legítima e frequente; ou **modelar melhor** — coluna `email_domain` extraída no write, com índice B-tree normal (resposta de senior: mudar o dado, não heroísmo no índice).

**c) `WHERE status = 'pending'`** — ✅ sargable. O problema aqui é outro: **seletividade**. Se pending é raro → partial index; se é a maioria → Seq Scan correto. (Pegadinha: sargable ≠ vai usar índice.)

**d) `WHERE CAST(order_number AS TEXT) = '12345'`** — ❌ cast na coluna. Compare no tipo nativo: `WHERE order_number = 12345`. Atenção ao caso inverso (coluna varchar comparada com número): o cast implícito cai **na coluna** e mata o índice silenciosamente.

**e) `WHERE created_at + INTERVAL '3 days' < now()`** — ❌ aritmética na coluna. Mova para o outro lado:
```sql
WHERE created_at < now() - INTERVAL '3 days'
```

---

## Exercício 2 — VACUUM (modelo)

> *"PostgreSQL uses MVCC: updates and deletes never overwrite a row — they create a new version and leave the old one behind as a dead tuple, so readers never block writers. VACUUM is the garbage collector for those dead tuples: it reclaims the space for reuse and maintains the visibility map that makes index-only scans possible. If it falls behind, tables and indexes bloat — a table with one million live rows can occupy the space of ten million — so every scan reads mostly garbage and performance degrades slowly and mysteriously. Two classic failure modes: an update-heavy table where autovacuum can't keep up, and a long-running transaction that pins old versions, because VACUUM can't remove what some snapshot might still see."*

Elementos obrigatórios: MVCC/versões → dead tuples → bloat → visibility map → long transaction segurando cleanup.

---

## Exercício 3 — lost update

As quatro opções (todas deviam aparecer):

1. **Atomic UPDATE** — `UPDATE accounts SET balance = balance - 20 WHERE id = ? AND balance >= 20` — leitura+escrita numa operação; o `AND balance >= 20` ainda protege contra saldo negativo (verifique rows afetadas).
2. **Pessimistic** — `SELECT ... FOR UPDATE` antes de calcular; o segundo espera. Para lógica complexa que não cabe num UPDATE.
3. **Optimistic** — coluna `version` + update condicional + retry.
4. **Serializable** — o banco detecta; a app faz retry do abort.

**Escolha para pagamento com alta concorrência na mesma conta (modelo):**

> *"For a hot account, I'd make the operation a single atomic UPDATE with the invariant in the WHERE clause — it holds the row lock for microseconds and can't lose updates. Optimistic locking would thrash here: high contention means constant version conflicts and retries. If the business logic around the debit is too complex for one statement, then SELECT FOR UPDATE in a short transaction. And at real scale I'd consider an insert-only ledger — append transactions, derive the balance — which removes the update contention entirely."*

(A menção ao ledger é o toque staff-level.)

---

## Exercício 4 — pagination

**Por quê:** `OFFSET 99950` obriga o banco a **produzir e descartar 99.950 rows** antes de devolver 50 — custo cresce linearmente com a página. Além disso, inserts concorrentes deslocam as páginas (itens repetidos/pulados).

**Keyset:**

```sql
SELECT *
FROM transactions
WHERE account_id = :account_id
  AND (created_at, id) < (:last_created_at, :last_id)
ORDER BY created_at DESC, id DESC
LIMIT 50;
```

**Índice necessário:** `(account_id, created_at DESC, id DESC)` — equality primeiro, depois as colunas do cursor na ordem do ORDER BY. Primeira página: mesma query sem o predicado do cursor. Trade-off a citar: não há "pular para a página N" — para scroll infinito/API cursors, irrelevante.

---

## Exercício 5 — upsert idempotente

```sql
INSERT INTO processed_messages (message_id, processed_at)
VALUES (:message_id, now())
ON CONFLICT (message_id) DO NOTHING;
```

Uso correto: **na mesma transação** dos efeitos do processamento — se o INSERT reportar 0 rows (conflito), a mensagem já foi processada → ack e sai sem efeitos; se inseriu, processa e commita tudo junto.

**Modelo em inglês:**

> *"SQS is at-least-once, so duplicates are guaranteed eventually. I record the message id in a dedup table in the same transaction as the side effects. ON CONFLICT DO NOTHING makes the insert atomic — no race between check and insert. A redelivered message hits the conflict, we skip the work and just ack. Either the whole transaction commits — effects plus the dedup record — or none of it does, so a crash mid-processing is also safe: the message comes back and is processed cleanly."*

O detalhe que separa senior: **dedup record e efeitos na MESMA transação** (senão crash entre os dois quebra a garantia).
