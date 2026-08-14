# Aula 01 — SQL JOINs, GROUP BY, Aggregates, WHERE vs HAVING

> Fundamentos necessários para as aulas 🔥 de CTEs, window functions e otimização.

---

## Schema de referência (usado a semana toda)

```sql
customers
+----+----------+---------+
| id | name     | country |
+----+----------+---------+
| 1  | Ana      | BR      |
| 2  | Bruno    | BR      |
| 3  | Carla    | US      |
| 4  | Daniel   | US      |
+----+----------+---------+

orders
+----+-------------+------------+--------+-----------+
| id | customer_id | created_at | amount | status    |
+----+-------------+------------+--------+-----------+
| 10 | 1           | 2026-01-05 | 100.00 | completed |
| 11 | 1           | 2026-02-10 | 250.00 | completed |
| 12 | 2           | 2026-01-20 |  80.00 | cancelled |
| 13 | 3           | 2026-03-01 | 500.00 | completed |
| 14 | 3           | 2026-03-15 | 120.00 | pending   |
+----+-------------+------------+--------+-----------+
```

⚠️ Repare: **Daniel (id 4) não tem orders.** É proposital.

---

## Conceito 1 — O modelo mental de JOIN (esqueça diagramas de Venn)

### Concept

O modelo mental correto não é Venn — é **row matching**:

> Um JOIN pega cada row da esquerda e procura rows correspondentes na direita. Para **cada match**, produz **uma row de output**.

Três consequências que resolvem 90% das pegadinhas:

1. **INNER JOIN**: row da esquerda sem match → **desaparece** do resultado.
2. **LEFT JOIN**: row da esquerda sem match → **aparece mesmo assim**, com colunas da direita em `NULL`.
3. **One-to-many**: se uma row da esquerda tem **3 matches** na direita, ela aparece **3 vezes**. O JOIN **multiplica rows** — não "anexa" dados.

### What can go wrong? — A armadilha do fan-out

```sql
-- "Total gasto por customer" — parece certo, está ERRADO se houver
-- outra tabela one-to-many no meio (ex: order_items ou payments)
SELECT c.name, SUM(o.amount)
FROM customers c
JOIN orders o    ON o.customer_id = c.id
JOIN payments p  ON p.order_id = o.id     -- 1 order pode ter 2 payments!
GROUP BY c.name;
```

Se a order 10 tem 2 payments, a row da order 10 **duplica**, e `SUM(o.amount)` conta 100.00 **duas vezes**. Isso se chama **fan-out** (join inflation).

Em entrevista, quando derem um JOIN com agregação, a primeira pergunta mental é:

> *"Algum desses JOINs é one-to-many? Meu aggregate está inflado?"*

**Soluções:** agregar em subquery/CTE **antes** do JOIN, ou `COUNT(DISTINCT o.id)` quando fizer sentido.

### RIGHT JOIN e FULL OUTER JOIN — 60 segundos

- `RIGHT JOIN` = `LEFT JOIN` com as tabelas trocadas. Resposta de entrevista:
  > *"I'd rewrite it as a LEFT JOIN for readability — they're semantically equivalent with the table order flipped."*
- `FULL OUTER JOIN` = mantém rows sem match **dos dois lados**. Caso de uso real: **reconciliation** — comparar duas fontes de dados e achar o que existe só de um lado. *(Guardar: reusaremos na aula de validação de migração.)*

---

## Conceito 2 — GROUP BY: colapsar rows em grupos

### Concept

> `GROUP BY customer_id` divide a tabela em "baldes", um por customer. **Cada balde vira exatamente 1 row de output.** No SELECT, só pode aparecer: (a) colunas do GROUP BY, ou (b) aggregates (`SUM`, `COUNT`, ...) — qualquer outra coluna teria valores múltiplos dentro do balde e o banco não sabe qual escolher.

```sql
SELECT customer_id, COUNT(*) AS orders_count, SUM(amount) AS total
FROM orders
GROUP BY customer_id;
```

### Os três COUNTs — cai MUITO em rapid fire

| Expressão | O que conta |
|---|---|
| `COUNT(*)` | todas as rows do grupo |
| `COUNT(col)` | rows onde `col IS NOT NULL` |
| `COUNT(DISTINCT col)` | valores distintos não-nulos |

