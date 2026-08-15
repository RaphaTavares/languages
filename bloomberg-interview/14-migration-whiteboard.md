# Aula 14 — A Migração no Whiteboard 🔥🔥 (o desenho completo)

> Este arquivo é o que você desenharia e falaria numa entrevista de system design com o cenário da vaga: **"~10 legacy microservices on one SQL database → PostgreSQL, minimal downtime."** Ordem de apresentação, diagramas, serviços AWS, e ONDE cada architectural pattern (aula 13) entra. Treine desenhando você mesmo num papel, sem olhar.

---

## 🎬 O roteiro de apresentação (a ordem em que você fala e desenha)

1. **Clarify** (2-3 min) — perguntas antes de desenhar. *Nunca pule.*
2. **Current state** — desenhe o problema.
3. **Target state** — desenhe onde queremos chegar.
4. **Migration machinery** — o pipeline de dados (backfill + CDC).
5. **Cutover de UM serviço** — o zoom que mostra profundidade.
6. **Validação** — reconciliation + shadow reads.
7. **Rollback** — reverse replication.
8. **Operação** — métricas, alarmes, failure handling.
9. **Riscos e trade-offs** — fale você, antes que perguntem.

---

## 1️⃣ CLARIFY — as perguntas (resumo da aula 06)

Fale em inglês, agrupado:

> *"Three groups of questions before I draw: **Coupling** — do the ten services own separate schemas or share tables? Can all of them be modified? **Constraints** — acceptable downtime, dataset size, write throughput, rollback requirement. **Legacy surface** — which engine, and how much logic lives in stored procedures and triggers?"*

**Assuma em voz alta** (para poder prosseguir): *"I'll assume SQL Server, schemas mostly per-service with a couple of shared tables, hundreds of GB, low-minutes downtime budget, and rollback required for days after cutover."* — Explicitar premissas é sinal de senior.

---

## 2️⃣ CURRENT STATE — o problema no quadro

```text
                        ┌──────────────────────────────┐
   Clients ──► ALB ──►  │  10 microservices (ECS)      │
                        │  svc-orders  svc-payments    │
                        │  svc-users   svc-billing ... │
                        └───────┬──────────┬───────────┘
                                │          │
                                ▼          ▼
                        ┌──────────────────────────────┐
                        │      LEGACY SQL SERVER       │   ← single shared DB
                        │  orders │ payments │ users…  │   ← schemas + algumas
                        │  stored procs, triggers      │      tabelas COMPARTILHADAS
                        └──────────────────────────────┘
```

O que você FALA apontando para o desenho:

> *"The real problem isn't the engine — it's that one database couples ten services: shared schema, shared failures, shared scaling ceiling, and vendor lock-in in the procs. The migration is also an opportunity to fix ownership."*

**Pattern citado aqui:** shared database = anti-pattern de acoplamento (aula 07); a migração é um **Strangler Fig de dados**.

---

## 3️⃣ TARGET STATE

```text
   Clients ──► ALB ──► 10 microservices (ECS)
                          │        │        │
                          ▼        ▼        ▼
                     ┌────────┐ ┌────────┐ ┌────────┐
                     │ PG:    │ │ PG:    │ │ PG:    │     RDS/Aurora PostgreSQL
                     │ orders │ │payments│ │ users  │ ... (1 DB ou 1 schema por
                     └────┬───┘ └───┬────┘ └────────┘      serviço — OWNERSHIP claro)
                          │         │
                          ▼         ▼
                     [outbox]   [outbox]  ──► relay ──► EventBridge/SNS ──► SQS ──► consumers
                                                        (integração por EVENTOS,
                                                         não por JOIN no banco)
```

O que você fala:

> *"Target: each service owns its data — at minimum its own schema, ideally its own database. Cross-service data needs are served by events and read models, not by reaching into someone else's tables."*

