# C# / .NET Interview Questions

> Answers are hidden by default — click each toggle to reveal.

## Collections & LINQ — Basics

### 1. What's the difference between `IQueryable<T>` and `IEnumerable<T>`? When would using the wrong one cause a performance problem?

<details>
<summary>Show answer</summary>

`IEnumerable<T>` represents an in-memory sequence — operations like `Where`, `Select`, etc. execute as LINQ-to-Objects in the .NET process, iterating one item at a time.

`IQueryable<T>` extends `IEnumerable<T>` but carries an **expression tree** instead of compiled delegates. A provider (like EF Core) translates that tree into another language (SQL) and pushes the work to the source.

**Performance trap:** if you start with an `IQueryable<T>` (e.g., a `DbSet<T>`) and cast/assign it to `IEnumerable<T>` too early, subsequent `Where` / `Select` calls happen *in memory*. So:

```csharp
IEnumerable<User> users = db.Users;                   // still IQueryable under the hood
var active = users.Where(u => u.IsActive).ToList();   // BUT extension resolves to Enumerable.Where
```

If the compile-time type is `IEnumerable<T>`, the C# compiler binds to `Enumerable.Where`, which pulls **all rows** from the database first and filters in memory. With millions of rows, that's a disaster. Keep it as `IQueryable<T>` until you really want to materialize.

</details>

---

### 2. What's the difference between `List<T>` and `IList<T>` as a return type from a method? What are the trade-offs of exposing one vs the other?

<details>
<summary>Show answer</summary>

- `List<T>` is a concrete class. Callers get access to `Add`, `RemoveAt`, `Sort`, `Capacity`, `AddRange`, etc.
- `IList<T>` is an interface. Callers get indexer, `Count`, `Add`/`Remove`, but no concrete-class extras.

**Trade-offs:**
- Returning `List<T>` lets callers mutate freely and use list-specific methods, but **locks you into that implementation**. Switching to an array, `ImmutableList<T>`, or a custom collection later is a breaking change.
- Returning `IList<T>` is more flexible, but still mutable — callers can `Add` and corrupt internal state if you handed them your private list.
- Often the best choice is `IReadOnlyList<T>` (read-only, indexable, has `Count`) or `IEnumerable<T>` (only iteration).

Rule of thumb: **return the least powerful interface that satisfies callers; accept the most permissive parameter type.**

</details>

---

### 3. Explain deferred execution in LINQ. What's the difference between `Where()` and `ToList()` in terms of when the query runs?

<details>
<summary>Show answer</summary>

Most LINQ operators (`Where`, `Select`, `OrderBy`, `Take`, …) are **deferred**: calling them only builds a query object. No work happens until you iterate (foreach, `ToList`, `ToArray`, `First`, `Count`, etc.).

```csharp
var query = numbers.Where(n => n > 10);  // nothing runs
foreach (var n in query) { ... }         // NOW Where's predicate runs
```

`ToList()` is a **terminal operator**: it forces enumeration, runs every predicate/projection, and materializes results into a `List<T>` in memory.

So `Where()` schedules a filter; `ToList()` executes the pipeline and gives you a snapshot.

</details>

---

### 4. What happens if you iterate the same `IEnumerable<T>` (backed by a LINQ query) twice in a row? Any side effects?

<details>
<summary>Show answer</summary>

The query **runs again from scratch** every iteration. Each `foreach` re-evaluates the source and re-applies every operator.

Consequences:
- If the source is a `DbSet`, **you hit the database twice**.
- If the source is `File.ReadLines`, you re-open and re-read the file.
- If predicates have side effects (logging, counters), they fire twice.
- If the underlying data changed between iterations, you get different results — confusing bugs.

If you need stable, single-pass data, call `.ToList()` (or `.ToArray()`) once and iterate the materialized copy.

</details>

---

### 5. Difference between `First()`, `FirstOrDefault()`, `Single()`, and `SingleOrDefault()` — and when would each throw?

<details>
<summary>Show answer</summary>

| Method | 0 matches | 1 match | 2+ matches |
|---|---|---|---|
| `First()` | throws `InvalidOperationException` | returns it | returns the first |
| `FirstOrDefault()` | returns `default(T)` | returns it | returns the first |
| `Single()` | throws | returns it | throws |
| `SingleOrDefault()` | returns `default(T)` | returns it | throws |

- Use `First` / `FirstOrDefault` when you want **any** match (often with `OrderBy`).
- Use `Single` / `SingleOrDefault` when you want to **assert uniqueness** — e.g., lookup by primary key. The throw is a feature: it tells you your assumption is broken.
- `default(T)` for reference types and nullable value types is `null`; for non-nullable value types it's `0`/`false`/etc. — so `FirstOrDefault()` on `IEnumerable<int>` returning `0` could mean "no match" *or* "matched a zero".

</details>

---

## EF Core specific

### 6. Difference between `Find()`, `Single()`, and `First()` on a `DbSet<T>`. Which one hits the database and which might not?

<details>
<summary>Show answer</summary>

- **`Find(key)`** — looks up by primary key. **First checks the change tracker / identity map**. If the entity is already loaded in this `DbContext`, returns it without a DB roundtrip. Only queries the DB on a miss.
- **`Single(predicate)`** / **`SingleOrDefault(predicate)`** — always generates SQL and hits the database. Asserts at most one match (`TOP 2` in the query so it can throw on duplicates).
- **`First(predicate)`** / **`FirstOrDefault(predicate)`** — always hits the database. Generates `TOP 1`.

So `Find` is the only one with a chance of skipping the DB. Use it when you're looking up by PK and there's a decent chance the entity is already tracked.

</details>

---

### 7. What's the difference between eager loading (`Include`), lazy loading, and explicit loading? What are the downsides of each?

<details>
<summary>Show answer</summary>

