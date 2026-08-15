# Aula 16 — System Design: os 9 clássicos no whiteboard

> Cada design segue o mesmo esqueleto (use-o SEMPRE, é o framework da aula 18/06): **Clarify → Estimates → API → High-level design → Deep dives → Trade-offs**. Treine: leia um design, feche, e reproduza o desenho + os deep dives de memória. As referências (§) apontam para a aula 15.

---

# 1. Design a Rate Limiter 🔥 (favorito para "technical + architectural")

**Clarify:** limitar por quê (proteção? billing?), por chave (user? IP? API key?), regras (100 req/min por user), resposta ao exceder (**429 + Retry-After** — §7), hard vs soft limit, onde (edge? gateway? por serviço?).

**Algoritmos (saiba comparar 3):**
- **Fixed window** — contador por janela (`user:minuto → count`). Simples; ⚠️ **burst na borda**: 100 às 10:00:59 + 100 às 10:01:01 = 200 em 2s.
- **Sliding window log** — timestamp de cada request; janela exata; caro em memória.
- **Token bucket** ⭐ — balde com capacidade B, reabastece a R tokens/s; request consome 1; sem token → rejeita. Permite **bursts controlados** (B) com taxa média R. 2 números por chave — barato. É o que AWS usa.

**High-level:**

```text
client → API Gateway/middleware → [rate limiter check] → serviço
                                        │
                                        ▼
                                  Redis (contadores)
                                  INCR + EXPIRE / token bucket em Lua
```

**Deep dives (onde a entrevista acontece):**
- **Atomicidade:** read-modify-write no Redis = race → **script Lua** (atômico) ou `INCR` (já atômico) + `EXPIRE`.
- **Distribuído:** N gateways compartilham o Redis → consistente mas +1 hop por request. Alternativa: contadores **locais com sync assíncrono** — mais rápido, levemente impreciso. *"For protection, approximate is fine; for billing, it isn't"* — frase de ouro.
- **Redis caiu?** Fail-open (deixa passar — proteção some) vs fail-closed (bloqueia tudo — derruba o site). Para proteção: **fail-open com alarme**.
- **Escala:** shard dos contadores por user key (consistent hashing — §14); TTL limpa chaves sozinho.
- Devolver headers: `X-RateLimit-Remaining`, `Retry-After` — clientes bem-comportados fazem backoff (aula 13: retry storm).

---

# 2. Design TinyURL

**Clarify:** tamanho do alias (7 chars?), custom aliases? expiração? analytics de cliques? **Read:write ~100:1** — read-heavy define tudo. Escala: 100M novas URLs/mês ≈ 40 writes/s, ~4k reads/s.

**API:** `POST /urls {long_url} → {short}` · `GET /{short} → 301/302 long_url`

**A decisão central — gerar o código:**
- Hash (MD5 truncado): colisões → re-hash loop. Ok, mas...
- ⭐ **Counter global + Base62**: ID único crescente → codifica em `[a-zA-Z0-9]` (62⁷ ≈ 3,5 **trilhões**). Sem colisão por construção. Counter distribuído: **ranges pré-alocados** por instância (svc A: 1-1M, svc B: 1M-2M) — sem coordenação por request. (= Key Generation Service.)
- ⚠️ Sequencial = adivinhável → embaralhe (bijeção) ou aceite (não é segredo).

**High-level:**

```text
write:  client → API → gera ID (range local) → base62 → DB {short → long}
read:   client → GET /abc123 → cache (Redis, LRU) → hit? 301
                                   └─ miss → DB → popula cache
```

**Deep dives:**
- **301 vs 302:** 301 = browser cacheia → menos tráfego para você, **analytics perdidos**; 302 = todo clique passa por você → analytics. A escolha é de NEGÓCIO — dizer isso vale a questão.
- **DB:** modelo trivial key→value, sem joins, escala horizontal → NoSQL (Dynamo) natural; SQL também serve com sharding por short key. Justifique, qualquer um.
- **Cache:** 20% das URLs = 80% dos hits; hot keys (viral) → réplicas da chave (§11).
- Expiração: TTL + lazy delete + cleanup batch.

---

# 3. Design Twitter (o rei do fan-out)

**Clarify:** core = postar tweet, follow, **home timeline**. Escala: 200M DAU, ~150:1 read:write no timeline. NFR: timeline p99 < 200ms, **eventual consistency ok** (tweet aparecendo 5s depois: fine — AP, §17).

