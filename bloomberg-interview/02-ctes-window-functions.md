# Aula 02 — CTEs + Window Functions 🔥 HIGH PRIORITY

> A JD cita "CTEs, window functions" explicitamente. Probabilidade altíssima de exercício ao vivo tipo "latest order per customer" ou "top N per group".

Schema de referência: o mesmo da aula 01 (`customers`, `orders`, `payments`).

---

# PARTE A — CTEs

## Problem

Você precisa de um resultado intermediário (ex: total por customer) para depois filtrar/juntar. Com subqueries aninhadas, a query vira uma cebola ilegível que se lê de dentro para fora.

## Concept

CTE (Common Table Expression) = **subquery nomeada**, declarada com `WITH`, que se lê de cima para baixo como etapas de um pipeline:

```sql
WITH customer_totals AS (
    SELECT customer_id, SUM(amount) AS total_spent
    FROM orders
    GROUP BY customer_id
)
SELECT *
FROM customer_totals
WHERE total_spent > 10000;
```

**Modelo mental:** cada CTE é uma "tabela temporária lógica" com nome. O fluxo de dados desce: CTE 1 → CTE 2 → query final.

### Chained CTEs

```sql
WITH completed AS (                        -- etapa 1: filtrar
    SELECT * FROM orders WHERE status = 'completed'
),
totals AS (                                -- etapa 2: agregar (usa a etapa 1)
    SELECT customer_id, SUM(amount) AS total_spent
    FROM completed
    GROUP BY customer_id
)
SELECT c.name, t.total_spent               -- etapa 3: enriquecer
FROM totals t
JOIN customers c ON c.id = t.customer_id
ORDER BY t.total_spent DESC;
```

Para ler uma query com múltiplos CTEs: **leia cada CTE isoladamente, anote em uma frase o que ela produz** ("orders completed", "total por customer"), depois leia a query final usando essas frases.

### Recursive CTEs (nível entrevista — reconhecer e explicar)

Caso de uso: hierarquias (org chart, categorias, grafo de dependências).

```sql
WITH RECURSIVE subordinates AS (
    SELECT id, name, manager_id FROM employees WHERE id = 1   -- âncora
    UNION ALL
    SELECT e.id, e.name, e.manager_id
    FROM employees e
    JOIN subordinates s ON e.manager_id = s.id                -- passo recursivo
)
SELECT * FROM subordinates;
```

Basta saber: **âncora + UNION ALL + passo que referencia a própria CTE**; roda até o passo não produzir rows. SKIP detalhes além disso.

## CTE vs subquery — a resposta de senior

- **Legibilidade/reuso:** CTE vence quando o mesmo resultado é usado 2+ vezes ou a query tem etapas.
- **Performance:** ⚠️ **CTE não é otimização.**
  - **PostgreSQL 12+**: CTEs simples são **inlined** (tratadas como subquery) — mesmo plano, mesma performance.
  - O planner **materializa** a CTE (executa uma vez, guarda o resultado) quando: você escreve `WITH x AS MATERIALIZED (...)`, ou a CTE é referenciada mais de uma vez, ou tem funções voláteis/é recursiva.
  - **Materialização é faca de dois gumes:** evita recomputar, mas vira uma **optimization fence** — predicados da query externa não são empurrados para dentro da CTE (sem predicate pushdown), então a CTE pode produzir milhões de rows que seriam filtradas depois.

### Interview answer (English)

> **"A CTE is mainly a readability and structuring tool, not a performance tool. In modern PostgreSQL, simple CTEs are inlined into the main query, so the plan is the same as a subquery. The planner materializes a CTE when it's referenced multiple times or marked MATERIALIZED — which can help by computing it once, but can also hurt because it acts as an optimization fence: outer filters don't get pushed down into it. So if a CTE-heavy query is slow, one of the first things I check in the plan is whether a CTE is being materialized with far more rows than the outer query actually needs."**

## What can go wrong?

- Achar que CTE deixa a query mais rápida "porque organiza" — o planner não liga para a sua organização.
- CTE materializada gigante filtrada só no final.
- Excesso de CTEs encadeadas escondendo um fan-out (JOIN duplicando rows lá na etapa 2).

---

# PARTE B — WINDOW FUNCTIONS 🔥

## Problem

"Me dê a **última order de cada customer**" — com GROUP BY você consegue `MAX(created_at)`, mas **perde as outras colunas da row** (amount, status). Você quer calcular algo **por grupo** sem **colapsar as rows**.

## Concept

> **GROUP BY colapsa: N rows viram 1 por grupo. Window function NÃO colapsa: cada row continua existindo e ganha uma coluna extra calculada olhando para as "vizinhas" da sua partição.**

```sql
SELECT
    customer_id,
    id,
    amount,
    SUM(amount) OVER (PARTITION BY customer_id) AS customer_total
FROM orders;
```

Cada order continua sendo uma row; `customer_total` repete o total do customer em cada uma.

Anatomia do `OVER`:

- `PARTITION BY x` → reinicia o cálculo por grupo (o "GROUP BY da janela");
- `ORDER BY y` dentro do OVER → define ordem **dentro da partição** (necessário para ranking e running totals);
- sem `PARTITION BY` → a janela é a tabela inteira.

### ROW_NUMBER vs RANK vs DENSE_RANK (rapid fire garantido)

Com valores `500, 300, 300, 100` ordenados DESC:

| Função | Resultado | Regra |
|---|---|---|
| `ROW_NUMBER()` | 1, 2, 3, 4 | sequência única, desempata arbitrariamente |
| `RANK()` | 1, 2, 2, **4** | empates dividem o rank, **pula** posições |
| `DENSE_RANK()` | 1, 2, 2, **3** | empates dividem o rank, **não pula** |

### Padrão-ouro nº 1 — Latest row per entity (DECORE)

> Get the most recent order for each customer.

```sql
WITH ranked AS (
    SELECT o.*,
           ROW_NUMBER() OVER (
               PARTITION BY customer_id
               ORDER BY created_at DESC
           ) AS rn
    FROM orders o
)
SELECT * FROM ranked WHERE rn = 1;
```

Por que precisa da CTE? Porque window functions são calculadas **depois** do WHERE (ordem lógica: `FROM → WHERE → GROUP BY → HAVING → window functions → SELECT → ORDER BY`) — você não pode escrever `WHERE rn = 1` na mesma query.

### Padrão-ouro nº 2 — Top N per group

> Top 3 customers by spending in each country.

Estrutura: agregar primeiro (total por customer), **depois** rankear por país, depois filtrar `rn <= 3`. (Você vai escrever essa no exercício.)

### Padrão-ouro nº 3 — Running total

```sql
SELECT
    created_at,
    amount,
    SUM(amount) OVER (
        PARTITION BY account_id
        ORDER BY created_at
    ) AS running_balance
FROM transactions;
```

`SUM() OVER (ORDER BY ...)` = soma acumulada até a row atual. ⚠️ Detalhe fino (só se perguntarem): com `ORDER BY`, o frame default é `RANGE ... CURRENT ROW`, que inclui **empates** (rows com o mesmo valor de ordenação entram juntas). Para acumular row a row estritamente, ordene por algo único (ex: `created_at, id`) ou use `ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW`.

## GROUP BY vs window function — Interview answer (English, DECORE)

> **"GROUP BY collapses rows — you get one row per group and lose the detail. A window function keeps every row and adds a computed column based on a partition of related rows. So if I need 'total per customer' as a report, that's GROUP BY; if I need each order alongside its customer's total, or a rank within a group, that's a window function. A useful tell: if the question says 'per each X, show the row(s) that...', it's usually a window function."**

## What can go wrong?

- `WHERE rn = 1` sem CTE/subquery → erro (window roda depois do WHERE).
- `RANK` em vez de `ROW_NUMBER` no "latest per entity" → empates retornam 2+ rows por entity.
- Esquecer `PARTITION BY` → ranking global em vez de por grupo.
- Window function sobre join com fan-out → valores inflados (mesma armadilha da aula 01).

## Trade-offs

- Window functions frequentemente exigem **Sort** no plano — em tabelas grandes, um índice compatível com `(partition_col, order_col)` pode evitar o sort.
- Alternativa a `ROW_NUMBER` para latest-per-entity no Postgres: `DISTINCT ON (customer_id) ... ORDER BY customer_id, created_at DESC` — idiomático e às vezes mais rápido; mencionar ganha ponto de "conhece Postgres".

---

## ✏️ Exercícios

### Exercício 1 — Previsão

Dado `orders` da aula 01, preveja o output completo de:

```sql
SELECT customer_id, id, amount,
       ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY amount DESC) AS rn,
       SUM(amount)  OVER (PARTITION BY customer_id)                      AS total
FROM orders;
```

### Exercício 2 — Latest order per customer (obrigatório)

Escreva a query que retorna **a order mais recente de cada customer** (todas as colunas da order). Depois responda: **why ROW_NUMBER and not RANK here?** (em inglês).

### Exercício 3 — Top 3 per group (obrigatório)

Schema: `customers(id, name, country)`, `orders(id, customer_id, amount, status)`.
Escreva: **top 3 customers by total completed spending in each country**. Expected shape:

```
country | name  | total_spent | rank_in_country
--------+-------+-------------+----------------
BR      | Ana   | 350.00      | 1
BR      | ...   | ...         | 2
US      | Carla | 500.00      | 1
...
```

Dica de estrutura: 2 CTEs encadeadas (agregar → rankear), filtro final.

### Exercício 4 — Running balance (obrigatório)

```sql
transactions
+----+------------+------------+--------+
| id | account_id | created_at | amount |   -- amount pode ser negativo
+----+------------+------------+--------+
```

Escreva a query que retorna cada transaction com o **running balance** da conta até aquele momento. Garanta ordem determinística com empates de `created_at`.

### Exercício 5 — CTE reasoning

Um colega reescreveu uma query de subquery para CTE e disse "agora vai ficar mais rápida". Responda em inglês (30-60s): **is that true? When could the CTE version actually be slower?**

### Exercício 6 — Ler fluxo de dados

Sem executar, descreva em 4 frases (uma por etapa) o que esta query produz:

```sql
WITH completed AS (
    SELECT * FROM orders WHERE status = 'completed'
),
per_customer AS (
    SELECT customer_id, SUM(amount) AS total, COUNT(*) AS cnt
    FROM completed GROUP BY customer_id
),
ranked AS (
    SELECT c.country, p.*,
           DENSE_RANK() OVER (PARTITION BY c.country ORDER BY p.total DESC) AS rnk
    FROM per_customer p JOIN customers c ON c.id = p.customer_id
)
SELECT * FROM ranked WHERE rnk = 1;
```

O que acontece se dois customers do mesmo país empatarem no total?

---

## ✅ Respostas / avaliação

*(Preenchido durante a sessão interativa, depois da tentativa.)*
