# Aula 13 — Architectural Patterns 🔥 (o cardápio completo)

> "Technical + design pattern questions + architectural based." Este arquivo cobre os 23 padrões da sua lista, agrupados como na imagem. Formato por pattern: **Problema → Como funciona → Exemplo → Trade-offs → Frase de entrevista (inglês)**. Os marcados com 🔥 são os mais prováveis para ESSA vaga (conectam com migração/dados).

---

# 1. SCALABILITY PATTERNS

## 1.1 Load Balancing

- **Problema:** uma instância não aguenta o tráfego; e instância única = ponto único de falha.
- **Como funciona:** um distribuidor na frente de N instâncias idênticas e stateless, roteando por round-robin/least-connections, com **health checks** tirando instâncias doentes de rotação.
- **Exemplo:** ALB na frente de um serviço em ECS com auto-scaling. L4 (NLB, TCP) vs L7 (ALB, HTTP — path routing, headers, sticky sessions).
- **Trade-offs:** exige serviços **stateless** (estado vai para Redis/DB); sticky sessions quebram a elasticidade; o LB vira componente crítico (por isso é gerenciado/redundante).
- **Interview:** *"Load balancing spreads traffic across stateless replicas and, just as importantly, gives you health-checked failover. The prerequisite is externalizing state — the pattern is really 'statelessness + a distributor'."*

## 1.2 Pipes and Filters

- **Problema:** um processamento complexo feito num bloco monolítico — impossível reusar, escalar ou testar etapas isoladamente.
- **Como funciona:** decompor em **filters** (etapas independentes, cada uma faz UMA transformação) conectados por **pipes** (canais — filas). Cada filter escala independente.
- **Exemplo:** pipeline de ingestão: `validate → enrich → transform → persist`, cada etapa um consumer com uma SQS entre elas. Se `enrich` é o gargalo, escala só ele.
- **Trade-offs:** latência extra por hop; observabilidade distribuída necessária (correlation id); ordem/duplicatas entre etapas (idempotência!).
- **Interview:** *"Pipes and filters decomposes processing into independent stages connected by queues — each stage scales and fails independently. The cost is per-hop latency and needing correlation ids to trace one item through the pipeline."*

## 1.3 Scatter-Gather

- **Problema:** uma resposta depende de N fontes; consultá-las em série soma as latências.
- **Como funciona:** o requester **espalha** (scatter) a request para N workers/serviços **em paralelo** e **agrega** (gather) as respostas, geralmente com **timeout**: responde com o que chegou.
- **Exemplo:** busca de preço consultando 10 fornecedores em paralelo; ou uma query fan-out para N shards, agregando os resultados.
- **Trade-offs:** a latência total = a do **mais lento** (por isso timeout + resposta parcial); pressão de N chamadas simultâneas; agregação precisa lidar com falhas parciais.
- **Interview:** *"Scatter-gather parallelizes a request across many providers and aggregates the answers, usually with a deadline — you trade completeness for latency: answer with whoever responded in time."*

## 1.4 Execution Orchestrator 🔥

- **Problema:** um fluxo de negócio atravessa vários serviços com ordem, condições e falhas — quem coordena?
- **Como funciona:** um **orquestrador central** conhece o fluxo e comanda cada passo (chama serviço A, espera, decide, chama B...), mantendo o **estado do fluxo** e disparando compensações em falha.
- **Exemplo:** AWS **Step Functions** orquestrando: reservar estoque → cobrar → criar shipping; um `OrderOrchestrator` próprio; a Saga orquestrada (§2.2).
- **Trade-offs:** fluxo explícito, observável, fácil de alterar; MAS o orquestrador concentra lógica (risco de "god service") e é dependência de todos os passos.
- **Interview:** *"An orchestrator makes the workflow explicit: one component owns the sequence, the state and the failure handling. You gain visibility and control; you pay with a central brain that every step depends on."*

## 1.5 Choreography 🔥

