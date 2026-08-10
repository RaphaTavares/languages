# Top 20 C# Interview Questions

## 1. What is C# and what's the difference between .NET Framework, .NET Core, and .NET 5+?

C# is a strongly-typed, object-oriented programming language developed by Microsoft that runs on the .NET platform.

- **.NET Framework** — Windows-only, legacy (versions 1.0–4.8), still maintained but no new features.
- **.NET Core** — cross-platform, open-source rewrite (versions 1.0–3.1), now legacy.
- **.NET 5+** — the unified successor merging Framework and Core into a single cross-platform runtime. Current LTS: .NET 8 / .NET 10.

## 2. What is the CLR (Common Language Runtime)?

The CLR is the runtime environment that manages the execution of .NET programs. It provides:

- **JIT compilation** — converts IL (Intermediate Language) to native machine code at runtime.
- **Garbage collection** — automatic memory management.
- **Type safety** — enforces type checks.
- **Exception handling** and **security** — unified across languages targeting the CLR.

## 3. What is the difference between value types and reference types?

- **Value types** (`int`, `struct`, `enum`, `bool`) — stored on the stack (usually), hold the actual data, copied by value.
- **Reference types** (`class`, `string`, `object`, arrays, delegates) — stored on the heap, variables hold a reference to the data, copied by reference.

```csharp
int a = 5;
int b = a;   // b is a copy; changing b doesn't affect a

var list1 = new List<int> { 1, 2 };
var list2 = list1;  // both point to the same list
list2.Add(3);       // list1 now also has 3
```

## 4. What is boxing and unboxing?

- **Boxing** — implicit conversion of a value type to `object` (or an interface it implements). Allocates on the heap.
- **Unboxing** — explicit conversion from `object` back to a value type.

```csharp
int x = 42;
object boxed = x;      // boxing
int unboxed = (int)boxed;  // unboxing
```

Boxing has a performance cost — avoid it in hot paths (use generics instead).

## 5. What is the difference between an abstract class and an interface?

- **Abstract class** — can have implemented methods, fields, constructors, access modifiers. A class can inherit only one.
- **Interface** — traditionally a pure contract; since C# 8, can have default implementations and static members. A class can implement many.

Use an abstract class for **is-a** relationships with shared state/behavior; use an interface for **can-do** capabilities.

## 6. What are properties in C#?

Properties are members that provide flexible read/write access to a field via `get` and `set` accessors.

```csharp
public class Person {
    public string Name { get; set; }              // auto-property
    public int Age { get; init; }                 // init-only (C# 9)
    private int _score;
    public int Score {
        get => _score;
        set => _score = Math.Max(0, value);       // validated setter
    }
}
```

## 7. What is dependency injection and how does .NET support it?

Dependency Injection (DI) is a design pattern where an object receives its dependencies from outside rather than creating them itself. It enables testability and loose coupling.

.NET provides built-in DI via `Microsoft.Extensions.DependencyInjection`:

```csharp
builder.Services.AddSingleton<ICache, MemoryCache>();
builder.Services.AddScoped<IUserService, UserService>();
builder.Services.AddTransient<IEmailSender, SmtpSender>();
```

- **Singleton** — one instance for the app lifetime.
- **Scoped** — one per request/scope.
- **Transient** — new instance every time.

## 8. What is `async`/`await` and how does it work?

`async`/`await` is syntactic sugar over the Task-based Asynchronous Pattern (TAP). It lets you write asynchronous code that reads sequentially.

```csharp
public async Task<string> FetchAsync() {
    using var client = new HttpClient();
    var response = await client.GetStringAsync("https://api.example.com");
    return response;
}
```

Under the hood, the compiler generates a state machine. At each `await`, control returns to the caller until the awaited task completes. It does **not** create a new thread by itself — for I/O, the thread is released back to the pool.

## 9. What is LINQ?

LINQ (Language Integrated Query) provides a unified query syntax over collections, databases, XML, and more. Two syntaxes: method (fluent) and query (SQL-like).

```csharp
var adults = users.Where(u => u.Age >= 18).OrderBy(u => u.Name).Select(u => u.Name);

var adults = from u in users
             where u.Age >= 18
             orderby u.Name
             select u.Name;
```

LINQ queries are **deferred** — they execute only when enumerated.

