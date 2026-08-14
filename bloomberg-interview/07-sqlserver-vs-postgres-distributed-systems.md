# Aula 07 — SQL Server → PostgreSQL: diferenças práticas + Distributed Systems + Data Modeling

> Três blocos: (A) as pegadinhas técnicas da migração (Parte 15), (B) revisão conectada de distributed systems — seu ponto forte, só afiar vocabulário (Parte 16), (C) data modeling (Parte 10).

*Assumo SQL Server como origem (mais comum em stack .NET legado). Se na entrevista for outro banco, os princípios se mantêm.*

---

# PARTE A — SQL Server → PostgreSQL: o mapa de minas

## Tipos de dados

| SQL Server | PostgreSQL | Pegadinha |
|---|---|---|
| `NVARCHAR / VARCHAR` | `text` / `varchar` | Postgres é UTF-8 nativo; sem distinção N/varchar |
| `DATETIME` | `timestamp` | DATETIME tem precisão de ~3.33ms → valores podem **arredondar diferente** |
| `DATETIME2 / DATETIMEOFFSET` | `timestamp` / **`timestamptz`** | ⚠️ decidir timezone AGORA: `timestamptz` armazena UTC e converte; migrar datetime "naive" sem saber o fuso original = corrupção silenciosa |
| `UNIQUEIDENTIFIER` | `uuid` | ok, mas cuidado com formatação em comparações string |
| `BIT` | `boolean` | `1/0` → `true/false`; queries `WHERE flag = 1` quebram |
| `MONEY / DECIMAL` | `numeric` | conferir precisão/escala; nunca float para dinheiro |
| `IDENTITY` | `GENERATED AS IDENTITY` / sequences | ⚠️ **ressincronizar a sequence após backfill**: `setval('orders_id_seq', (SELECT MAX(id) FROM orders))` — esquecer = violação de PK no primeiro insert |

## Comportamento — as diferenças que quebram em produção

1. **Case sensitivity** 🔥 — SQL Server default é **case-INsensitive** (`'ANA' = 'ana'`); Postgres é **case-sensitive**. Logins, buscas e joins por string mudam de resultado **silenciosamente**. Soluções: `citext`, ou `LOWER()` + expression index. **Cite esta primeiro em "what would you investigate?" — é a mais traiçoeira.**
2. **Collation / sort order** — `ORDER BY name` pode ordenar diferente (acentos, maiúsculas). Relatórios e paginação keyset mudam de ordem.
3. **Locking model** 🔥 — SQL Server (sem RCSI): **readers block writers e vice-versa**. Postgres MVCC: nunca. Consequências: (a) deadlocks que "sumiram" — bom; (b) código que **dependia** de leitura bloqueante para correção agora tem race conditions — precisa de `SELECT FOR UPDATE` explícito; (c) `NOLOCK` hints não existem/não fazem nada.
4. **Stored procedures / T-SQL** — T-SQL ≠ PL/pgSQL: reescrita, não tradução. Decisão de senior: **migrar a lógica para o application layer** quando possível (testável, versionável) e manter em PL/pgSQL só o que é intrinsecamente data-heavy. Em entrevista, trate "how do you migrate stored procedures?" como questão de **inventário e priorização**: listar, classificar (trivial / reescrever / repensar), e usar a migração como chance de pagar dívida.
5. **Triggers** — mesmos problemas; inventariar cedo, porque CDC + triggers no destino podem **disparar duas vezes** a mesma lógica.

## Sintaxe — tradução rápida

| SQL Server | PostgreSQL |
|---|---|
| `SELECT TOP 10 ...` | `... LIMIT 10` |
| `GETDATE()` | `now()` |
| `ISNULL(a, b)` | `COALESCE(a, b)` |
| `SCOPE_IDENTITY()` | `INSERT ... RETURNING id` (melhor!) |
| `MERGE` | `INSERT ... ON CONFLICT` (ou `MERGE` no PG15+) |
| `OFFSET/FETCH` | `LIMIT/OFFSET` (e keyset para profundidade) |
| `[colchetes]` | `"aspas duplas"` ⚠️ identificadores sem aspas viram **lowercase** |
| `+` para concat string | `\|\|` (`+` com NULL/tipos dá erro) |

## Exercício-tipo da entrevista

> **"This query works in the old database but behaves differently in PostgreSQL. What would you investigate?"**

Checklist mental de resposta: (1) case sensitivity/collation em comparações e ORDER BY de strings; (2) tipos — bit vs boolean, datetime precision, timezone; (3) NULL semantics em concat/aritmética; (4) locking esperado que sumiu; (5) identifier casing; (6) diferenças de planner (a mesma query com plano diferente).

---

# PARTE B — Distributed Systems (revisão conectada — você já domina, afie o vocabulário)

O formato aqui é o das **cadeias causais** — é assim que se demonstra profundidade em entrevista:

```text
retry ──► possible duplicate ──► idempotency (keys / ON CONFLICT DO NOTHING / conditional writes)

DB transaction + publish event ──► dual-write problem ──► Transactional Outbox ──► relay ──► at-least-once ──► consumer idempotente

sync call chain ──► latência acoplada + falha em cascata ──► async messaging ──► eventual consistency ──► read-your-writes concerns

falha repetida no consumer ──► retries com exponential backoff + jitter ──► esgotou ──► DLQ ──► alerta + replay manual

dependência instável ──► Circuit Breaker (fecha o bico rápido, half-open para testar) ──► fallback/degradação

transação distribuída entre serviços ──► 2PC não escala/bloqueia ──► Saga: sequência de transações locais + compensações
   ├─ Choreography: eventos, sem coordenador — simples, mas fluxo implícito (difícil de rastrear)
   └─ Orchestration: coordenador explícito — fluxo visível, mas ponto central

monolito/legado ──► Strangler Fig: fatiar por domínio, rotear tráfego incrementalmente, estrangular o antigo
   └─ (a migração de banco da vaga É um Strangler Fig de dados)

database-per-service ──► autonomia, deploy independente, migração isolada
   └─ custo: sem JOINs cross-service ──► composição via API, eventos, CQRS/read models
shared database ──► acoplamento por schema: um ALTER TABLE quebra N serviços — é o que a vaga quer desfazer
```

**Dica de entrevista:** sempre que citar um pattern, cite o problema que o motiva e o novo problema que ele cria. Ex.: *"The outbox gives me atomicity between state change and event, at the cost of at-least-once delivery — so consumers must be idempotent."*

---

# PARTE C — Data Modeling (Parte 10 — nível revisão)

- **Normalization** — eliminar redundância; 3NF como default de OLTP. **Denormalization** — duplicação **deliberada e justificada por leitura** (contadores, colunas snapshot tipo `unit_price` na order — que aliás é *correto* semanticamente: preço no momento da compra).
- **Surrogate keys** (id numérico/uuid) como PK default; **natural keys** (email, CPF) como UNIQUE constraint, não PK — porque mudam, e PK que muda propaga por todas as FKs.
- **Relacionamentos**: 1-1 (mesma tabela ou tabela satélite para colunas raras/pesadas); 1-N (FK no lado N + **índice na FK!**); N-N (tabela de junção com PK composta `(a_id, b_id)` + índice no reverso `(b_id, a_id)`).
- **Soft delete** — `deleted_at timestamptz NULL`. Custos que um senior menciona: todo query precisa do filtro (view ou EF global query filter), UNIQUE constraints quebram (email do deletado bloqueia recadastro → **partial unique index** `WHERE deleted_at IS NULL` — resposta que impressiona), tabelas só crescem.
- **Audit fields** — `created_at`, `updated_at`, `created_by`, `updated_by` em tudo; barato agora, impagável depois. Histórico completo → audit table ou event sourcing.
- **Schema evolution** — migrations versionadas (EF Migrations/Flyway); padrão **expand → migrate → contract** para mudanças sem downtime (adicionar coluna nova → dupla escrita/backfill → remover a antiga). ⚠️ Postgres: `ALTER TABLE ADD COLUMN` com default é barato (PG11+), mas `NOT NULL` em tabela grande valida tudo — fazer em etapas.

---

## ✏️ Exercícios

### Exercício 1 — a query que mudou de comportamento

> Depois da migração, o endpoint de login parou de encontrar usuários que existem, e um relatório passou a ordenar nomes diferente. **What would you investigate?** (inglês, estruturado)

### Exercício 2 — o deadlock que sumiu (e a race que apareceu)

No SQL Server, dois processos que atualizavam o mesmo pedido se serializavam "sozinhos". No Postgres, ambos executam e um update se perde. Explique **por quê** (modelo de locking) e **duas** correções possíveis.

### Exercício 3 — cadeias causais de memória

Sem olhar a Parte B, escreva as cadeias: (a) retry → ... → idempotency; (b) transaction + event → ... → outbox; (c) 2PC → ... → saga (com os dois sabores e o trade-off de cada).

### Exercício 4 — modeling sob fogo

Modele `subscriptions`: um customer tem N subscriptions, cada uma com plano, status, período; precisa de histórico de mudanças de plano e soft delete. Escreva o DDL (Postgres) com PKs, FKs, constraints e **os índices com justificativa**. Inclua o partial unique index que impede duas subscriptions ativas do mesmo plano por customer.

### Exercício 5 — interview question

> **"Would you migrate the stored procedures to PL/pgSQL or move the logic to the services? Walk me through your decision."** (inglês, 60-90s, trade-offs dos dois lados)

---

## ✅ Respostas / avaliação

*(Preenchido durante a sessão interativa, depois da tentativa.)*