**O problema central — montar o home timeline:**

- **Fan-out on read (pull):** no GET, busca tweets de todos os seguidos + merge + sort. Leitura cara (N queries), escrita barata. Timeline sempre fresco.
- **Fan-out on write (push)** ⭐: ao tweetar, **injeta o tweet ID na timeline cache (Redis list) de cada follower**. Leitura = 1 lookup (rapidíssima); escrita cara.
- ⚠️ **O problema da celebridade:** 100M followers = 100M writes por tweet. **Híbrido** (a resposta certa): push para usuários normais; tweets de celebridades são **puxados no read e mesclados** na hora. *"Push for the many, pull for the mighty."*

**High-level:**

```text
POST tweet → Tweet Service → DB (tweets) + fanout queue (SQS/Kafka)
                                  └► fanout workers → Redis timelines dos followers
GET timeline → Timeline Service → Redis (lista de IDs) + hydrate (tweet cache)
                                  + merge tweets de celebridades seguidas (pull)
follow graph → Graph/Social Service (quem segue quem — sharded por user)
```

**Deep dives:** timeline cache = só IDs (hidratar de um tweet cache — economiza RAM); fanout assíncrono via fila (absorve picos — §19); usuários inativos não têm timeline materializada (lazy rebuild); media no S3+CDN (§18/12); search e trending = pipeline separado (Kafka → Elasticsearch — *"analytics off the hot path"*, §20).

---

# 4. Design Discord (real-time chat)

**Clarify:** canais/servidores (grupos), DMs, presença online, histórico persistente, typing indicator. NFR: entrega em tempo real (<100ms percebido), escala de **conexões** (milhões simultâneas).

**High-level:**

```text
clients ⇄ WebSocket Gateways (stateful! §8)     ← camada de CONEXÃO
              │        (registry: user → gateway)
              ▼
        pub/sub backbone (Redis pub/sub / Kafka)  ← roteia msg por canal
              ▼
        Chat Service → persiste msg → Cassandra   ← camada de DADOS
                                       (wide-column, §16)
        Presence Service (heartbeats → TTL no Redis)
```

**Fluxo:** user manda msg no canal X → gateway → chat service persiste + publica no tópico do canal X → todos os gateways com membros do canal X inscritos recebem → empurram pelas WebSockets.

**Deep dives:**
- **Por que Cassandra para mensagens:** escrita massiva append-only, ordenada por tempo — partition key = `channel_id` (+ bucket temporal para canais gigantes ≈ hot partition, aula 11), clustering por `message_id` decrescente (Snowflake ID = time-ordered). Leitura típica: "últimas 50 do canal" = 1 partição.
- **Gateways são estado** (§8): user reconecta → outro gateway → registry atualiza; sticky não resolve failover, o pub/sub sim.
- **Presença:** heartbeat a cada 30s → chave Redis com TTL; expirou = offline. Fan-out de presença é o maior volume do sistema → coalescing/batching.
- **Offline/mobile:** fila de notificação (push) quando não há conexão ativa.
- Ordem: por canal (IDs time-ordered + ordenação no cliente) — ordem global não existe nem precisa (§19).

---

# 5. Design YouTube (upload pipeline + delivery)

**Clarify:** upload, transcode, watch, metadados (título, views), busca fora do core. NFR: **durabilidade do vídeo** (nunca perder), início de playback < 1-2s global, upload de GBs confiável. Watch:upload ≈ 100:1+.

**High-level:**

```text
UPLOAD (write path):
 client → presigned URL (§18) → S3 (raw)  [upload DIRETO, multipart/resumable]
             └► evento S3 → fila → TRANSCODING PIPELINE (pipes & filters! aula 13)
                  split em chunks → transcode paralelo (1080p/720p/480p…)
                  → segmentos HLS/DASH → S3 (processed) → metadata DB: status=ready

WATCH (read path):
 client → API: GET /videos/{id} → metadata DB (cache na frente)
        → player busca manifest + segmentos → CDN (§12) → S3 na origem
```

