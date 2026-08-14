# 🔒 Gabarito — Aula 07 (SQL Server → Postgres + Distributed Systems + Modeling)

> **Só abra depois de tentar.**

---

## Exercício 1 — login quebrado + ordenação diferente (modelo)

> *"Both symptoms point at string comparison semantics. SQL Server's default collation is case-insensitive — `'Ana@x.com' = 'ana@X.com'` matched there; PostgreSQL is case-sensitive, so the login lookup now misses rows that differ only in casing. I'd confirm by checking the stored values' casing versus what the login sends. Fix: normalize emails on write, and make the lookup case-insensitive with an expression index on LOWER(email) — or the citext type. The report ordering is the sibling issue: collation rules for accents and case differ between the engines, so ORDER BY name sorts differently. If the old order is a real requirement, set an explicit collation; usually the answer is agreeing on the new one. The broader lesson: after this kind of migration, every string equality and every ORDER BY on text is a suspect."*

Bônus: mencionar que **keyset pagination** baseada em colunas de texto também muda de comportamento com a collation.

---

## Exercício 2 — o deadlock que sumiu

**Por quê:** no SQL Server (sem RCSI), o segundo processo **bloqueava** ao ler a row que o primeiro estava atualizando — a serialização era um efeito colateral do locking pessimista de leitura. No Postgres, MVCC: cada um lê sua **snapshot** sem bloquear, ambos calculam sobre o valor antigo, o segundo commit sobrescreve o primeiro → **lost update**. O código estava **implicitamente correto por acidente** no banco antigo.

**Duas correções (qualquer dupla vale):**
1. `SELECT ... FOR UPDATE` — restaura explicitamente a serialização que existia por acidente.
2. Optimistic concurrency — coluna `version`/`xmin` + update condicional + retry (em EF: concurrency token).
3. (Melhor quando cabe) UPDATE atômico: `SET total = total + :delta`.

**Frase de entrevista:** *"MVCC removes blocking, and with it removes accidental correctness — migrations from lock-based engines need an audit of every read-then-write path."*

---

## Exercício 3 — cadeias causais (gabarito)

**a)** retry → possible duplicate (timeout ≠ falha; a operação pode ter sido aplicada) → **idempotency**: dedup key / `ON CONFLICT DO NOTHING` / conditional write → duplicata vira no-op.

**b)** transação no DB + publish no broker → **dual-write problem** (commit de um, falha do outro) → **Transactional Outbox**: evento gravado na mesma transação local, relay publica depois → entrega at-least-once → consumer idempotente (volta para a cadeia a).

**c)** transação distribuída entre serviços → **2PC** bloqueia e não escala (coordenador é SPOF, locks presos durante a incerteza) → **Saga**: sequência de transações locais + **compensações** para desfazer.
- **Choreography**: cada serviço reage a eventos — sem coordenador, baixo acoplamento; fluxo implícito, difícil rastrear "onde parou".
- **Orchestration**: um orquestrador comanda os passos — fluxo explícito e observável; ponto central de lógica (e de falha, mitigável).
- Trade-off resumo: coreografia para fluxos curtos/estáveis, orquestração quando o fluxo é longo, ramificado ou precisa de visibilidade operacional.

---

## Exercício 4 — DDL de subscriptions

```sql
CREATE TABLE subscriptions (
    id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_id   bigint      NOT NULL REFERENCES customers(id),
    plan          text        NOT NULL,
    status        text        NOT NULL CHECK (status IN ('active','paused','cancelled')),
    started_at    timestamptz NOT NULL,
    ended_at      timestamptz,
    deleted_at    timestamptz,                -- soft delete
    created_at    timestamptz NOT NULL DEFAULT now(),
    updated_at    timestamptz NOT NULL DEFAULT now()
);

-- FK não é indexada automaticamente pelo Postgres:
CREATE INDEX idx_subs_customer ON subscriptions (customer_id);

-- A joia da questão — no máximo UMA subscription ativa por customer+plan,
-- ignorando deletadas:
CREATE UNIQUE INDEX uq_subs_one_active
    ON subscriptions (customer_id, plan)
    WHERE status = 'active' AND deleted_at IS NULL;

-- Histórico de mudanças de plano: tabela de eventos append-only
CREATE TABLE subscription_plan_changes (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    subscription_id bigint      NOT NULL REFERENCES subscriptions(id),
    old_plan        text,
    new_plan        text        NOT NULL,
    changed_at      timestamptz NOT NULL DEFAULT now(),
    changed_by      text        NOT NULL
);
CREATE INDEX idx_plan_changes_sub ON subscription_plan_changes (subscription_id, changed_at);
```

**Justificativas que a resposta devia conter:**
- Surrogate key (`identity`) como PK; nada de PK natural.
- **Índice explícito na FK** (aula 03 — Postgres não cria).
- **Partial unique index** para a regra "uma ativa" — unique constraint comum quebraria: histórico de subscriptions canceladas do mesmo plano violaria a unicidade. O `WHERE` restringe a regra ao subconjunto vivo.
- Histórico como **tabela append-only separada** (não colunas `previous_plan` na própria row).
- `timestamptz`, não `timestamp` (lição da migração).
- Audit fields em ambas.

---

## Exercício 5 — stored procedures (modelo)

> *"It's an inventory-and-triage decision, not a single answer. First I'd inventory the procedures and classify them: trivial CRUD wrappers, real business logic, and data-heavy set operations. My default is to move business logic into the services — it becomes testable, versioned, deployable, and observable like the rest of the code, and it removes a vendor-specific dialect from the critical path; T-SQL to PL/pgSQL is a rewrite anyway, so if we're rewriting, rewrite it into the right place. The exception is genuinely data-heavy set-based logic — bulk transformations over millions of rows — where dragging the data to the app would be slower and I'd port to PL/pgSQL. The risks to manage: procedures are often untested and undocumented, so each migrated one needs characterization tests comparing old and new outputs; and hidden callers — jobs, reports, other services — need to be found before anything is decommissioned. I'd also use the triage to delete the dead ones, which in legacy systems is a surprisingly large fraction."*
