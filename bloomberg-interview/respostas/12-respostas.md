# 🔒 Gabarito — Aula 12 (SQL Coding Drills)

> **Só abra depois de escrever cada query.** Variações sintáticas são aceitáveis — compare a LÓGICA (joins certos, filtro no lugar certo, sem fan-out) e os resultados numéricos.

---

## Nível 1 — JOINs

### Drill 1

```sql
SELECT u.name, s.plan, s.started_at
FROM users u
JOIN subscriptions s ON s.user_id = u.id;
```

5 rows (Daniel fora — INNER).

### Drill 2 — ON vs WHERE (o ponto da questão)

```sql
SELECT u.name, s.plan, s.started_at
FROM users u
LEFT JOIN subscriptions s
       ON s.user_id = u.id
      AND s.ended_at IS NULL;      -- filtro no ON!
```

Resultado: Ana/premium, Bruno/basic, Elena/basic, **Carla/NULL** (a subscription dela terminou), **Daniel/NULL**.

**Por que o filtro vai no `ON`:** condições no `ON` decidem **o que conta como match** — quem não tem match ainda aparece (com NULLs). Se você escrever `WHERE s.ended_at IS NULL`, o filtro roda **depois** do join: as rows de Carla e Daniel têm `s.ended_at = NULL`... mas a de Carla tem `ended_at = '2025-11-10'` e é eliminada, e a de Daniel sobrevive por acaso — porém qualquer condição como `WHERE s.plan = 'basic'` eliminaria os NULLs e **transformaria silenciosamente o LEFT em INNER**. Regra: **filtro sobre a tabela da direita de um LEFT JOIN pertence ao ON** (a menos que você QUEIRA o efeito de INNER).

### Drill 3

```sql
-- Forma 1: LEFT JOIN + IS NULL
SELECT u.*
FROM users u
LEFT JOIN subscriptions s ON s.user_id = u.id
WHERE s.id IS NULL;

-- Forma 2: NOT EXISTS (preferida — intenção explícita, imune a NULL semantics)
SELECT u.*
FROM users u
WHERE NOT EXISTS (
    SELECT 1 FROM subscriptions s WHERE s.user_id = u.id
);
```

Resultado: Daniel. Na entrevista, escreva a NOT EXISTS e **mencione** a outra.

---

## Nível 2 — GROUP BY / HAVING

### Drill 4

```sql
SELECT u.name, SUM(p.amount) AS revenue
FROM users u
JOIN subscriptions s ON s.user_id = u.id
JOIN payments p      ON p.subscription_id = s.id
WHERE p.status = 'ok'
GROUP BY u.id, u.name;
```

Ana 79.60 · Bruno 9.90 · Carla 29.90.

**Por que Elena não aparece:** o único payment dela é `failed` → eliminado no WHERE → ela não tem row nenhuma entrando no GROUP BY (Daniel idem, sem subscription). **Incluindo todos com 0.00:**

```sql
SELECT u.name,
       COALESCE(SUM(p.amount) FILTER (WHERE p.status = 'ok'), 0) AS revenue
FROM users u
LEFT JOIN subscriptions s ON s.user_id = u.id
LEFT JOIN payments p      ON p.subscription_id = s.id
GROUP BY u.id, u.name;
```

Dois mecanismos: LEFT JOINs preservam os users, e o filtro de status **sai do WHERE** (que mataria os NULLs) para um `FILTER` no aggregate (ou para o `ON`). `FILTER (WHERE ...)` é idiomático de Postgres — usar isso ao vivo impressiona.

### Drill 5

```sql
SELECT country, COUNT(*) AS users_2025
FROM users
WHERE created_at >= '2025-01-01' AND created_at < '2026-01-01'
GROUP BY country
HAVING COUNT(*) > 1;
```

BR 2 · US 2. O filtro de data é condição de **row** → WHERE (e sargable, range meio-aberto — não `YEAR()`); a contagem é condição de **grupo** → HAVING.

### Drill 6

```sql
SELECT s.plan,
       COUNT(DISTINCT s.id) AS subs,
       COALESCE(SUM(p.amount) FILTER (WHERE p.status = 'ok'), 0) AS revenue_ok,
       ROUND(
           COUNT(*) FILTER (WHERE p.status = 'failed')::numeric
           / NULLIF(COUNT(p.id), 0),
       2) AS failure_rate
FROM subscriptions s
LEFT JOIN payments p ON p.subscription_id = s.id
GROUP BY s.plan;
```

```
plan    | subs | revenue_ok | failure_rate
--------+------+------------+-------------
basic   | 3    | 29.70      | 0.40
premium | 2    | 89.70      | 0.00
```