**Patterns citados:** database-per-service; **Transactional Outbox** para eventos; **CQRS + Materialized View** para as leituras compostas que hoje eram JOINs cross-schema (este é O ponto que resolve "mas como vou juntar orders com payments sem o banco único?").

---

## 4️⃣ MIGRATION MACHINERY — o pipeline (o coração do desenho)

```text
     writes continuam no legado (single source of truth)
                     │
                     ▼
      ┌─────────────────────────────┐
      │       LEGACY SQL SERVER      │
      └──────┬───────────────┬──────┘
             │               │
   (1) BACKFILL         (2) CDC (transaction log)
   AWS DMS full-load    DMS ongoing replication
   (ou export/import)   (ou Debezium em ECS → MSK/Kinesis)
             │               │
             ▼               ▼
      ┌─────────────────────────────┐
      │    PostgreSQL (RDS/Aurora)   │   ← réplica derivada, converge até lag≈0
      └─────────────────────────────┘
             ▲
             │ (3) RECONCILIATION (contínuo)
      ┌──────┴──────────────────────┐
      │ reconciler (Lambda agendada │ → mismatch metrics → CloudWatch
      │ / ECS task): counts,        │   dashboard + alarmes
      │ checksums, invariants       │
      └─────────────────────────────┘
```

O que você fala, na ordem dos números:

> *"(1) Backfill: DMS full-load copies history — days if needed, no pressure on prod. (2) CDC tails the transaction log and streams every committed change, in order — the legacy DB stays the single source of truth, services are untouched. (3) A continuous reconciler compares counts, block checksums and business invariants, publishing mismatch metrics — that metric is my objective cutover criterion."*

**Decisões AWS para citar se perguntarem:**
- **DMS**: gerenciado, resolve full-load + CDC + conversão de tipos (com Schema Conversion Tool para DDL/procs). Limitações: transformações complexas, observabilidade.
- **Debezium (ECS) + MSK/Kinesis**: mais controle, eventos reutilizáveis (podem alimentar consumers de negócio depois!), mais infra para operar.
- Resposta segura: *"I'd start with DMS for the bulk mechanics and reach for Debezium where I need the change stream as a first-class event feed."*

**Patterns citados:** CDC; single source of truth; **por que NÃO dual-write no app** → recite os 3 argumentos (partial failure, timeout≠falha, ordering) — aula 06/13.

---

## 5️⃣ CUTOVER DE UM SERVIÇO — o zoom (aqui você ganha a entrevista)

Desenhe a sequência como timeline:

```text
  svc-orders (exemplo)                          feature flag: AWS AppConfig
─────────────────────────────────────────────────────────────────────────►
 FASE A          FASE B              FASE C           FASE D        FASE E
 backfill+CDC    SHADOW READS        CANARY reads     writes flip   cleanup
 (lag→0)         lê dos 2, responde  1%→10%→50%→100%  reverse CDC   desligar
                 legado, COMPARA,    das leituras     LIGADO ANTES; reverse CDC,
                 emite mismatch      no PG (flag)     pausa curta   remover flags,
                 metric              (métricas p99,   de writes,    ACL e shadow
                                     errors vs base)  drena lag,    code
                                                      flip
```

Detalhes que você narra em cada fase:

- **FASE B — Shadow reads:** *"The service reads both, serves from legacy, diffs the results and emits a mismatch metric. This validates with real production queries — including the ORDER BY/collation surprises — at zero user risk."* (**Pattern:** parallel run / shadow traffic.)
- **FASE C — Canary de reads:** flag no **AppConfig** (ou LaunchDarkly) move % das leituras para o PG, comparando p99/error rate/mismatch. Regressão → flag off, rollback em segundos. (**Pattern:** Canary Release — diga explicitamente *"the cutover is a canary deployment where the 'new version' is a database."*)
- **FASE D — Writes flip:** *"Reverse CDC — Postgres back to legacy — is switched on BEFORE the write flip. Then: pause writes for seconds, drain the residual lag, flip the flag. 'Minimal downtime' honestly means a seconds-long write pause per service, not literal zero."*
- **Acesso ao legado durante a transição:** onde o serviço novo ainda precisa ler dados de outros serviços não migrados, ele passa por uma **Anti-Corruption Layer** — *"the domain never learns the legacy schema; the ACL dies with the legacy DB."*
- **Stored procedures deste serviço:** triagem (CRUD → app; set-based pesado → PL/pgSQL) com characterization tests — aula 07.