- **Problema:** o mesmo fluxo, sem querer um cérebro central.
- **Como funciona:** cada serviço **reage a eventos** e publica os seus; o fluxo **emerge** das assinaturas. Ninguém conhece o processo inteiro.
- **Exemplo:** `OrderPlaced` → Payment cobra e publica `PaymentConfirmed` → Inventory reserva e publica `StockReserved` → Shipping despacha. Via EventBridge/SNS+SQS/Kafka.
- **Trade-offs:** baixo acoplamento, sem SPOF de lógica; MAS o fluxo é **implícito** — "onde parou o pedido 123?" exige tracing/correlação; mudanças no processo tocam vários serviços.
- **Interview (a comparação que SEMPRE cai):** *"Choreography for short, stable flows with few steps — it keeps services decoupled. Orchestration when the flow is long, branching, or operations needs to see and manage it. My rule of thumb: if I can't answer 'where is order 123 stuck?' easily, the flow outgrew choreography."*

---

# 2. PERFORMANCE PATTERNS FOR DATA-INTENSIVE SYSTEMS

## 2.1 MapReduce

- **Problema:** processar um volume de dados que não cabe numa máquina.
- **Como funciona:** **Map** — particionar os dados e aplicar uma função a cada pedaço em paralelo (N workers); **Shuffle** — agrupar resultados intermediários por chave; **Reduce** — agregar cada grupo.
- **Exemplo:** contar eventos por tipo em 10TB de logs: mappers emitem `(tipo, 1)` por linha, reducers somam por tipo. Hoje: EMR/Spark, Athena (SQL que vira scatter-gather+reduce por baixo).
- **Trade-offs:** brilha em batch massivo paralelizável; overhead alto para dados pequenos ou baixa latência (aí é streaming — Kinesis/Flink).
- **Interview:** *"MapReduce parallelizes big-data processing: map applies a function over partitions in parallel, shuffle groups by key, reduce aggregates. It's a batch pattern — for a few gigabytes or low latency, it's overkill."*

## 2.2 Saga 🔥

- **Problema:** uma "transação" atravessa N serviços com N bancos — não há ACID distribuído; 2PC bloqueia e não escala.
- **Como funciona:** sequência de **transações locais**; cada passo commita no seu serviço; se um passo falha, executam-se **compensações** (transações que desfazem semanticamente os passos anteriores). Dois sabores: **orquestrada** (§1.4) ou **coreografada** (§1.5).
- **Exemplo:** pedido: `charge payment` → `reserve stock` → `create shipment`. Falhou o estoque? Compensação: `refund payment`.
- **Trade-offs:** sem isolamento entre passos (estados intermediários visíveis — eventual consistency); compensações precisam existir E poder falhar também (retry + idempotência); nem tudo é compensável (email enviado) → ordene os passos do mais reversível para o menos.
- **Interview:** *"A saga replaces a distributed transaction with a chain of local transactions plus compensations. The honest costs: no isolation — other services see intermediate states — and every step needs a designed 'undo'. I order steps so the hardest-to-compensate action goes last."*

## 2.3 Transactional Outbox 🔥🔥

- **Problema:** salvar no banco **e** publicar um evento — dois sistemas, sem transação atômica entre eles (**dual-write problem**). Commit + broker fora do ar = evento perdido; publicar antes + rollback = evento mentiroso.
- **Como funciona:** o evento é gravado numa tabela **outbox** na MESMA transação local do estado. Um **relay** (polling ou CDC na outbox) publica depois e marca como enviado.
- **Exemplo:** `INSERT INTO orders ...; INSERT INTO outbox (event) ...; COMMIT;` → relay lê a outbox e publica no SNS/Kafka. Debezium Outbox SMT faz isso via CDC.
- **Trade-offs:** entrega **at-least-once** → consumers idempotentes obrigatórios; o relay é um componente a operar; latência pequena entre commit e publicação.
- **Interview:** *"The outbox solves the dual-write between database and broker: the event is committed atomically with the state, in an outbox table, and a relay publishes it afterwards. Delivery becomes at-least-once, so consumers dedupe — that's the price of atomicity."*
- **🔥 Conexão com a vaga:** é o mesmo dual-write problem da migração de banco (aula 06) — cite a analogia.

## 2.4 Materialized View 🔥

