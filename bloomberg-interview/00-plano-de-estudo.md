# Plano de Estudo — Entrevista Senior Full Stack Engineer

> **Entrevista:** segunda-feira, 2026-08-17 (provável)
> **Foco da vaga:** "Deep expertise in SQL... advanced querying, joins, aggregations, CTEs, window functions, query optimization, performance tuning" + "Strong database expertise taking priority"
> **Projeto:** ~10 microsserviços legados migrando de um banco SQL para PostgreSQL

---

## 📅 Cronograma

### Sexta (dia pesado — ~6-8h)

| Bloco | Aula | Conteúdo | Tempo |
|---|---|---|---|
| Manhã 1 | 01 | JOINs, GROUP BY, aggregates, WHERE vs HAVING | 1h30 |
| Manhã 2 | 02 | CTEs + Window Functions 🔥 (ROW_NUMBER, top-N per group, latest row per entity) | 2h |
| Tarde 1 | 03 | Indexes 🔥 (B-tree, composite, column order, selectivity) | 1h30 |
| Tarde 2 | 04 | Query optimization framework + EXPLAIN / EXPLAIN ANALYZE 🔥 | 2h |
| Noite (leve) | 05 | Sargability + PostgreSQL internals (MVCC, VACUUM, ANALYZE) | 1h |

### Sábado (até a tarde — ~4-5h)

| Bloco | Aula | Conteúdo | Tempo |
|---|---|---|---|
| Manhã 1 | 06 | Migration SQL → PostgreSQL 🔥 + dual-write problem + validação de dados | 2h |
| Manhã 2 | 07 | Diferenças SQL Server → Postgres + revisão de distributed systems (ponto forte — só conectar vocabulário) | 1h |
| Tarde 1 | 08 | Design patterns (só alto ROI, formato entrevista) | 1h |
| Tarde 2 | 09 | MOCK INTERVIEW — cenário de migração 🔥 | 1h30 |

### Domingo

**SKIP — competição de jiu-jitsu.** Descansar. 🥋

### Segunda (manhã, antes da entrevista — ~1-2h, revisão leve)

| Bloco | Aula | Conteúdo |
|---|---|---|
| Revisão 1 | 10 | Rapid fire (respostas de 30-60s, em inglês) |
| Revisão 2 | 11 | AWS + DynamoDB (afiar respostas arquiteturais) |
| Revisão 3 | — | Reler framework de troubleshooting (Measure → EXPLAIN → …) em voz alta 2x |

### ❌ Cortado por baixo ROI (SKIP FOR NOW)

- React / Jest / Playwright em profundidade (20 min segunda, se sobrar tempo)
- Compiled queries do EF
- LSIs em profundidade
- Configuração de AWS (foco só em decisões arquiteturais)
- GoF patterns fora da lista de alto ROI

---

## ⚠️ As 15 competências de maior risco

Ordenadas por (probabilidade de cair) × (lacuna atual):

1. 🔥 **Window functions** — "latest order per customer", "top 3 per group". Quase certeza que cai: a JD cita window functions explicitamente.
2. 🔥 **Escolha de índice para uma query específica** — "which index and why?" com justificativa de column order.
3. 🔥 **Ler um EXPLAIN ANALYZE** — identificar Seq Scan suspeito, misestimate de rows.
4. 🔥 **Framework de troubleshooting** — "query ficou lenta, o que você investiga?" Resposta estruturada separa mid de senior.
5. 🔥 **Estratégia de migração com minimal downtime** — CDC vs dual-write vs cutover por serviço. É literalmente o projeto da vaga.
6. 🔥 **Dual-write problem + Outbox** — conectar o Outbox (que já conheço de event-driven) ao contexto de migração.
7. **CTE vs subquery + quando CTE não ajuda performance** — pergunta clássica de profundidade.
8. **WHERE vs HAVING** — pergunta-filtro; errar derruba credibilidade em 10 segundos.
9. **Duplicação de rows em JOINs one-to-many (fan-out)** — armadilha favorita em exercícios de SQL ao vivo.
10. **MVCC / VACUUM / ANALYZE** — o "por que Postgres é diferente"; esperado de quem lidera migração para Postgres.
11. **Sargability** — `WHERE DATE(created_at) = ...` matando índice; exemplo barato que impressiona.
12. **Validação de dados na migração** — "how do you prove both databases match?" Row count não basta.
13. **Keyset vs OFFSET pagination** — favorita em vagas com foco em performance.
14. **Optimistic vs pessimistic concurrency** — conecta com EF (`rowversion`/`xmin`) e DynamoDB conditional writes.
15. **DynamoDB access patterns + hot partitions** — risco de pergunta "Postgres or DynamoDB, when?"

