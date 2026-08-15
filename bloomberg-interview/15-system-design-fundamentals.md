# Aula 15 — System Design Fundamentals (o alicerce)

> Arquivo de referência rápida: os 20 blocos fundamentais de system design, cada um com o essencial para **raciocinar e citar em entrevista**. Você já domina vários (queues, caching básico) — neles, só afie o vocabulário. Onde conecta com outra aula do curso, está indicado.

---

## 1. Computer Architecture (o que importa para design)

A hierarquia que explica quase toda decisão de performance:

| Camada | Latência típica | Nota |
|---|---|---|
| CPU cache (L1/L2) | ~1 ns | |
| RAM | ~100 ns | |
| SSD read | ~100 µs | 1.000× a RAM |
| Disco magnético seek | ~10 ms | |
| Round-trip mesmo datacenter | ~0.5 ms | |
| Round-trip inter-região (ex: US↔EU) | ~80-150 ms | |

**As 3 conclusões de entrevista:** (1) **RAM é ouro** — por isso caching funciona; (2) **round-trips dominam** — por isso batching, N+1 e chattiness importam mais que CPU; (3) **IO sequencial >> IO aleatório** — por isso logs append-only (Kafka, WAL, LSM trees) são rápidos.

> *"Most system design decisions are about avoiding the slow layers: cache instead of disk, batch instead of round-trips, sequential instead of random IO."*

## 2. Application Architecture (a evolução canônica)

```text
1 servidor (app+DB juntos)
 → separar app e DB (escalam diferente)
 → vertical scaling (máquina maior — limite e $$$)
 → horizontal scaling (N servidores STATELESS) + Load Balancer
 → cache (Redis) + CDN (estáticos)
 → réplicas de leitura do DB → sharding
 → filas para trabalho assíncrono → microservices (por time/domínio, não por moda)
```

**Regra:** servidores stateless (estado em Redis/DB) é o pré-requisito do scaling horizontal. **Microservices resolvem problema de organização (times, deploys independentes), não de performance** — dizer isso em entrevista vale ponto.

## 3. Design Requirements (como abrir QUALQUER pergunta de design)

- **Functional** — o que o sistema faz (features). Escolha 2-3 core, corte o resto em voz alta.
- **Non-functional** — como: scale (DAU, QPS), latência (p99!), disponibilidade, consistência, durabilidade, custo.
- **Back-of-envelope:** DAU × ações/dia ÷ 86.400 ≈ QPS (dia ~10⁵ s facilita); pico ≈ 2-5× média; storage = itens/dia × tamanho × retenção. **Read:write ratio** define a arquitetura (100:1 → cache pesado).
- **Availability:** 99,9% = ~8,7h down/ano; 99,99% = ~52min. Cada "nove" custa uma ordem de complexidade.
- Números úteis: 1M req/dia ≈ **12 QPS** (surpreendentemente pouco!); char = 1 byte; ID = 8 bytes; timestamp = 4-8 bytes.

> *"I always anchor on read:write ratio, p99 latency target, and whether we need strong or eventual consistency — those three decide most of the architecture."*

## 4. Networking Basics

- **IP** — endereçamento e roteamento de **pacotes** (best-effort, sem garantias). IPv4 (esgotado, NAT) vs IPv6.
- **Portas** — múltiplos serviços por host (80 HTTP, 443 HTTPS, 5432 Postgres).
- Modelo mental em 3 camadas (basta para entrevista): **network** (IP — leva o pacote), **transport** (TCP/UDP — garantias de entrega), **application** (HTTP, DNS, gRPC — semântica).
- **Public vs private IP**, e por que seus serviços ficam em subnets privadas atrás de um LB público.

## 5. TCP vs UDP

| | TCP | UDP |
|---|---|---|
| Conexão | 3-way handshake (SYN, SYN-ACK, ACK) | nenhuma |
| Garantias | entrega, **ordem**, retransmissão, congestion control | nenhuma — fire and forget |
| Custo | handshake (1 RTT+), overhead de estado | mínimo |
| Uso | HTTP, DBs, filas — quase tudo | vídeo/voz ao vivo, games, DNS, telemetria |