- **Problema:** uma leitura frequente exige query cara (joins + agregações) toda vez.
- **Como funciona:** **pré-computar** o resultado e armazenar como dado consultável; atualizar por refresh periódico ou incrementalmente por eventos. É trocar custo de leitura por custo de escrita + staleness.
- **Exemplo:** dashboard "receita por dia": `REFRESH MATERIALIZED VIEW CONCURRENTLY` no Postgres a cada 15 min; ou uma tabela `customer_stats` atualizada por consumer de eventos.
- **Trade-offs:** dados **stale** (defina o SLA de frescor com o negócio!); custo de manter; refresh full vs incremental.
- **Interview:** *"A materialized view precomputes an expensive read and serves it as data. The design question is freshness: how stale can this number be? That answer decides between periodic refresh and event-driven incremental updates."*

## 2.5 CQRS 🔥

- **Problema:** o modelo bom para **escrever** (normalizado, consistente, com invariantes) é ruim para **ler** (joins caros, shapes diferentes por tela), e leitura/escrita escalam diferente (tipicamente 100:1).
- **Como funciona:** **separar** o caminho de comando (write model) do caminho de consulta (read model) — no mínimo classes/handlers separados; no máximo **bancos separados**, com o read model alimentado por eventos do write model.
- **Exemplo:** writes de pedidos no Postgres normalizado; um consumer projeta eventos para um read model desnormalizado (outra tabela, Elasticsearch, DynamoDB) que serve as telas de listagem/busca.
- **Trade-offs:** read model é **eventualmente consistente** (UX: read-your-writes?); duplicação de dados; mais infraestrutura. **Não use** onde CRUD simples resolve — CQRS por moda é o anti-pattern clássico.
- **Interview:** *"CQRS separates the write model — normalized, guarding invariants — from read models shaped for each query and scaled independently. It earns its complexity when read and write needs genuinely diverge; for plain CRUD it's pure overhead."*

## 2.6 CQRS + Materialized View para Microservices 🔥

- **Problema:** com database-per-service, uma tela precisa de dados de 3 serviços — e **não existe JOIN cross-service**. Chamar 3 APIs síncronas por request = latência somada + acoplamento.
- **Como funciona:** os serviços publicam eventos (via outbox!); um serviço de leitura consome e mantém uma **view materializada composta** (o "join" é pré-computado na escrita). A query vira um lookup local.
- **Exemplo:** `OrderHistoryView` combinando Orders + Payments + Shipping: 3 consumers alimentam uma tabela desnormalizada; a UI lê de um lugar só.
- **Trade-offs:** eventual consistency; reprocessamento/rebuild da view precisa ser possível (replay de eventos); ownership da view (de quem é o bug quando o dado diverge?).
- **Interview:** *"Since there are no cross-service joins, I precompute the join: each service publishes events and a read service maintains a composed, denormalized view. Queries become local lookups; the price is eventual consistency and owning a rebuildable projection."*

## 2.7 Event Sourcing

- **Problema:** o UPDATE destrói história — "como o saldo chegou nesse valor?" não tem resposta; auditoria vira gambiarra.
- **Como funciona:** persistir **os eventos** (fatos imutáveis, append-only) em vez do estado; o estado atual é a **redução** (fold) dos eventos; **snapshots** aceleram a reconstrução.
- **Exemplo:** conta bancária como `AmountDeposited`, `AmountWithdrawn`...; saldo = replay. Ledger contábil é event sourcing avant la lettre.
- **Trade-offs:** auditoria e replay de graça, débito temporal ("estado em qualquer ponto do tempo"); MAS: consultas exigem projeções (casa com CQRS quase obrigatoriamente), evolução de schema de eventos é difícil (versionamento), curva de aprendizado alta. **Não é default** — use onde a história É o domínio (financeiro, auditoria).
- **Interview:** *"Event sourcing stores the facts, not the state — state is a fold over the events. You get audit and time travel for free, but querying needs projections, so it almost always pairs with CQRS. I'd use it where history is the domain — ledgers, compliance — not as a default."*

---

# 3. SOFTWARE EXTENSIBILITY PATTERNS

## 3.1 Sidecar & Ambassador

