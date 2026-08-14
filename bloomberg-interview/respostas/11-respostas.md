# 🔒 Gabarito — Aula 11 (AWS + DynamoDB)

> **Só abra depois de tentar.** (A aula 10 não tem gabarito separado — as respostas-modelo estão no próprio arquivo.)

---

## Exercício 1 — decisões rápidas

**a) 200 imagens/dia via S3.** — *"Lambda: it's event-driven, spiky and tiny — S3 triggers the function, we pay per invocation and there's zero idle cost. ECS would be an always-on container for two hundred events a day."* (Ressalva a citar se a imagem for pesada: limites de memória/15 min → então um job ECS acionado por evento.)

**b) API 800 req/s constantes.** — *"ECS behind an ALB. Steady sustained traffic is where per-invocation pricing loses and containers win; the ALB gives health checks, TLS termination and path routing, and ECS auto-scales on load."*

**c) 4 sistemas reagem a pagamento confirmado.** — *"Fan-out of a fact: publish PaymentConfirmed once and let subscribers consume. EventBridge if I want content-based routing and SaaS integrations, SNS if it's simple fan-out — and either way, one SQS queue per consumer, so each has its own retry policy, DLQ and backpressure. Point-to-point SQS alone doesn't fit: four consumers need four deliveries."*

**d) Mensagem processada 2×.** — Duas causas prováveis: **visibility timeout menor** que o pior caso de processamento (a mensagem reaparece enquanto ainda está sendo processada) e a natureza **at-least-once** do SQS (redelivery em falha de ack/rede; deleção que não aconteceu após sucesso). Defesa: **consumer idempotente** — dedup por message id/business key (`ON CONFLICT DO NOTHING`, conditional write) — e visibility timeout dimensionado (com heartbeat/extensão para trabalhos longos).

---

## Exercício 2 — modelagem DynamoDB

Uma solução (single-table):

| Pattern | Como resolver |
|---|---|
| (1) get customer by id | PK = `CUSTOMER#<id>`, SK = `PROFILE` → GetItem |
| (2) customer's orders newest-first | itens de order: PK = `CUSTOMER#<id>`, SK = `ORDER#<iso_date>#<order_id>` → Query com `begins_with(SK, 'ORDER#')`, `ScanIndexForward = false` |
| (3) get order by order id | **GSI1**: PK = `ORDER#<order_id>` → Query no GSI (a tabela principal só busca por customer) |
| (4) all pending orders | **GSI2**: PK = `status`, SK = `created_at` → Query `status = 'pending'` ordenado por data |

(Duas tabelas separadas customers/orders com as mesmas chaves também é resposta válida — single-table não é obrigatório.)

**Hot partition no pattern 4 (o ponto da questão):** GSI2 com PK = `status` concentra **todas as orders pending do sistema inteiro numa única partição** do índice — baixa cardinalidade por definição. Sob volume, o GSI throttla (e throttling de GSI faz backpressure na escrita da tabela!). Mitigações: **write sharding** — PK = `status#<n>` com n = hash(order_id) % N, leitura faz fan-in nas N partições; ou repensar: pendings são fila de trabalho? Talvez SQS seja o lugar delas, não uma query.

---

## Exercício 3 — hot partition story (modelo)

> *"Provisioned capacity is a table-level number, but it's divided across partitions — each partition serves roughly three thousand RCUs and one thousand WCUs. If my partition key has low cardinality or skewed traffic — all of today's writes under a single date key, or one celebrity customer — one partition gets hammered while the rest sit idle, so I throttle at ten percent utilization. Diagnosis: CloudWatch throttling metrics plus CloudWatch Contributor Insights to find the hot keys. Fix: redesign the key for cardinality — put the natural high-cardinality id in the partition key — or shard the hot key with a suffix and fan-in on read. Adaptive capacity helps absorb moderate skew, but it doesn't repeal the per-partition limit; the real fix is the key design."*

---

## Exercício 4 — "why not DynamoDB instead?" (modelo)

> *"The criterion is access patterns, not fashion. DynamoDB shines when a service has a handful of known, stable, key-shaped lookups and needs predictable single-digit-millisecond latency at scale. It's a poor fit where the business asks ad-hoc questions — joins, aggregations, reporting, flexible filters — because in Dynamo every new access pattern is a design change, sometimes a new GSI or a remodel.*
> *Of these services, something like a session store, an idempotency-key table, or a notification-preferences lookup would do great in Dynamo: pure key-value, massive read volume, TTL for free. The order-management service would not: finance wants aggregations by period, support searches by a dozen fields, and we'd be rebuilding relational features on top of a key-value store.*
> *There's also a migration-risk argument: we're already changing the database under ten services; changing the paradigm at the same time doubles the unknowns. I'd land on PostgreSQL first, and revisit specific hot paths for DynamoDB as a separate, per-service decision."*

O terceiro parágrafo (risco de mudar **dois eixos ao mesmo tempo**) é o que faz a resposta soar staff-level no contexto DESTA vaga.
