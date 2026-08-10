# Interview Overview: AWS Services & Testing Tools

Concise interview-ready overviews of common AWS services (SQS, Lambda, ECS, CloudFront, ALB, EventBridge) and testing tools (Jest, Playwright).

---

## SQS (Simple Queue Service)

**What it is:** A fully managed message queuing service for decoupling producers and consumers. Producers push messages, consumers poll and process them.

**Queue types:**
- **Standard** — nearly unlimited throughput, **at-least-once** delivery, best-effort ordering.
- **FIFO** — strict ordering, exactly-once processing, up to 3,000 msg/s with batching (300 without).

**Key concepts:**
- **Visibility timeout** — how long a received message is hidden from other consumers. Must exceed processing time or duplicates occur.
- **Long polling** — `WaitTimeSeconds` up to 20s reduces empty responses and cost vs short polling.
- **Dead-Letter Queue (DLQ)** — messages that fail processing N times get moved here for inspection.
- **Message retention** — 1 minute to 14 days (default 4 days).
- **Max message size** — 256 KB (use S3 for larger payloads via Extended Client).

**Common interview points:** at-least-once vs exactly-once, idempotent consumers, poison messages/DLQs, ordering guarantees, when to pick SQS vs SNS vs Kinesis vs EventBridge.

---

## Lambda

**What it is:** A serverless compute service that runs code in response to events without provisioning servers. You pay for invocations and execution time.

**Key concepts:**
- **Runtimes** — Node.js, Python, Java, .NET, Go, Ruby, plus custom runtimes and container images.
- **Cold start** — the first invocation (or after idle scaling) has extra latency while the runtime bootstraps. Mitigate with **provisioned concurrency** or **SnapStart** (Java).
- **Memory / CPU** — memory setting (128 MB to 10 GB) proportionally scales CPU.
- **Timeout** — max 15 minutes per invocation.
- **Concurrency** — account-level default 1,000 concurrent executions; can set per-function reserved concurrency.
- **Triggers** — API Gateway, S3, SQS, DynamoDB Streams, EventBridge, ALB, Kinesis, and more.
- **Execution context reuse** — variables outside the handler persist between warm invocations (useful for connection pools).

**Common interview points:** cold starts and mitigations, VPC networking (ENI setup), idempotency, use with SQS (batch size, partial batch response), why long-running or stateful workloads don't fit.

---

## ECS (Elastic Container Service)

**What it is:** A container orchestration service to run Docker containers on AWS.

**Launch types:**
- **Fargate** — serverless; AWS manages the underlying instances. Pay per vCPU/GB-second.
- **EC2** — you manage a cluster of EC2 instances that run the containers. More control, potentially cheaper at scale.

**Key concepts:**
- **Task Definition** — a blueprint (image, CPU, memory, env vars, IAM role, ports, volumes).
- **Task** — an instantiated Task Definition (one or more containers running together).
- **Service** — keeps a desired number of tasks running, integrates with load balancers, handles rolling deploys.
- **Cluster** — logical grouping of tasks/services.
- **Task IAM role** vs **Task Execution role** — the former grants app-level permissions; the latter lets ECS pull images and write logs.
- **Service discovery** — via ECS Service Connect or AWS Cloud Map.

**Common interview points:** Fargate vs EC2 trade-offs, ECS vs EKS (Kubernetes), rolling vs blue/green deploys, autoscaling (target tracking on CPU/memory or custom metrics), integration with ALB target groups.

---

## CloudFront

**What it is:** AWS's global Content Delivery Network (CDN). Caches content at 400+ edge locations to deliver low-latency responses worldwide.

**Key concepts:**
- **Origin** — the backend (S3, ALB, EC2, MediaStore, or any HTTP endpoint).
- **Distribution** — the CDN configuration (origins, behaviors, cache policies, restrictions).
- **Behaviors** — path-pattern rules that determine origin, cache policy, headers/cookies to forward, etc.
- **Cache policies / Origin request policies / Response headers policies** — modular controls.
- **TTL** — how long objects stay cached; controllable via origin headers (`Cache-Control`).
- **Invalidation** — evict cached objects (`/path/*`); first 1,000 paths per month are free.
- **Signed URLs / Signed Cookies** — protect private content.
- **Lambda@Edge / CloudFront Functions** — run code at edge for request/response manipulation. CloudFront Functions are cheaper and faster but more restricted.
- **HTTPS** — supports ACM certificates (must be in `us-east-1` for CloudFront).

**Common interview points:** cache hit ratio, invalidation vs versioned URLs (`asset.v2.js`), OAC (Origin Access Control) to secure S3 origins, geo-restriction, WAF integration.

---

## ALB (Application Load Balancer)

**What it is:** A Layer 7 (HTTP/HTTPS) load balancer that distributes traffic to targets based on request content.

