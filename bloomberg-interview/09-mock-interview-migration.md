# Aula 09 — MOCK INTERVIEW: a migração 🔥

> Sessão interativa de sábado à tarde. Este arquivo é o **roteiro e a rubrica** — a entrevista acontece no chat, uma pergunta por vez, sem respostas antecipadas. Pré-requisito: aulas 06 e 07 feitas.

---

## O cenário

> **"We have approximately 10 legacy microservices using an existing SQL database. We need to migrate to PostgreSQL while maintaining reliability and minimal downtime. How would you approach this?"**

## Regras da sessão (para o Claude aplicar)

1. **Uma pergunta por vez.** Sem resposta antecipada, sem dica não pedida.
2. Follow-ups agressivos a cada resposta — no mínimo um "**Why?**" por rodada.
3. Respostas vagas são rejeitadas na hora: *"Which index?"*, *"Why that order?"*, *"What guarantee do you need?"*
4. Tudo em **inglês** (perguntas e respostas); correção de inglês técnico ao final de cada rodada, não no meio.
5. Ao final: avaliação por dimensão + nível geral + o que falta para subir de nível.

## Banco de follow-ups (o entrevistador vai puxar daqui)

**Estratégia:**
- Why did you choose that approach? What alternative did you consider and reject?
- What could go wrong with that? What's your blast radius if it does?
- Walk me through the cutover of ONE service, step by step.

**Dual-write / consistência:**
- What if both systems receive writes during the transition?
- Why not simply write to both databases from the application?
- What happens if replication falls behind? How far behind is too far?

**Rollback:**
- How would you roll this back one hour after cutover? And two days after?
- How do you roll back without losing the writes that happened on PostgreSQL?

**Validação:**
- How do you prove the data is correct? Why isn't row count enough?
- Your reconciliation job reports 0.01% mismatches. Ship or wait? What do you need to know?

**Casos difíceis:**
- What if one service can't be changed at all?
- What if four services write to the same table?
- How do you migrate the stored procedures?
- What if PostgreSQL performs WORSE for some critical queries after cutover?
- The migration is 80% done and the business asks to pause for 6 months. What state do you leave things in?

**Operação:**
- What metrics would you monitor during the migration? What alerts would page you?
- How does the team keep shipping features on these services during the migration?

## Rubrica de avaliação

| Dimensão | Mid-level | Senior | Strong Senior | Staff |
|---|---|---|---|---|
| **Abertura** | pula direto para solução | faz algumas perguntas | perguntas agrupadas com o porquê | perguntas expõem o risco dominante (coupling) e reformulam o problema |
| **Estratégia** | big bang ou dual-write ingênuo | phased + backfill+CDC | + shadow reads, flags, reverse CDC | + sequenciamento por risco/valor, critérios objetivos de go/no-go |
| **Falhas** | responde ao happy path | cita 2-3 modos de falha | para cada decisão, um modo de falha e mitigação | raciocina por blast radius; projeta para a falha ser barata |
| **Rollback** | "restore backup" | flag flip para reads | reverse replication para writes | rollback como requisito de design desde o dia 1, com prazo de validade explícito |
| **Validação** | row counts | + aggregates | + checksums, invariants, mismatch metrics | validação contínua como critério de cutover, não evento |
| **Comunicação** | detalhes soltos | estruturado | trade-offs explícitos a cada escolha | narrativa: contexto → opções → decisão → riscos → sinais |

**Nível geral = a dimensão mais fraca puxa para baixo** (é assim que entrevistadores reais avaliam consistência).

## Como usar (sábado à tarde)

Me mande: **"start mock interview"**. Eu abro com o cenário e conduzo. Reserve ~60-90 min. Depois da avaliação, repetimos as rodadas fracas.

---

## ✅ Avaliação da sessão

*(Preenchido após o mock: nível por dimensão, nível geral, gaps específicos, frases em inglês para polir.)*