**Ordem dos 10 serviços:** *"Start with the lowest-risk, least-coupled service to debug the machinery, then climb the risk ladder; shared tables go last — after fixing ownership (one writer, others via API/events) or as one coordinated unit."*

---

## 6️⃣ VALIDAÇÃO — como eu PROVO que está certo

Camadas (aula 06, resumidas para o quadro):

```text
row counts (por janela de tempo)      ← barato, localiza drift
   └► aggregates de negócio (SUM/dia) ← pega truncamento e updates perdidos
       └► checksums por bloco de PKs  ← conteúdo em escala (rows NORMALIZADAS:
           (drill-down binário)          timezone, precisão, collation!)
           └► sampling coluna a coluna
               └► business invariants nos DOIS lados
                   └► shadow reads = validação com queries reais
```

Tudo publicado como **mismatch metrics** no CloudWatch; **critério de cutover objetivo**: *"mismatch ≈ 0 sustained for N days"*. Mismatches na cauda = lag esperado → compare com corte de tempo.

---

## 7️⃣ ROLLBACK — desenhado antes, não improvisado

```text
   PG (agora fonte de verdade p/ svc-orders)
        │ reverse CDC (Debezium/DMS PG→legacy)
        ▼
   LEGACY continua ATUALIZADO ──► rollback = flag flip de volta, SEM perda,
                                  mesmo dias depois do cutover
```

> *"Rollback is a feature we build, with an explicit expiry: reverse replication runs for, say, two weeks after each cutover; turning it off is a deliberate, announced decision — that's when the migration becomes one-way."*

Gatilhos **pré-definidos** de rollback (não julgamento no calor): mismatch > X, p99 > Y por Z min, error rate > W.

---

## 8️⃣ OPERAÇÃO — failure handling e monitoramento (amarre com seus pontos fortes)

Onde os reliability patterns (aula 13) entram NESTA arquitetura:

| Componente | Pattern aplicado |
|---|---|
| Pipeline CDC falha ao aplicar uma mudança | **Retry com backoff** → **DLQ** (mudança quarentenada + alarme + replay ordenado) |
| Reconciler encontra mismatch | métrica + alarme; acima do threshold → **gatilho de rollback** |
| Serviço novo com PG lento no canary | **Circuit breaker** interno? Não — aqui o "breaker" é a **feature flag** (flip back); diga essa analogia |
| Consumers de eventos (outbox relay) | **at-least-once** → consumers **idempotentes** (`ON CONFLICT DO NOTHING` com message id) |
| Burst de backfill afetando produção | **Throttling** do DMS/task; janelas; réplica como fonte do full-load |
| Legado sob carga dupla (shadow reads) | shadow com **sampling** (p.ex. 10% das reads) se o custo dobrar |

**Dashboard (o que você lista quando perguntarem "what do you monitor?"):**
replication lag (ida E reversa) · mismatch rate · p95/p99 + error rate por serviço (antes/depois do flip) · saúde do pipeline CDC (DLQ depth, connector status) · PG: slow queries, connections, locks, autovacuum · flags: quem está em qual fase.

---

## 9️⃣ RISCOS E TRADE-OFFS — fale antes que perguntem (fecho da apresentação)