- **Eager loading (`Include` / `ThenInclude`)** — load related data in the same query as the parent. Downside: easy to over-fetch by including big relations you don't need, and `Include` with multiple collection navigations causes a Cartesian explosion (one row per combination) unless EF splits queries.
- **Lazy loading** — relations are loaded on first property access via a proxy. Downside: causes the **N+1 problem**, hidden DB calls scattered across your code, and breaks when the `DbContext` is already disposed.
- **Explicit loading (`context.Entry(entity).Reference(...).Load()` / `Collection(...).Load()`)** — manually trigger a load after the fact. Downside: more verbose, and you have to know when to call it; still a separate roundtrip per load.

Default: eager-load what you know you need, avoid lazy loading globally, reach for explicit loading when a relation is *sometimes* needed.

</details>

---

### 8. What is the N+1 query problem and how does it relate to lazy loading?

<details>
<summary>Show answer</summary>

You issue **1** query to fetch N parent rows, then accessing a navigation property on each parent triggers **1 query per parent** to load its children — **N+1** roundtrips total.

```csharp
var orders = db.Orders.ToList();           // 1 query
foreach (var o in orders)
    Console.WriteLine(o.Customer.Name);    // N queries (lazy loading)
```

Lazy loading is the classic cause because the extra queries are silent. Fix:
- `db.Orders.Include(o => o.Customer).ToList()` — single JOINed query.
- Or project to a DTO: `db.Orders.Select(o => new { o.Id, o.Customer.Name })`.

Even without lazy loading you can hit N+1 by manually querying inside a loop, so the pattern matters more than the mechanism.

</details>

---

### 9. Difference between `AsNoTracking()` and a regular query. When should you use it?

<details>
<summary>Show answer</summary>

By default EF Core attaches every materialized entity to the change tracker so it can detect mutations and persist them on `SaveChanges`. That costs memory, CPU, and prevents the GC from collecting entities until the context is disposed.

`AsNoTracking()` skips that — entities aren't tracked, and EF won't notice changes to them.

Use it when:
- The query is **read-only** (display, reports, API responses).
- You're loading **large result sets**.
- You're not going to call `SaveChanges` on these entities.

Don't use it when you intend to mutate and save the entities — you'd have to manually `Update`/`Attach`, which is error-prone.

There's also `AsNoTrackingWithIdentityResolution()` for read-only queries where you still want one CLR instance per PK across the result.

</details>

---

### 10. What happens if you call `.Where(x => SomeCSharpMethod(x.Name))` on a `DbSet<T>`? Does it run on the database or in memory?

<details>
<summary>Show answer</summary>

EF Core tries to translate the lambda's expression tree into SQL. If the call references a custom C# method, the provider can't translate it.

In **EF Core 3.0+**, untranslatable expressions **throw at runtime** (`InvalidOperationException`) — no silent client-side evaluation. (Older EF Core silently fell back to in-memory evaluation, which caused massive performance bugs.)

To get the behavior you want, you must explicitly opt in:
```csharp
db.Users.AsEnumerable().Where(x => SomeCSharpMethod(x.Name))
```
…which pulls all rows into memory first, then filters. Usually you should rewrite the predicate into something EF *can* translate (e.g., expression tree functions, mapped scalar functions, or pre-computing values).

</details>

---

### 11. Difference between `IQueryable.ToList()` and `IQueryable.AsEnumerable().ToList()`. Where does filtering happen in each?

<details>
<summary>Show answer</summary>

```csharp
db.Users.Where(u => u.IsActive).ToList();
// → SQL: SELECT * FROM Users WHERE IsActive = 1
//   Filter runs in the database. Only matching rows cross the wire.

db.Users.AsEnumerable().Where(u => u.IsActive).ToList();
// → SQL: SELECT * FROM Users
//   ALL rows stream into memory; filter runs in C# via Enumerable.Where.
```

`AsEnumerable()` is the "switch from `IQueryable` to LINQ-to-Objects" boundary. It doesn't execute immediately, but every operator after it runs in memory. Use it deliberately when you need a C# method in the middle of a pipeline — and only after you've narrowed the data down on the server.

</details>

---

### 12. What's the difference between `SaveChanges()` and `SaveChangesAsync()` beyond the async part? Anything to watch out for with the change tracker?

<details>
<summary>Show answer</summary>

The semantics are essentially the same: both flush tracked changes to the database in a transaction and return the number of affected rows. The async version frees the calling thread while awaiting the DB roundtrip — important under load, especially in ASP.NET.

Watch out for:
- **`DbContext` is not thread-safe.** Don't call `SaveChangesAsync` while another query/await on the *same* context is in flight. Concurrent operations throw `InvalidOperationException`.
- **Change tracker state persists between saves.** Successfully saved entities remain tracked. If you reuse a long-lived context and run repeated saves, the tracker grows and slows down. Prefer short-lived contexts (DI scoped is the usual pattern).
- **Exceptions leave the tracker dirty.** If `SaveChangesAsync` throws (e.g., constraint violation), the in-memory state still reflects your changes — fix and retry, or discard the context.
- **Interceptors / `SavingChanges` events** run on both. Don't double-trigger side effects across nested saves.

</details>

---

## Async & threading

### 13. Difference between `Task`, `Task<T>`, and `ValueTask<T>`. When would you use `ValueTask`?

<details>
<summary>Show answer</summary>

- `Task` — represents an async operation with no result.
- `Task<T>` — async operation returning a `T`. Both are reference types — every invocation allocates.
- `ValueTask<T>` — a struct that can wrap *either* an immediately-available result *or* a `Task<T>` for the asynchronous path. Avoids the allocation when the operation completes synchronously.

Use `ValueTask<T>` when:
- The method **often completes synchronously** (e.g., reading from a buffered stream, cached lookups).
- The method is on a **hot path** where the per-call allocation matters.

