# 🔒 Gabarito — Aula 02 (CTEs + Window Functions)

> **Só abra depois de tentar.**

---

## Exercício 1 — Previsão

Partições por `customer_id`, ranking por `amount DESC`, total por partição:

```
customer_id | id | amount | rn | total
------------+----+--------+----+-------
1           | 11 | 250.00 | 1  | 350.00
1           | 10 | 100.00 | 2  | 350.00
2           | 12 |  80.00 | 1  |  80.00
3           | 13 | 500.00 | 1  | 620.00
3           | 14 | 120.00 | 2  | 620.00
```

Pontos-chave: **5 rows entram, 5 rows saem** (window não colapsa); `total` **repete** em todas as rows da partição; `rn` reinicia por customer.

---

## Exercício 2 — Latest order per customer

```sql
WITH ranked AS (
    SELECT o.*,
           ROW_NUMBER() OVER (
               PARTITION BY customer_id
               ORDER BY created_at DESC
           ) AS rn
    FROM orders o
)
SELECT id, customer_id, created_at, amount, status
FROM ranked
WHERE rn = 1;
```

Resultado: orders **11** (Ana), **12** (Bruno), **14** (Carla).

**Why ROW_NUMBER and not RANK (modelo):**

> *"RANK gives the same number to ties — if a customer had two orders with the same created_at, both would get rank 1 and I'd return two rows for that customer. ROW_NUMBER guarantees exactly one row per partition, breaking ties arbitrarily; if I care how ties break, I add a deterministic tiebreaker like `ORDER BY created_at DESC, id DESC`."*

**Bônus Postgres (cite se quiser impressionar):**

```sql
SELECT DISTINCT ON (customer_id) *
FROM orders
ORDER BY customer_id, created_at DESC;
```

---

## Exercício 3 — Top 3 per country

```sql
WITH totals AS (
    SELECT customer_id, SUM(amount) AS total_spent
    FROM orders
    WHERE status = 'completed'
    GROUP BY customer_id
),
ranked AS (
    SELECT c.country, c.name, t.total_spent,
           ROW_NUMBER() OVER (
               PARTITION BY c.country
               ORDER BY t.total_spent DESC
           ) AS rank_in_country
    FROM totals t
    JOIN customers c ON c.id = t.customer_id
)
SELECT country, name, total_spent, rank_in_country
FROM ranked
WHERE rank_in_country <= 3
ORDER BY country, rank_in_country;
```

**Erros clássicos aqui:**
1. Rankear **antes** de agregar (window direto sobre `orders`) — o ranking tem que ser sobre o **total**, então agregue primeiro. É a ordem das CTEs que carrega a lógica.
2. Esquecer o `WHERE status = 'completed'` **dentro** da agregação.
3. `ROW_NUMBER` vs `DENSE_RANK`: com `ROW_NUMBER`, empate no 3º lugar corta um dos empatados arbitrariamente. Se o requisito for "todos os empatados no top 3", use `DENSE_RANK() <= 3`. **Mencionar essa escolha em voz alta é ponto de senior.**

---

## Exercício 4 — Running balance

```sql
SELECT
    id,
    account_id,
    created_at,
    amount,
    SUM(amount) OVER (
        PARTITION BY account_id
        ORDER BY created_at, id
    ) AS running_balance
FROM transactions
ORDER BY account_id, created_at, id;
```

O ponto da questão: **`ORDER BY created_at, id`** — o `id` desempata. Sem ele, duas transactions com o mesmo `created_at` caem no mesmo frame (`RANGE ... CURRENT ROW`) e mostram o **mesmo** saldo acumulado — extrato errado. Com desempate único, o acúmulo é row a row. (Alternativa explícita: `ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW`.)

---

## Exercício 5 — CTE ≠ performance (modelo)

> *"Not necessarily. In PostgreSQL 12 and later, a simple CTE is inlined — the planner treats it exactly like a subquery, so the plan and the performance are identical; the rewrite is purely about readability. The CTE version can actually be slower when it gets materialized — because it's referenced twice or marked MATERIALIZED — since materialization is an optimization fence: the outer query's filters don't get pushed down into the CTE, so it may compute millions of rows that are thrown away afterwards. If a CTE-heavy query is slow, that's one of the first things I look for in the plan."*

---

## Exercício 6 — Fluxo de dados

1. `completed` — filtra orders para só `status = 'completed'`.
2. `per_customer` — agrega: total e contagem de orders completed **por customer**.
3. `ranked` — junta com `customers` para obter o país e calcula `DENSE_RANK` do total **dentro de cada país** (maior total = rank 1).
4. Query final — retorna **o(s) top spender(s) de cada país** entre orders completed.

**Empate:** com `DENSE_RANK`, dois customers empatados no topo do mesmo país recebem **ambos** `rnk = 1` e **ambos aparecem**. Se o requisito fosse "exatamente um por país", seria `ROW_NUMBER` com desempate explícito. Reconhecer essa diferença era o objetivo do exercício.