**Deep dives:**
- **Upload resumável:** multipart — GBs por rede ruim falham; retomar por chunk. Bytes **não passam pelos seus servidores** (presigned).
- **Transcoding = DAG de jobs** numa fila (workers escalam com o backlog; spot instances — barato): é o exemplo perfeito de **queue + pipes and filters**; falha de um chunk → retry daquele chunk (idempotente), não do vídeo.
- **Streaming adaptativo:** vídeo = playlist de segmentos de ~2-10s em N qualidades; o player troca de qualidade por segmento conforme a banda. Por isso CDN serve arquivos estáticos pequenos — cacheável perfeito.
- **View count:** incrementar um contador por view a milhões/s = hot row → **agregação aproximada**: eventos → fila → agregador soma em batch → flush periódico. *"Views can be eventually consistent — nobody audits 1,000,003 vs 1,000,007."*
- Metadata: SQL (vídeos, canais, relações) com read replicas + cache pesado.

---

# 6. Design Google Drive (sync + storage)

**Clarify:** upload/download, **sync entre devices**, compartilhamento, versões, offline. NFR: **durabilidade acima de tudo**, consistência do estado de arquivos razoavelmente forte (ver seu arquivo recém-salvo).

**A ideia central — separar metadata de blocos:**

```text
client (sync agent)
  │ divide arquivo em CHUNKS (~4-8MB), hash de cada chunk (content-addressed)
  ▼
Block Service → S3: chunks armazenados POR HASH  → dedup de graça
Metadata DB (SQL): file → versão → lista ordenada de chunk hashes
                   + folders, permissões, shares
Notification Service: long polling/WebSocket → "algo mudou" → clientes re-sync
```

**Deep dives:**
- **Delta sync:** editou 1 página de um PDF de 1GB → só os chunks alterados sobem (hashes diferentes). Banda e tempo despencam.
- **Dedup:** mesmo chunk (hash) já existe → só referência. Entre usuários também (o mesmo instalador famoso é armazenado 1×).
- **Versionamento = grátis:** nova versão = nova lista de hashes; chunks antigos permanecem → restore = apontar para lista antiga. GC de chunks órfãos por refcount.
- **Conflito** (2 devices editam offline): last-write-wins **perde dados** → a resposta certa de produto: **manter as duas** ("conflicted copy") e deixar o humano resolver. Diga isso.
- **Notificação de mudança:** long polling é suficiente (não é chat — latência de segundos ok, §8).
- Upload/download direto no storage via presigned; metadata é o caminho quente → cache + réplicas.

---

# 7. Design Google Maps (geo + routing)

**Clarify:** o que exatamente — exibir mapa? busca de lugares? **rotas + ETA**? tráfego em tempo real? (Escolha rotas + ETA como core.)

**Os 3 subproblemas:**

**(a) Servir o mapa:** mundo pré-renderizado em **tiles** por níveis de zoom (pirâmide) → estáticos → **CDN** (§12). Cliente busca os tiles do viewport. Nada é desenhado on-the-fly no caminho quente.

**(b) Indexar coisas no espaço** (busca "restaurantes perto de mim"): lat/long não indexa bem em B-tree 2D → **geohash** (divide o mundo em células recursivas; prefixo comum = vizinhança) ou **quadtree**. Query: células que cobrem o raio → índice → filtro fino. (= como "encontre motoristas próximos" no Uber.)

**(c) Rotas:** mapa = **grafo** (interseções = nós, ruas = arestas com peso = tempo). Dijkstra/A* puro no grafo do planeta = lento demais → **pré-processamento hierárquico** (contraction hierarchies: atalhos por vias principais — como humanos navegam: local → rodovia → local). Nível de entrevista: *"precompute a hierarchy so queries touch a tiny fraction of the graph."*

**Deep dives:**
- **Tráfego/ETA:** telemetria anônima dos próprios clientes (posição/velocidade) → stream (Kafka) → agrega por segmento de via → **atualiza os pesos das arestas** → ETA dinâmico. Loop: dados dos usuários melhoram o produto.
- Trânsito muda a rota ideal durante a viagem → re-routing periódico.
- Escala de escrita da telemetria = maior volume do sistema → batch no cliente (a cada Xs), fila, agregação (§19/20).

---

# 8. Design a Key-Value Store (Dynamo-style) 🔥 (o mais "fundamentos")

**Clarify:** GET/PUT por chave; tunable consistency; escala horizontal; alta disponibilidade (AP por default — §17); valores pequenos (<1MB).

**Monte por camadas (a ordem de apresentação):**

