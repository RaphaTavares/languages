# 🔒 Gabarito — Aula 09 (Mock Interview: pontos-chave por follow-up)

> **NÃO leia antes do mock no chat** — leia depois, para comparar com o que você respondeu ao vivo. As respostas completas estão no gabarito da aula 06; aqui está o **checklist do que cada follow-up quer extrair**, no formato que o entrevistador avalia.

---

## Estratégia

- **Why that approach / what alternative did you reject?** — Espera-se: nomeou 2+ alternativas (big bang, dual-write no app, CDC-based phased), rejeitou com critério (downtime, blast radius, reversibilidade), não por moda.
- **What could go wrong? / blast radius?** — Espera-se: para CADA etapa do seu plano, um modo de falha + mitigação. Backfill (carga na origem, dados mudando durante a cópia), CDC (lag, schema drift, tipos mal mapeados), cutover (performance pior no destino, cache frio), rollback (janela expirada).
- **Walk me through ONE service's cutover** — Espera-se a sequência de 8 passos (backfill → CDC → shadow reads → flip reads → reverse CDC → flip writes → observar → descomissionar) **na ordem certa**, especialmente reverse CDC ANTES do flip de writes.

## Dual-write / consistência

- **Both systems receive writes?** — Nomear como o pior cenário; a regra "one owner per table at any instant"; se inevitável na transição, janela mínima + reconciliation agressivo + critério de qual lado vence conflito.
- **Why not write to both?** — Os 3 argumentos: partial failure silencioso, timeout ≠ falha (retry duplica), ordering divergente entre instâncias. + a alternativa (CDC/outbox).
- **Replication falls behind?** — Lag como critério de go/no-go; causa raiz antes de remediar; cutover de writes exige drenar o lag (pausa curta de escrita ≠ downtime total).

## Rollback

- **1 hour after? 2 days after?** — 1h: flip de flag de volta (reads) — trivial se as flags existem. 2 dias: só sem perda se reverse replication manteve o legado vivo. Frase esperada: *"rollback is designed before cutover, not improvised after."*
- **Without losing PG writes?** — Reverse CDC é A resposta. Menção ao prazo de validade explícito do rollback = ponto extra.

## Validação

- **Prove the data is correct / why not row count?** — Camadas: counts por janela → aggregates → checksums normalizados por bloco → sampling → invariants → reconciliation contínuo com mismatch metrics como critério objetivo.
- **0.01% mismatches — ship or wait?** — A resposta certa é **investigar a natureza, não a taxa**: mismatches de lag na cauda (esperados, comparar com corte de tempo) vs mismatches de conteúdo (bug de conversão — bloqueia). Perguntar "which rows, which columns, what age?" antes de decidir. Quem responde "ship" ou "wait" sem perguntar, falha.

## Casos difíceis

- **Service can't be changed?** — Migra por último; CDC não exige mudança de app; config-only cutover; proxy como último recurso; escalar a premissa ("nem config?") ao negócio.
- **Four services, same table?** — Nomear o acoplamento; caminho A (fix ownership primeiro — forcing function) vs B (migrar os 4 como unidade); nunca em momentos diferentes.
- **Stored procedures?** — Inventário → triagem (CRUD trivial / lógica de negócio → app / set-based pesado → PL/pgSQL) → characterization tests comparando outputs → caçar callers ocultos.
- **PG performs WORSE after cutover?** — Primeiro: por que só descobrimos agora? (shadow reads deviam ter pego — admitir gap de processo vale ponto.) Depois: EXPLAIN ANALYZE nas queries regredidas; suspeitos usuais pós-migração: estatísticas frias (`ANALYZE`), índices faltando (FKs!), cache frio, collation em ORDER BY, queries escritas para o otimizador antigo. Rollback da leitura enquanto corrige, se houver SLA.
- **Pause for 6 months at 80%?** — O estado deixado precisa ser: sem dual-ownership de nenhuma tabela, CDC rodando (ou desligado com plano de re-sync documentado), runbook de retomada, e custo declarado de manter dois bancos vivos. Quem diz "ok, pausamos" sem listar o estado, falha.

## Operação

- **Metrics?** — Replication lag (ida e reversa), mismatch rate, p95/p99 + error rate por serviço antes/depois do flip, saúde do pipeline CDC, e **gatilhos pré-definidos de rollback** ligados a alarmes.
- **Team keeps shipping features?** — Schema changes durante a migração precisam de processo: expand → migrate → contract; mudanças compatíveis nos dois bancos enquanto o CDC roda; freeze curto apenas em janelas de cutover; comunicação de "tabela X está em cutover esta semana".

---

## Como se autoavaliar contra a rubrica

Depois do mock, para cada dimensão da rubrica (abertura, estratégia, falhas, rollback, validação, comunicação), pergunte:

- Eu **perguntei antes de propor**? (abertura)
- Cada escolha veio com **alternativa rejeitada + porquê**? (estratégia)
- Eu citei o modo de falha **sem o entrevistador pedir**? (falhas)
- Meu rollback funcionava **depois** do write cutover? (rollback)
- Minha validação tinha **critério objetivo de cutover**? (validação)
- Minha resposta tinha estrutura audível — "three things: ..." ? (comunicação)

4+ sins = Strong Senior no tema. O nível geral é puxado pela dimensão mais fraca — treine a pior, não a melhor.