## 10. What are delegates, `Func`, `Action`, and `Predicate`?

A **delegate** is a type-safe pointer to a method.

- **`Action<T>`** — delegate that returns void.
- **`Func<T, TResult>`** — delegate that returns a value.
- **`Predicate<T>`** — delegate that takes `T` and returns `bool` (equivalent to `Func<T, bool>`).

```csharp
Action<string> log = msg => Console.WriteLine(msg);
Func<int, int, int> add = (a, b) => a + b;
Predicate<int> isEven = n => n % 2 == 0;
```

## 11. What are lambda expressions?

Lambdas are anonymous functions used to create delegates or expression trees.

```csharp
Func<int, int> square = x => x * x;
list.Where(x => x > 0);
Task.Run(() => DoWork());
```

Captured variables (closures) extend the lifetime of those variables.

## 12. What is the difference between `IEnumerable`, `ICollection`, `IList`, and `IQueryable`?

- **`IEnumerable<T>`** — forward-only iteration; no count, no indexer.
- **`ICollection<T>`** — adds `Count`, `Add`, `Remove`, `Contains`.
- **`IList<T>`** — adds indexed access (`this[int]`), `Insert`, `RemoveAt`.
- **`IQueryable<T>`** — like `IEnumerable`, but translates expressions to a remote query (e.g., SQL via Entity Framework).

Use `IEnumerable` for streams/deferred pipelines; `IQueryable` for LINQ-to-DB.

## 13. How does garbage collection work in C#?

The .NET GC is a **generational, tracing** collector that manages memory on the managed heap.

- **Gen 0** — short-lived objects; collected most often.
- **Gen 1** — survivors of Gen 0.
- **Gen 2** — long-lived objects; collected least often.
- **Large Object Heap (LOH)** — objects ≥ 85KB, collected with Gen 2.

The GC pauses managed threads during collection. Use `IDisposable` / `using` for unmanaged resources (files, sockets), not to control GC.

## 14. What is the difference between `struct` and `class`?

