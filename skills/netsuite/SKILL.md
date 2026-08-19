---
name: netsuite
description: Work with NetSuite as a finance data source and system of record - SuiteQL and saved-search extraction, period/subsidiary/book structure, the transaction and account model, journal entry staging (never posting), revenue and deferred schedules, and warehouse replication patterns. Use when pulling data from NetSuite, reconciling to it, preparing entries for it, or debugging why a NetSuite figure disagrees with a report. Trigger on "NetSuite", "SuiteQL", "saved search", "NetSuite extract", "post a JE", "subsidiary", "accounting period", "why doesn't NetSuite match".
---

# NetSuite

NetSuite is usually the system of record, which makes it the arbiter in any disagreement: when a
warehouse figure and a NetSuite figure differ, **NetSuite is right until proven otherwise** and the
warehouse pipeline is the first suspect.

This skill covers extracting from it correctly, reconciling to it, and staging entries for it. It
does **not** post anything — see `finance-guardrails` Rail 1.

---

## The structure that causes most reconciliation breaks

Four dimensions silently filter or split every query. Get one wrong and the number is wrong, with no
error to tell you.

| Dimension | Trap |
|---|---|
| **Subsidiary** | A query without a subsidiary filter returns consolidated data across entities, or the primary subsidiary only, depending on how it is written. Always filter explicitly, even in a single-entity company — the day a second entity appears, unfiltered queries silently change meaning |
| **Accounting period** | The period is a first-class object, not a date range. A transaction's `postingperiod` is what determines which period it lands in — **not** its `trandate`. These differ constantly at cutoff |
| **Accounting book** | Multi-book setups carry different values per book. A query with no book filter returns the primary book. State the book |
| **Posting vs non-posting** | Sales orders, estimates, and opportunities are transactions but do not hit the GL. Filter to posting transactions when reconciling to the GL, or your subledger total will exceed it |

### Period status matters

A period can be open, locked for AP/AR, or fully closed. **An extract from an open period is not
reproducible** — entries land in it after you extract. Record the period status alongside the as-of
timestamp; if the period was open, the extract is provisional and must be re-run after close.

This is the most common cause of "the number changed and nobody changed anything."

---

## Extraction

Three routes. Prefer them in this order.

### 1. SuiteQL (preferred)

Real SQL over the record model via the REST `suiteql` endpoint. Reproducible, diffable, and
reviewable — it lives in version control like any other query.

```sql
-- gl-by-account.sql
-- Grain:      one row per (account, period, subsidiary)
-- Period:     by postingperiod, NOT trandate
-- Book:       primary (book 1)
-- Posting:    posting transactions only
-- Ties to:    NetSuite Trial Balance for the same period/subsidiary
SELECT
    a.acctnumber              AS account_number,
    a.acctname                AS account_name,
    ap.periodname             AS period,
    t.subsidiary              AS subsidiary_id,
    SUM(tal.amount)           AS amount,
    COUNT(*)                  AS line_count
FROM transactionaccountingline tal
JOIN transaction        t  ON t.id  = tal.transaction
JOIN account            a  ON a.id  = tal.account
JOIN accountingperiod   ap ON ap.id = t.postingperiod
WHERE t.posting      = 'T'
  AND tal.accountingbook = 1
  AND ap.periodname  = 'Jul 2026'
  AND t.subsidiary   = 1
GROUP BY a.acctnumber, a.acctname, ap.periodname, t.subsidiary
```

Notes that save hours:
- `transactionaccountingline` carries the **book-specific** amounts; `transactionline` does not.
  Reconciling from `transactionline` in a multi-book environment gives the wrong answer.
- `posting = 'T'` is the GL filter. Omit it and non-posting transactions inflate the result.
- Join periods through `postingperiod`, never by comparing `trandate` to a date range.
- SuiteQL paginates. **Confirm you retrieved every page** — a truncated result is a silent
  understatement, and it looks exactly like a correct small result.

### 2. Saved searches

Useful when the business already maintains one and the definition is agreed. The risk: **a saved
search is editable by anyone with access, and edits are invisible to your pipeline.** If you depend
on one, snapshot its definition alongside the results, and re-check the definition each period.
Otherwise the day someone adds a filter, your numbers change and the run log shows nothing.

### 3. Scheduled CSV export

Last resort. Fragile to column changes and manual steps. If you must, apply `sheets-bridge` schema
pinning — read by header name, fail loudly on drift.

---

## Warehouse replication

When NetSuite data lands in BigQuery or Snowflake, the reconciliation obligation does not go away —
it moves.

- **Reconcile the replica to NetSuite every period.** Account-level totals, per subsidiary, per
  period, per book. The replica is a copy, and copies drift.
