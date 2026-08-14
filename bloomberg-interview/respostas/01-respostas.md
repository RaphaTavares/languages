# 🔒 Gabarito — Aula 01 (JOINs, GROUP BY, WHERE vs HAVING)

> **Só abra depois de escrever suas respostas.** Compare linha a linha e anote onde errou — os erros daqui preveem os erros da entrevista. Mesmo com o gabarito, vale me mandar suas respostas no chat para eu corrigir o raciocínio e o inglês.

---

## Exercício 1 — Previsão (LEFT vs INNER)

**LEFT JOIN → 6 rows:**

```
name   | order_id | amount
-------+----------+-------
Ana    | 10       | 100.00
Ana    | 11       | 250.00
Bruno  | 12       |  80.00
Carla  | 13       | 500.00
Carla  | 14       | 120.00
Daniel | NULL     | NULL     ← preservado pelo LEFT, colunas da direita em NULL
```

**INNER JOIN → 5 rows:** a row do Daniel **desaparece** (sem match). Nada mais muda.

**Erros comuns:** achar que Ana aparece 1 vez (o join multiplica — 2 orders, 2 rows); esquecer que o LEFT preserva Daniel.

---

## Exercício 2 — COUNT com LEFT JOIN

```sql
SELECT c.name, COUNT(o.id) AS orders_count
FROM customers c
LEFT JOIN orders o ON o.customer_id = c.id
GROUP BY c.id, c.name
ORDER BY c.name;
```

**Os dois pontos que valem a questão:**

1. **`COUNT(o.id)`, não `COUNT(*)`** — a row do Daniel existe (cheia de NULLs), então `COUNT(*)` daria **1**; `COUNT(o.id)` ignora NULL e dá **0**.
2. **LEFT JOIN, não INNER** — com INNER, Daniel nem entraria no resultado.

**Detalhe de qualidade:** `GROUP BY c.id, c.name` (agrupar pela PK) é mais seguro que só `c.name` — dois customers podem ter o mesmo nome. No Postgres, agrupando pela PK você pode até selecionar `c.name` sem listá-lo (functional dependency), mas listar os dois é o hábito portável.

---

## Exercício 3 — WHERE + HAVING juntos

```sql
SELECT customer_id, SUM(amount) AS total_completed
FROM orders
WHERE status = 'completed'
GROUP BY customer_id
HAVING SUM(amount) > 150;
```

Resultado: `(1, 350.00)` e `(3, 500.00)`. Bruno sai no WHERE (cancelled); a order 14 da Carla (pending) sai no WHERE antes de somar.

**Resposta em inglês (modelo):**

> *"The status filter goes in WHERE because it's a condition on individual rows and must be applied before aggregation — I only want completed orders entering the SUM. The total filter goes in HAVING because it's a condition on the aggregate itself, which only exists after GROUP BY. Putting the status filter in WHERE is also cheaper: fewer rows reach the aggregation."*

**Erro comum:** colocar `status = 'completed'` no HAVING. Funciona? Nem sempre (a coluna teria que estar no GROUP BY) — e mesmo quando funciona, é mais caro e semanticamente errado.

---

## Exercício 4 — Fan-out

### (a) Previsão

A order **10** tem **2 payments** (90 e 91) → a row dela duplica no join → `o.amount = 100.00` somado **duas vezes**.

- Ana: 100 + 100 + 250 = **450.00** (inflado; o real é 350.00).
- Bruno: **desaparece** do resultado — a order 12 não tem payments e o `JOIN payments` é INNER.
- Carla: 500.00 — a order 14 (sem payment) também foi dropada; por acaso o número "parece razoável", o que torna o bug ainda mais perigoso.

**Três defeitos na query do colega:** aggregate inflado (fan-out), rows sumindo (INNER com tabela opcional), e o pior — o erro é **silencioso**.

### (b) Correção — agregar ANTES de juntar

```sql
SELECT
    c.name,
    SUM(o.amount)                 AS total_ordered,
    COALESCE(SUM(p.paid), 0)      AS total_paid
FROM customers c
JOIN orders o ON o.customer_id = c.id
LEFT JOIN (
    SELECT order_id, SUM(amount) AS paid
    FROM payments
    GROUP BY order_id
) p ON p.order_id = o.id
GROUP BY c.id, c.name;
```

Por que funciona: a subquery colapsa payments para **1 row por order** → o join volta a ser 1:1 → `SUM(o.amount)` não infla. `LEFT JOIN` + `COALESCE` preservam orders sem payment.

```
name  | total_ordered | total_paid
------+---------------+-----------
Ana   | 350.00        | 350.00
Bruno |  80.00        |   0.00
Carla | 620.00        | 500.00
```

**Frase de entrevista para guardar:** *"When I aggregate across a one-to-many join, I pre-aggregate the many side to one row per key before joining — otherwise the join fans out and inflates the sums."*

---

## Exercício 5 — Resposta modelo (inglês)

> *"WHERE filters individual rows before any grouping happens; HAVING filters whole groups after aggregation. That's why aggregate conditions like `SUM(amount) > 150` can only live in HAVING — the sum doesn't exist yet when WHERE runs. It matters for performance because WHERE reduces the number of rows that reach the GROUP BY, so I always push every row-level condition into WHERE and keep HAVING only for conditions on aggregates."*

**Correções de inglês frequentes nesse tema:**
- ✅ "filters rows / filters groups" — ❌ "filter the lines" (rows, não lines).
- ✅ "before/after aggregation" — ❌ "before/after the grouping happen" (happens).
- ✅ "the sum doesn't exist yet" — ❌ "the sum still doesn't exist" (calco do "ainda não existe"; "doesn't exist yet" é o natural).