**Conexão com LEFT JOIN (pegadinha clássica):** com `LEFT JOIN orders`, um customer sem orders gera uma row cheia de NULLs. `COUNT(*)` retorna **1**; `COUNT(o.id)` retorna **0**.

---

## Conceito 3 — WHERE vs HAVING

### Interview answer (memorizar)

> **"WHERE filters individual rows before grouping; HAVING filters entire groups after aggregation. So conditions on raw columns belong in WHERE, and conditions on aggregate results — like `SUM(amount) > 1000` — can only go in HAVING. Filtering early in WHERE is also better for performance, because fewer rows reach the aggregation step."**

### Ordem lógica de execução (decorar — explica quase tudo em SQL)

```
FROM → JOIN → WHERE → GROUP BY → HAVING → SELECT → ORDER BY → LIMIT
```

É por isso que:
- não dá para usar alias do SELECT dentro do WHERE;
- não dá para usar `SUM()` no WHERE — o WHERE roda **antes** de o grupo existir.

---

## Conceito 4 — EXISTS vs IN, subqueries, UNION (visão rápida)

- `IN (subquery)`: "o valor está nessa lista?"
- `EXISTS (subquery correlacionada)`: "existe pelo menos 1 row que satisfaz?" — para no primeiro match.
- ⚠️ Pegadinha: `NOT IN` com subquery que retorna **NULL** → resultado vazio (three-valued logic). `NOT EXISTS` não sofre disso.
  > Resposta segura de senior: **"I default to NOT EXISTS over NOT IN because of NULL semantics."**
- `UNION` deduplica (custa sort/hash); `UNION ALL` só concatena.
  > Resposta de quem pensa em performance: **se sei que não há duplicatas, uso `UNION ALL`.**

---

## ✏️ Exercícios — SEM olhar as respostas antes de tentar

Usar o schema `customers` / `orders` acima. Escrever as queries sem consultar nada; onde pedir previsão, prever **antes** de raciocinar a query.

### Exercício 1 — Previsão (INNER vs LEFT)

Sem escrever query nova, **prever o output** (rows e valores) de:

```sql
SELECT c.name, o.id AS order_id, o.amount
FROM customers c
LEFT JOIN orders o ON o.customer_id = c.id;
```

- Quantas rows retornam?
- O que aparece para Daniel?
- Se trocar `LEFT JOIN` por `INNER JOIN`, o que muda?

### Exercício 2 — Aggregate com armadilha

Query que retorne **todos** os customers (mesmo sem orders) com o número de orders de cada um. Expected output:

```
name    | orders_count
--------+-------------
Ana     | 2
Bruno   | 1
Carla   | 2
Daniel  | 0
```

⚠️ Dica de que há armadilha: pensar em **qual COUNT** usar.

### Exercício 3 — WHERE vs HAVING no mesmo problema

Total gasto (amount) **apenas em orders `completed`**, por customer, mas **somente customers cujo total completed > 150**. Expected output:

```
customer_id | total_completed
------------+----------------
1           | 350.00
3           | 500.00
```

Pergunta extra (responder em inglês, como ao entrevistador):
> **Why does the status filter go in one clause and the total filter in the other?**

### Exercício 4 — Fan-out

Tabela adicional:

```sql
payments
+----+----------+--------+------------+
| id | order_id | amount | method     |
+----+----------+--------+------------+
| 90 | 10       |  50.00 | card       |
| 91 | 10       |  50.00 | pix        |
| 92 | 11       | 250.00 | card       |
| 93 | 13       | 500.00 | card       |
+----+----------+--------+------------+
```

Um colega escreveu:

```sql
SELECT c.name, SUM(o.amount) AS total_ordered
FROM customers c
JOIN orders o   ON o.customer_id = c.id
JOIN payments p ON p.order_id = o.id
GROUP BY c.name;
```

**(a)** Prever o valor de `total_ordered` para Ana. Está certo ou inflado? Por quê?

**(b)** Corrigir a query para que `total_ordered` seja o valor real somado das orders de cada customer **e** incluir também uma coluna `total_paid` (soma dos payments) — ambas corretas na mesma query.

### Exercício 5 — Interview question (responder em inglês, 30-60s)

> **"What's the difference between WHERE and HAVING, and why does it matter for performance?"**

Escrever a resposta como falaria na entrevista (o inglês técnico também será corrigido).

---

## ✅ Respostas / avaliação

*(Preenchido durante a sessão interativa, depois da tentativa.)*