Caveats:
- `ValueTask` instances should be awaited **at most once**. Awaiting twice, calling `.Result`, or `GetAwaiter().GetResult()` more than once is undefined behavior.
- Don't store them in fields or pass them around. Prefer `Task` for public APIs unless profiling proves the allocation hurts.

</details>

---

### 14. What does `ConfigureAwait(false)` do and why does it matter in library code?

<details>
<summary>Show answer</summary>

By default, `await` captures the current `SynchronizationContext` (or `TaskScheduler`) and resumes the continuation on it. In classic ASP.NET and WinForms/WPF that means resuming on a specific thread (UI thread or request context).

`ConfigureAwait(false)` tells the awaiter: *don't bother capturing the context; resume on any thread pool thread*.

Why it matters in libraries:
- **Performance** — skips the context capture/post.
- **Deadlock avoidance** — if some caller blocks synchronously on your task (`.Result` / `.Wait()`) while holding the captured context, your continuation can never run on that same context → deadlock. `ConfigureAwait(false)` avoids that trap.

In **ASP.NET Core**, there's no `SynchronizationContext`, so `ConfigureAwait(false)` is a no-op functionally but still recommended in shared libraries that might be used in other hosts.

Application code (UI, WinForms) often *wants* to capture the context, so don't sprinkle it everywhere — it's a library-author idiom.

</details>

---

### 15. What happens if you call `.Result` or `.Wait()` on an async method in an ASP.NET context? Why is it dangerous?

<details>
<summary>Show answer</summary>

`.Result` and `.Wait()` block the current thread until the task completes. Combined with a captured `SynchronizationContext`, this is the classic **sync-over-async deadlock**:

1. Request thread T enters your method and calls `SomeAsync().Result` — T blocks waiting.
2. Inside `SomeAsync`, an `await` captures the ASP.NET context (which is associated with T).
3. When the awaited op finishes, the continuation tries to resume on the captured context — but the context is "owned" by thread T, which is blocked waiting for the result.
4. Deadlock. The request hangs forever.

Even when it doesn't deadlock (ASP.NET Core has no sync context, so the request just runs), `.Result` / `.Wait()`:
- **Blocks a thread pool thread**, killing scalability under load (thread starvation).
- Wraps exceptions in `AggregateException`, which complicates error handling.

Rule: **async all the way down.** If you must bridge (`Main`, event handler), use `await` or `GetAwaiter().GetResult()` consciously and only at the top of the stack.

</details>

---

## Language fundamentals

### 16. Difference between `class` and `struct`. What does it mean that one is a value type and the other a reference type — and how does that affect passing them to methods?

<details>
<summary>Show answer</summary>

- `class` is a **reference type** — instances live on the heap, variables hold a reference (pointer). Assigning copies the *reference*, not the data; multiple variables can refer to the same object.
- `struct` is a **value type** — instances live wherever they're declared (stack for locals, inline within a containing heap object for fields). Assignment **copies the whole value**.

Passing to methods:
- A reference type parameter is a copy of the *reference*. Mutations to the object's fields are visible to the caller; reassigning the parameter isn't (unless `ref`).
- A struct parameter is a **copy of the entire struct**. Mutations to its fields are local to the method and lost when it returns — unless you pass `ref` / `in`.

Other implications:
- Structs have no nullability by default (need `Nullable<T>` / `T?`).
- Boxing: storing a struct in `object` / a non-generic collection allocates on the heap.
- Big structs (>16 bytes-ish) are expensive to copy; prefer `class` or `readonly struct` with `in`.
- Structs can't have a parameterless constructor on older C#; in C# 10+ they can, but defaults still come from `default`.

Use struct for small, immutable, value-like data (points, money). Use class for almost everything else.

</details>

---

### 17. Difference between `const`, `readonly`, and `static readonly`. When is each evaluated?

<details>
<summary>Show answer</summary>

- **`const`** — compile-time constant. Value must be a literal expression known at compile time. **Baked into the calling assembly** at compile time, so if you change a `const` in library A, library B keeps the old value until it's recompiled. Implicitly `static`.
- **`readonly`** — instance field. Assignable only in the declaration or constructor. Evaluated **at construction time**. Different instances can have different values.
- **`static readonly`** — static field, assignable only in the declaration or the static constructor. Evaluated **once, lazily, the first time the type is used**. Not baked into callers — changes propagate to consumers without recompilation.

Use `const` for true, never-changing primitives (`Pi`, `MaxBufferSize` literal). Use `static readonly` for things that *feel* constant but are computed or shared, or where binary compatibility matters. Use `readonly` for per-instance immutable fields.

</details>

---

### 18. What's the difference between `string` and `StringBuilder`? Why does concatenating strings in a loop matter?

<details>
<summary>Show answer</summary>

`string` is **immutable**. Every operation (`+`, `Substring`, `Replace`) allocates a new `string`. Concatenating in a loop:

```csharp
string s = "";
for (int i = 0; i < n; i++)
    s += i;   // allocates a new string each iteration
```
…is O(n²) in time and memory: each `+=` copies all previous characters into the new string.

`StringBuilder` holds a mutable internal buffer that grows geometrically (usually doubling). `Append` mutates in place, amortized O(1) per char. After the loop you call `.ToString()` once.

```csharp
var sb = new StringBuilder();
for (int i = 0; i < n; i++) sb.Append(i);
string s = sb.ToString();
```

Rules of thumb:
- Single-shot concats with a few parts: `string` (`+`, interpolation, `string.Concat`) is fine and the compiler may fold them.
- Loops / unknown number of parts: `StringBuilder`.
- Joining a known collection: `string.Join` is concise and efficient.

</details>

---

### 19. Explain `IDisposable` and the `using` statement. What happens if you forget to dispose something like a `DbContext`?

<details>
<summary>Show answer</summary>

`IDisposable` is the standard interface for releasing **unmanaged resources** (file handles, sockets, DB connections, native memory) or managed resources with non-trivial cleanup (event subscriptions, pooled objects).