Armadilhas cobradas: `::numeric` (senão **divisão inteira** → 0), `NULLIF` (plano sem payments dividiria por zero), `COUNT(DISTINCT s.id)` (o join com payments multiplica as rows de subscription — fan-out da aula 01!).

---

## Nível 3 — Subqueries / EXISTS

### Drill 7

```sql
WITH revenue AS (
    SELECT s.user_id, SUM(p.amount) AS rev
    FROM subscriptions s
    JOIN payments p ON p.subscription_id = s.id
    WHERE p.status = 'ok'
    GROUP BY s.user_id
)
SELECT u.name, r.rev
FROM revenue r
JOIN users u ON u.id = r.user_id
WHERE r.rev > (SELECT AVG(rev) FROM revenue);
```

Média = (79.60 + 9.90 + 29.90) / 3 = **39.80** → só **Ana**. A CTE aqui se justifica de verdade: `revenue` é usada **duas vezes** (na query e na média) — sem CTE você duplicaria a agregação.

### Drill 8

```sql
-- Com pelo menos um failed
SELECT s.*
FROM subscriptions s
WHERE EXISTS (
    SELECT 1 FROM payments p
    WHERE p.subscription_id = s.id AND p.status = 'failed'
);
-- → subs 10 e 14

-- Sem nenhum ok
SELECT s.*
FROM subscriptions s
WHERE NOT EXISTS (
    SELECT 1 FROM payments p
    WHERE p.subscription_id = s.id AND p.status = 'ok'
);
-- → sub 14 (só tem o failed 97)
```

Note: "sem nenhum ok" ≠ "com algum failed" — a sub 10 tem failed **e** oks, então aparece na primeira e não na segunda. Se confundiu as duas semânticas, releia.

---

## Nível 4 — CTEs

### Drill 9

```sql
WITH monthly AS (
    SELECT s.user_id,
           date_trunc('month', p.paid_at) AS month,
           SUM(p.amount) AS rev
    FROM payments p
    JOIN subscriptions s ON s.id = p.subscription_id
    WHERE p.status = 'ok'
    GROUP BY s.user_id, date_trunc('month', p.paid_at)
),
best AS (
    SELECT m.*,
           ROW_NUMBER() OVER (
               PARTITION BY user_id
               ORDER BY rev DESC, month ASC   -- desempate: primeiro mês
           ) AS rn
    FROM monthly m
)
SELECT user_id, month, rev
FROM best
WHERE rn = 1;
```

⚠️ Pegadinha embutida: a Ana **empata** (jun e jul de 2025, 29.90 cada) — sem o desempate `month ASC` o resultado seria não-determinístico. Se você usou subquery correlacionada com `MAX`, também precisa decidir o empate. **Preferência (justificativa):** window function — uma passada, desempate explícito, estende fácil para "top N".

### Drill 10

```sql
WITH monthly AS (
    SELECT date_trunc('month', paid_at) AS month, SUM(amount) AS rev
    FROM payments
    WHERE status = 'ok'
    GROUP BY 1
)
SELECT month,
       rev,
       rev - LAG(rev) OVER (ORDER BY month)                          AS delta,
       ROUND((rev - LAG(rev) OVER (ORDER BY month))
             / LAG(rev) OVER (ORDER BY month) * 100, 1)              AS pct_growth
FROM monthly
ORDER BY month;
```

Primeiro mês: `LAG` = NULL → delta/pct NULL (correto). **Nuance de senior para citar:** meses **sem receita não existem na CTE** (ex: mar/2025) — o `LAG` compara com o último mês existente, não com o mês-calendário anterior. Para série completa, gerar o calendário com `generate_series` e LEFT JOIN.

---

## Nível 5 — Window functions

### Drill 11

```sql
WITH ranked AS (
    SELECT s.*,
           ROW_NUMBER() OVER (
               PARTITION BY user_id
               ORDER BY started_at DESC, id DESC
           ) AS rn
    FROM subscriptions s
)
SELECT id, user_id, plan, started_at, ended_at, price
FROM ranked WHERE rn = 1;
```

→ subs 11 (Ana), 12 (Bruno), 13 (Carla), 14 (Elena). (Ou `DISTINCT ON (user_id) ... ORDER BY user_id, started_at DESC`.)

### Drill 12

```sql
SELECT id, paid_at, amount,
       SUM(amount) OVER (ORDER BY paid_at, id) AS running_revenue
FROM payments
WHERE status = 'ok'
ORDER BY paid_at, id;
```

O `, id` no ORDER BY da janela é o que estava sendo cobrado (empates → mesmo valor acumulado sem ele).