> *"Three risks I'd call out myself. **One**: the shared tables — that's coupling, not migration; we either fix ownership first or move those as one coordinated unit, and I'd decide that with the teams. **Two**: PostgreSQL performing differently — collation, planner, missing FK indexes; shadow reads and canary exist precisely to catch that before users do. **Three**: the long tail — procs, triggers, hidden consumers of the database like reports and jobs; I'd inventory those in week one, because that's where migrations slip."*

Terminar listando os próprios riscos = a marca de staff.

---

## 🧩 Mapa: pattern → onde ele aparece neste desenho

| Pattern (aula 13) | Onde entra na migração |
|---|---|
| **Strangler Fig** | a estratégia inteira: serviço a serviço, legado "estrangulado" |
| **CDC** | replicação legado→PG e reversa, sem tocar os serviços |
| **Transactional Outbox** | eventos dos serviços já migrados; e a analogia que justifica NÃO fazer dual-write |
| **Anti-Corruption Layer** | serviço novo lendo o mundo legado sem contaminar o domínio |
| **Canary Release** | cutover de reads por % com métricas comparadas |
| **Blue-Green (analogia)** | os dois bancos são blue/green; o flip é a flag |
| **Parallel Run / Shadow** | shadow reads com mismatch metrics |
| **Retry + DLQ** | pipeline CDC e consumers de eventos |
| **Throttling** | backfill sem derrubar produção |
| **CQRS + Materialized View** | substitui os JOINs cross-service perdidos com o fim do banco único |
| **Saga / Choreography** | fluxos de negócio entre serviços após a separação (sem transação distribuída) |
| **Chaos Engineering** | game day ANTES do primeiro cutover: matar o connector CDC, injetar lag, ensaiar o rollback |
| **Rolling deploy + expand→migrate→contract** | mudanças de schema que os times fazem DURANTE a migração |

---

## 🎤 O pitch de 3 minutos (decore a espinha, não as palavras)

> *"I'd treat this as ten small migrations, not one big one — strangler fig at the data layer. The legacy database stays the single source of truth while AWS DMS does a full-load backfill and then CDC keeps PostgreSQL converged from the transaction log — no service changes, no dual-writes, because there's no atomic transaction across two databases. A continuous reconciler — counts, checksums, invariants — publishes a mismatch metric that becomes my objective cutover criterion. Then, service by service, in rising order of risk: shadow reads to validate with real traffic, a feature-flag canary moving read percentages to Postgres, and before flipping writes, reverse CDC so the legacy stays current — that's what makes rollback a seconds-long flag flip even days later, with an explicit expiry date. Shared tables are the exception: that's a coupling problem, so we fix ownership first or move them as one coordinated unit. Throughout: DLQs and alerts on the pipeline, pre-agreed rollback triggers on mismatch and latency, and a game day rehearsing the failure modes before the first real cutover."*

---

## ✏️ Exercícios

1. **Reproduza o desenho** — papel em branco, 10 minutos, sem olhar: current state → machinery → cutover timeline → rollback. Compare e anote o que esqueceu.
2. **Narre as fases** — grave-se (ou escreva) narrando a timeline do §5 em inglês, 2 min.
3. **Defenda 3 escolhas:** DMS vs Debezium; flag por serviço vs flip global; por que a pausa de segundos em writes é aceitável ("minimal ≠ zero").
4. **Ataques do entrevistador** (responda em inglês, 30-60s cada):
   - *"Your CDC connector dies for 4 hours during Phase C. What happens and what do you do?"*
   - *"A report job nobody knew about reads the legacy DB directly. When do you discover it and what do you do?"*
   - *"Why not use AWS DMS for everything and skip the flags — just cut over on a weekend?"*
   - *"Two services need a JOIN that died with the shared database. Walk me through the read model you'd build."*
5. **O pitch** — fale o pitch de 3 minutos em voz alta 3×, até sair sem ler.

---

## ✅ Respostas / avaliação

*(Gabarito em `respostas/14-respostas.md` — só depois de tentar.)*