- **`class`** — reference type, on the heap, supports inheritance, has a default parameterless constructor.
- **`struct`** — value type, usually on the stack, no inheritance (can implement interfaces), copied by value, cannot have a parameterless constructor (before C# 10).

Use `struct` for small, immutable, short-lived data (`Point`, `DateTime`).

## 15. What are extension methods?

Extension methods add methods to existing types without modifying them or using inheritance. Declared as static methods in a static class with `this` on the first parameter.

```csharp
public static class StringExtensions {
    public static bool IsNullOrEmpty(this string s) => string.IsNullOrEmpty(s);
}

// Usage
"hello".IsNullOrEmpty();
```

LINQ is built almost entirely on extension methods over `IEnumerable<T>`.

## 16. What are generics and why use them?

Generics let you define classes, interfaces, and methods with type parameters, providing **type safety without boxing** and code reuse.

```csharp
public class Repository<T> where T : class, IEntity {
    public T GetById(int id) { ... }
}

var users = new Repository<User>();
```

Constraints (`where T : ...`) restrict the allowed type arguments.

## 17. What's the difference between `ref`, `out`, and `in` parameters?

- **`ref`** — pass by reference; must be initialized before the call; can be modified.
- **`out`** — pass by reference; does **not** need to be initialized; **must** be assigned inside the method.
- **`in`** — pass by reference as read-only; useful for large structs to avoid copying.

```csharp
void Swap(ref int a, ref int b) { (a, b) = (b, a); }
bool TryParse(string s, out int result) { ... }
void Process(in LargeStruct data) { ... }
```

## 18. What is the difference between `==` and `Equals()`?

- **`==`** — for value types, compares values; for reference types (by default), compares references. Can be overloaded.
- **`Equals()`** — virtual method inherited from `object`. Overridable to define value equality.

`string` overloads both to do value comparison. Always override `GetHashCode()` when overriding `Equals()`.

## 19. What are records in C#?

Records (C# 9+) are reference types (or value types with `record struct`) designed for **immutable data**. They provide value-based equality, `with` expressions, and concise syntax.

```csharp
public record Person(string Name, int Age);

var p1 = new Person("Alice", 30);
var p2 = p1 with { Age = 31 };   // non-destructive mutation
Console.WriteLine(p1 == new Person("Alice", 30));  // True (value equality)
```

## 20. What is the difference between `Task` and `Thread`?

- **`Thread`** — a low-level OS thread. Expensive to create, blocks while waiting.
- **`Task`** — a higher-level abstraction representing an async operation. Uses the thread pool, supports composition (`await`, `ContinueWith`), cancellation, and returns values (`Task<T>`).

Prefer `Task` for async work. Use `Thread` only for long-running, dedicated background work that shouldn't share the pool.

## 21. What is `IDisposable`, `IAsyncDisposable`, and the `using` statement?

`IDisposable` provides a `Dispose()` method to deterministically release unmanaged resources (files, sockets, DB connections). The `using` statement guarantees `Dispose` is called even on exceptions.

```csharp
using (var stream = File.OpenRead("file.txt")) { ... }   // scoped
using var stream = File.OpenRead("file.txt");           // C# 8+: disposed at end of enclosing scope
```

`IAsyncDisposable` (C# 8+) is for async cleanup (e.g., flushing a network stream). Consumed with `await using`.

```csharp
await using var conn = new SqlConnection(cs);
```

Implement the **dispose pattern** correctly for classes owning both managed and unmanaged resources.

## 22. What are nullable reference types (NRT)?

NRT (C# 8+, on by default in new projects) is a compile-time feature that distinguishes `string` (non-null) from `string?` (nullable). The compiler warns on potential null dereferences.

```csharp
#nullable enable
string name = null;      // warning
string? maybe = null;    // OK
int len = maybe.Length;  // warning: dereference of possibly null
if (maybe is not null) { int len2 = maybe.Length; }  // OK, flow analysis
```

Use `!` (null-forgiving) sparingly, only when you know better than the compiler.

## 23. What is pattern matching in C#?

Pattern matching extracts and tests data in a concise way. Kinds:

- **Type pattern** — `if (obj is Cat c)`
- **Constant pattern** — `case 0:` / `is null`
- **Relational pattern** (C# 9) — `is > 0 and < 100`
- **Logical pattern** (C# 9) — `and`, `or`, `not`
- **Property pattern** — `is { Length: > 0 }`
- **Tuple / positional pattern** — `is (0, 0)`
- **List pattern** (C# 11) — `is [1, 2, .., 5]`

```csharp
string Describe(object o) => o switch {
    null                                      => "null",
    int n when n < 0                          => "negative int",
    string { Length: 0 }                      => "empty string",
    Point (0, 0)                              => "origin",
    IEnumerable<int> [var first, .., var last] => $"first={first}, last={last}",
    _                                         => "other",
};
```

## 24. What are tuples and value tuples? What is deconstruction?

**Value tuples** (`(int, string)`) are lightweight, mutable, stack-allocated structs — good for multiple return values without a class.

```csharp
(int min, int max) MinMax(int[] a) => (a.Min(), a.Max());
var (lo, hi) = MinMax(nums);                     // deconstruction
```

**Deconstruction** splits an object into individual variables using a `Deconstruct` method (records provide it automatically). The older `Tuple<T1,T2>` class is reference-type, immutable, and mostly obsolete.

## 25. What is `ConfigureAwait(false)` and when should you use it?

By default, `await` captures the current **SynchronizationContext** and resumes on it (important for UI apps to marshal back to the UI thread). `ConfigureAwait(false)` tells the runtime not to capture it — the continuation runs on any thread pool thread.

```csharp
var data = await httpClient.GetStringAsync(url).ConfigureAwait(false);
```

**Use in library code** to avoid deadlocks when callers `.Result` or `.Wait()`, and for a small perf win. **Do not use** in ASP.NET Core (no sync context) or UI code that needs to touch UI elements after.

## 26. What are attributes and reflection?

**Attributes** are metadata attached to types/members via `[SomeAttr]`. Examples: `[Obsolete]`, `[Serializable]`, `[HttpGet]`.

```csharp
[AttributeUsage(AttributeTargets.Method)]
public class RetryAttribute : Attribute {
    public int Times { get; }
    public RetryAttribute(int times) => Times = times;
}
```

**Reflection** reads attributes and inspects/invokes members at runtime.

```csharp
var attr = method.GetCustomAttribute<RetryAttribute>();
var value = property.GetValue(instance);
```

Reflection is powerful but slow — prefer **source generators** or cached `Expression`-compiled delegates in hot paths.

## 27. What is the difference between `readonly`, `const`, and `static readonly`?

- **`const`** — compile-time constant; baked into callers; only primitives/strings; implicitly `static`.
- **`readonly`** — assignable only in the declaration or constructor; runtime constant; per-instance.
- **`static readonly`** — one shared value per type; assigned in a static constructor or field initializer; safe for non-primitive types.

Use `const` only when the value is truly immutable across versions (changing it requires recompiling **all** referencing assemblies).

## 28. What is covariance and contravariance in generics?

- **Covariance** (`out T`) — accept a **more derived** type. Example: `IEnumerable<out T>` allows `IEnumerable<string>` → `IEnumerable<object>`.
- **Contravariance** (`in T`) — accept a **less derived** type. Example: `Action<in T>` allows `Action<object>` → `Action<string>`.
- **Invariance** — the default; exact type match required.

Only reference-type generics support variance; not value types.

## 29. What is the `yield` keyword?

`yield return` / `yield break` create **iterator methods** that produce sequences lazily. The compiler generates a state machine.

```csharp
IEnumerable<int> Fibonacci() {
    int a = 0, b = 1;
    while (true) {
        yield return a;
        (a, b) = (b, a + b);
    }
}

foreach (var n in Fibonacci().Take(10)) Console.Write(n + " ");
```

Nothing runs until enumeration begins — great for infinite sequences and pipelining.

## 30. Explain thread synchronization primitives.

- **`lock (obj)`** — syntactic sugar over `Monitor.Enter/Exit`. Simple mutual exclusion within a process.
- **`Monitor`** — same, but with `TryEnter`, `Wait`, `Pulse`.
- **`Mutex`** — cross-process mutual exclusion (named).
- **`Semaphore` / `SemaphoreSlim`** — allow N concurrent holders. `SemaphoreSlim` is lighter and supports async (`WaitAsync`).
- **`ReaderWriterLockSlim`** — many readers OR one writer.
- **`Interlocked`** — atomic operations on primitives (`Increment`, `CompareExchange`).

Never `lock` on `this`, a type, or a public object — use a private `readonly object _sync = new();`.

## 31. What is a deadlock and how do you prevent it?

A **deadlock** occurs when two+ threads each hold a resource the other needs and neither releases. Classic causes:

- Inconsistent lock ordering.
- Blocking on an async task (`.Result`) that awaits back to the captured context.

Prevention:
- Always acquire locks in the same order.
- Prefer `SemaphoreSlim` + `async/await` over synchronous blocking.
- Never mix `.Result`/`.Wait()` with `await` on the same call stack. Use `async` all the way down.
- Use timeouts (`Monitor.TryEnter(obj, timeout)`).

## 32. What is `CancellationToken` and cooperative cancellation?

`CancellationTokenSource` produces a `CancellationToken` that async methods **cooperatively check** to abort work early.

```csharp
using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(5));
var result = await httpClient.GetAsync(url, cts.Token);
// inside a loop:
foreach (var item in items) {
    cts.Token.ThrowIfCancellationRequested();
    Process(item);
}
```

Pass the token down; never swallow `OperationCanceledException`. `CancellationTokenSource.CreateLinkedTokenSource(...)` combines multiple tokens.

## 33. What is `Span<T>` and `Memory<T>`?

- **`Span<T>`** — a stack-only, zero-allocation view over contiguous memory (arrays, stackalloc, unmanaged pointers). Great for slicing without copies.
- **`Memory<T>`** — like `Span<T>` but can live on the heap (async fields), at a small perf cost.

```csharp
ReadOnlySpan<char> text = "hello world";
var word = text.Slice(0, 5);            // "hello" — no allocation
```

Used heavily in high-perf code (JSON parsers, `Utf8Formatter`, `StringBuilder`).

## 34. What are expression trees?

Expression trees represent code as **data** (an AST). `Expression<Func<T,bool>>` gets compiled into a tree instead of a delegate, letting libraries **inspect** it (e.g., EF Core translating LINQ to SQL).

```csharp
Expression<Func<Person, bool>> pred = p => p.Age > 18;
// pred.Body is a BinaryExpression (>)
// LINQ providers walk it and translate to SQL / a remote query
```

Can be compiled to a delegate with `.Compile()` — used in high-perf mapping/serialization.

## 35. What is the difference between `throw` and `throw ex`?

- **`throw;`** — rethrows the current exception, **preserving** the original stack trace.
- **`throw ex;`** — throws it as a new exception, **overwriting** the stack trace (losing where it originated).

```csharp
try { ... }
catch (Exception ex) {
    Log(ex);
    throw;      // correct
    // throw ex;  // WRONG — loses stack
}
```

Use `throw new WrapperException("context", ex)` if you want to wrap and preserve the inner exception.

## 36. What is middleware in ASP.NET Core?

Middleware are components chained into the request pipeline. Each can:

- Process the request.
- Call `next()` to pass to the next middleware (or short-circuit).
- Process the response on the way back.

```csharp
app.Use(async (ctx, next) => {
    var sw = Stopwatch.StartNew();
    await next();
    logger.LogInformation("{Path} took {Ms}ms", ctx.Request.Path, sw.ElapsedMilliseconds);
});

app.UseAuthentication();
app.UseAuthorization();
app.MapControllers();
```

**Order matters** — auth before authorization, exception handler first, etc.

## 37. What is the Options pattern in ASP.NET Core?

Binds configuration sections to strongly-typed classes, injected via `IOptions<T>`, `IOptionsSnapshot<T>`, or `IOptionsMonitor<T>`.

```csharp
public class SmtpOptions { public string Host { get; set; } public int Port { get; set; } }

builder.Services.Configure<SmtpOptions>(builder.Configuration.GetSection("Smtp"));

public class EmailSender {
    public EmailSender(IOptions<SmtpOptions> opts) { _opts = opts.Value; }
}
```

- **`IOptions<T>`** — singleton, snapshot at startup.
- **`IOptionsSnapshot<T>`** — scoped, refreshed per request.
- **`IOptionsMonitor<T>`** — singleton with change notifications.

Add validation with `services.AddOptions<T>().Bind(...).ValidateDataAnnotations().ValidateOnStart()`.

## 38. What is `IHostedService` / `BackgroundService`?

Interfaces for running background tasks alongside your ASP.NET Core app (queue consumers, timers, warmup).

```csharp
public class Worker : BackgroundService {
    protected override async Task ExecuteAsync(CancellationToken ct) {
        while (!ct.IsCancellationRequested) {
            await DoWorkAsync(ct);
            await Task.Delay(TimeSpan.FromMinutes(1), ct);
        }
    }
}

builder.Services.AddHostedService<Worker>();
```

Started with the host, stopped on shutdown (respect the cancellation token for graceful shutdown).

## 39. What is Entity Framework Core and how does change tracking work?

EF Core is Microsoft's ORM. It maps C# objects to database tables and provides LINQ-to-SQL translation.

**Change tracking**: the `DbContext` tracks entities loaded via queries or added via `Add`, comparing their current state to the snapshot on `SaveChanges` to generate the right SQL.

```csharp
var user = await db.Users.FirstAsync(u => u.Id == 1);
user.Name = "New";       // tracked
await db.SaveChanges();  // UPDATE users SET name = ... WHERE id = 1
```

- **`AsNoTracking()`** — skip tracking for read-only queries (faster, less memory).
- **`AsSplitQuery()`** — avoid Cartesian explosion with multiple `Include`s.
- Watch for **N+1** — use `.Include()` / projections.
- **Migrations** — `dotnet ef migrations add / database update`.

## 40. What are DTOs and why decouple entities from API models?

**DTOs (Data Transfer Objects)** are simple classes shaped for a specific boundary (HTTP API, external integration), separate from your domain/entity model.

Reasons to decouple:
- **Avoid over-posting** — clients can't set fields you didn't expose.
- **Avoid over-fetching / lazy loading traps** — return only what's needed.
- **Independent evolution** — DB schema can change without breaking the API contract.
- **Security** — never leak `PasswordHash`, internal IDs, or navigation cycles.

Map manually (fast, explicit) or with **AutoMapper** / **Mapster** (less boilerplate, hidden cost). Many teams have moved back to manual mapping for clarity and startup performance.
