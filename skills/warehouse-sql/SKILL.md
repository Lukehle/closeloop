---
name: warehouse-sql
description: Write and run finance queries against BigQuery or Snowflake with point-in-time correctness, close-cutoff and timezone discipline, slowly-changing-dimension handling, cost-aware execution (dry-run byte estimates, partition pruning), and reproducible query artifacts. Use for any warehouse query whose result will become a reported number. Trigger on "BigQuery", "Snowflake", "SQL", "query the warehouse", "pull the data", "bq", "snowsql", "dbt", "why is this query slow", "why did the number change".
---

# Warehouse SQL for finance

A finance query has a harder correctness bar than an analytics query, because the result becomes a
reported number that someone signs. Three properties are non-negotiable:

1. **Reproducible.** Re-running the same query for the same period returns the same answer, forever.
2. **Point-in-time correct.** It reflects what was true as of a stated moment, not what is true now.
3. **Cheap enough to run repeatedly.** A query you avoid re-running is a query nobody verifies.

Load `tie-out` — any query result that becomes a reported figure needs a tie-out block.

---

## Reproducibility: the rules that make a query re-runnable

### Never use unpinned "now"

```sql
-- WRONG: the answer changes every time you run it. Not reproducible, not auditable.
WHERE created_at >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)

-- RIGHT: explicit boundaries, declared once, half-open interval
DECLARE period_start DATE DEFAULT '2026-07-01';
DECLARE period_end   DATE DEFAULT '2026-08-01';   -- exclusive
WHERE created_at >= period_start AND created_at < period_end
```

**Always half-open intervals** (`>= start AND < end`). `BETWEEN` on a timestamp column silently drops
the final day's transactions after midnight, because `BETWEEN '2026-07-01' AND '2026-07-31'` excludes
everything from `2026-07-31 00:00:01` onward. This is the most common silent period error in finance
SQL and it under-reports by roughly one day per month.

### Pin the snapshot, not just the period

Two different questions, and finance usually wants the second:

```sql
-- "What does the table say today about July?"     - moves as data is corrected
-- "What did the table say on Aug 5 about July?"   - what you actually reported
```

If the warehouse supports time travel, use it and record the timestamp:

```sql
-- BigQuery
FROM `finance.ar_open_items` FOR SYSTEM_TIME AS OF TIMESTAMP '2026-08-05 09:00:00 UTC'

-- Snowflake
FROM finance.ar_open_items AT (TIMESTAMP => '2026-08-05 09:00:00'::timestamp_tz)
```

If it does not, **materialize a snapshot table at close** and query that thereafter. A reported
figure must remain reproducible after the underlying table has been corrected — otherwise you cannot
explain, six months later, why the board deck said what it said.

### Timezone discipline

Declare the reporting timezone once and convert explicitly at every boundary.

```sql
-- Warehouse stores UTC; the business closes on America/New_York
WHERE DATETIME(created_at, 'America/New_York') >= DATETIME(period_start)
  AND DATETIME(created_at, 'America/New_York') <  DATETIME(period_end)
```

A UTC-vs-local mismatch moves transactions between periods at every month boundary — for a company
with evening activity this is a real, recurring, and entirely silent misstatement. Write the
timezone into the query header, not into someone's memory.

### Effective date vs posting date vs created date

Three different dates, three different answers. Finance almost always wants **effective/accounting
date** (which period the transaction belongs to), not created or posted date (when the row appeared).
State which one the query uses, in a comment, at the top.

---

## Point-in-time joins and slowly changing dimensions

The classic error: joining current dimension attributes to historical facts.

```sql
-- WRONG: applies today's segment/plan/owner to a transaction from 14 months ago,
-- silently restating history every time a customer is re-segmented
JOIN dim_customer c ON f.customer_id = c.customer_id

-- RIGHT: the attribute as it was when the fact occurred
JOIN dim_customer c
  ON  f.customer_id = c.customer_id
  AND f.effective_date >= c.valid_from
  AND f.effective_date <  COALESCE(c.valid_to, DATE '9999-12-31')
```

This matters most for segment, region, sales owner, pricing tier, and entity — exactly the
dimensions finance slices by. If prior-period revenue by segment changes when nobody restated
anything, an SCD join is the first place to look.

`COALESCE(valid_to, '9999-12-31')` rather than `IS NULL` keeps the open-ended current row in the
half-open interval without a second branch.

