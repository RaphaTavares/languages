# 🔒 Gabarito — Aula 14 (Migration Whiteboard)

> **Só abra depois de tentar** — especialmente o exercício 1 (desenhar de memória) e o 5 (pitch em voz alta), que são os que mais transferem para a entrevista real.

---

## Exercício 1 — o desenho de memória

Checklist do que o seu desenho precisava ter (confira item a item):

- [ ] Current state: 10 serviços → **um** banco compartilhado (e a frase "o problema é o acoplamento, não o engine")
- [ ] Machinery: **backfill** (DMS full-load) + **CDC** (transaction log) + **reconciler** emitindo mismatch metrics
- [ ] Legado como **single source of truth** até o flip — escrito no desenho
- [ ] Timeline de cutover com as 5 fases: lag→0 → **shadow reads** → **canary de reads** (flag/%) → **reverse CDC ANTES do write flip** → cleanup
- [ ] Rollback: seta reversa PG→legado com "expiry date" explícito
- [ ] Alvo: um schema/DB por serviço + outbox → eventos → read models (o substituto dos JOINs)

Os dois itens mais esquecidos (e mais valiosos): **reverse CDC antes do write flip** e **mismatch metric como critério objetivo de cutover**.

## Exercício 3 — as 3 defesas (modelos)

**DMS vs Debezium:** *"DMS is managed and solves 80% — full load, ongoing CDC, type conversion, plus the Schema Conversion Tool for DDL. Debezium gives me the change stream as a first-class event feed I can reuse for outbox-style integration and custom transforms, at the cost of running connectors and Kafka/MSK myself. Pragmatic answer: DMS for the bulk mechanics, Debezium where the change stream itself has product value. What I'd avoid is building a bespoke replicator — that's undifferentiated heavy lifting with data-loss risk."*

**Flag por serviço vs flip global:** *"Per-service flags fatiam o blast radius — cada cutover é pequeno, observável e reversível sozinho; um flip global transforma qualquer surpresa em incidente de 10 serviços. O custo — conviver semanas com serviços em fases diferentes — é real (dashboards de 'quem está onde'), mas é exatamente o custo que compramos de propósito."*

**Pausa de segundos em writes:** *"Zero-downtime absoluto para o write flip exigiria aceitar escrita nos dois lados durante a troca — ou seja, dual-write, com tudo que rejeitamos. Uma pausa de segundos (fila segurando requests, health check tirando o serviço, drena o lag, flip, volta) é honesta, testável e imperceptível para a maioria dos SLAs. 'Minimal downtime' é um número negociado com o negócio, não um dogma."*

## Exercício 4 — os ataques (modelos)

**a) CDC morre por 4 horas na Fase C.**
> *"Nothing is lost — that's why log-based CDC: the connector resumes from its saved position in the transaction log and replays. What users see: Postgres reads go stale for those hours. Detection is the replication-lag alarm; the automatic response is the pre-agreed trigger — lag beyond threshold flips the read flag back to legacy until the connector catches up. Two things I'd verify in the post-mortem: log retention on the source covers our worst outage window — if the log rotates past the connector's position, we need a re-sync plan — and that the reconciler flagged the divergence window correctly."*

**b) O report job fantasma lendo o legado direto.**
> *"Ideally I discover it in week one — the inventory step: scanning connection logs and login audits on the legacy DB for unknown principals is explicitly part of my plan because hidden consumers are where migrations slip. If it surfaces late — say, its numbers drift after a service's write flip — the fix is honest: point it at Postgres (often it's SQL that needs the dialect pass), give it a read model or replica of its own, or schedule it for decommission. What I would not do is keep the legacy DB alive indefinitely as a zombie for one report."*

**c) Por que não DMS + cutover no fim de semana, sem flags?**
> *"That's a big-bang with better tooling. It can be right for small, low-risk services — and I'd even use it for the first, simplest one. But for ten services: the weekend window caps how much validation you get — no shadow reads under real traffic, so collation and planner surprises hit users Monday morning; rollback after the weekend means losing or hand-migrating the new writes, because nothing kept the legacy current; and one bad service poisons the whole cutover. Flags cost engineering time and buy blast-radius control and cheap rollback — for a system of this criticality, that trade is clearly worth it."*

**d) O JOIN que morreu — read model walk-through.**
> *"Say the UI needs orders joined with payment status. Owner: a read service — or the consumer of the data, decided by team topology. Orders and Payments each publish domain events via their outbox — OrderPlaced, PaymentConfirmed. The read service consumes both from SQS queues and maintains a denormalized order_summary table — the join is precomputed at write time. Queries become an indexed local lookup. Three things I design for: idempotent consumers, since delivery is at-least-once; out-of-order events — a PaymentConfirmed arriving before its OrderPlaced gets parked or upserted with partial data; and a rebuild path — replay from the event archive or re-project from the source tables when the projection drifts. The consistency is eventual — for order history that's fine; I'd confirm the freshness SLA with the product team."*

## Exercício 5 — autoavaliação do pitch

Critérios (do §9 e da rubrica da aula 09):

- Falou **strangler fig / ten small migrations** na primeira frase? (enquadramento)
- Disse **por que não dual-write** sem ser perguntado?
- O rollback apareceu como **coisa construída antes** (reverse CDC + expiry)?
- Citou **critério objetivo** de cutover (mismatch sustained)?
- Fechou com **os próprios riscos** (shared tables, performance diferente, cauda de procs/consumers ocultos)?
- Coube em ~3 min sem correr?

5+ sim = pronto. Menos que isso: repita o pitch, não releia a teoria — o gargalo a essa altura é fluência, não conhecimento.