> *"TCP when correctness matters, UDP when latency beats completeness — a lost frame in a video call is better skipped than retransmitted late."*

(QUIC/HTTP-3 = "TCP-like sobre UDP" — cite só se perguntarem.)

## 6. DNS

Resolução: browser cache → OS cache → **recursive resolver** (ISP/8.8.8.8) → root → TLD (.com) → **authoritative** nameserver → IP. Tudo cacheado com **TTL**.

- **A record** = nome → IPv4 (AAAA = IPv6); **CNAME** = nome → nome.
- Design relevante: TTL baixo = failover rápido mas mais queries; **DNS-based load balancing/geo-routing** (Route 53) é o primeiro nível de distribuição global.
- ⚠️ Propagação: mudou o registro ≠ todos veem — caches respeitam o TTL antigo. (Conecta com blue-green via DNS: rollback não é instantâneo — por isso flip por LB/flag é melhor.)

## 7. HTTP

- Request/response **stateless** sobre TCP: método + path + headers + body → status + headers + body.
- **Métodos e semântica** (cai em API design): GET (safe, cacheável), POST (não idempotente), **PUT (idempotente!)**, PATCH, DELETE (idempotente).
- **Status codes:** 200/201/204 · 301 (moved, cacheável) vs 302 (temporary) · 304 (not modified — cache) · 400/401/403/404/409 (conflict) · **429 (too many requests)** · 500/502/503/504.
- **HTTPS** = HTTP sobre TLS.
- HTTP/1.1: 1 request por vez por conexão (head-of-line) → HTTP/2: multiplexação na mesma conexão.
- Headers de cache: `Cache-Control`, `ETag` (→ §11).

## 8. WebSockets (e as alternativas)

O problema: servidor precisa **empurrar** dados (chat, notificações, live) — HTTP é pull.

| Técnica | Como | Custo |
|---|---|---|
| **Polling** | cliente pergunta a cada Xs | latência média X/2, requests vazios |
| **Long polling** | servidor segura a request até ter dado | 1 request pendurada por cliente; simples |
| **WebSockets** | upgrade da conexão HTTP → canal **full-duplex persistente** | estado no servidor: milhões de conexões = memória, e LB precisa de sticky/gateway dedicado |
| **SSE** | stream servidor→cliente sobre HTTP | só uma direção; simples; bom para feeds/notificações |

> *"WebSockets for bidirectional real-time — chat, presence. SSE when only the server pushes. Long polling as the lowest-infra fallback. The hidden cost of WebSockets is that connections are state: you need connection-aware gateways and a pub/sub backbone behind them."* (→ Design Discord, aula 16.)

## 9. API Paradigms

- **REST** — recursos + verbos HTTP + stateless; cacheável, universal. Fraqueza: **over/under-fetching** (tela precisa de 3 recursos = 3 round-trips).
- **GraphQL** — cliente declara o shape; 1 request, sem over-fetch. Custos: caching HTTP difícil, queries caras imprevisíveis (N+1 no resolver!), complexidade no servidor. Brilha para frontends variados (≈ alternativa ao BFF).
- **gRPC** — HTTP/2 + protobuf: binário, rápido, contrato forte, streaming bidirecional. Ideal **service-to-service interno**; ruim para browser (precisa proxy).

> *"REST for public APIs — ubiquity and cacheability; gRPC for internal service-to-service — performance and contracts; GraphQL when diverse clients need flexible shapes and I'm willing to pay the server-side complexity."*

## 10. API Design

O que entrevistador quer ver quando pede "define the API":

- **Recursos e verbos:** `POST /videos`, `GET /videos/{id}`, `GET /users/{id}/videos?limit=20&cursor=...`
- **Paginação por cursor** (keyset! — aula 05), não offset — e por quê.
- **Idempotência:** PUT idempotente por definição; POST de pagamento → **idempotency key** no header.
- **Versionamento:** `/v1/` no path (pragmático) — e a regra de ouro: **mudanças backward-compatible sempre que possível** (adicionar campo ok; renomear/remover = breaking).
- **Erros consistentes** (problem details), **rate limit headers** (429 + `Retry-After`).
- Nunca expor IDs sequenciais do banco (enumeração) — UUID/opaque IDs.