### Drill 13

```sql
WITH revenue AS (
    SELECT s.user_id, SUM(p.amount) AS rev
    FROM subscriptions s
    JOIN payments p ON p.subscription_id = s.id
    WHERE p.status = 'ok'
    GROUP BY s.user_id
),
ranked AS (
    SELECT u.country, u.name, r.rev,
           RANK() OVER (PARTITION BY u.country ORDER BY r.rev DESC) AS rnk
    FROM revenue r
    JOIN users u ON u.id = r.user_id
)
SELECT country, name, rev
FROM ranked WHERE rnk = 1;
```

→ BR: Ana (79.60) · US: Carla (29.90). **`RANK` porque o enunciado pediu empates incluídos** (dois empatados no topo → ambos com rnk 1). Nota fina: DE não aparece — Elena não tem receita, logo não tem row em `revenue`. Se o requisito fosse "todo país", seria preciso partir de `users` com LEFT JOIN.

### Drill 14

```sql
SELECT p.id, p.subscription_id, p.paid_at, p.amount,
       p.amount - LAG(p.amount) OVER (
           PARTITION BY p.subscription_id
           ORDER BY p.paid_at, p.id
       ) AS diff_from_previous
FROM payments p
ORDER BY p.subscription_id, p.paid_at;
```

Primeiro payment de cada subscription → NULL (sem anterior). `PARTITION BY subscription_id` era o ponto — sem ele, o LAG cruza subscriptions.

---

## Nível 6 — Otimização e índices

### Drill 15 — o índice que NÃO resolve

Pontos esperados: a query agrega **a tabela quase inteira** (se `ok` é a grande maioria dos 80M) — um índice em `status` não muda nada: baixa seletividade → Seq Scan continua sendo o plano certo. O tempo está na leitura de 80M rows + agregação, não na localização.

Melhorias reais: **pré-agregação** (materialized view ou summary table incremental com refresh) para relatório recorrente; rodar em **réplica**; se as queries reais sempre cortam por período, índice/partição por `paid_at` (ou **BRIN**, barato em tabela append-only). Um **covering index** `(status, subscription_id, amount)` habilitando Index Only Scan pode reduzir IO, mas ainda varre dezenas de milhões de entries — melhora marginal, cite como "possível, não a solução". A resposta de senior aqui é: **"the index doesn't fix an aggregation over the whole table — restructuring when/where the aggregation happens does."**

### Drill 16

```sql
CREATE INDEX ON payments (subscription_id, status, paid_at DESC);
```

Equality (`subscription_id`) → equality (`status`) → sort (`paid_at DESC`). O plano vai de "achar todos os payments da subscription + filtrar + Sort" para **Index Scan que lê 10 entries já ordenadas e para** (LIMIT). Alternativa defensável: `(subscription_id, paid_at DESC)` deixando `status` como filtro — boa se quase todos os payments são `ok` e você quer o índice servindo outras queries; pior se houver muitos failed intercalados. Dizer essa alternativa com o critério = ponto extra.

### Drill 17

`UPPER(country)` é expressão sobre a coluna → índice em `country` não navega (não-sargable). Soluções: (1) reescrever `WHERE country = 'BR'` — os dados já estão em uppercase, a função é desnecessária (sempre questione se a função tem motivo!); (2) se entrada do usuário varia: expression index `ON users (UPPER(country))` — ou normalizar no write. A melhor resposta ataca a **causa** (por que tem UPPER aí?) antes da ferramenta.

### Drill 18 — o integrador

**O que está errado:** a CTE `MATERIALIZED` junta e materializa **80M payments** (todos, de todos os tempos) e só DEPOIS o filtro de status e dos últimos 30 dias é aplicado — mas a materialização é uma **optimization fence**: os predicados não são empurrados para dentro. ~78M rows computadas para o lixo.

**Fix:**

```sql
SELECT s.user_id, SUM(p.amount)
FROM payments p
JOIN subscriptions s ON s.id = p.subscription_id
WHERE p.status = 'ok'
  AND p.paid_at >= now() - INTERVAL '30 days'
GROUP BY s.user_id;
```

(Ou manter a CTE sem `MATERIALIZED` e com os filtros **dentro** dela.) Índice de apoio: `(paid_at)` ou `(status, paid_at)` — o corte de 30 dias é seletivo (2M de 80M). Resultado: o join processa 2M rows, não 80M. Este drill amarra aula 02 (fence) + 03 (índice) + 04 (reduzir rows cedo) — se você pegou os três pontos, está pronto para a parte de SQL da entrevista.
