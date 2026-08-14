# Aula 06 — Database Migration SQL → PostgreSQL 🔥 EXTREMELY HIGH PRIORITY

> É literalmente o projeto da vaga: **~10 microsserviços legados num banco SQL migrando para PostgreSQL com minimal downtime.** Cobre também dual-write problem e validação de dados (Partes 12, 13 e 14 do curso).

---

# PARTE A — Como um Staff Engineer aborda o problema

## Problem

O erro de mid-level: sair desenhando a solução. O sinal de senior/staff: **fazer perguntas antes**. Na entrevista, quando derem o cenário, sua PRIMEIRA resposta deve ser clarificar.

## As perguntas a fazer ANTES de propor qualquer coisa (decore os grupos)

**Sobre a origem:**
- Which database are we migrating from? (SQL Server? Oracle? MySQL? Muda tudo: tipos, procs, ferramentas de CDC.)
- Are there stored procedures, triggers, vendor-specific queries? How many, how complex?

**Sobre escala e carga:**
- How large is the dataset? What's the read/write throughput?
- How long can data replication lag?

**Sobre acoplamento (a pergunta mais importante para 10 microsserviços):**
- Do services share the same schema? **Do services write to the same tables?**
  - Se cada serviço tem seu schema → dá para migrar **serviço por serviço** (risco fatiado).
  - Se escrevem nas mesmas tabelas → é de fato **uma** migração com coordenação — muito mais difícil.
- Can all legacy services be modified? (Um serviço "congelado" muda a estratégia inteira.)

**Sobre requisitos de negócio:**
- What downtime is acceptable? (zero? minutos? janela de madrugada?)
- What consistency guarantees are required? What are the transaction boundaries?
- What is the rollback requirement? (Precisa poder voltar depois de quanto tempo?)

### Interview framing (English)

> **"Before proposing a strategy I'd want to understand three things: the coupling — whether the ten services share tables or own separate schemas, because that decides if this is ten small migrations or one big one; the constraints — acceptable downtime, dataset size, and how much replication lag we can tolerate; and the legacy surface — stored procedures, triggers, and vendor-specific SQL, because that's usually where the real cost hides, not in moving the data."**

---

# PARTE B — As estratégias (do mais simples ao mais seguro)

### 1. Big Bang

Parar tudo → dump/restore → apontar tudo para o Postgres → religar.
- ✅ Simples, consistência trivial. ❌ Downtime proporcional ao volume; rollback = religar o antigo e **perder as escritas novas** (ou migrar de volta).
- Aceitável para: bancos pequenos, janela de manutenção real, serviços não críticos. Para 10 serviços críticos: **não**.

### 2. Phased / service-by-service cutover (a espinha dorsal da resposta certa)

Migrar **um serviço (ou domínio) por vez**: seu schema, seus dados, seu tráfego. Cada cutover é pequeno, testável, reversível. É o **Strangler Fig** aplicado a banco. Pré-requisito: ownership de dados razoavelmente separado (por isso a pergunta de coupling é a nº 1).

### 3. O pipeline de dados por trás de qualquer fase: **backfill + CDC**

```text
  1. Snapshot/backfill  ──► copia o histórico para o Postgres (dias, sem pressa)
  2. CDC                ──► replica as mudanças contínuas (log-based: Debezium etc.)
  3. Postgres alcança   ──► lag ~zero
  4. Validação          ──► reconciliation (Parte D)
  5. Cutover            ──► flip por feature flag, por serviço
  6. Reverse CDC        ──► Postgres → legado, para permitir ROLLBACK sem perda
```

- **CDC (Change Data Capture)**: ler o **transaction log** do banco origem e aplicar as mudanças no destino. Não intrusivo (não muda o app), ordenado, replayável.
- **Shadow reads**: antes do cutover, o serviço lê dos **dois** bancos, responde com o legado, **compara** os resultados e emite métrica de mismatch. Prova de equivalência com tráfego real, sem risco.
- **Shadow traffic / parallel run**: duplicar tráfego para o novo caminho sem servir a resposta. Mesma ideia em nível de request.
- **Feature flags**: o flip de leitura/escrita por serviço (e por % de tráfego) é uma flag, não um deploy. Rollback = desligar a flag.
- **Reverse replication**: após o cutover, replicar Postgres → legado por um tempo. É isso que torna o rollback **barato mesmo dias depois** — o legado continua atualizado.

### A sequência de cutover de UM serviço (decore como história)

> Backfill → CDC contínuo → shadow reads (medir mismatches até ~zero) → flip **reads** via flag → observar → flip **writes** (com reverse CDC ligado) → observar dias → desligar reverse CDC → descomissionar.

---

# PARTE C — O Dual-Write Problem 🔥

## Problem

> **"Why wouldn't you simply write to both databases?"** ← pergunta quase garantida.

```text
Application
    |
    +--> Legacy DB   ✅ committed
    |
    +--> PostgreSQL  ❌ timeout / crash / deploy no meio
```

## Por que dual-write no app é perigoso (os 5 argumentos)

1. **Partial failure**: não existe transação atômica entre dois bancos — uma escrita commita, a outra falha → **estado inconsistente permanente e silencioso**.
2. **Retry implications**: retry da escrita que falhou pode duplicar (se a primeira "falhou" mas commitou — timeout ≠ falha) → precisa de idempotência nos dois lados.
3. **Ordering**: duas instâncias do app escrevendo concorrentemente podem aplicar as escritas em **ordens diferentes** em cada banco → estados divergem mesmo sem falha nenhuma.
4. **Rollback problems**: transação faz rollback no banco A depois de já ter escrito no B — desfazer o quê, como?
5. **Deriva silenciosa**: sem um mecanismo de comparação, você não SABE que divergiu. Descobre no cutover.

