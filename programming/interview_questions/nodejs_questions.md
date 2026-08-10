# Top 20 Node.js Interview Questions

## 1. What is Node.js and how does it work?

Node.js is an open-source, cross-platform JavaScript runtime built on Chrome's V8 JavaScript engine. It executes JavaScript code outside of a web browser, using a single-threaded, non-blocking, event-driven architecture that makes it lightweight and efficient for I/O-intensive applications.

## 2. What is the Event Loop in Node.js?

The event loop is what allows Node.js to perform non-blocking I/O operations despite JavaScript being single-threaded. It offloads operations to the system kernel whenever possible and processes callbacks in phases:

1. **Timers** — executes `setTimeout()` and `setInterval()` callbacks
2. **Pending callbacks** — executes I/O callbacks deferred to the next iteration
3. **Idle, prepare** — internal use
4. **Poll** — retrieves new I/O events
5. **Check** — executes `setImmediate()` callbacks
6. **Close callbacks** — e.g., `socket.on('close', ...)`

## 3. What is the difference between `process.nextTick()` and `setImmediate()`?

- `process.nextTick()` fires immediately after the current operation completes, before the event loop continues. It has higher priority.
- `setImmediate()` fires on the next iteration of the event loop, during the "check" phase.

```js
setImmediate(() => console.log('immediate'));
process.nextTick(() => console.log('nextTick'));
// Output: nextTick, immediate
```

## 4. What is the difference between blocking and non-blocking code?

- **Blocking**: execution of additional JavaScript in the Node.js process must wait until a non-JavaScript operation completes (e.g., `fs.readFileSync`).
- **Non-blocking**: the process continues executing other code while I/O completes in the background (e.g., `fs.readFile` with a callback).

## 5. What are callbacks, Promises, and async/await?

- **Callback**: a function passed as an argument to be invoked later. Prone to "callback hell".
- **Promise**: an object representing the eventual completion (or failure) of an async operation, with `.then()` and `.catch()`.
- **async/await**: syntactic sugar over Promises that lets you write async code that reads synchronously.

```js
async function readFile() {
  try {
    const data = await fs.promises.readFile('file.txt', 'utf8');
    return data;
  } catch (err) {
    console.error(err);
  }
}
```

## 6. What is the difference between `require` and `import`?

- `require` is CommonJS, synchronous, and loads modules at runtime. Default in older Node.js.
- `import` is ES Modules (ESM), asynchronous, statically analyzed, and supports tree-shaking. Requires `"type": "module"` in `package.json` or `.mjs` extension.

## 7. What are Streams in Node.js and what types exist?

Streams are objects that let you read data from a source or write data to a destination continuously, chunk by chunk. There are four types:

- **Readable** — e.g., `fs.createReadStream()`
- **Writable** — e.g., `fs.createWriteStream()`
- **Duplex** — both readable and writable, e.g., TCP sockets
- **Transform** — duplex streams that modify data as it's written/read, e.g., `zlib.createGzip()`

## 8. What are Buffers and why are they needed?

Buffers are fixed-size chunks of memory allocated outside of the V8 heap, used to handle binary data (files, network packets). JavaScript strings can't efficiently represent raw binary, so Node.js uses `Buffer` for I/O.

```js
const buf = Buffer.from('hello', 'utf8');
console.log(buf.toString('hex')); // 68656c6c6f
```

## 9. What is middleware in Express?

Middleware are functions that have access to the request (`req`), response (`res`), and the `next` function in the request-response cycle. They can execute code, modify `req`/`res`, end the cycle, or call the next middleware.

```js
app.use((req, res, next) => {
  console.log(`${req.method} ${req.url}`);
  next();
});
```

## 10. How does Node.js handle concurrency with a single thread?

Node.js uses an event-driven, non-blocking I/O model. The main thread runs JavaScript, but I/O operations are delegated to the **libuv thread pool** (default size: 4). This lets Node.js handle thousands of concurrent connections without spawning a thread per request.

## 11. What is the `cluster` module?

The `cluster` module lets you create child processes (workers) that share the same server port, enabling Node.js to take advantage of multi-core systems. The master process forks workers and distributes incoming connections.

