# 🔒 Gabarito — Aula 13 (Architectural Patterns)

> **Só abra depois de tentar.**

---

## Exercício 1 — Orchestration vs Choreography (modelo)

> *"Choreography: each service reacts to events and publishes its own — no central brain, maximum decoupling. It shines for short, stable flows with two or three steps. Orchestration: one component owns the sequence, the state and the failure handling — Step Functions or a saga orchestrator. It wins when the flow is long, branches, needs timeouts and compensations, or when operations needs visibility. My practical test: if I can't easily answer 'where is order 123 stuck, and why?', the flow has outgrown choreography. And it's not either-or — I orchestrate within a bounded context and choreograph between contexts."*

A última frase (híbrido) é o diferencial.

## Exercício 2 — Outbox de memória (gabarito do fluxo)

```text
1. BEGIN TRANSACTION
2.   UPDATE orders SET status = 'placed' ...        (estado)
3.   INSERT INTO outbox (id, type, payload) ...     (evento, MESMA transação)
4. COMMIT                                            ← atomicidade garantida aqui
5. Relay (polling da outbox OU CDC/Debezium na tabela)
6.   publica no broker (SNS/Kafka) → marca published (ou avança offset)
7. Broker entrega → consumer
8.   consumer: INSERT message_id ON CONFLICT DO NOTHING  ← dedup
9.   se 0 rows → duplicata → ack e sai (no-op)
10.  senão → processa + commita efeitos JUNTO com o registro de dedup
```

- **At-least-once entra em 5-7:** o relay pode publicar, falhar antes de marcar, e publicar de novo; o broker pode reentregar.
- **Dedup entra em 8-10** — e o detalhe que vale a questão: **dedup record e efeitos na MESMA transação** do consumer, senão um crash entre eles quebra a garantia.

## Exercício 3 — Cadeia de resiliência (uma composição defensável)

```text
[caller] → Circuit Breaker → Retry (backoff+jitter) → Timeout → [payment gateway]
                                                          + Fallback no breaker aberto
                                                          + (se async) DLQ após esgotar
```

Justificativas esperadas:

- **Timeout mais interno**, por tentativa — sem timeout, o retry nunca dispara e threads ficam presas. Timeout por tentativa × tentativas < SLA do caller (faça essa conta em voz alta!).
- **Retry envolve o timeout** — cada tentativa tem seu prazo; backoff + jitter; só erros transientes; só se a operação for idempotente (pagamento: **idempotency key** antes de qualquer retry!).
- **Circuit breaker mais externo, contando tudo** — ele deve enxergar o resultado FINAL (após retries) para medir a saúde real; aberto → **fallback** (fila para processar depois, resposta degradada) em vez de erro seco.
- **DLQ** — no mundo async: mensagem que esgotou tentativas vai para quarentena com alarme + replay.

Composição alternativa (breaker por dentro do retry) é defensável se você quer que o retry "espere o half-open" — o que importa é **saber que a ordem muda a semântica** e dizer qual você quer.

## Exercício 4 — "When would you NOT use CQRS?" (modelo)

> *"When reads and writes don't genuinely diverge — a straightforward CRUD domain, moderate scale, forms-over-data. CQRS buys you independently scaled, purpose-shaped read models; it costs eventual consistency — including the read-your-writes problem where a user saves and doesn't see their change — plus duplicated data, projection code, and a rebuild story for when projections drift. If one well-indexed relational model serves both sides comfortably, separate models are pure overhead. I'd also avoid full CQRS-with-separate-stores as a first step: start with separate handlers over the same database, and split storage only when scale or shape actually demands it."*

## Exercício 5 — Deploy do cutover de reads

Resposta esperada: **Canary** — e a explicação da analogia: *"the 'new version' isn't code, it's a database."* A flag move 1% → 10% → 50% → 100% das **leituras** para o Postgres; as métricas de comparação são error rate, p99 **e mismatch rate das shadow reads**; regressão → flag off = rollback em segundos, blast radius = a fração. Blue-green é a analogia estrutural (dois "ambientes" completos — os dois bancos), mas o flip 100%-de-uma-vez joga fora o principal benefício aqui: descobrir com 1% do tráfego que a collation mudou um ORDER BY.

## Exercício 6 — Compensação que falha

Pontos esperados (em qualquer ordem):

1. **Retry com backoff da compensação** — falha transiente é o caso comum; para isso a compensação **precisa ser idempotente** (refund com idempotency key — refund duplicado é incidente financeiro).
2. Esgotou → **DLQ / fila de compensações falhas** com alarme — nunca engolir silenciosamente.
3. A saga fica em estado explícito `compensation_failed` (orquestrador registra) — visível, consultável.
4. **Intervenção humana como passo DESENHADO** — runbook, fila de trabalho para operações, não heroísmo às 3h.
5. Nível staff: distinguir falha técnica (retry resolve) de **impossibilidade semântica** (conta encerrada — o dinheiro não tem para onde voltar) → esta última é regra de negócio a definir COM o negócio, não um bug.