---

## Cost-aware execution

Cost discipline here is the same instinct as the token discipline in `token-economics`: pay for the
bytes you need, not the bytes that exist.

**Estimate before you run.** Always, on any table you have not queried before:

```bash
# BigQuery - dry run, returns bytes without executing or billing
bq query --use_legacy_sql=false --dry_run "$(cat query.sql)"

# Snowflake - inspect the plan
EXPLAIN USING TEXT SELECT ...;
```

Rules that do most of the work:

| Rule | Why |
|---|---|
| **Filter the partition column in the WHERE clause, literally** | A partition filter buried in a subquery, a function, or a join predicate does not prune. `WHERE DATE(ts) = x` defeats pruning on `ts`; `WHERE ts >= x AND ts < y` does not |
| **Never `SELECT *` on a wide table** | Columnar storage bills per column read. On a 200-column fact table this is often a 20x difference |
| **Aggregate in the warehouse, not in context** | Return the 40 rows you need, not the 2 million you aggregate locally. This is the single biggest lever on both warehouse cost and token cost |
| **Materialize expensive intermediates** | A CTE referenced three times may be computed three times. If it is expensive, write it to a temp table |
| **Sample during development, full-scan once** | Develop against `LIMIT`/`TABLESAMPLE`, then run the real query once when the logic is settled |

**Never load a large extract into the conversation.** Write it to a file, aggregate it with a script,
and return the distilled result. A 200MB CSV read into context is a self-inflicted wound that buys
nothing a `GROUP BY` would not.

---

## Query artifacts

A finance query is a durable object, not a one-off. Save it:

```
queries/
  ar-aging-by-period.sql       <- the query, with a header block
  ar-aging-by-period.md        <- what it answers, grain, owner, known caveats
  runs/2026-07/result.csv      <- the pinned result, with its as-of
```

Every query file opens with:

```sql
-- ar-aging-by-period.sql
-- Question:  AR open items by aging bucket at period end
-- Grain:     one row per (customer, aging_bucket)
-- Date used: effective_date (accounting date), NOT created_at
-- Timezone:  America/New_York
-- Snapshot:  FOR SYSTEM_TIME AS OF close date; see :snapshot_ts
-- Ties to:   GL account 1200 - see reconciliation/ar-subledger-to-gl
-- Caveats:   excludes intercompany (counterparty_type = 'IC'), handled separately
-- Owner:     finance-automation
```

The `Ties to` line is what makes a query auditable a year later. Without it, nobody can tell whether
a result was ever proven against anything.

---

## Correctness checklist before a result becomes a number

- [ ] Half-open date interval, no `BETWEEN` on timestamps
- [ ] Correct date column (effective, not created or posted) and it is stated
- [ ] Timezone converted explicitly, and declared
- [ ] Snapshot pinned, or the run timestamp recorded
- [ ] SCD joins are point-in-time, not current-attribute
- [ ] Deduplication is deliberate — `GROUP BY` vs `DISTINCT` vs window `ROW_NUMBER()`, chosen not
      inherited. A fan-out join that silently doubles amounts is the classic
- [ ] Currency handled explicitly: which rate, which rate date, transaction vs functional
- [ ] `NULL` handling deliberate — a `NULL` amount in a `SUM` is skipped, but a `NULL` in a join key
      drops the row entirely
- [ ] Row count and control total captured for the `tie-out` block
- [ ] Result reconciles to an independent source (that is `tie-out`, and it is not optional)

---

## Degraded mode

**No warehouse client on the seat:** produce the reviewed query with its full header block plus a
run-and-return procedure — what to run, where to save the output, what the expected row count and
control total are so the person running it can tell whether it worked. That expectation statement is
what keeps the work verifiable across the handoff.

**Read-only access:** snapshot materialization becomes a request to the data team rather than
something you do. Record the request in the query's `.md` file so the gap is visible.

**No dry-run capability:** bound the query by hand — restrict to one partition, `LIMIT` during
development, and state the expected scan size before running.

---

## Related skills

- `tie-out` — proving the query result
- `data-quality-gate` — validating the extract before anything consumes it
- `netsuite` — extracting the source data into the warehouse
- `token-economics` — the same aggregate-at-source discipline, applied to context
- `sheets-bridge` — moving results into a spreadsheet interface