- **Replicate `postingperiod`, not just `trandate`.** A pipeline that carries only `trandate` cannot
  reproduce a NetSuite period total, ever.
- **Handle deletes and edits.** NetSuite transactions can be edited or deleted after posting in an
  open period. An append-only replication will keep the stale version. Use `lastmodifieddate`-based
  incremental loads plus a periodic full reconciliation.
- **Freeze closed periods.** Once a period is closed, snapshot it and stop re-replicating. That is
  what makes historical reporting reproducible.

See `warehouse-sql` for the point-in-time and snapshot patterns, and `data-quality-gate` for the
boundary checks on each load.

---

## Journal entries: stage, never post

**This skill does not post.** Per `finance-guardrails` Rail 1, it prepares and hands over.

A staged NetSuite entry specifies every field the poster needs, so nothing is reconstructed:

```markdown
# STAGED JE - July revenue reclass | NOT POSTED

Subsidiary:      Acme Operating Co (1)
Accounting book: Primary (1)
Period:          Jul 2026
Date:            2026-07-31
Currency:        USD
Source/memo:     CLOSE-RECLASS | reclass implementation revenue per ASC 606
Auto-reverse:    NO
Approval:        routes to Controller queue on entry

| Line | Account | Name | Debit | Credit | Department | Class | Location | Memo |
|---|---|---|---|---|---|---|---|---|
| 1 | 4100 | Subscription revenue | 42,800.00 | | Rev | SaaS | US | reclass out |
| 2 | 4200 | Implementation revenue | | 42,800.00 | Rev | Svc | US | reclass in |

Balanced: 42,800.00 / 42,800.00  OK

## Basis
12 contracts with implementation obligations recognized in subscription in error.
Detail: close-runs/2026-07/tasks/C09/impl-reclass-detail.csv (12 rows, foots to 42,800.00)

## Blast radius
No net income impact - reclass within revenue. Changes revenue mix reporting and
therefore the ARR/GL reconciliation in saas-metrics. Period Jul 2026 only.

## Rollback
Reversing entry, same lines inverted. No data migration.

STAGED - human posts this. Approver: ______________  Date: __________
```

**Segment fields (department, class, location) are mandatory in most configurations.** An entry
missing them fails at post time, or worse, posts with blanks and breaks every segment report. Fill
them from the source detail, never guess.

---

## Revenue and deferred schedules

If Advanced Revenue Management is in use, revenue is driven by **revenue arrangements and revenue
elements**, not directly by the invoice. Two consequences:

- Reconciling billings to revenue means reconciling through the arrangement, not the invoice. The
  invoice tells you what was billed; the arrangement tells you what will be recognized and when.
- **A contract modification rebuilds the element allocation.** If a schedule was not regenerated
  after an upsell, the deferred roll-forward can foot while the underlying allocation is wrong — see
  the deferred revenue trap in `reconciliation`.

This is also exactly where dashboard ARR and GL revenue diverge; `saas-metrics` has the
reconciliation.

---

## Debugging "NetSuite doesn't match"

Work this list in order — it is ordered by how often each is the cause:

1. **Period vs date.** Is the report on `postingperiod` and the query on `trandate`? (Most common.)
2. **Subsidiary.** Consolidated vs single entity; elimination subsidiary included or not.
3. **Accounting book.** Primary vs secondary.
4. **Posting filter.** Non-posting transactions included.
5. **Period status.** Was the period open when one side was extracted?
6. **Pagination.** Did the SuiteQL result truncate?
7. **Currency.** Transaction vs base vs consolidated currency, and which rate.
8. **Account rollup.** Parent-child account hierarchy summed at different levels.
9. **Timezone.** The NetSuite account timezone versus the warehouse's.

Then produce a `tie-out` block for whichever one it was, so the next person does not repeat the
search.

---

## Degraded mode

**No API access:** request a saved-search export, snapshot its definition alongside the data, and
apply `sheets-bridge` schema pinning to the CSV. All the structural rules above still govern
correctness — they are properties of the data model, not of the access method.

**Read-only role:** unchanged. This skill never writes to NetSuite anyway; entries are staged for a
human either way.

---

## Related skills

- `finance-guardrails` — Rail 1, why nothing here posts
- `warehouse-sql` — replication, snapshots, point-in-time correctness
- `reconciliation` — subledger-to-GL and deferred revenue mechanics
- `data-quality-gate` — validating each NetSuite load
- `saas-metrics` — the ARR-to-GL-revenue bridge that runs through revenue arrangements
- `close-orchestrator` — where extraction and staging sit in the close