```js
const cluster = require('cluster');
const os = require('os');

if (cluster.isMaster) {
  os.cpus().forEach(() => cluster.fork());
} else {
  require('./server');
}
```

## 12. What is the difference between `spawn`, `exec`, `execFile`, and `fork`?

All are in the `child_process` module:

- **`spawn`** — launches a new process, returns a stream. Good for large output.
- **`exec`** — runs a command in a shell, buffers output. Good for small output.
- **`execFile`** — like `exec` but doesn't spawn a shell (safer, faster).
- **`fork`** — spawns a new Node.js process with an IPC channel for messaging.

## 13. How do you handle errors in Node.js?

- **Try/catch** for synchronous code and `async/await`.
- **Callback error-first pattern**: `callback(err, result)`.
- **`.catch()`** on Promises.
- **`process.on('uncaughtException')`** and **`process.on('unhandledRejection')`** as last-resort handlers (should log and exit, not recover).
- **EventEmitter `error` events**: always attach a listener or the process crashes.

## 14. What is the purpose of `package.json` and `package-lock.json`?

- **`package.json`** — declares dependencies, scripts, metadata, and version ranges.
- **`package-lock.json`** — locks the exact versions of every installed package (including transitive deps) to ensure reproducible installs across environments.

## 15. What is the difference between `dependencies`, `devDependencies`, and `peerDependencies`?

- **`dependencies`** — required at runtime in production.
- **`devDependencies`** — only needed during development (testing, linting, building).
- **`peerDependencies`** — expected to be provided by the consuming project (common in plugins/libraries).

## 16. What is EventEmitter?

`EventEmitter` is a core class that lets objects emit named events and register listeners. It's the foundation for many Node.js APIs (streams, HTTP servers).

```js
const EventEmitter = require('events');
const emitter = new EventEmitter();

emitter.on('greet', (name) => console.log(`Hello, ${name}`));
emitter.emit('greet', 'World');
```

## 17. How do you prevent memory leaks in Node.js?

- Avoid global variables that keep growing.
- Remove event listeners with `.off()` / `.removeListener()` when done.
- Be cautious with closures capturing large objects.
- Use `WeakMap` / `WeakSet` for object-keyed caches.
- Profile with `--inspect` and Chrome DevTools heap snapshots.
- Watch for accumulating timers and unclosed streams/connections.

## 18. What is the difference between `null`, `undefined`, and `undeclared`?

- **`undefined`** — a variable has been declared but not assigned a value.
- **`null`** — an intentional absence of value, assigned by the developer.
- **`undeclared`** — a variable that has not been declared at all; accessing it throws `ReferenceError` in strict mode.

## 19. What are Worker Threads and when should you use them?

Worker Threads (`worker_threads` module) allow running JavaScript in parallel on multiple threads. Unlike `cluster`, they share memory via `SharedArrayBuffer`. Use them for **CPU-intensive tasks** (image processing, cryptography, heavy computation) that would otherwise block the event loop. For I/O-bound work, the event loop is already sufficient.

## 20. How does Node.js handle HTTP requests? Explain the request lifecycle.

1. Client sends an HTTP request to the Node.js server.
2. The OS accepts the connection; libuv notifies the event loop.
3. Node.js parses headers and creates `req` (IncomingMessage) and `res` (ServerResponse) objects.
4. The registered request handler (or Express router/middleware chain) executes.
5. The handler may perform async I/O (DB, file system) — control returns to the event loop while waiting.
6. When the handler calls `res.end()` (or the response stream finishes), the response is flushed to the client.
7. The connection is closed or kept alive (depending on headers).

## 21. What is CORS and how do you handle it in Express?

**CORS (Cross-Origin Resource Sharing)** is a browser security mechanism that blocks requests from one origin (scheme + host + port) to another unless the server opts in via response headers (`Access-Control-Allow-Origin`, etc.).

```js
const cors = require('cors');
app.use(cors({
  origin: ['https://app.example.com'],
  credentials: true,
  methods: ['GET', 'POST'],
}));
```

Preflight (`OPTIONS`) requests are sent for "non-simple" requests. Never respond with `Access-Control-Allow-Origin: *` while also using credentials — the browser will reject it.