**Key concepts:**
- **Listener** — checks for connection requests on a port/protocol (e.g., 443 HTTPS).
- **Rules** — evaluated in order, route based on host, path, headers, query strings, or source IP.
- **Target group** — set of registered targets (EC2, IP, Lambda, ECS tasks). Health-checked independently.
- **Target types** — instance, IP, Lambda, ALB (for chaining).
- **Sticky sessions** — cookie-based session affinity.
- **HTTPS termination** — ACM certificates; SNI support for multiple certs on one listener.
- **Access logs** — delivered to S3.
- **Deregistration delay** — grace period for in-flight requests during target removal.

**Comparison with other AWS load balancers:**
- **ALB** — HTTP/HTTPS/gRPC/WebSocket, content-based routing.
- **NLB** — Layer 4 (TCP/UDP/TLS), ultra-high performance, static IPs.
- **CLB** — legacy, avoid for new work.

**Common interview points:** ALB vs NLB, path/host-based routing, WebSocket support, integrating with ECS/EKS (dynamic port mapping), authenticating users via OIDC/Cognito at the ALB.

---

## EventBridge

**What it is:** A serverless event bus that routes events from AWS services, custom apps, and SaaS partners to targets, based on rules.

**Key concepts:**
- **Event bus** — the pipe events flow through. Default bus, custom buses, partner buses.
- **Rule** — pattern-matches events (by source, detail-type, or JSON content) and forwards matches to one or more targets.
- **Targets** — Lambda, SQS, SNS, Step Functions, ECS tasks, Kinesis, API destinations (external HTTP endpoints), and 20+ others.
- **Schema Registry** — discovers, stores, and generates code bindings for event schemas.
- **Archive & Replay** — record events and replay them for debugging or rebuilds.
- **Pipes** — point-to-point integration (source → optional filter/transform/enrich → target) for streams like DynamoDB Streams, Kinesis, SQS, Kafka.
- **Scheduler** — cron-like scheduled events (supersedes CloudWatch Events cron rules).

**EventBridge vs SNS vs SQS:**
- **SNS** — pub/sub fan-out, immediate push, limited filtering.
- **SQS** — decoupled queue, pull-based.
- **EventBridge** — richer routing/filtering, many built-in integrations, event archives, cross-account.

**Common interview points:** event pattern matching, delivery retries and DLQs, cross-account event delivery, when to use Pipes vs Rules.

---

## Jest

**What it is:** A JavaScript/TypeScript testing framework by Meta, popular for React and Node.js. Provides test runner, assertions, mocking, and coverage in one package.

**Key concepts:**
- **Test structure** — `describe`, `test` / `it`, `beforeAll`, `beforeEach`, `afterEach`, `afterAll`.
- **Matchers** — `expect(value).toBe(x)`, `.toEqual()`, `.toContain()`, `.toThrow()`, custom matchers.
- **Mocking** — `jest.fn()`, `jest.mock('module')`, `jest.spyOn(obj, 'method')`, automatic vs manual mocks.
- **Snapshot testing** — `expect(tree).toMatchSnapshot()` for UI regression detection.
- **Async testing** — `async/await`, returning promises, or `done` callback.
- **Coverage** — `--coverage` flag produces reports (statements, branches, functions, lines).
- **Configuration** — `jest.config.js`: `testEnvironment` (jsdom vs node), `moduleNameMapper`, `setupFilesAfterEach`, `transform`.
- **Watch mode** — `--watch` reruns tests affected by changed files.

**Common interview points:** unit vs integration tests, mocking modules, snapshot pros/cons (brittle, opaque diffs), test isolation, `beforeEach` cleanup, testing async code, avoiding implementation-detail assertions.

---

## Playwright

**What it is:** A cross-browser end-to-end testing framework by Microsoft. Automates Chromium, Firefox, and WebKit with one API. Node.js is the primary language; also supports Python, Java, and .NET.

**Key concepts:**
- **Browser / Context / Page** — a **browser** launches once; each **context** is an isolated session (cookies, storage); each **page** is a tab.
- **Locators** — `page.getByRole()`, `getByText()`, `getByLabel()`, `getByTestId()`. Preferred over CSS/XPath for resilience.
- **Auto-waiting** — actions like `click`, `fill`, `expect(locator).toBeVisible()` automatically wait for the element to be actionable/visible. No manual sleeps.
- **Assertions** — `expect(locator).toHaveText(...)`, `.toBeVisible()`, `.toHaveURL()`, with built-in retries.
- **Fixtures** — reusable setup (browser, page, authenticated user) declared via `test.extend()`.
- **Trace viewer** — records DOM snapshots, screenshots, network, and actions on failure. Debug with `npx playwright show-trace`.
- **Codegen** — `npx playwright codegen url` records a script from user actions.
- **Parallel execution** — tests run in parallel workers; **sharding** distributes across machines in CI.
- **Network interception** — `page.route()` to mock/modify requests.
- **Authentication reuse** — save `storageState` (cookies + localStorage) once, reuse across tests to skip login.

**Common interview points:** Playwright vs Cypress vs Selenium (multi-browser, auto-wait, faster, no in-browser runtime), test flakiness (why locators + auto-wait help), parallelization, CI integration, visual regression, page object model vs fixture-based composition.
