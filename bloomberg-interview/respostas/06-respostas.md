# 🔒 Gabarito — Aula 06 (Migration SQL → PostgreSQL)

> **Só abra depois de tentar.** Este é o tema central da vaga — se suas respostas divergirem muito, refaça o exercício no dia seguinte.

---

## Exercício 1 — abertura de entrevista (modelo, ~90s)

> *"Before proposing anything, I'd want to clarify three groups of things.*
> *First, coupling — because it decides the whole shape of the migration: do the ten services own separate schemas, or do they share tables? If each service owns its data, this is ten small, individually reversible migrations. If several services write to the same tables, we effectively have one big migration — or a refactoring to do first. Related: can all ten services be modified, or is any of them frozen?*
> *Second, constraints: what downtime is actually acceptable — zero, minutes, a weekend window? How large is the dataset and what's the write throughput, since that sets backfill time and replication lag? And what's the rollback requirement — do we need to be able to return a week after cutover without losing data?*
> *Third, the legacy surface: which engine are we leaving — SQL Server, Oracle? — and how much logic lives in the database: stored procedures, triggers, vendor-specific SQL? In my experience that's where the real cost hides, not in moving rows.*
> *With those answers I'd shape the strategy — but my default instinct is service-by-service, CDC-based, with a validated, reversible cutover per service."*

Repare na estrutura: **3 grupos nomeados, cada um com o porquê**, e um fecho que sinaliza a direção sem se comprometer cegamente.

---

## Exercício 2 — o pipeline de cutover (gabarito para conferência)

1. **Backfill** — snapshot do histórico para o Postgres (sem pressa, sem tocar produção).
2. **CDC contínuo** — replica as mudanças desde o snapshot; Postgres converge (lag → ~0).
3. **Shadow reads** — serviço lê dos dois, responde com o legado, compara e emite mismatch metrics; roda até mismatch ~0 sustentado.
4. **Flip de reads** — feature flag, gradual (%, por tenant); observar latência/erros.
5. **Flip de writes** — com **reverse CDC (Postgres → legado) ligado ANTES** do flip.
6. **Observação** — dias com o legado atualizado via reverse replication = rollback barato.
7. **Desligar reverse CDC** — fim da janela de rollback (decisão explícita, comunicada).
8. **Descomissionar** — remover código de shadow/flags, arquivar o legado.

Itens mais esquecidos: **ligar o reverse CDC antes do flip de writes** (5) e **tratar o fim da janela de rollback como decisão explícita** (7).

---

## Exercício 3 — dual-write (modelo)

> *"Because there's no atomic transaction across two databases — simplicity is exactly what you don't get. Three failure modes: first, partial failure — the legacy write commits, the Postgres write fails, and now they've diverged silently; nobody gets an error that says 'databases inconsistent'. Second, retries are unsafe: a timeout doesn't mean the write didn't commit, so retrying can duplicate. Third, even with zero failures, two app instances writing concurrently can apply changes in different orders on each side, and the states drift. And you'd be adding this failure surface to ten services at once. Instead I'd keep the legacy database as the single source of truth and derive PostgreSQL from its transaction log with CDC — ordered, atomic by construction, replayable, and it needs no changes to the services. Dual-write is the same trap as 'save to the database and publish to the broker' — and the industry answer there is the outbox, not writing twice."*

---

## Exercício 4 — follow-ups

**a) Replication lag antes do cutover.** Lag é um **critério de go/no-go**, não um contratempo: não corta com lag acima do limiar. Investigar a causa (throughput de escrita > capacidade do apply? transações gigantes? índice faltando no destino?). O cutover de reads pode prosseguir com lag pequeno e conhecido (leituras levemente stale — decisão de produto); o de **writes** exige lag ~zero + congelamento curto: pausar escritas segundos, drenar o lag, flip. *"Minimal downtime, not necessarily zero."*

**b) Rollback 2 dias depois.** Só é possível sem perda porque o **reverse CDC** manteve o legado atualizado: flip das flags de volta, legado já contém as escritas dos 2 dias. Sem reverse replication, as opções são ruins: perder 2 dias de escritas ou migração reversa ad-hoc sob pressão. Moral (diga explicitamente): *"rollback is a feature you build before cutover, not something you improvise after."*

**c) Serviço que não pode ser modificado.** Migre-o **por último**; CDC não exige mudança no app, então os dados dele continuam fluindo enquanto os outros migram. Para o cutover dele: se "não modificável" permite mudar **connection string/config**, basta uma janela curta. Se nem isso: proxy de protocolo/camada de compatibilidade (complexo, último recurso) — ou questionar o negócio: *"if we can't even change its configuration, the real problem is that service, not the migration."*

**d) Métricas.** Replication **lag** (origem→destino e reverso); **mismatch rate** do reconciliation e das shadow reads; **error rate e latência p95/p99 por serviço** comparando antes/depois do flip; throughput de escrita nos dois bancos; saúde do pipeline CDC (fila/DLQ do connector); no Postgres: slow queries, connections, locks, autovacuum. Alarmes = gatilhos **pré-definidos de rollback** (ex: "mismatch > X ou p99 > Y por Z min → flip back").

**e) Validação.** Ver Parte D da aula: counts por janela → aggregates de negócio → checksums por bloco (rows normalizadas) → sampling profundo → invariants nos dois lados → reconciliation contínuo com mismatch metrics como **critério objetivo de cutover**.

---

## Exercício 5 — 4 serviços escrevendo na mesma tabela

Pontos esperados:

1. **Nomear o problema:** isso não é um problema de migração — é **acoplamento por dados**; a tabela compartilhada é um contrato implícito entre 4 serviços. Se migrar assim, migra o acoplamento junto.
2. **Caminho A (ideal, se houver tempo):** consertar ownership ANTES — eleger um serviço **dono** de `orders`, os outros 3 passam a escrever via API/eventos do dono. Depois, a migração da tabela é trivial (um dono só). É o caminho staff: *"use the migration as the forcing function to fix the boundary."*
3. **Caminho B (pragmático):** tratar os 4 como **uma unidade de migração** — cutover coordenado dos 4 juntos (mesma flag), depois dos outros 6 individualmente. Blast radius maior nessa fatia, mas honesto.
4. **O que NÃO fazer:** migrar os 4 em momentos diferentes com a tabela recebendo escrita dos dois lados = dual-write distribuído, o pior cenário da aula.
5. **Trade-off explícito:** A custa mais tempo antes, paga para sempre; B entrega mais rápido, mantém a dívida. A escolha depende do apetite do negócio — e **dizer que depende, com os dois preços na mesa**, é a resposta certa.