## 22. How do you implement JWT authentication?

A **JWT (JSON Web Token)** is a signed token (`header.payload.signature`) that carries claims (userId, roles, expiry) and is verified without a session lookup.

```js
const jwt = require('jsonwebtoken');

const token = jwt.sign({ sub: user.id, role: 'admin' }, SECRET, { expiresIn: '15m' });

function auth(req, res, next) {
  const token = req.headers.authorization?.split(' ')[1];
  try {
    req.user = jwt.verify(token, SECRET);
    next();
  } catch { res.sendStatus(401); }
}
```

Best practices: short access tokens + rotating refresh tokens, `HttpOnly` `Secure` cookies (not `localStorage` — XSS-exposed), key rotation, small payloads (JWTs are not encrypted, only signed — use JWE if you need confidentiality).

## 23. What is backpressure and how does `pipeline()` help?

**Backpressure** is a slow consumer causing a fast producer's buffer to grow. In Node streams, calling `.write()` returns `false` when the internal buffer is full — the producer should pause until `'drain'` fires.

`.pipe()` handles this automatically but doesn't propagate errors or clean up on failure. `stream.pipeline()` (or its promise version) is the modern replacement:

```js
const { pipeline } = require('node:stream/promises');

await pipeline(
  fs.createReadStream('in.log'),
  zlib.createGzip(),
  fs.createWriteStream('out.gz')
);
```

It properly forwards errors and destroys all streams on failure.

## 24. What is graceful shutdown and how do you implement it?

Graceful shutdown stops accepting new work, finishes in-flight requests, closes DB/queue connections, and only then exits — avoiding dropped requests during deploys or scale-in.

```js
const server = app.listen(3000);

async function shutdown(signal) {
  console.log(`${signal} received, shutting down`);
  server.close();                     // stop accepting new connections
  await db.end();                     // close pool
  await broker.disconnect();
  process.exit(0);
}

process.on('SIGTERM', () => shutdown('SIGTERM'));
process.on('SIGINT',  () => shutdown('SIGINT'));
```

Always add a **hard timeout** (e.g., `setTimeout(() => process.exit(1), 30_000).unref()`) so a stuck request can't block shutdown forever. Kubernetes and PM2 send `SIGTERM` first, then `SIGKILL` after a grace period.

## 25. How do you detect and diagnose memory leaks in Node.js?

Symptoms: RSS/heap grows monotonically, GC frequency rises, event loop lag increases.

Tools:
- **`--inspect`** + Chrome DevTools **Memory** tab — take heap snapshots, compare with the "3 snapshot" technique (baseline → interact → cleanup → snapshot; anything still growing leaks).
- **`clinic doctor`** / **`clinic heapprofiler`** (npm package) — automated diagnosis.
- **`node --heap-prof`** — sampling heap profiler.
- **`process.memoryUsage()`** — quick programmatic check.

Common causes: unbounded caches, event listeners never removed, closures capturing large objects, unfreed timers, unclosed streams/HTTP agents.

## 26. What are common Node.js security best practices?

- Use **`helmet`** to set safe HTTP headers (CSP, HSTS, X-Frame-Options).
- **Validate & sanitize input** — `zod`, `joi`, `express-validator`; never trust `req.body` shapes.
- **Parameterized queries / ORMs** — never string-concatenate SQL.
- **Rate limit** (per IP, per user, per route) to mitigate brute force / DoS.
- Keep dependencies patched — `npm audit`, Dependabot, Snyk.
- Store secrets in a vault or environment, never in code or Git.
- **Bcrypt / Argon2** for passwords (never MD5/SHA).
- Use `HttpOnly`, `Secure`, `SameSite` cookies.
- Disable `x-powered-by` header (`app.disable('x-powered-by')`).
- Run as a non-root user in containers; use minimal base images.

## 27. What is rate limiting and how do you implement it?

Rate limiting caps the number of requests a client can make in a time window, protecting against abuse and accidental overload.

```js
const rateLimit = require('express-rate-limit');

app.use('/api', rateLimit({
  windowMs: 60_000,
  max: 100,               // 100 requests per minute per IP
  standardHeaders: true,
  legacyHeaders: false,
}));
```

