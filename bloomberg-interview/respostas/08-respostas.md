# 🔒 Gabarito — Aula 08 (Design Patterns)

> **Só abra depois de tentar.**

---

## Exercício 1 — pattern matching reverso

**a)** **Decorator** — *"Wrap the existing repository in a class implementing the same interface: try Redis, fall back to the inner repository and populate the cache. The original class and its callers don't change."*

**b)** **Strategy** (+ Factory/keyed DI para selecionar) — *"Each provider becomes a strategy behind IShippingProvider; the switch collapses into a single resolution point. Adding a provider means adding a class, not editing four files."*

**c)** **Adapter** — *"Define my own IPaymentGateway and write one adapter per vendor SDK, keeping vendor types out of the domain. Each adapter can then be selected as a strategy."*

**d)** **Captive dependency** (o anti-pattern de DI) — *"A singleton must not capture a scoped DbContext — it would share one context across requests. Inject IServiceScopeFactory and create a scope per execution inside the scheduler."*

**e)** **Observer / Pub-Sub** — *"The payment service publishes a PaymentConfirmed event — domain event in-process or SNS/EventBridge across services — and each reaction subscribes. The publisher knows nothing about the three consumers."*

**f)** **Transactional Outbox** — *"Save the order and insert the OrderPlaced event into an outbox table in the same transaction; a relay publishes it. Removes the dual-write between database and broker."*

---

## Exercício 2 — Repository over EF (modelo)

> *"Honest answer: it depends on what the repository does. The case against: DbContext already is a repository and unit of work — wrapping it in a generic IRepository<T> with GetAll and GetById usually subtracts value, hiding Include, projections, AsNoTracking and paging, and teams end up leaking IQueryable through the abstraction, which defeats its purpose. The case for: thin, intentional repositories with named domain queries — GetPendingOrdersForCustomer — centralize query logic, keep EF types out of the domain, and give a clean seam for testing and, relevantly here, for a database migration: swapping the persistence behind a stable interface. So my position: no generic repositories; yes to focused, domain-shaped ones where the queries deserve a name. And never return IQueryable from them — that's the abstraction quietly giving up."*

O que o entrevistador avalia: você conhece **os dois lados** e tem posição própria com critério.

---

## Exercício 3 — Decorator stack (uma resposta defensável)

Do mais externo ao mais interno: **Logging → Metrics → Retry → RateLimit → real sender**.

Justificativas (o que importa é defender cada posição):
- **Logging/Metrics fora de tudo**: medem a operação como o chamador a vê — latência total incluindo retries, resultado final. (Se você também quiser métrica **por tentativa**, um segundo medidor interno — dizer isso mostra maturidade.)
- **Retry fora do RateLimit**: cada tentativa passa pelo rate limiter de novo → os retries **também são limitados** e não atropelam o downstream justamente quando ele está sofrendo. Na ordem inversa (RateLimit fora), o limite é checado uma vez e o loop de retry martela o serviço por dentro.
- **RateLimit imediatamente sobre o real**: é a proteção do recurso, deve ser a última porta.

Resposta alternativa defensável: retry por dentro se o rate limit for **por cliente** e você não quiser que retries consumam a cota do usuário. **O exercício mede se você enxerga que a ordem muda a semântica** — não a ordem em si.

---

## Exercício 4 — estrutura da história de produção

Esqueleto (60s falados) — preencha com seu caso real e me mande para lapidar:

1. **Context** (10s): *"In our payments service we had to X…"*
2. **Problem** (15s): a dor concreta, com sintoma observável — *"deploys meant editing the same switch in four places / we lost events when the broker was down after commit…"*
3. **Pattern & decision** (15s): qual pattern, por que ele e não a alternativa — *"we introduced an outbox table instead of dual-writing because…"*
4. **Outcome** (10s): resultado mensurável — *"zero lost events over six months; adding a provider became a one-class change."*
5. **Trade-off accepted** (10s): o preço pago, dito espontaneamente — *"we accepted at-least-once delivery, so consumers had to become idempotent."*

O item 5 é o que diferencia a história de senior — **nunca conte uma história de pattern sem o preço**. Se seu melhor caso real for Outbox ou Strategy, melhor ainda: são os que conectam com o resto da entrevista.