`using` ensures `Dispose()` is called even if an exception is thrown:

```csharp
using (var ctx = new MyDbContext()) { ... }
// equivalent to a try/finally that calls ctx.Dispose() at the end
```

C# 8+ has the `using` declaration: `using var ctx = new MyDbContext();` disposes at the end of the enclosing scope.

If you forget to dispose a `DbContext`:
- The underlying DB connection isn't returned to the pool until the GC eventually runs the finalizer (if any). Under load this can **exhaust the connection pool** and break the app.
- Tracked entities and the change tracker stay in memory longer than needed.
- Any `IDisposable` event subscriptions held by the context aren't released.

For async resources, the equivalent is `IAsyncDisposable` + `await using`, which lets cleanup itself be async (good for flushing buffers, closing network sockets without blocking).

</details>

---

### 20. Difference between `==` and `.Equals()` for reference types and for strings specifically. What about for nullable value types?

<details>
<summary>Show answer</summary>

- **Reference types (default)** — `==` and `.Equals()` both perform **reference equality** unless overridden. They return `true` only when both operands are the same object on the heap.
- **`string`** — both `==` and `.Equals()` perform **value (ordinal) equality**. `string` overloads `==` to compare characters, and overrides `.Equals`. `ReferenceEquals(a, b)` is the way to check if they're literally the same instance. (Note: string interning can make distinct-looking literals share a reference, but that's an optimization, not a semantic rule.)
- **Custom classes** — if you don't override `Equals` and `==`, you get reference equality. If you override `Equals` but not `==`, the two operators give different answers — a classic bug. Override both (and `GetHashCode`) together, or use a `record` which does it for you.

For **nullable value types (`T?` / `Nullable<T>`)**:
- `==` is lifted to nullables: `null == null` is `true`, `null == 5` is `false`, `5 == 5` is `true`.
- `.Equals()` follows the same logic, but you can't call `null.Equals(...)` — you'd `NullReferenceException`. Use `Nullable.Equals(a, b)` or the `==` operator when either side might be null.
- For boxed nullables, comparisons get tricky — boxing a `Nullable<int>` with no value boxes to `null`, which can surprise reflection-based comparisons.

General rule: use `==` for primitives and strings, `.Equals` (or pattern matching / records) when you want value semantics on custom types — and always be aware of which one you're getting.

</details>

---

## LINQ — Deeper

### 21. Difference between `Select` and `SelectMany`? When would you use each?

<details>
<summary>Show answer</summary>

`Select` is a **1-to-1** projection: each input produces exactly one output. Shape and length are preserved.

`SelectMany` is a **1-to-many** projection that **flattens**. Each input produces an `IEnumerable<U>`, and `SelectMany` concatenates them all into a single sequence.

```csharp
// Select: IEnumerable<IEnumerable<LineItem>>
var nested = orders.Select(o => o.LineItems);

// SelectMany: IEnumerable<LineItem>
var flat = orders.SelectMany(o => o.LineItems);
```

There's also a 3-arg overload that pairs each child with its parent — perfect for joining nested data back to its source:

```csharp
orders.SelectMany(
    o => o.LineItems,
    (o, li) => new { OrderId = o.Id, li.Sku, li.Qty });
```

In query syntax, multiple `from` clauses compile to `SelectMany`:
```csharp
from o in orders
from li in o.LineItems   // SelectMany
select new { o.Id, li.Sku };
```

</details>

---

### 22. What does `GroupBy` return and how do you flatten or aggregate its results?

<details>
<summary>Show answer</summary>

`GroupBy(keySelector)` returns `IEnumerable<IGrouping<TKey, TElement>>`. An `IGrouping<K,T>` is itself an `IEnumerable<T>` that also exposes a `.Key`.

```csharp
var byCustomer = orders.GroupBy(o => o.CustomerId);
foreach (var g in byCustomer) {
    Console.WriteLine($"Customer {g.Key} has {g.Count()} orders");
    foreach (var o in g) Console.WriteLine($"  {o.Id}");
}
```

