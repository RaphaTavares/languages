# 🔒 Gabarito — Aula 04 (Query Optimization + EXPLAIN)

> **Só abra depois de tentar.** Nos cenários de troubleshooting, avalie-se por: estruturou a investigação? Separou hipóteses? Citou a ferramenta certa? Não existe resposta única.

---

## Exercício 1 — resposta de 60s (modelo)

> *"First I'd measure: confirm what changed and when — pg_stat_statements or APM — and whether it's slow for every execution or specific parameters. Then reproduce with the real parameters and run EXPLAIN ANALYZE. I'm looking for three things: which node the time actually goes to, whether estimated rows match actual rows — a bad estimate means the planner picked a bad join strategy — and whether the expected index is used and usable. Typical culprits: the table grew and a seq scan that used to be cheap no longer is, statistics went stale, a predicate stopped being sargable after a change, or it's not the query at all — it's waiting on a lock. Then I change one thing and re-benchmark against the original measurement."*

Se sua resposta não tinha: **medir antes**, **estimated vs actual**, **uma mudança por vez** — refaça.

---

## Exercício 2 — dois problemas no plano

1. **Misestimate gigante:** `rows=1000` estimado vs `rows=4200000` real no Hash Join. Primeiro a checar: **as 4.2M rows deveriam existir?** Se o resultado esperado é pequeno → suspeite **fan-out** (chave de join duplicada) ou filtro faltando. Se 4.2M é legítimo → estatísticas: `ANALYZE`, statistics target, colunas correlacionadas (`CREATE STATISTICS`).
2. **Sort spillando em disco:** `external merge Disk: 890MB` — o sort não coube em `work_mem` e passou a fazer IO. Correções: reduzir as rows **antes** do sort (filtro/pré-agregação), índice que entregue a ordem, ou `work_mem` maior para essa sessão/relatório (com parcimônia — é por operação de sort, não por query).

A conexão (o insight): **o misestimate causa o subdimensionamento** — o planner reservou memória para 1.000 rows e chegaram 4.2M. Consertar as estatísticas pode consertar o spill de graça.

---

## Exercício 3 — misestimate (modelo)

> *"Estimates drive every planner decision — join strategy, memory, scan type. Expecting 100 rows, a nested loop with an index probe is perfect; at 2 million actual rows those become 2 million random lookups. Estimates go wrong when statistics are stale after heavy writes, when the data is skewed so the average hides outliers, or when correlated columns make the planner multiply selectivities that aren't independent. Concretely: run ANALYZE and re-check; if the estimate is still off, raise the statistics target for that column, and for correlated predicates create extended statistics with CREATE STATISTICS. If the planner still can't know — say, a parameter that's sometimes huge — I restructure the query instead of fighting the planner."*

---

## Exercícios 4-13 — os 10 cenários (pontos que sua resposta devia cobrir)

**4. 500k → 50M rows, 200ms → 8s.** O plano de antes provavelmente era um Seq Scan barato que "cabia"; com 100× mais dados, ou o Seq Scan ficou caro (falta índice para o predicado) ou o plano **flipou** para pior. EXPLAIN ANALYZE agora; conferir se existe índice seletivo para o filtro; conferir se autovacuum/ANALYZE acompanharam o crescimento; considerar particionamento se a query sempre corta por tempo.

**5. Seq Scan com índice existente.** Quatro hipóteses, nesta ordem: (a) predicado **não-sargable** (função/cast na coluna, mismatch de tipo — `varchar = int`); (b) **baixa seletividade** — o planner está certo; (c) **estatísticas velhas** superestimando as rows retornadas; (d) tabela pequena demais para valer índice. Diagnóstico: EXPLAIN com estimated vs actual; teste com `SET enable_seqscan = off` para ver o custo que o planner atribui ao índice.

**6. Usa índice e ainda é lento.** O índice acha as rows, mas: `loops` alto (inner de nested loop executado milhões de vezes — multiplique actual time × loops); index scan retornando milhões de rows = milhões de acessos aleatórios ao heap; **`Rows Removed by Filter` alto** = índice pouco seletivo, o resto é filtrado depois (índice composto melhor resolveria); Heap Fetches altos num Index Only Scan (visibility map/VACUUM); ou o gargalo é outro nó (sort/aggregate) e o índice é inocente.

**7. CPU ok, latência subiu.** Latência sem CPU = **espera**, não trabalho. Checar: `pg_stat_activity` (wait events — lock? IO?), `pg_locks` (transação longa segurando lock? migração/DDL rodando?), connection pool esgotado (a espera é ANTES do banco), IO saturado (EBS burst balance!), checkpoint/autovacuum agressivo. A pergunta-chave: *"is the database working slowly or waiting on something?"*

**8. JOIN retorna 100× mais rows.** Fan-out: a chave de join que você assumiu única **não é** (duplicatas na dimensão), ou condição de join incompleta (faltou uma coluna da chave composta → produto parcial). Diagnóstico: `SELECT key, COUNT(*) ... GROUP BY key HAVING COUNT(*) > 1` no lado "one". Fix: corrigir a condição, deduplicar ou pré-agregar. (Mesma lição da aula 01.)

**9. Estimado 1.000, real 4M.** = Exercício 3: ANALYZE, statistics target, extended statistics, skew. Acrescente: se é uma query parametrizada, o **generic plan** pode estar sendo usado com um parâmetro atípico.

**10. Relatório com GROUP BYs e sorts, 30s.** Verificar spills (`external merge`, `Batches` no hash) → work_mem; reduzir rows **cedo** (filtros antes das agregações — CTE materializada atrapalhando? aula 02); índice que entregue a ordem de um sort caro; pré-agregação incremental ou **materialized view** para relatório recorrente; rodar em **réplica** para não competir com OLTP. Pergunta de senior: *"does this need to be computed at query time at all?"*

**11. API lenta, queries rápidas.** Primeiro suspeito: **N+1** — 500 queries de 2ms = 1s (conte queries por request no APM ou `pg_stat_statements.calls`). Depois: espera por conexão no pool, round-trips seriais que poderiam ser batched, serialização/payload gigante (Include demais — cartesian explosion), latência de rede app↔banco, trabalho no app. A frase: *"the database is innocent until the profile says otherwise — I'd break down where the request time actually goes."*

**12. Rápida para a maioria, 20s para alguns.** **Data skew**: os customers-baleia. O plano bom para 50 orders é péssimo para 2M (nested loop → deveria ser hash). EXPLAIN ANALYZE **com os parâmetros lentos**; conferir MCVs/histogramas; considerar: índice melhor, query alternativa para os grandes, paginação obrigatória, ou (raro) forçar replan. Também: generic vs custom plan em prepared statements.

**13. Spike diário no mesmo horário.** Algo agendado: relatório/ETL pesado, backup, batch job, reindex, pico de negócio. Correlacionar o horário com cron/schedulers e `pg_stat_activity` durante o spike; identificar se a dor é lock, IO ou CPU; remediar isolando (réplica para o relatório, janela diferente, throttling do batch). Resposta de senior inclui: *"first correlate, then isolate — don't tune the query before knowing what it competes with."*