1. **Partitioning:** **consistent hashing** (§14) com virtual nodes — chave → posição no anel → nó dono. Membership muda → só 1/N das chaves move.
2. **Replication:** cada chave escrita nos **N próximos nós** do anel (N=3, preference list).
3. **Consistência — quorum:** escreve espera **W** acks, leitura consulta **R** réplicas; **R + W > N** ⇒ leitura intersecta a escrita mais recente. N=3: W=2,R=2 balanceado; W=1 = escrita rápida e arriscada; R=1 = leitura rápida possivelmente stale. **Tunable por operação.**
4. **Conflitos** (aceitar escrita nos dois lados de uma partição = AP): **versioning** — vector clocks detectam escritas concorrentes → reconciliar no read (LWW simples mas perde dados; ou devolver irmãos ao cliente — carrinho do Dynamo).
5. **Falhas:** **hinted handoff** — nó down? o vizinho aceita a escrita "em nome dele" e entrega quando voltar (disponibilidade de escrita); **read repair** + **anti-entropy (Merkle trees)** — comparar réplicas por árvore de hashes e sincronizar divergências baratamente; **gossip protocol** — membership/health sem coordenador central.
6. **Storage engine local:** **LSM tree** — escritas vão para memtable + WAL (sequencial! §1), flush em **SSTables** imutáveis, **compaction** ao fundo; leituras: memtable → bloom filters → SSTables. Write-optimized (vs B-tree read-optimized) — é o motor de Cassandra/RocksDB.

> Pitch: *"Consistent hashing to place data, N-way replication with R/W quorums for tunable consistency, vector clocks for conflicts, gossip + hinted handoff + Merkle-tree anti-entropy for failures, LSM storage for write throughput. That's Dynamo — and each piece answers one failure mode."*

---

# 9. Design a Distributed Message Queue (Kafka-style) 🔥

**Clarify:** pub/sub com múltiplos consumidores independentes? ordem? retenção/replay? throughput alvo? at-least-once ok? (Estas respostas escolhem entre queue-based e log-based — assuma log-based, é o design rico.)

**A ideia central — a fila é um LOG:**

```text
topic = N PARTIÇÕES; cada partição = log append-only, imutável, ordenado
producer → hash(key) % partições → append no líder da partição
consumer groups: cada grupo tem OFFSETS próprios por partição
  → consumir ≠ deletar: a mensagem fica (retenção por tempo/tamanho) → REPLAY
  → dentro do grupo: cada partição é lida por 1 consumer (paralelismo = nº partições)
```

**Por que é rápido:** append sequencial em disco (§1) + batching + zero-copy — disco sequencial compete com RAM.

**Deep dives:**
- **Ordering:** garantida **por partição** (mesma key → mesma partição → ordem); global não existe (§19). Escolha da partition key = a decisão de design (hot partition de novo!).
- **Replicação:** cada partição tem líder + followers (**ISR** — in-sync replicas); producer `acks=all` = durável (espera ISR), `acks=1` = rápido; líder cai → um ISR assume (eleição via metadata/controller).
- **Delivery:** consumer processa **e depois** commita offset = at-least-once (crash entre os dois → reprocessa → **idempotência**, sempre ela); commita antes = at-most-once. "Exactly-once" = idempotent producer + transações de offset — na prática: *"effectively-once via at-least-once plus dedup."*
- **Consumer lag** = a métrica operacional nº 1 (backlog crescendo = consumers não acompanham → escalar consumers até o limite = nº de partições).
- **Rebalancing:** consumer entra/sai do grupo → partições redistribuídas (pausa breve — trade-off de elasticidade).
- vs SQS/Rabbit (queue-based): sem replay, sem múltiplos grupos baratos, mas: filas dinâmicas, roteamento rico, por-mensagem ack/DLQ nativos, operação mais simples. *"Log for streams and fan-out with replay; queue for work distribution."*

---

## 🎯 Como treinar com este arquivo (pouco tempo)

1. **Prioridade para essa vaga:** Rate Limiter, Key-Value Store e Distributed Queue (mais "technical/architectural", conectam com aulas 13/14/15) > Twitter/Discord (clássicos de fan-out/real-time) > YouTube/Drive/Maps/TinyURL (leia 1× para ter o mapa).
2. Para cada um dos 3 prioritários: leia → feche → **desenhe e narre em inglês em 5 min**. O que travou, releia.
3. Em TODOS, a abertura é igual: clarify (functional + NFR + read:write + consistência) — o hábito da aula 06/14 vale aqui.