- **Problema:** funcionalidades transversais (TLS, métricas, retry, service discovery) reimplementadas em cada serviço, em cada linguagem.
- **Como funciona:** **Sidecar** — um processo/container auxiliar **colado** ao serviço (mesmo pod/task), oferecendo a funcionalidade fora do código do app. **Ambassador** — sidecar especializado em **proxy de saída**: o app fala com `localhost`, o ambassador cuida de retry, TLS, circuit breaking, roteamento.
- **Exemplo:** Envoy como sidecar (base de service meshes — Istio, App Mesh); agente de observabilidade (CloudWatch/OTel collector) ao lado da task ECS; Fluent Bit para logs.
- **Trade-offs:** tira cross-cutting do código (poliglota, upgrade central); MAS +latência por hop, +recursos por instância, +complexidade operacional (a "malha" precisa de dono).
- **Interview:** *"A sidecar attaches cross-cutting capabilities as a separate container next to the service; an ambassador is the outbound-proxy flavor — the app talks to localhost and the proxy handles TLS, retries, circuit breaking. It's how service meshes move resilience out of application code."*

## 3.2 Anti-Corruption Layer 🔥🔥 (Adapter arquitetural)

- **Problema:** integrar com um sistema legado (ou externo) cujo modelo é confuso/diferente — e o modelo dele começa a **vazar** para dentro do seu domínio, corrompendo-o.
- **Como funciona:** uma camada de tradução na fronteira: converte modelo legado ↔ seu modelo limpo. Seu domínio só conhece o próprio vocabulário. É o Adapter (aula 08) elevado a fronteira arquitetural.
- **Exemplo 🔥 direto da vaga:** durante a migração, o serviço novo lê o schema legado através de uma ACL que traduz para o modelo novo — quando o legado for desligado, **só a ACL morre**, o domínio não muda.
- **Trade-offs:** código de tradução para manter (é o preço de não apodrecer o domínio); mapeamentos podem ficar complexos.
- **Interview:** *"An anti-corruption layer is a translation boundary that keeps a legacy or third-party model from leaking into my domain. In a migration it's what makes the legacy schema disposable: the domain speaks its own language, only the ACL knows the old one, and it dies with the legacy system."*

## 3.3 Backends for Frontends (BFF)

- **Problema:** um API gateway único servindo web, mobile e parceiros vira campo de batalha: cada frontend quer shapes, agregações e auth diferentes.
- **Como funciona:** **um backend por tipo de frontend** (BFF web, BFF mobile), cada um agregando/adaptando os serviços de domínio para as necessidades DAQUELA experiência, mantido pelo time daquele frontend.
- **Exemplo:** BFF mobile agrega 4 chamadas numa resposta enxuta (payload/battery matters); BFF web expõe shapes ricos para a SPA.
- **Trade-offs:** N backends para manter; risco de lógica de negócio escorregar para o BFF (deve ficar nos serviços de domínio); duplicação entre BFFs.
- **Interview:** *"A BFF is an aggregation layer per frontend experience, owned by the frontend team — it shapes and composes domain APIs for that client. The discipline is keeping business logic in the domain services; the BFF only adapts and aggregates."*

---

# 4. RELIABILITY, ERROR HANDLING & RECOVERY

## 4.1 Throttling & Rate Limiting

- **Problema:** demanda acima da capacidade — um cliente abusivo, um pico, um retry storm — derruba o serviço para todos.
- **Como funciona:** limitar a taxa aceita: **rejeitar** (429 + `Retry-After`), **enfileirar** (buffer) ou **degradar**. Algoritmos: token bucket (permite bursts), sliding window. Por cliente/API key/global. **Load shedding** = a variante "rejeitar para sobreviver".
- **Exemplo:** API Gateway com usage plans por key; rate limiter no Redis (contador + janela); SQS entre produtor e consumer como buffer natural.
- **Trade-offs:** rejeitar é melhor do que cair — mas defina O QUE rejeitar (prioridade); limites mal calibrados punem clientes legítimos.
- **Interview:** *"Rate limiting protects the service from demand spikes and abusive clients — reject with 429 and Retry-After, buffer through a queue, or shed load. Failing fast for some beats falling over for everyone."*

## 4.2 Retry (com backoff + jitter)