## 11. Caching 🔥 (aparece em TODO design)

- **Onde:** browser (Cache-Control/ETag) → CDN → API/app cache (Redis) → DB internals.
- **Padrões de escrita:**
  - **Cache-aside** (o default): app lê cache; miss → lê DB → popula cache. Escritas invalidam a chave.
  - **Write-through:** escreve cache+DB juntos — leitura sempre quente, escrita mais lenta.
  - **Write-back:** escreve só no cache, flush assíncrono para o DB — rápido e **arriscado** (perda em crash).
- **Eviction:** LRU (default), LFU, TTL.
- **Os problemas clássicos (cite-os você mesmo):** **invalidation** ("one of the two hard problems"), **stale reads**, **thundering herd/stampede** (chave quente expira → mil misses simultâneos batem no DB; mitigação: lock/single-flight, TTL com jitter, refresh antecipado), **hot key** (celebridade → réplicas da chave).
- Métricas: **hit ratio** é A métrica; medir antes/depois.

> *"Caching buys latency and DB offload at the price of staleness — so the first question is always: how stale can this data be?"* (→ Materialized View, aula 13 — mesmo trade-off.)

## 12. CDN

- Edge servers geograficamente distribuídos servindo conteúdo **cacheável** perto do usuário — corta o round-trip inter-continental (§1).
- **Pull** (default): edge busca da origin no primeiro miss, cacheia por TTL. **Push:** você faz upload para as edges (releases grandes previsíveis).
- Serve: estáticos (JS/CSS/imagens), **vídeo** (chunks HLS/DASH — Design YouTube), e aceleração/WAF para APIs dinâmicas (CloudFront).
- Invalidation: versionar a URL (`app.v42.js`) >> purge manual.

## 13. Proxies & Load Balancing

- **Forward proxy** — na frente do **cliente** (esconde o cliente; egress corporativo). **Reverse proxy** — na frente do **servidor** (esconde/protege servidores): LB, TLS termination, cache, WAF — nginx, ALB.
- **Algoritmos de LB:** round robin · weighted · **least connections** (melhor com requests de duração variável) · IP hash (afinidade) · **consistent hashing** (→ §14).
- **L4 vs L7:** L4 (TCP, NLB) — rápido, cego ao conteúdo; L7 (HTTP, ALB) — path routing, headers, cookies, custo maior.
- **Health checks** ativos tiram instância doente de rotação — LB é também **ferramenta de disponibilidade**, não só de escala.
- O LB não pode ser SPOF: pares redundantes / anycast / gerenciado.

## 14. Consistent Hashing 🔥

**Problema:** distribuir chaves entre N servidores com `hash(key) % N` — quando N muda (scale up/down, falha), **quase todas** as chaves mudam de dono → cache inteiro invalidado / rebalanceamento massivo.

**Solução:** um **anel** (0 → 2³²); servidores e chaves são hasheados para posições no anel; cada chave pertence ao **primeiro servidor no sentido horário**. Adicionar/remover um servidor move apenas **~1/N das chaves** (as do vizinho).

**Virtual nodes:** cada servidor físico aparece em ~100-200 pontos do anel → distribuição uniforme e rebalanceamento suave (sem vnodes, um servidor que sai despeja tudo num único vizinho).

**Onde aparece:** caches distribuídos (Memcached), Cassandra/DynamoDB (partitions), LBs com afinidade, **Design Key-Value Store** (aula 16).

> *"Consistent hashing makes membership changes cheap: only 1/N of the keys move, and virtual nodes keep the load even. It's the answer whenever the interviewer asks 'what happens when you add a cache server?'"*

## 15. SQL (o resumo para design — profundidade nas aulas 01-05)

- **B+ tree** indexes: leituras e range scans O(log n); escrita paga manutenção de índice.
- **ACID** com transações multi-row e **constraints** — integridade que NoSQL não dá de graça.
- Escala: read replicas (fácil) → sharding (difícil: sem JOINs cross-shard, sem transações cross-shard, resharding doloroso).
- **Default de entrevista:** *"I start with a relational database unless the access patterns or scale argue otherwise — flexibility of queries is worth a lot."*

## 16. NoSQL + Replication + Sharding