For distributed apps, use a **shared store** (Redis via `rate-limit-redis`) so all instances share counts. Algorithms: fixed window, sliding window, token bucket, leaky bucket.

## 28. WebSockets vs HTTP vs Server-Sent Events (SSE)

- **HTTP** — request/response, stateless, one round-trip per exchange.
- **WebSocket** — full-duplex, persistent, bidirectional over one TCP connection. Great for chat, live collab, games.
- **SSE** — server → client stream over HTTP; simpler than WebSocket, auto-reconnects, unidirectional. Good for notifications, dashboards.

WebSockets need sticky sessions / a shared broker (Redis pub/sub) when running multiple instances behind a load balancer.

## 29. What is `AbortController` and how do you use it?

`AbortController` is the standard cancellation mechanism, available in modern Node (also in fetch, timers, streams).

```js
const ctrl = new AbortController();
setTimeout(() => ctrl.abort(), 5000);

try {
  const res = await fetch(url, { signal: ctrl.signal });
} catch (e) {
  if (e.name === 'AbortError') { /* timed out */ }
}
```

Also supported by `fs.readFile`, `events.once`, `setTimeout(..., { signal })`. Replaces bespoke cancellation tokens.

## 30. What is `util.promisify`?

Converts a callback-based function (Node's error-first callback style) into one that returns a promise.

```js
const util = require('node:util');
const fs = require('node:fs');
const readFile = util.promisify(fs.readFile);

const data = await readFile('file.txt', 'utf8');
```

Most core modules now expose promise variants directly (`fs/promises`, `stream/promises`, `dns/promises`). Use `promisify` mostly for legacy libraries.

## 31. What is `AsyncLocalStorage`?

`AsyncLocalStorage` (from `node:async_hooks`) provides per-request context that survives across async boundaries — like thread-local storage for single-threaded async code. Common use: propagating a **request ID**, tenant ID, or trace context through nested async calls without threading it through every function.

```js
const { AsyncLocalStorage } = require('node:async_hooks');
const als = new AsyncLocalStorage();

app.use((req, res, next) => als.run({ reqId: crypto.randomUUID() }, next));

function log(msg) {
  const { reqId } = als.getStore() ?? {};
  console.log(`[${reqId}] ${msg}`);
}
```

## 32. Deep dive: ES Modules vs CommonJS interop

Key differences and pitfalls:
- ESM is **static** — imports are resolved before execution; no conditional `import` (use `await import()`).
- ESM is **async** — top-level `await` allowed.
- ESM has **no** `__dirname` / `__filename` / `require` — use `import.meta.url` + `fileURLToPath`.
- **CJS → ESM**: `import cjs from 'cjs-lib'` gives the `module.exports` object as default.
- **ESM → CJS**: `require('esm-lib')` throws (`ERR_REQUIRE_ESM`); use dynamic `import()`.
- **Dual packages**: package.json `"exports"` with conditional `import` / `require` entries.

Enable ESM with `"type": "module"` in `package.json`, or `.mjs` extension. Node 22+ has experimental synchronous `require()` of ESM under a flag.

## 33. `Buffer.alloc` vs `Buffer.allocUnsafe`

- **`Buffer.alloc(size)`** — zero-fills memory. Safe. Default choice.
- **`Buffer.allocUnsafe(size)`** — returns uninitialized memory (may contain leftover data from previous allocations). Faster but you **must** fully overwrite before reading.
- **`Buffer.from(...)`** — creates a Buffer from a string, array, or another buffer (copies).

`Buffer.allocUnsafe` is dangerous if leaked to user code — never send its contents over the network without overwriting first.

## 34. `worker_threads` vs `cluster` vs `child_process` — when to use each?

- **`child_process`** — spawn any external program or a Node script as a **separate OS process**. IPC via stdio or `fork()`'s channel.
- **`cluster`** — spawns Node worker **processes** that share a TCP server port (round-robin by default). Scales an HTTP server across CPU cores. Deprecated in favor of using a process manager (PM2, systemd) + `worker_threads` for CPU work.
- **`worker_threads`** — real threads inside the same process; share memory via `SharedArrayBuffer`. Use for **CPU-bound** work (crypto, image processing, parsing) so the main event loop stays responsive.

Rule of thumb: **I/O → event loop**; **CPU → worker_threads**; **scale HTTP → run N replicas** (containers/PM2) behind a load balancer.

## 35. Environment variables and secret management

- Load `.env` files with **`dotenv`** (or Node 20+'s built-in `--env-file=.env`).
- **Never commit `.env`** — add to `.gitignore`; commit an `.env.example` template instead.
- **Validate at startup** — parse `process.env` through `zod` / `envalid` so the app fails fast with clear errors on misconfig.
- In production, prefer a **secret store**: AWS Secrets Manager, Parameter Store, HashiCorp Vault, Kubernetes Secrets. Rotate periodically.
- Never log environment values; strip them from error reports.

## 36. npm vs yarn vs pnpm; what does the lockfile do?

- **npm** — default, ships with Node. Fast enough since v7. `package-lock.json`.
- **yarn** — originally faster and deterministic; classic v1 still widely used; Yarn 3+ (Berry) adds PnP (no `node_modules`). `yarn.lock`.
- **pnpm** — uses a content-addressable global store with symlinks; much less disk, much faster installs; strict about phantom dependencies. `pnpm-lock.yaml`.

The **lockfile** pins the exact resolved versions of every direct and transitive dependency, ensuring reproducible installs across machines and CI. Always commit it.

## 37. Explain semantic versioning and version ranges.

**SemVer**: `MAJOR.MINOR.PATCH`
- **MAJOR** — breaking API change.
- **MINOR** — backward-compatible new feature.
- **PATCH** — backward-compatible bug fix.

Version ranges in `package.json`:
- **`^1.2.3`** — `>=1.2.3 <2.0.0` (compatible with next minor/patch). Default when running `npm install`.
- **`~1.2.3`** — `>=1.2.3 <1.3.0` (patch only).
- **`1.2.3`** — exact.
- **`*`** / **`latest`** — any (avoid).

Pre-1.0 versions treat minor bumps as potentially breaking.

## 38. How do you handle large file uploads?

- **Stream** the request body, don't buffer everything in memory.
- Use **`multer`** with disk or memory storage (small files) or a streaming multipart parser (**`busboy`**) for large files.
- For very large uploads, use **multipart / resumable** protocols (tus, S3 multipart upload) so a dropped connection doesn't restart from zero.
- Consider **pre-signed URLs** — client uploads directly to S3/GCS, your server only issues the credential. Avoids proxying gigabytes through your app.
- Enforce size limits (`limits: { fileSize: 100 * 1024 * 1024 }`) and MIME-type checks; validate content, not just filename.

## 39. Caching strategies with Redis

Common patterns:
- **Cache-aside (lazy loading)** — app reads from cache; on miss, loads from DB and writes to cache.
- **Write-through** — writes go to cache and DB together.
- **Write-behind** — writes to cache; async flush to DB (risk of loss).
- **Read-through** — cache library handles miss + fill transparently.

Always set a **TTL** (`EX`). Handle **cache stampede** with locks (`SET NX`) or `SWR` semantics. Invalidate on writes; when hard, prefer short TTLs. Redis is also used for **sessions, rate limits, pub/sub, leaderboards** (sorted sets), and simple queues.

## 40. How do you test a Node.js API?

Layers:
- **Unit tests** — pure functions, business logic; fast, isolated. Frameworks: Jest, Vitest, Node's built-in `node:test`.
- **Integration tests** — real dependencies (DB via **Testcontainers** or a test DB), mock external HTTP with **`nock`** or **MSW**.
- **API tests** — **`supertest`** against an in-process Express/Fastify app; no need to bind a real port.
- **E2E** — deploy to a test env, drive with Playwright or a real HTTP client.

```js
const request = require('supertest');
const app = require('../app');

test('GET /health returns 200', async () => {
  const res = await request(app).get('/health');
  expect(res.status).toBe(200);
  expect(res.body).toEqual({ status: 'ok' });
});
```

Isolate tests (own DB schema per worker or transactional rollback), keep them deterministic (no real network, seeded clock/random), and run them in CI on every push.