- **Problema:** falhas transientes (rede, timeout, throttling) resolveriam sozinhas — mas retry ingênuo cria **retry storm**: todos tentam de novo ao mesmo tempo e pioram a avalanche.
- **Como funciona:** retry **apenas** para erros transientes/idempotentes, com **exponential backoff** (1s, 2s, 4s...) + **jitter** (aleatoriedade para dessincronizar os clientes) + **limite de tentativas** + depois DLQ/falha.
- **Exemplo:** Polly no .NET: `WaitAndRetryAsync` com backoff+jitter; SDK da AWS já embute. ⚠️ retry de POST não-idempotente = cobrança dupla — idempotency key antes.
- **Trade-offs:** retries multiplicam carga sobre um sistema já sofrendo (por isso casam com circuit breaker); cuidado com **retries em cascata** (cada camada 3× = 27× na ponta).
- **Interview:** *"Retries handle transient faults — with exponential backoff and jitter so clients don't synchronize into a storm, a cap on attempts, and only on idempotent operations. And I watch for retry amplification across layers: three layers of three retries is twenty-seven calls downstream."*

## 4.3 Circuit Breaker

- **Problema:** dependência caída + timeouts longos = threads presas, filas crescendo, **falha em cascata**; e o marteladas de retry impedem a dependência de se recuperar.
- **Como funciona:** monitora falhas; acima do limiar **abre** (falha instantânea, sem chamar); após um tempo, **half-open** deixa passar chamadas de teste; sucesso → **fecha**. Estados: Closed → Open → Half-Open.
- **Exemplo:** Polly `CircuitBreakerAsync`; com **fallback**: resposta de cache, default, degradação graciosa ("recomendações indisponíveis, catálogo ok").
- **Trade-offs:** thresholds mal calibrados = breaker abrindo à toa (flapping); precisa de métricas para observar os estados; por-dependência, não global.
- **Interview:** *"A circuit breaker fails fast when a dependency is unhealthy — protecting my threads and giving the dependency room to recover — then probes with half-open before closing. It pairs with retry: retry handles blips, the breaker handles outages."*

## 4.4 Dead Letter Queue (DLQ)

- **Problema:** uma mensagem que **sempre** falha (poison message) trava/loopa o consumer para sempre e esconde falhas sistêmicas.
- **Como funciona:** após N tentativas (`maxReceiveCount` no SQS), a mensagem vai para uma fila separada; um **alarme** dispara; humanos/automação inspecionam, corrigem a causa e fazem **replay**.
- **Exemplo:** SQS redrive policy → DLQ + CloudWatch alarm em `ApproximateNumberOfMessagesVisible > 0`; replay com redrive para a fila original após o fix.
- **Trade-offs:** DLQ sem alarme e sem processo de replay é um cemitério de dados — o pattern é o **processo**, não a fila; mensagens na DLQ podem estar fora de ordem quando reprocessadas.
- **Interview:** *"A DLQ quarantines messages that keep failing so they don't block the queue, and turns silent failure into an alarm. The pattern is really the process around it: alert, diagnose, fix, replay — a DLQ nobody drains is just a data graveyard."*

---

# 5. DEPLOYMENT & PRODUCTION TESTING

## 5.1 Rolling Deployment

- **Como funciona:** substituir instâncias **gradualmente** (1 a N por vez) atrás do LB — sem downtime, sem dobrar infra.
- **⚠️ A consequência que separa senior:** durante o rollout, **versão velha e nova coexistem** → toda mudança de schema/API/mensagem precisa ser **backward-compatible** (expand → migrate → contract).
- **Trade-offs:** rollback = rolar de volta (lento); durante o rollout, comportamento misto dificulta debug.
- **Interview:** *"Rolling deployment replaces instances gradually behind the load balancer — no downtime, no double infrastructure. The real implication: old and new versions run side by side, so every schema and API change must be backward-compatible."*

## 5.2 Blue-Green Deployment

- **Como funciona:** dois ambientes completos; **Green** recebe a versão nova, é testado, e o tráfego **vira de uma vez** (DNS/LB). Blue fica de prontidão.
- **Trade-offs:** rollback quase instantâneo (virar de volta) e ambiente de verificação real; MAS custo 2× durante a janela, e **o banco é o problema**: os dois ambientes compartilham o banco → mesma exigência de compatibilidade de schema; virar "tudo de uma vez" = blast radius de 100% se algo escapou.
- **Interview:** *"Blue-green keeps two full environments and flips traffic atomically — near-instant rollback. The catch people miss: the database is usually shared, so schema changes still need to be compatible with both versions, and the flip is all-or-nothing risk."*