Common follow-ups:
- **Aggregate per group:** `Select(g => new { g.Key, Total = g.Sum(o => o.Amount) })`
- **Map of key → list:** `ToDictionary(g => g.Key, g => g.ToList())`
- **Multi-value dictionary in one shot:** `orders.ToLookup(o => o.CustomerId)` — returns `ILookup<K,T>`, eagerly built, immutable.
- **Flatten back** (rare — you've grouped for nothing): `SelectMany(g => g)`.

In SQL/EF, `GroupBy` translates to `GROUP BY` — but only when followed by an aggregate projection. `GroupBy(...).ToList()` (asking for the raw groups) often forces client-side evaluation.

</details>

---

### 23. Difference between `Join` and `GroupJoin` in LINQ?

<details>
<summary>Show answer</summary>

**`Join`** is an inner join: one output row per matching (outer, inner) pair. Outer rows with no inner match disappear (like SQL `INNER JOIN`).

```csharp
customers.Join(orders,
    c => c.Id, o => o.CustomerId,
    (c, o) => new { c.Name, o.Amount });
```

**`GroupJoin`** is like "left join with grouping": one output row per outer element, with **all** matching inner elements as a sub-collection. Outer elements with no matches still appear, with an empty group.

```csharp
customers.GroupJoin(orders,
    c => c.Id, o => o.CustomerId,
    (c, os) => new { c.Name, OrderCount = os.Count() });
```

For a SQL-style LEFT JOIN (flat rows, nulls for missing inner), chain `GroupJoin` + `SelectMany` + `DefaultIfEmpty`:

```csharp
from c in customers
join o in orders on c.Id equals o.CustomerId into co
from o in co.DefaultIfEmpty()
select new { c.Name, Amount = o?.Amount };
```

</details>

---

### 24. What's the difference between `OrderBy().OrderBy()` and `OrderBy().ThenBy()`?

<details>
<summary>Show answer</summary>

`OrderBy(a).OrderBy(b)` **discards the first sort.** Each `OrderBy` is a fresh sort by a single key — the second sort doesn't know about the first. The final order is purely by `b`.

`OrderBy(a).ThenBy(b)` is a single **composite** sort: primary key `a`, tiebreaker `b`. This is almost always what you want.

```csharp
// WRONG: only sorts by Name
people.OrderBy(p => p.LastName).OrderBy(p => p.FirstName);

// RIGHT: sorts by LastName, ties broken by FirstName
people.OrderBy(p => p.LastName).ThenBy(p => p.FirstName);
```

Same applies for `OrderByDescending` and `ThenByDescending` — they mix freely:
```csharp
people.OrderBy(p => p.LastName).ThenByDescending(p => p.Age);
```

`ThenBy` is only available on `IOrderedEnumerable<T>` / `IOrderedQueryable<T>` — that's how the compiler enforces that it follows an `OrderBy`. The bug is easy to miss because both versions compile and run.

</details>

---

### 25. `Any()` vs `Count() > 0` vs `Contains()` — performance considerations?

<details>
<summary>Show answer</summary>

- **`Any()`** — short-circuits on the first match. For `IEnumerable<T>` it stops at the first hit instead of walking the whole sequence. In EF it translates to `EXISTS` (no row count). Always cheapest for "is there at least one?".
- **`Count() > 0`** — on a plain `IEnumerable<T>`, must enumerate the entire sequence. On `ICollection<T>` (`List`, `Array`, `HashSet`) it uses the `Count` property — O(1). In EF it runs `SELECT COUNT(*)`, which is more expensive than `EXISTS` on large tables.
- **`Contains(item)`** — O(n) for `List<T>` / `IEnumerable<T>`. O(1) average for `HashSet<T>` / `Dictionary<K,V>.ContainsKey`. In EF, translates to `WHERE col IN (...)` or `EXISTS`.

Rules of thumb:
- "Does any match exist?" → `Any(pred)`. Always.
- "Is this collection empty?" on a `List` / `Array` → `Count == 0` or `.Length == 0` is fine.
- "Is X in this collection (repeated)?" → put the haystack in a `HashSet<T>` once.
- Never write `coll.Where(pred).Count() > 0` — use `coll.Any(pred)`.

</details>

---

### 26. What does `Aggregate` do? When would you use it over a built-in?

<details>
<summary>Show answer</summary>

`Aggregate` is a fold/reduce: walk the sequence, threading an accumulator.

Three overloads:
```csharp
// 1. No seed — uses first element as the initial accumulator. Throws if empty.
numbers.Aggregate((acc, n) => acc * n);   // product

// 2. Seed + folder
numbers.Aggregate(0, (acc, n) => acc + n);    // same as Sum()

// 3. Seed + folder + result selector
words.Aggregate(
    new StringBuilder(),
    (sb, w) => sb.Append(w).Append(' '),
    sb => sb.ToString().TrimEnd());
```

Reach for it when:
- No built-in (`Sum`, `Min`, `Max`, `Average`, `Count`) covers your case.
- You want to compute several things in one pass — use a tuple/struct accumulator: `numbers.Aggregate((sum: 0, count: 0), (a, n) => (a.sum + n, a.count + 1))`.
- You're going for a functional style and the team is comfortable with it.

Avoid for string concatenation in a loop — allocates a new string per step. Use `string.Join` or `StringBuilder` directly. A plain `foreach` is often more readable than a clever `Aggregate`.

</details>

---

### 27. Difference between `Distinct()`, `DistinctBy()`, and `GroupBy(k).Select(g => g.First())`?

<details>
<summary>Show answer</summary>

- **`Distinct()`** — dedupes using the element's **own** equality. For value types and `string`, that's value equality. For custom classes without an `Equals` override, you get reference equality — almost never what you want.
- **`Distinct(IEqualityComparer<T>)`** — same, but with custom equality (e.g., `StringComparer.OrdinalIgnoreCase`).
- **`DistinctBy(keySelector)`** (.NET 6+) — dedupes by a key extracted from each element. Keeps the **first** occurrence per key. Streams: uses a `HashSet<TKey>` internally, doesn't buffer.
- **`GroupBy(k).Select(g => g.First())`** — same end result as `DistinctBy`, but **buffers the entire sequence** to form groups. Cheaper to write in older .NET; in modern code, `DistinctBy` is the right call.

In EF, `DistinctBy` doesn't translate cleanly — use the `GroupBy(...).Select(...)` form or a window function via raw SQL.

</details>

---

### 28. What's the difference between `Zip`, `Concat`, and `Union`?

<details>
<summary>Show answer</summary>

- **`Concat(a, b)`** — appends `b` after `a`. Lengths add. Duplicates kept.
  ```csharp
  new[]{1,2}.Concat(new[]{2,3});   // 1, 2, 2, 3
  ```
- **`Union(a, b)`** — set union: distinct elements from both. Uses default equality or a comparer.
  ```csharp
  new[]{1,2}.Union(new[]{2,3});    // 1, 2, 3
  ```
- **`Zip(a, b)`** — pairs the i-th elements. Result length = min of the two. Default overload returns tuples; another takes a combiner.
  ```csharp
  new[]{1,2,3}.Zip(new[]{"a","b"});   // (1,"a"), (2,"b")
  ```

Related set operations: **`Intersect`** (elements present in both, deduped) and **`Except`** (in `a`, not in `b`, deduped). All of these accept an `IEqualityComparer<T>` overload.

</details>

---

### 29. `Take`, `Skip`, `TakeWhile`, `SkipWhile` — what are the differences?

<details>
<summary>Show answer</summary>

- **`Take(n)`** — first `n` elements (or all if fewer).
- **`Skip(n)`** — discards the first `n`, yields the rest.
- **`TakeWhile(pred)`** — yields while the predicate holds; **stops at the first false** and yields nothing after, even if later elements would pass.
- **`SkipWhile(pred)`** — skips while the predicate holds; **starts yielding at the first false** and yields everything from then on, regardless of predicate.

```csharp
new[]{1,2,3,4,3,2,1}.TakeWhile(n => n < 4);  // 1, 2, 3
new[]{1,2,3,4,3,2,1}.SkipWhile(n => n < 4);  // 4, 3, 2, 1
```

Common patterns:
- **Paging:** `query.Skip(page * size).Take(size)`.
- **Streaming until a sentinel:** `lines.TakeWhile(l => l != "END")`.
- **End slicing** (.NET 6+): `TakeLast(n)`, `SkipLast(n)`.

In EF, `Skip`/`Take` translate to `OFFSET ... FETCH`. `TakeWhile`/`SkipWhile` don't translate and force client evaluation — they're LINQ-to-Objects tools.

</details>

---

### 30. Query syntax vs method syntax — what do `let` and `into` do?

<details>
<summary>Show answer</summary>

Query syntax (`from x in xs ... select ...`) is **sugar** for the method calls — the compiler rewrites it. So they have identical capabilities for the operators they cover, but query syntax has a couple of nice features:

**`let`** introduces a named intermediate value — handy when you'd otherwise compute the same expression twice:
```csharp
from u in users
let fullName = u.First + " " + u.Last
where fullName.Contains("Smith")
select new { u.Id, fullName }
```
Method syntax has no direct equivalent; it compiles to a `Select` that produces an anonymous object adding the new field, then later operators reference it.

**`into`** rebinds a "continuation" — after a `select` or `group`, you keep querying as if from a new source:
```csharp
from o in orders
group o by o.CustomerId into g
where g.Count() > 5
select new { g.Key, Total = g.Sum(o => o.Amount) }
```

When to pick which:
- **Query syntax** wins for multi-source joins, complex `group by`, and `let`-heavy pipelines — reads top-to-bottom like SQL.
- **Method syntax** wins for short pipelines, custom operators (anything not covered by keywords: `Skip`, `Take`, `Distinct`, `Aggregate`, `Any`, …), and chaining off existing variables.

You can mix: wrap a query expression in parentheses and chain method calls off it.

</details>

---

## Collections — Deeper

### 31. Difference between `Dictionary<K,V>`, `SortedDictionary<K,V>`, `ConcurrentDictionary<K,V>`, and `ImmutableDictionary<K,V>` — when to use each?

<details>
<summary>Show answer</summary>

- **`Dictionary<K,V>`** — hash table. O(1) average lookup/insert. **Unordered.** Not thread-safe. The default choice.
- **`SortedDictionary<K,V>`** — red-black tree. O(log n) lookup/insert. Iterates in **key order**. Use when you need sorted iteration.
- **`SortedList<K,V>`** — sorted, backed by parallel arrays. Lookup O(log n) via binary search; insert O(n) because of shifting. Lower memory and faster iteration than `SortedDictionary`, slower mutation. Good for build-once-read-many.
- **`ConcurrentDictionary<K,V>`** — thread-safe via fine-grained striping. Atomic `GetOrAdd` / `AddOrUpdate`. More overhead per op; use only when multiple threads write. Reads can race with writes safely.
- **`ImmutableDictionary<K,V>`** — every mutation returns a **new** dictionary (structural sharing). Thread-safe by virtue of immutability. Mutations O(log n). Great for "snapshot" semantics shared across threads.
- **`FrozenDictionary<K,V>`** (.NET 8+) — read-only, optimized for **read-heavy** workloads after construction. Faster lookups than `Dictionary`, at the cost of slow construction. Built via `dict.ToFrozenDictionary()`.

Comparer note: all of these take an `IEqualityComparer<K>` / `IComparer<K>` overload — use `StringComparer.OrdinalIgnoreCase` for case-insensitive string keys.

</details>

---

### 32. `HashSet<T>` vs `List<T>` for lookup operations — what's the Big-O of `Contains`?

<details>
<summary>Show answer</summary>

- `List<T>.Contains(item)` — **O(n)** linear scan, calling `Equals` on each element.
- `HashSet<T>.Contains(item)` — **O(1) average** (hash + bucket check, then `Equals` on collisions).

Classic optimization: when you need to check membership repeatedly, build a `HashSet<T>` once and query it. Replacing `if (badIds.Contains(x))` where `badIds` is a `List<int>` of 10k items, with the same call on a `HashSet<int>`, turns a O(m·n) loop into O(m).

```csharp
var bannedSet = bannedIds.ToHashSet();  // build once
var allowed = users.Where(u => !bannedSet.Contains(u.Id)).ToList();
```

Other things `HashSet<T>` gives you:
- Enforces uniqueness — `Add` returns `false` on duplicates instead of throwing.
- Set operations: `UnionWith`, `IntersectWith`, `ExceptWith`, `SetEquals`, `IsSubsetOf`.

If you also need ordering, `SortedSet<T>` is O(log n) per op.

Caveat: hashing only works if `GetHashCode` and `Equals` are consistent. For custom types, override both — or use `record`, or pass a custom `IEqualityComparer<T>`.

</details>

---

### 33. Difference between `Array`, `List<T>`, and `LinkedList<T>` — when is `LinkedList` ever the right choice?

<details>
<summary>Show answer</summary>

- **`T[]`** — fixed size, contiguous memory. O(1) index. Fastest iteration (cache-friendly). Can't grow — you allocate a new array.
- **`List<T>`** — `T[]` under the hood with auto-growth (capacity doubles when full). O(1) index, O(1) amortized append, O(n) insert/remove at front or middle (shifts elements).
- **`LinkedList<T>`** — doubly-linked list of `LinkedListNode<T>` objects. O(1) insert/remove **given a node**. O(n) lookup by value or index. Every node is a heap allocation — terrible cache behavior; iteration is much slower than `List<T>` in practice.

`LinkedList<T>` is rarely the right answer. It wins only when:
- You're doing many O(1) splices at known positions (you already hold the node — e.g., an LRU cache that moves entries to the front).
- You need stable iterators that survive insertions/removals elsewhere.

In almost any other scenario — including "I do lots of inserts" — `List<T>` is faster because the memory layout dominates the algorithmic complexity at realistic sizes. Profile before reaching for `LinkedList<T>`.

</details>

---

### 34. `Queue<T>`, `Stack<T>`, `PriorityQueue<T,P>` — what's each for?

<details>
<summary>Show answer</summary>

- **`Queue<T>`** — FIFO. `Enqueue`, `Dequeue`, `Peek`, `TryDequeue`. O(1) amortized. Backed by a circular buffer.
- **`Stack<T>`** — LIFO. `Push`, `Pop`, `Peek`, `TryPop`. O(1) amortized. Backed by an array that grows on push.
- **`PriorityQueue<TElement, TPriority>`** (.NET 6+) — min-heap by priority. `Enqueue(item, priority)`; `Dequeue()` returns the **lowest-priority** element. O(log n) per op.

Thread-safe alternatives (`System.Collections.Concurrent`):
- `ConcurrentQueue<T>`, `ConcurrentStack<T>` — lock-free.
- `BlockingCollection<T>` wraps an underlying producer/consumer collection with bounded capacity and blocking semantics.
- **No built-in concurrent priority queue** — wrap your own with a lock if you need it.

Gotcha: `PriorityQueue` is **not stable** — items with equal priority can come out in any order. If you need stability, pack a monotonically-increasing sequence number into the priority (e.g., `(priority, seq)` tuple priority).

</details>

---

### 35. Collection interface hierarchy — `IEnumerable<T>`, `ICollection<T>`, `IList<T>`, `IReadOnlyCollection<T>`, `IReadOnlyList<T>`?

<details>
<summary>Show answer</summary>

Two parallel hierarchies, both rooted at `IEnumerable<T>`:

```
IEnumerable<T>                      // foreach only
├─ ICollection<T>                   // + Count, Add, Remove, Contains, Clear, IsReadOnly
│  └─ IList<T>                      // + indexer, Insert, RemoveAt, IndexOf
│
└─ IReadOnlyCollection<T>           // + Count
   └─ IReadOnlyList<T>              // + indexer
```

Notes:
- `IReadOnlyList<T>` does **not** extend `IList<T>` — they're parallel. `List<T>` implements both.
- `IReadOnlyCollection<T>` was added in .NET 4.5 specifically so you could say "I have a count, but you can't mutate" — `IEnumerable<T>` alone forces you to enumerate to count.
- "Read-only" means the *interface* exposes no mutation methods, **not that the underlying collection is truly immutable**. A caller can downcast back to `IList<T>` and mutate. For real immutability, use `ImmutableList<T>` / `ImmutableArray<T>`.

Guidelines:
- **Parameter types:** accept the **weakest** interface that works (often `IEnumerable<T>` or `IReadOnlyList<T>`). Lets more callers reuse your method.
- **Return types:** return the **strongest read-only** interface that matches your invariant — preserves your right to refactor the implementation later.

</details>

---

### 36. What is `yield return` and when does the code in an iterator actually run?

<details>
<summary>Show answer</summary>

`yield return` turns a method into a **state machine**. The compiler generates a hidden class that implements `IEnumerable<T>` / `IEnumerator<T>`; each `yield return` produces the next element and pauses the method, saving its state (locals, instruction pointer).

Key behaviors:
- **The body doesn't execute when you call the method** — it runs only when something starts iterating (`foreach`, `ToList`, `MoveNext`).
- Each `MoveNext()` runs the body up to the next `yield return`, then suspends.
- `yield break` ends iteration cleanly.
- `try/finally` and `using` work across `yield`s — the `finally` runs when the iterator is **disposed** (which `foreach` does automatically when it exits).

```csharp
IEnumerable<int> Generate() {
    Console.WriteLine("start");      // runs on first MoveNext, not on call
    for (int i = 0; i < 3; i++) {
        Console.WriteLine($"yielding {i}");
        yield return i;
    }
    Console.WriteLine("end");
}
```

Common traps:
- **Argument validation** in an iterator method doesn't fire until enumeration starts. Wrap the iterator in a non-iterator method that validates first, then returns the inner iterator.
- Re-iterating produces a fresh state machine each time (see Q4) — side effects repeat.
- Async equivalent: `async IAsyncEnumerable<T>` with `yield return`, consumed via `await foreach`.

</details>

---

### 37. `ToList()`, `ToArray()`, `ToDictionary()`, `ToHashSet()` — ordering, uniqueness, gotchas?

<details>
<summary>Show answer</summary>

All four are **terminal** — they force enumeration and materialize results.

- **`ToList()`** — `List<T>`. **Preserves source order.** Keeps duplicates. Growable. Slight over-allocation (capacity rounded up).
- **`ToArray()`** — `T[]`. Preserves source order. Keeps duplicates. Fixed size. Slightly less memory than `List<T>` (no extra capacity slack).
- **`ToDictionary(keySelector, [valueSelector], [comparer])`** — `Dictionary<K,V>`. **Throws `ArgumentException` on duplicate keys.** No guaranteed order. Common bug: forgetting that a non-unique key blows up at runtime. If dupes are possible, use `GroupBy` / `ToLookup` instead.
- **`ToHashSet([comparer])`** — `HashSet<T>`. **Silently drops duplicates.** No guaranteed order. Optionally takes an `IEqualityComparer<T>`.

Bonus:
- **`ToLookup(keySelector)`** — returns `ILookup<K,T>`, a one-shot, immutable, multi-valued dictionary. Lookups on missing keys return an **empty sequence** instead of throwing (vs. `Dictionary`).
- **`ToFrozenDictionary()` / `ToFrozenSet()`** (.NET 8+) — for read-heavy workloads with rare changes; faster lookups, slower build.

Sizing: when the source implements `ICollection<T>`, these methods pre-size their output to avoid resizes — `someList.ToArray()` is essentially `Array.Copy`. For pure `IEnumerable<T>`, they grow as they go.

</details>

---

### 38. How do you compare two collections for value equality? What does `SequenceEqual` do?

<details>
<summary>Show answer</summary>

`==` on collections is **reference equality** (unless the type overloads it — `List<T>` and arrays don't). Two distinct `List<int>` with identical contents are not `==`.

**`SequenceEqual(other, [comparer])`** compares element-by-element using the element type's equality (or a supplied `IEqualityComparer<T>`). Both **length and order** matter:

```csharp
new[]{1,2,3}.SequenceEqual(new[]{1,2,3});   // true
new[]{1,2,3}.SequenceEqual(new[]{3,2,1});   // false (order matters)
```

For order-insensitive comparison:
- **Sets:** `new HashSet<T>(a).SetEquals(b)` — fast.
- **Multisets / bags** (counts matter, order doesn't): the cheap-and-dirty version is `a.OrderBy(x => x).SequenceEqual(b.OrderBy(x => x))`; for performance, group both sides and compare counts:
  ```csharp
  bool MultisetEqual<T>(IEnumerable<T> a, IEnumerable<T> b) {
      var counts = new Dictionary<T, int>();
      foreach (var x in a) counts[x] = counts.GetValueOrDefault(x) + 1;
      foreach (var x in b) {
          if (!counts.TryGetValue(x, out var c) || c == 0) return false;
          counts[x] = c - 1;
      }
      return counts.Values.All(c => c == 0);
  }
  ```

For **dictionaries**: no built-in. Compare `Count`, then iterate one side and check the other has matching `(key, value)`. Or `OrderBy(kvp => kvp.Key).SequenceEqual(...)` if keys are ordered.

For **deep / nested** structures (DTOs containing lists): write a custom `IEqualityComparer<T>`, use `record` types, or pull in a library (FluentAssertions' `BeEquivalentTo`).

</details>

---

### 39. What's `IEqualityComparer<T>` for? Where can you pass one?

<details>
<summary>Show answer</summary>

`IEqualityComparer<T>` lets you **override how equality and hashing work** for a type without modifying the type itself. Two methods you must implement together:

```csharp
public interface IEqualityComparer<T> {
    bool Equals(T x, T y);
    int GetHashCode(T obj);    // must agree: x.Equals(y) ⇒ GetHashCode(x) == GetHashCode(y)
}
```

**LINQ operators that accept one:** `Distinct`, `Union`, `Intersect`, `Except`, `GroupBy`, `Join`, `GroupJoin`, `Contains`, `ToDictionary`, `ToLookup`, `ToHashSet`, `SequenceEqual`.

**Collections that accept one:** `Dictionary<K,V>`, `HashSet<T>`, `ConcurrentDictionary<K,V>`, `SortedDictionary<K,V>` (takes `IComparer<K>`, the ordering sibling), `ImmutableDictionary<K,V>`, `FrozenDictionary<K,V>`, etc.

Built-ins worth knowing:
- `StringComparer.Ordinal`, `OrdinalIgnoreCase`, `InvariantCulture`, `CurrentCulture` (and their `IgnoreCase` variants).
- `EqualityComparer<T>.Default` — the comparer that LINQ uses when you don't pass one.
- `ReferenceEqualityComparer.Instance` — compares by `object.ReferenceEquals`, ignoring `Equals` overrides.

For ordering (sorting, sorted containers), the sibling interface is **`IComparer<T>`** — returns -1/0/+1. Used by `OrderBy`, `Array.Sort`, `List.Sort`, `SortedSet`, `SortedDictionary`. Different interface, different job.

Modern alternative: create a `record` type — automatic value equality on all members. Or build inline with `EqualityComparer<T>.Create((a, b) => ..., x => ...)` (.NET 8+).

</details>

---

### 40. `Span<T>` and `Memory<T>` — when to use them over `T[]` / `List<T>`?

<details>
<summary>Show answer</summary>

- **`Span<T>`** — a **ref struct** that points to a contiguous region of memory. The region can live on the heap (a `T[]`), the stack (`stackalloc`), or in native memory. Zero-copy slicing via `Slice(start, len)`. Allocation-free.
  Constraints: ref structs **can only live on the stack** — can't be a field of a class, can't be captured by a lambda, can't cross an `await` or `yield`. Method-local only.

- **`Memory<T>`** — a heap-safe handle to the same kinds of regions. Can be stored in fields, passed across `async`, captured in lambdas. You get a `Span<T>` from it via `memory.Span` inside synchronous code.

- **`ReadOnlySpan<T>` / `ReadOnlyMemory<T>`** — read-only variants. `string` exposes `AsSpan()` returning `ReadOnlySpan<char>`, letting you parse and slice substrings **without allocating** new strings.

When they're worth reaching for:
- **Parsing hot paths** — split, trim, scan characters without `Substring` allocations.
- **IO buffers** — `Stream.ReadAsync(Memory<byte>)`, `Pipe`s, `ArrayPool<T>` slicing.
- **High-performance numeric loops** with `MemoryMarshal.Cast<T,U>` and SIMD.

When **not** to reach for them:
- Normal business code where allocations aren't the bottleneck. The API constraints (ref struct rules) and the cognitive overhead aren't worth it.
- Anything async — you can't hold a `Span<T>` across `await`. Use `Memory<T>` instead, or buffer up front.

Companion APIs: `ArrayPool<T>.Shared.Rent(...)` / `.Return(...)` to pool large buffers, and `MemoryMarshal` / `Unsafe` for advanced reinterpretation.

</details>