**Famílias:** key-value (Redis, Dynamo) · document (Mongo) · **wide-column** (Cassandra — escrita massiva, LSM) · graph (Neo4j). Traço comum: abrem mão de JOINs/transações ricas por **escala horizontal e modelo flexível** — design por access patterns (aula 11).

**Replication:**
- **Leader-follower:** escritas no leader, leituras nas réplicas. **Sync** (durável, lento) vs **async** (rápido, risco de perda no failover + **replication lag** → read-your-writes problem).
- **Multi-leader / leaderless (Dynamo-style):** escreve em qualquer nó + **quorum**: `N` réplicas, escreve em `W`, lê de `R`; **`R + W > N` ⇒ leitura vê a escrita mais recente**. Ajuste fino de consistência vs latência.

**Sharding:**
- **Por range** (scans bons; risco de hot shard — datas!) vs **por hash** (uniforme; range queries ruins) — com consistent hashing para membership.
- A **shard key** é a decisão: deve distribuir uniformemente E servir os access patterns (= partition key do Dynamo, hot partitions — aula 11).

## 17. CAP Theorem

Durante uma **partição de rede** (P — que você não escolhe: ela acontece), escolha: **C**onsistency (recusar responder para não responder errado) ou **A**vailability (responder, possivelmente stale).

- **CP:** sistemas de coordenação/dinheiro (Zookeeper; bancos com quorum estrito).
- **AP:** carrinho de compras, feeds, DNS, Cassandra/Dynamo default — melhor stale do que fora do ar.
- **PACELC** (o upgrade de senior): **sem** partição, o trade-off vira **L**atency vs **C**onsistency — replicação sync custa latência sempre, não só em falha.

> *"CAP is about behavior during a partition — and PACELC reminds us we pay the consistency-vs-latency tax even without one. Per feature, not per system: the same product can serve the feed AP and process payments CP."*

## 18. Object Storage

- **S3 e afins:** blobs imutáveis em namespace flat (key → object), acesso HTTP, **durabilidade absurda** (11 noves via replicação/erasure coding), barato, escala "infinita".
- **Não é** filesystem (sem append/edit parcial — reescreve o objeto) **nem** DB (sem queries — metadata vai num DB apontando para a key).
- Uso em design: vídeos, imagens, backups, data lake. Padrão-ouro: **presigned URLs** — o cliente faz upload/download **direto no S3**, sem passar bytes pelos seus servidores (→ Design YouTube/Drive).
- Tiers (Standard → Glacier) para custo por acesso.

## 19. Message Queues (seu território — só o vocabulário de design)

- **Por quê:** desacoplar produtor/consumidor, absorver picos (buffer), trabalho assíncrono, retry — disponibilidade e elasticidade.
- **Modelos:** point-to-point (SQS — 1 consumer group) vs **pub/sub** (SNS/EventBridge/Kafka — N assinantes).
- **Log-based (Kafka)** vs **queue-based (SQS/Rabbit)**: o log **retém** mensagens (replay, múltiplos consumer groups com offsets próprios, ordem por partição) — a fila deleta após consumo.
- Garantias: at-least-once (default; → idempotência) · at-most-once · "exactly-once" (na prática: **effectively-once** = at-least-once + dedup).
- Ordering: por **partição/message group**, nunca global (ordem global = throughput de 1).
- (Profundidade: aulas 07, 11, 13; internals → Design Distributed Queue, aula 16.)

## 20. MapReduce (resumo — detalhes na aula 13 §2.1)

Map (paralelo por partição) → shuffle (agrupa por chave) → reduce (agrega). **Batch** sobre dados massivos; para latência baixa/contínua → **streaming** (Kinesis/Flink/Spark Streaming). Em entrevista de design aparece como: *"analytics/relatórios pesados saem do caminho quente — batch/streaming pipeline sobre o data lake, não queries no OLTP."*

---

## 🎯 Como usar este arquivo

1ª passada: leia tudo (~40 min). 2ª passada: para cada seção, **feche o arquivo e fale a frase de entrevista em inglês** de memória. Os que travearem → releia só eles. Este arquivo alimenta diretamente a aula 16 — cada design de lá referencia estes blocos.