## 5.3 Canary Release + A/B Testing

- **Como funciona (canary):** versão nova recebe uma **fração** do tráfego (1% → 5% → 25% → 100%), com **métricas comparadas** (erro, p99, negócio) contra a versão atual; regressão → rollback automático afetando só a fração. É o **blast radius controlado**.
- **A/B testing:** mesma mecânica de split, mas o objetivo é **medir comportamento de produto** (conversão) entre variantes — decisão de negócio, não de saúde de deploy.
- **Trade-offs:** exige métricas boas e comparáveis (senão o canary é teatro); sessões precisam de consistência (usuário não deve alternar entre versões); duas versões vivas por mais tempo.
- **Interview:** *"Canary shifts a small, growing slice of real traffic to the new version while comparing error rates, latency and business metrics — the blast radius is the slice. A/B testing uses the same traffic-splitting machinery but answers a product question, not a deployment-health question."*
- **🔥 Conexão com a vaga:** o cutover da migração de banco É um canary — flip de reads por % com mismatch metrics como métrica de comparação (aula 14).

## 5.4 Chaos Engineering

- **Como funciona:** injetar falhas **deliberadamente e de forma controlada** (matar instâncias, adicionar latência, derrubar uma AZ/dependência) para **verificar hipóteses de resiliência** antes que a produção as teste por você. Método: hipótese ("se a réplica cair, failover em <30s sem erro para o usuário") → experimento com blast radius mínimo → medir → corrigir → ampliar.
- **Exemplo:** AWS Fault Injection Service; o clássico Chaos Monkey; game days.
- **Trade-offs:** exige observabilidade madura e botão de abort; começa em staging, mas o valor real é produção (com guarda-rails); cultura antes de ferramenta.
- **Interview:** *"Chaos engineering tests resilience hypotheses by injecting controlled failures — kill an instance, add latency, drop a dependency — with a minimal blast radius and an abort switch. It converts 'we think we survive a failover' into evidence, before an outage runs the experiment for you."*

---

## 🗺️ Mapa mental — como esses patterns se conectam (decore as setas)

```text
Load Balancer → exige stateless → estado externalizado (Redis/DB)

Microservices + database-per-service
        → sem JOIN cross-service → CQRS + Materialized View (consumers projetam)
        → sem transação distribuída → Saga (+ compensações)
        → estado + evento atômicos → Transactional Outbox
        → fluxo multi-serviço → Orchestration vs Choreography

Chamada a dependência instável → Retry (backoff+jitter) → Circuit Breaker → Fallback
Consumo de fila → retries → DLQ + alarme + replay → consumer idempotente

Sistema legado na fronteira → Anti-Corruption Layer
Migração incremental → Strangler Fig (aula 07) → cutover como Canary
Deploy sem downtime → Rolling/Blue-Green/Canary → schema backward-compatible (expand→migrate→contract)
Resiliência declarada → Chaos Engineering prova
```

---

## ✏️ Exercícios

1. **Orchestration vs Choreography** — em inglês, 60s: quando cada um, com o critério prático ("where is order 123 stuck?").
2. **Outbox de memória** — desenhe (texto) o fluxo completo: transação → outbox → relay → broker → consumer idempotente. Onde entra at-least-once? Onde entra a dedup?
3. **Cadeia de resiliência** — seu serviço chama um gateway de pagamento instável. Componha: retry, circuit breaker, timeout, fallback, DLQ. **Em que ordem e por quê?** (ex.: timeout por tentativa < retry por fora do quê? breaker conta o quê?)
4. **CQRS honesto** — em inglês: *"When would you NOT use CQRS?"* — cite o custo (eventual consistency, infra, read-your-writes) e o cenário onde CRUD ganha.
5. **Deploy da migração** — qual estratégia de deployment você usaria para o cutover de reads da migração de banco, e por quê ela é um canary disfarçado?
6. **Saga com falha na compensação** — o refund (compensação) também falhou. E agora? (retry + idempotência da compensação, DLQ, intervenção humana como último passo DESENHADO, não improvisado.)

---

## ✅ Respostas / avaliação

*(Gabarito em `respostas/13-respostas.md` — só depois de tentar.)*
