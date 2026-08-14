# Aula 11 — AWS + DynamoDB (revisão arquitetural de segunda)

> Foco em **decisões**, não configuração. A JD cita: Lambda, ECS, SQS, EventBridge, CloudFront, ALB, DynamoDB, Terraform, GitLab. Seu histórico com SQS/SNS/mensageria é forte — capitalize.

---

# PARTE A — AWS: as 5 decisões arquiteturais

## 1. Lambda or ECS? 🔥

Decida por **formato do workload**, não por moda:

| Fator | Lambda | ECS (Fargate/EC2) |
|---|---|---|
| Tráfego | spiky, imprevisível, esparso | constante, previsível |
| Duração | curta (limite **15 min**) | longa / contínua (consumers, websockets) |
| Custo | por invocação; zero idle | por hora; barato sob carga constante |
| Runtime | gerenciado, cold starts | controle total (container), sem cold start |
| Operação | mínima | orquestração, deploys, scaling policies |

> *"For an API with steady traffic I'd run ECS behind an ALB; for event-driven glue — S3 triggers, SQS consumers with modest volume, scheduled jobs — Lambda. At very high sustained volume, per-invocation pricing often crosses over and ECS wins."*

## 2. SQS or EventBridge? (ou SNS?)

- **SQS** = fila: **1 grupo consumidor**, buffering, retry, DLQ, backpressure. "Distribuir trabalho."
- **SNS** = fan-out pub/sub simples para N assinantes (inclusive N SQS).
- **EventBridge** = event **bus**: roteamento por conteúdo (rules sobre o payload), integrações SaaS, schema registry, archive/replay. "Publicar fatos para quem interessar."
- **Composição canônica (fale isso):** EventBridge/SNS roteia → **uma SQS por consumidor** → cada consumidor tem seu retry/DLQ isolado.

## 3. ALB na frente do ECS — quando e por quê

Sempre que houver tráfego HTTP para múltiplas tasks: distribui carga, **health checks** (tira task doente de rotação), path-based routing (`/api/orders` → serviço A), TLS termination, integra com auto-scaling. Sem ALB: service discovery interno (Cloud Map) para tráfego service-to-service, ou API Gateway para APIs públicas gerenciadas.

## 4. Retries e DLQ com SQS (seu território — responda com autoridade)

Visibility timeout esconde a mensagem enquanto processa → falhou/expirou → volta para a fila → `maxReceiveCount` excedido → **DLQ** → alarme no CloudWatch + replay controlado depois do fix. Pontos de senior: visibility timeout > pior caso de processamento (senão duplicata garantida); **consumer idempotente sempre** (at-least-once); FIFO queue quando ordering importa (com custo de throughput por message group).

## 5. CloudFront / Terraform / GitLab — nível "uma frase boa"

- **CloudFront**: CDN — cache na borda para estáticos E aceleração/WAF para APIs dinâmicas.
- **Terraform**: IaC declarativa; state como fonte da verdade; `plan` revisado em MR como gate. *"Infrastructure changes go through the same review process as code."*
- **GitLab CI**: pipelines em `.gitlab-ci.yml`; build → test → plan → apply com aprovação manual para prod.

---

# PARTE B — DynamoDB

## O modelo mental que a entrevista quer 🔥

> **"Why do we design DynamoDB from access patterns rather than relationships?"**

Relacional: modele os dados normalizados → qualquer query depois (JOINs, planner). DynamoDB: **não há JOINs nem query planner** — só busca eficiente por chave. Então o design **começa** pela lista de perguntas que a aplicação fará ("get user by id", "orders of a customer, newest first") e a tabela é **moldada** para que cada pergunta seja um único `Query` por chave.

> *"In relational modeling I normalize entities and rely on the query planner to answer anything. DynamoDB has no joins and no planner — it answers exactly one kind of question efficiently: give me items by key. So I enumerate the access patterns first and shape the table so each pattern is a single key lookup. Flexibility moves from query-time to design-time."*

## Os blocos

