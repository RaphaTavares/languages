# Aula 12 — SQL Coding Drills (sessão de exercícios progressivos)

> Simula a parte hands-on de SQL da entrevista (Parte 22 do curso). Dificuldade crescente: JOIN → GROUP BY → HAVING → subqueries → CTEs → window functions → EXISTS → otimização → índices. **Sem soluções neste arquivo** — escreva cada query e me mande em lote; eu corrijo como entrevistador. Faça na sexta à noite ou intercalado com as aulas 02-04.

---

## Schema completo dos drills

```sql
users
+----+----------+---------+---------------------+
| id | name     | country | created_at          |
+----+----------+---------+---------------------+
| 1  | Ana      | BR      | 2025-01-10          |
| 2  | Bruno    | BR      | 2025-03-22          |
| 3  | Carla    | US      | 2025-05-05          |
| 4  | Daniel   | US      | 2025-06-30          |
| 5  | Elena    | DE      | 2025-09-14          |
+----+----------+---------+---------------------+

subscriptions
+----+---------+----------+------------+------------+-----------+
| id | user_id | plan     | started_at | ended_at   | price     |
+----+---------+----------+------------+------------+-----------+
| 10 | 1       | basic    | 2025-01-15 | 2025-06-15 |  9.90     |
| 11 | 1       | premium  | 2025-06-15 | NULL       | 29.90     |
| 12 | 2       | basic    | 2025-04-01 | NULL       |  9.90     |
| 13 | 3       | premium  | 2025-05-10 | 2025-11-10 | 29.90     |
| 14 | 5       | basic    | 2025-10-01 | NULL       |  9.90     |
+----+---------+----------+------------+------------+-----------+
-- ended_at NULL = assinatura ativa. Daniel (4) nunca assinou.

payments
+----+-----------------+------------+--------+----------+
| id | subscription_id | paid_at    | amount | status   |
+----+-----------------+------------+--------+----------+
| 90 | 10              | 2025-01-15 |  9.90  | ok       |
| 91 | 10              | 2025-02-15 |  9.90  | ok       |
| 92 | 10              | 2025-03-15 |  9.90  | failed   |
| 93 | 11              | 2025-06-15 | 29.90  | ok       |
| 94 | 11              | 2025-07-15 | 29.90  | ok       |
| 95 | 12              | 2025-04-01 |  9.90  | ok       |
| 96 | 13              | 2025-05-10 | 29.90  | ok       |
| 97 | 14              | 2025-10-01 |  9.90  | failed   |
+----+-----------------+------------+--------+----------+
```

---

## Nível 1 — JOINs

**Drill 1.** Liste nome do user, plan e started_at de todas as subscriptions (users sem subscription ficam de fora).

**Drill 2.** Liste TODOS os users e, se tiverem, suas subscriptions ativas (`ended_at IS NULL`). Users sem subscription ativa devem aparecer com NULL. ⚠️ Pegadinha: onde vai o filtro de `ended_at` — no `ON` ou no `WHERE`? Os resultados são diferentes; explique por quê.

**Drill 3.** Users que **nunca** tiveram subscription. Escreva de **duas formas**: LEFT JOIN + IS NULL, e NOT EXISTS.

## Nível 2 — GROUP BY / HAVING

**Drill 4.** Receita total (`amount` com `status = 'ok'`) por user. Expected:

```
name  | revenue
------+--------
Ana   | 79.60
Bruno |  9.90
Carla | 29.90
```

⚠️ Por que Elena não aparece — e como incluí-la com revenue 0.00?

**Drill 5.** Países com **mais de 1 user cadastrado em 2025**. (WHERE ou HAVING para cada condição?)

**Drill 6.** Por plan: número de subscriptions, receita ok, e **taxa de falha de pagamento** (failed / total, como decimal). Cuidado com divisão inteira.

## Nível 3 — Subqueries / EXISTS

**Drill 7.** Users cuja receita total é maior que a **média de receita entre os users que têm receita**. (Subquery no HAVING ou CTE — sua escolha; justifique.)

**Drill 8.** Subscriptions que têm **pelo menos um pagamento failed** (EXISTS) e subscriptions **sem nenhum pagamento ok** (NOT EXISTS). Duas queries.

## Nível 4 — CTEs

**Drill 9.** Com CTEs encadeadas: (1) receita mensal por user (`date_trunc('month', paid_at)`); (2) o **melhor mês** de cada user (maior receita). Resolva com CTE + window function ou CTE + subquery — depois me diga qual preferiu e por quê.

**Drill 10.** Receita mensal total da empresa com **crescimento vs mês anterior** (valor e %). Dica: `LAG()`.

## Nível 5 — Window functions

**Drill 11.** A subscription **mais recente** de cada user (todas as colunas). O drill clássico.

**Drill 12.** **Running total** de receita da empresa por data de pagamento (só `ok`), com desempate determinístico.

**Drill 13.** **Top 1 user por receita em cada país**, incluindo empates (qual função de ranking?).

**Drill 14.** Para cada payment, mostre `amount` e a **diferença para o payment anterior da mesma subscription** (`LAG` com `PARTITION BY`).

## Nível 6 — Otimização e índices (responda em texto, não SQL)

**Drill 15.** A query do Drill 4 roda sobre 80M payments e demora 40s. O plano mostra `Seq Scan on payments` + `HashAggregate`. Que índice(s) você consideraria? O índice resolve, melhora ou não muda? Justifique (pense: seletividade de `status='ok'` e agregação sobre a tabela quase toda).

**Drill 16.**

```sql
SELECT * FROM payments
WHERE subscription_id = ?
AND status = 'ok'
ORDER BY paid_at DESC
LIMIT 10;
```

Which index, and why that column order? O que muda no plano com e sem ele?

**Drill 17.**

```sql
SELECT * FROM users WHERE UPPER(country) = 'BR';
```

Índice em `country` existe e não é usado. Diagnóstico + 2 soluções.

**Drill 18 (integrador).** O relatório abaixo demora 25s:

```sql
WITH all_pay AS MATERIALIZED (
    SELECT s.user_id, p.amount, p.status, p.paid_at
    FROM payments p JOIN subscriptions s ON s.id = p.subscription_id
)
SELECT user_id, SUM(amount)
FROM all_pay
WHERE status = 'ok' AND paid_at >= now() - INTERVAL '30 days'
GROUP BY user_id;
```

`payments` tem 80M rows; os últimos 30 dias são ~2M. **What's wrong with this query and how would you fix it?** (Dica: onde os filtros estão sendo aplicados vs onde deveriam?)

---

## ✅ Respostas / avaliação

*(Preenchido conforme você manda os drills — pode mandar por nível.)*
