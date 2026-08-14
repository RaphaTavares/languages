# Aula 08 — Design Patterns (alto ROI para backend)

> A entrevista foi descrita como "technical + design pattern questions + architectural based". Formato por pattern: Problem → Solution → Real-world example (C#) → Trade-offs → Interview answer → Follow-ups. **Não decore GoF inteiro — domine estes.**

> **Meta-dica para a entrevista:** nunca comece pelo nome do pattern. Comece pelo **problema**, mostre a dor, e o pattern entra como consequência. "I reach for Strategy when I see a growing switch statement over behavior" > "Strategy is a behavioral pattern that...".

---

## 1. Strategy

- **Problem:** `switch (paymentMethod)` espalhado; cada método novo = editar N lugares (viola Open/Closed).
- **Solution:** uma interface por comportamento; implementações intercambiáveis; seleção em runtime.
- **Example (C#):** `IPaymentProcessor { Task<Result> ProcessAsync(Payment p); }` com `CardProcessor`, `PixProcessor`, `BoletoProcessor`; resolvidos via DI (`IEnumerable<IPaymentProcessor>` + seletor, ou keyed services no .NET 8).
- **Trade-offs:** para 2 casos estáveis, um `if` é mais simples. Indireção tem custo de legibilidade.
- **Interview answer:** *"Strategy replaces conditional logic over behavior with interchangeable implementations behind one interface. In our payment service, each payment method is a strategy resolved by DI — adding a method means adding a class, not editing a switch."*
- **Follow-ups:** How do you pick the right strategy at runtime? (factory/keyed DI) — When is a plain switch better?

## 2. Factory / Factory Method

- **Problem:** criação de objetos complexa/condicional espalhada pelos call sites; `new` acopla ao tipo concreto.
- **Solution:** centralizar a decisão de criação num único lugar que retorna a abstração.
- **Example:** `IMessagePublisherFactory.Create(BrokerType t)` → retorna `KafkaPublisher`/`SqsPublisher` conforme config. Ou a factory que escolhe a Strategy do item 1.
- **Trade-offs:** DI container já É uma factory genérica — não crie factories para o que o container resolve sozinho.
- **Interview answer:** *"A factory centralizes conditional creation logic so callers depend on the abstraction. I use it when construction needs runtime data the DI container doesn't have."*
- **Follow-ups:** Factory vs DI container? Abstract Factory vs Factory Method? (famílias de objetos vs um objeto)

## 3. Repository

- **Problem:** lógica de acesso a dados espalhada; domínio acoplado ao ORM; difícil de testar.
- **Solution:** interface orientada ao domínio (`IOrderRepository.GetPendingForCustomer(id)`) escondendo a persistência.
- **Example:** implementação EF Core por trás; nos testes, fake in-memory ou a interface mockada.
- **Trade-offs 🔥 (esperado de senior .NET):** `DbContext` **já é** repository + unit of work; um repository genérico `IRepository<T>` com `GetAll()` frequentemente só **empobrece** o EF (perde `Include`, projeções, `AsNoTracking`). Vale a pena quando: queries de domínio nomeadas e reusadas, ou para poder trocar/testar a persistência. Repositories que vazam `IQueryable` quebram a abstração.
- **Interview answer:** *"Repository puts a domain-shaped interface over persistence. With EF I keep them thin and intentional — named domain queries, not a generic wrapper over DbSet, because DbContext already is a repository and unit of work."*
- **Follow-ups:** Generic repository — good idea? Should a repository return IQueryable? Why not?

## 4. Dependency Injection / Dependency Inversion

- **Problem:** classes instanciando as próprias dependências = acoplamento, impossível testar, lifetime manual.
- **Solution:** **DIP (princípio)**: dependa de abstrações; módulos de alto nível não dependem de detalhes. **DI (técnica)**: as dependências chegam de fora (construtor); container gerencia lifetimes.
- **Example:** todo o ASP.NET Core: `builder.Services.AddScoped<IOrderRepository, EfOrderRepository>()`.
- **Trade-offs:** lifetimes errados são a fonte nº 1 de bug: **captive dependency** — singleton capturando um `DbContext` scoped → contexto compartilhado entre requests → dados vazados/concurrency exceptions.
- **Interview answer:** *"Dependency Inversion is the principle — depend on abstractions. Injection is the mechanism that delivers them. The classic production bug is a captive dependency: a singleton capturing a scoped DbContext."*
- **Follow-ups:** Singleton vs Scoped vs Transient — quando cada um? What happens if a singleton depends on a scoped service?

## 5. Adapter

- **Problem:** integrar código com interface incompatível (SDK de terceiro, sistema legado) sem contaminar o domínio.
- **Solution:** classe que traduz a interface que você QUER para a que o terceiro TEM.
- **Example:** `IPaymentGateway` seu; `StripeAdapter` e `LegacyBankAdapter` traduzem para os SDKs. O domínio nunca vê tipos da Stripe.
- **Trade-offs:** camada extra; para um único fornecedor estável pode ser cerimônia.
- **Interview answer:** *"Adapter translates a third-party interface into the one my domain defines, keeping vendor types out of business logic — which also makes vendor swaps and testing cheap. It's Strategy's best friend: each vendor adapter can be a strategy."*
- **Follow-ups:** Adapter vs Facade? (adaptar contrato incompatível vs simplificar subsistema complexo)

## 6. Decorator

- **Problem:** adicionar comportamento (cache, retry, logging, métricas) a um serviço **sem alterá-lo**.
- **Solution:** implementar a MESMA interface, envolver a instância real, delegar adicionando comportamento.
- **Example:** `CachedCustomerRepository : ICustomerRepository` envolvendo o real: tenta Redis, senão delega e cacheia. Empilhável: metrics → cache → retry → real. (Scrutor no .NET: `services.Decorate<...>()`.)
- **Trade-offs:** pilhas profundas dificultam debug; ordem dos decorators importa (retry por fora ou por dentro do cache?).
- **Interview answer:** *"Decorator wraps an implementation of the same interface to add cross-cutting behavior — caching, retries, metrics — without touching the original class. Callers can't tell the difference."*
- **Follow-ups:** Decorator vs middleware/pipeline? Decorator vs inheritance? Em que ordem você empilharia cache e retry, e por quê?

## 7. Proxy

- **Problem/Solution:** mesma forma do Decorator, **intenção diferente**: controlar o ACESSO ao objeto (lazy loading, permissão, chamada remota), não adicionar comportamento.
- **Example:** EF lazy-loading proxies; clients gRPC/HTTP tipados (Refit) são remote proxies.
- **Interview answer:** *"Structurally like a decorator, but the intent is access control — laziness, authorization, remoteness — rather than added behavior."*
- **Follow-ups:** Proxy vs Decorator? (intenção) Where does EF use proxies?

## 8. Facade

- **Problem:** um caso de uso exige orquestrar 5 subsistemas; os callers conhecem todos.
- **Solution:** um ponto de entrada simples para uma operação de negócio: `CheckoutService.PlaceOrderAsync()` orquestra estoque, pagamento, pedido, evento.
- **Trade-offs:** risco de virar **god class**; facades por caso de uso, não uma para tudo.
- **Interview answer:** *"A facade gives a simple entry point over a complex subsystem — my application-layer services are facades: the controller calls PlaceOrder and doesn't know about inventory, payment or messaging."*
- **Follow-ups:** Facade vs Mediator? How do you stop a facade becoming a god class?

## 9. Observer / Pub-Sub

- **Problem:** quando X acontece, N interessados reagem — sem que X conheça os N.
- **Solution:** publisher emite; subscribers registram interesse. Em memória: eventos C#/MediatR notifications. Entre serviços: **SNS/Kafka/RabbitMQ — pub-sub é Observer distribuído** (seu território!).
- **Trade-offs:** fluxo implícito (quem reage a quê?); em distribuído: at-least-once, ordering, idempotência — conecte com aula 07.
- **Interview answer:** *"Observer decouples an event source from its reactions. At service scale that's pub-sub through a broker — same pattern, plus delivery guarantees, ordering and idempotency to handle."*
- **Follow-ups:** What breaks when Observer goes distributed? Event vs Command? (fato ocorrido, N receptores vs intenção, 1 receptor)

## 10. Builder

- **Problem:** construção com muitos parâmetros opcionais / etapas.
- **Solution:** API fluente que monta passo a passo e `Build()` valida o conjunto.
- **Example:** `HostBuilder`/`WebApplicationBuilder`, `PolicyBuilder` do Polly; test data builders (`OrderBuilder.WithCustomer(x).WithItems(3).Build()`).
- **Interview answer:** *"Builder separates the construction of a complex object from its representation — .NET's HostBuilder is the canonical example; I also use test-data builders to keep tests readable."*
- **Follow-ups:** Builder vs constructor com optional parameters? Vs object initializer?

## 11. Command

- **Problem:** representar uma ação como **objeto** — para enfileirar, logar, desfazer, despachar uniformemente.
- **Solution:** `record CancelOrderCommand(Guid OrderId)` + handler. É a espinha de CQRS via MediatR; uma mensagem SQS É um command serializado.
- **Trade-offs:** MediatR em app pequeno = indireção por esporte; command vs event: **intenção dirigida a 1 handler** vs **fato para N interessados**.
- **Interview answer:** *"Command reifies an action as an object, so it can be queued, logged, retried or dispatched uniformly — it's the backbone of CQRS-style handlers and of every message on a queue."*
- **Follow-ups:** Command vs Event? How does this relate to your SQS consumers?

---

## Patterns arquiteturais para citar de passagem

(Já cobertos na aula 07 — na entrevista, conte-os como patterns também): **Outbox, Saga, Circuit Breaker, Strangler Fig, CQRS, Retry with backoff.** Se pedirem "a design pattern you actually used in production", **Outbox ou Strategy** são suas melhores histórias — prepare 60s de cada.

---

## ✏️ Exercícios

### Exercício 1 — pattern matching reverso

Para cada cenário, diga o pattern e justifique em 1-2 frases (inglês):

a) Adicionar cache Redis a um repositório existente sem modificá-lo.
b) O código tem `switch (shippingProvider)` em 4 arquivos diferentes.
c) Integrar o 3º gateway de pagamento, cada um com SDK próprio.
d) Um singleton `ReportScheduler` precisa de `DbContext`.
e) Quando um pedido é pago: enviar email, atualizar estoque, notificar analytics — sem acoplar o serviço de pagamento a nada disso.
f) Garantir atomicidade entre salvar o pedido e publicar `OrderPlaced`.

### Exercício 2 — o follow-up perigoso

> **"Repository over Entity Framework — good pattern or anti-pattern? Defend your position."**
Responda em inglês (60-90s) mostrando os DOIS lados antes de se posicionar.

### Exercício 3 — Decorator stack

Você tem `INotificationSender` com decorators de: retry, rate-limiting, logging e métricas. **Em que ordem você os empilha (do mais externo ao mais interno) e por quê?** Não existe uma única resposta certa — o que importa é a justificativa.

### Exercício 4 — história de produção

Escreva (inglês, ~60s falados) sua melhor história real de pattern em produção — problema, pattern, resultado, trade-off aceito. Vamos lapidar esse texto juntos.

---

## ✅ Respostas / avaliação

*(Preenchido durante a sessão interativa, depois da tentativa.)*