- **Partition key (PK)**: hash → decide a partição física. `Query` exige PK exata.
- **Sort key (SK)**: ordena itens dentro da partição; permite `begins_with`, ranges, `ScanIndexForward=false` (ex.: PK=`customer_id`, SK=`order_date` → "orders do customer X no período Y, mais recentes primeiro" em um Query).
- **GSI** (Global Secondary Index): a MESMA tabela reindexada por outra PK/SK — um novo access pattern depois do fato. **Eventually consistent sempre**; custa WCU extra em cada escrita (parecido com índice em Postgres: pago na escrita).
- **LSI**: mesma PK, SK alternativa; só na criação da tabela; limite de 10GB por partição. Nível entrevista: *"I generally reach for GSIs; LSIs are restrictive."* — SKIP além disso.
- **Hot partitions** 🔥: throughput é **por partição** (~3.000 RCU / 1.000 WCU). PK de baixa cardinalidade (ex.: `date` como PK → todo o tráfego de hoje numa partição) ou "celebrity key" → throttling com a tabela "vazia". Fix: chave de alta cardinalidade, ou **write sharding** (sufixo `date#1..N` e fan-in na leitura).
- **Consistência**: default **eventually consistent** (réplicas); strong read disponível (2× RCU, não em GSI). Escolha por operação.
- **Transactions**: `TransactWriteItems` — até 100 itens ACID entre tabelas; 2× custo. Para o resto: **conditional writes**.
- **Conditional writes / optimistic concurrency**: `ConditionExpression: version = :expected` → falha se mudou → retry. **É o mesmo optimistic locking da aula 05** — diga isso, conecta os mundos. Também: `attribute_not_exists(pk)` = "insert only" = **idempotência**.
- **TTL**: expiração automática por atributo timestamp (sessões, locks, dedup keys). Lazy — item pode viver horas após expirar; filtre na leitura.
- **Single-table design** (conceitual): entidades diferentes na mesma tabela com chaves compostas (`PK=CUSTOMER#123, SK=ORDER#2026-08-01#456`) para buscar "customer + suas orders" em **um** Query — o "join" é pré-computado na escrita. Trade-off: leitura dos patterns previstos é ótima; flexibilidade e legibilidade sofrem; pattern novo pode exigir GSI ou remodelagem.

## PostgreSQL vs DynamoDB — a decisão (cai quase certeza, dado o contexto da vaga)

| Escolha | Quando |
|---|---|
| **PostgreSQL** | access patterns variados/desconhecidos; ad-hoc queries, JOINs, agregações, relatórios; transações multi-row ricas; constraints e integridade referencial |
| **DynamoDB** | poucos access patterns **conhecidos e estáveis**, por chave; latência single-digit ms em escala massiva; throughput enorme com operação mínima; TTL/session/lookup tables |

> *"They're not competitors so much as tools for different shapes of problem. If I can enumerate the access patterns on one hand and they're all key lookups, DynamoDB gives me predictable latency at any scale. The moment the business wants ad-hoc questions, aggregations and joins, I want PostgreSQL. In practice many systems use both — Postgres as the system of record, DynamoDB for hot key-value paths."*

---

## ✏️ Exercícios

### Exercício 1 — decisões rápidas (1-2 frases em inglês cada)

a) Processar imagens enviadas a um bucket S3, ~200/dia. Lambda or ECS?
b) API de pedidos com 800 req/s constantes. Lambda or ECS? E o que fica na frente?
c) Quando um pagamento é confirmado, 4 sistemas reagem (email, estoque, analytics, fraude). SQS, SNS ou EventBridge — e qual topologia?
d) Um consumer SQS às vezes processa a mesma mensagem duas vezes. Duas causas prováveis + a defesa.

### Exercício 2 — modele em DynamoDB

Access patterns: (1) get customer by id; (2) list a customer's orders newest-first; (3) get order by order id; (4) list all orders with status = 'pending' across customers.
Defina PK/SK da tabela e o que precisa de GSI. Onde está o risco de hot partition no pattern 4?

### Exercício 3 — hot partition story

> **"Your DynamoDB table is heavily throttled but the metrics say you're way under provisioned capacity. What's happening and how do you fix it?"** (inglês, 60s)

### Exercício 4 — a pergunta híbrida

> **"You're migrating these services to PostgreSQL — why not take the opportunity to move some of them to DynamoDB instead?"**
Responda em inglês mostrando o critério (access patterns) e dando um exemplo de serviço que iria bem em Dynamo e um que não.

---

## ✅ Respostas / avaliação

*(Preenchido durante a sessão interativa, depois da tentativa.)*