**Pontos fortes (colchão de segurança):** retries, idempotency, DLQ, message brokers, eventual consistency, K8s. Sempre que possível, puxar a resposta para esse território.

---

## 📁 Padrão das aulas

Cada aula é um arquivo `NN-titulo.md` nesta pasta, com a estrutura:

1. **Problem** — o problema primeiro
2. **Concept** — modelo mental
3. **Example** — exemplo realista (customers, orders, payments...)
4. **What can go wrong?** — armadilhas
5. **Trade-offs** — alternativas
6. **Interview questions** — em inglês
7. **✏️ Exercícios** — sem resposta; respostas só após tentativa

Idioma: explicações em português, termos técnicos e perguntas/respostas de entrevista em inglês.

## 📁 Aulas (todas criadas — marcar conforme for FAZENDO)

- [ ] `01-sql-joins-group-by-aggregates.md`
- [ ] `02-ctes-window-functions.md` 🔥
- [ ] `03-indexes.md` 🔥
- [ ] `04-query-optimization-explain.md` 🔥 (inclui N+1/EF + os 10 cenários de troubleshooting)
- [ ] `05-sargability-postgres-internals.md` (inclui transactions & concurrency)
- [ ] `06-migration-sql-to-postgresql.md` 🔥 (inclui dual-write + validação de dados)
- [ ] `07-sqlserver-vs-postgres-distributed-systems.md` (inclui data modeling)
- [ ] `08-design-patterns.md`
- [ ] `09-mock-interview-migration.md` 🔥 (sessão interativa — mandar "start mock interview" no chat)
- [ ] `10-rapid-fire.md` (única com respostas-modelo no arquivo — não olhar antes de tentar)
- [ ] `11-aws-dynamodb.md`
- [ ] `12-sql-coding-drills.md` (18 drills progressivos — sexta à noite ou intercalado com aulas 02-04)
- [ ] `13-architectural-patterns.md` 🔥 (os 23 padrões arquiteturais — scalability, data, extensibility, reliability, deployment)
- [ ] `14-migration-whiteboard.md` 🔥🔥 (a migração desenhada como whiteboard: diagramas, AWS, patterns aplicados, pitch de 3 min)

## ⚡ REPRIORIZAÇÃO (pouco tempo restante)

Como a entrevista foi descrita como **"technical + design pattern questions + architectural based"** e o tempo de estudo encurtou, a ordem de ataque muda para:

1. **`14-migration-whiteboard.md`** 🔥🔥 — o cenário da vaga inteiro num arquivo; treinar o desenho e o pitch
2. **`13-architectural-patterns.md`** 🔥 — os padrões que sustentam as respostas do 14
3. **`08-design-patterns.md`** — "design pattern questions" literal
4. **`06-migration-sql-to-postgresql.md`** — aprofunda o 14 (perguntas, dual-write, validação)
5. **`10-rapid-fire.md`** — na manhã da entrevista
6. SQL (aulas 01-05, 12) — o que der: priorizar aula 02 (window functions) e o framework da aula 04, que são os mais prováveis de SQL

## 🔁 Fluxo de trabalho

1. Ler a aula e fazer os exercícios **sem consultar** a parte teórica.
2. Conferir no gabarito da pasta `respostas/` (um por aula; a 10 tem as respostas no próprio arquivo) — **só depois de tentar**.
3. Opcional, mas recomendado nos temas 🔥: mandar as respostas no chat para correção de raciocínio e de inglês técnico como entrevistador.
4. Marcar a aula aqui e seguir a ordem do cronograma.

⚠️ Disciplina com os gabaritos: ler a resposta sem ter escrito a sua dá sensação de aprendizado sem retenção — na entrevista não haverá gabarito.