## As alternativas (compare — isso é a resposta de senior)

| Abordagem | Como resolve | Custo |
|---|---|---|
| **CDC** | uma só escrita (legado); o log da transação é a fonte da replicação — ordenado, atômico por natureza | infra (Debezium/kafka), lag |
| **Transactional Outbox** | escrita + evento na **mesma transação local**; relay publica depois | mudança no app; at-least-once (consumidor idempotente) |
| **Migration middleware / proxy** | camada única intercepta e roteia escritas | vira ponto crítico; complexidade |
| **Single source of truth** | regra de ouro: **em qualquer instante, exatamente UM banco é o dono da verdade de cada tabela**; o outro é réplica derivada | disciplina de design |

### Interview answer (English, DECORE)

> **"I'd avoid application-level dual-writes because there's no atomic transaction across two databases. A partial failure leaves them silently inconsistent, retries can duplicate because a timeout doesn't mean the write didn't commit, and concurrent writers can apply changes in different orders on each side. Instead I'd keep a single source of truth and derive the other database from it — log-based CDC if I can't touch the services, or a transactional outbox if I can. Both give me ordering and replayability that ad-hoc dual writes don't."**

*(Conexão com seu repertório: é o MESMO dual-write problem de "DB transaction + publish event" que o Outbox resolve em event-driven — diga isso na entrevista, mostra profundidade.)*

---

# PARTE D — Validação: how do you prove the data is correct?

## Problem

> "Row counts match" **não prova nada**: mesmas contagens podem ter conteúdo diferente (updates perdidos, colunas truncadas, timezones deslocados).

## O arsenal, em camadas

1. **Row counts** — barato, primeiro sinal, por tabela e **por janela de tempo** (`WHERE created_at >= X`), para localizar onde diverge.
2. **Aggregates de negócio** — `SUM(amount)`, `MAX(updated_at)`, `COUNT DISTINCT customer_id` por dia/mês. Pega truncamento e updates perdidos que o count não vê.
3. **Checksums/hashes** — hash por row (colunas normalizadas) agregado por bloco de PKs → comparar blocos → drill-down binário no bloco divergente. Escala para bilhões de rows. ⚠️ Normalizar antes: timezone, precisão numérica, collation, trailing spaces — senão o checksum acusa falso mismatch.
4. **Sampling profundo** — N rows aleatórias comparadas coluna a coluna (pega o que a normalização do checksum mascarou).
5. **Business invariants** — "todo order completed tem payment", "saldo = soma das transactions". Rodar nos DOIS bancos; devem falhar/passar igual.
6. **Reconciliation job contínuo** — roda tudo acima em loop durante a migração, publica **mismatch metrics** em dashboard. Critério de cutover objetivo: *"mismatch rate < X por N dias"*. Mismatches na cauda são esperados (replication lag) — comparar com corte de tempo.
7. **Shadow reads** (de novo) — validação com queries reais de produção, não só dados em repouso.

### Interview answer (English)

> **"Row counts are necessary but nowhere near sufficient — identical counts can hide different content. I'd layer it: counts per table and time-window to localize drift, business-level aggregates like SUM of amounts per day, then block-level checksums over normalized rows to compare content at scale, plus random-sample deep comparisons and business invariants run on both sides. All of that runs as a continuous reconciliation job emitting mismatch metrics, and the cutover criterion is objective: near-zero mismatches sustained over days, not a one-off check."**

---

## ✏️ Exercícios

### Exercício 1 — abertura de entrevista

O entrevistador diz: *"We have ~10 legacy microservices on one SQL database and want to move to PostgreSQL with minimal downtime. How would you approach it?"*
Escreva sua **resposta de abertura** (em inglês, ~90s): as perguntas que você faria, agrupadas, com o porquê de cada grupo. NÃO proponha solução ainda.

### Exercício 2 — desenhe o pipeline

De memória (sem olhar acima), escreva a sequência completa de cutover de um serviço, do backfill ao descomissionamento. Depois compare com a Parte B e anote o que esqueceu.

### Exercício 3 — dual-write sob pressão

Responda em inglês, como na entrevista:
> **"Why wouldn't you simply write to both databases from the application? It seems much simpler than CDC."**
Cubra: partial failure, timeout≠failure, ordering, e a alternativa que você proporia.

### Exercício 4 — follow-ups do entrevistador (um por um)

a) **What happens if replication falls behind right before cutover?**
b) **How would you roll back two days AFTER the write cutover, without losing data?**
c) **What if one of the ten services can't be modified at all?**
d) **What metrics would you monitor during the migration?**
e) **How do you prove the data is correct?** (sem olhar a Parte D)

### Exercício 5 — o caso das tabelas compartilhadas

Descobre-se que 4 dos 10 serviços **escrevem na mesma tabela `orders`**. Como isso muda sua estratégia? O que você proporia para esses 4? (Dica: ownership primeiro, migração depois — ou migração conjunta desses 4 como uma unidade.)

---

## ✅ Respostas / avaliação

*(Preenchido durante a sessão interativa, depois da tentativa.)*
