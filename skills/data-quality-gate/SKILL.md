---
name: data-quality-gate
description: Validate a dataset at the boundary before anything downstream consumes it - control totals, row counts, duplicate keys, referential integrity, period completeness, null and sign sanity, and drift against the prior run. Blocks the pipeline on failure rather than passing bad data forward. Use on every extract, load, or handoff between systems. Trigger on "data quality", "validate the extract", "check the data", "the numbers look wrong", "bad data", "did the load work", "DQ check", "sanity check the file".
---

# Data quality gate

A gate that warns is not a gate. **This one blocks.**

The economics are one-sided: catching a bad extract at the boundary costs minutes; catching it after
it has flowed into a reconciliation, a metric, a board deck, and an external commitment costs days
and a credibility hit. Every check below runs *before* anything downstream reads the data.

Load `tie-out` — the gate emits the same PASS/FAIL discipline, with thresholds declared in advance.

---

## The seven checks

Run in this order. Order matters: a failed row count makes every later check meaningless, so stop at
the first `BLOCK`.

### 1. Row count within expected bounds

```
expected: 14,000 - 16,000 (prior 3 periods: 14,882 / 15,104 / 14,655)
actual:   14,882                                                    PASS
```

Derive bounds from history, not from a guess. **A row count of zero is always a BLOCK**, never an
empty period — an empty result is far more often a broken query, a permissions failure, or a wrong
date filter than a genuinely quiet month.

### 2. Control total agrees to source

```
source (NetSuite AR aging report):  12,441,520.11
extract sum(amount_usd):            12,441,520.11                   PASS (exact)
```

This is the check that matters most, because it catches the failures the others cannot see —
truncation, a fan-out join doubling amounts, a partial load. **Exact match required.** A control
total tolerance is not a tolerance, it is a decision to ship unknown differences.

### 3. Duplicate keys

```
grain: (transaction_id)
duplicate keys: 0                                                   PASS
```

Declare the intended grain explicitly. Duplicates usually mean a fan-out join or a re-run that
appended instead of replacing. A duplicated transaction inflates every downstream total silently and
plausibly.

### 4. Referential integrity

```
customer_id not in dim_customer:  0 rows                            PASS
account_id  not in chart_of_accounts:  3 rows ($4,120)              BLOCK
```

Orphans mean either a dimension that has not loaded yet (a sequencing bug) or genuinely bad source
data. Both need a human before the data moves on. Report the orphan **value**, not just the count —
three orphan rows worth $4M is a different problem from three worth $40.

### 5. Period completeness

```
period 2026-07: 31 of 31 days present                               PASS
gaps: none
weekend/holiday pattern consistent with prior periods               PASS
```

A missing day is the classic silent extract failure. Check calendar completeness, and check the
*shape* — if weekdays normally carry 20x weekend volume and this month they do not, something is
wrong even though every day is present.

### 6. Null, sign, and range sanity

```
null amount_usd:        0                                           PASS
null customer_id:       0                                           PASS  (join key - any null is BLOCK)
negative revenue rows:  4 ($-2,840, credit memos)                   PASS  (expected)
amount > $1M:           2 (largest $1.4M - Contoso renewal)         PASS  (verified)
amount = exactly 0:     118 rows                                    WARN  (investigate)
```

**A null in a join key is always a BLOCK** — those rows will silently vanish in the next join rather
than error. A null in an amount is usually a BLOCK too, since `SUM` skips nulls and the total will
be quietly short.

Sign checks catch reversed conventions after a source change, which is one of the hardest defects to
spot downstream because everything still foots.

### 7. Drift vs prior run

```
row count vs prior period:      +1.5%                               PASS
control total vs prior period:  +4.4%                               PASS
distinct customers:             -18.2%                              BLOCK - investigate
new columns appeared:           none
column types changed:           none
```

Thresholds: flag beyond ±20% period-over-period unless a known event explains it. **Schema drift is
always a BLOCK** — a new or retyped column means the contract changed and nobody told you.

Drift is the check that catches problems the absolute checks pass. A dataset can have a valid row
count, a matching control total, and still be wrong if half the customers vanished and the remaining
ones doubled.

---

## Verdicts

Three, and only three:

| Verdict | Meaning | Effect |
|---|---|---|
| **PASS** | Every check within threshold | Data proceeds |
| **WARN** | Anomalous but explained and recorded | Data proceeds; the note travels with it |
| **BLOCK** | A check failed | **Pipeline stops.** A human investigates |

A `BLOCK` is not overridden by re-running. It is overridden by a human who understands the cause and
records the override in the run log with a reason — per `pipeline-change-control`.

**Never downgrade a BLOCK to a WARN to unblock a close.** That converts a data problem into a
reporting problem, and the reporting problem is discovered by someone outside finance.

---

## Running the checks

```bash
python scripts/dq_check.py \
    --data extract.csv \
    --config dq/ar_extract.yaml \
    --prior runs/2026-06/extract.csv \
    > dq-report.json 2>dq.err; status=$?
echo "exit=$status"
[ $status -eq 0 ] || echo "GATE BLOCKED - pipeline halted"
```

Exit codes: `0` pass, `1` warnings only, `2` **blocked**, `3` could not run. Capture the status —
per `tie-out`, piping this into a filter throws away the only signal that matters.

Config declares the thresholds up front, which is the whole point:

```yaml
grain: [transaction_id]
row_count: {min: 14000, max: 16000}
control_total:
  column: amount_usd
  expected: 12441520.11
  tolerance: 0.00          # exact
not_null: [transaction_id, customer_id, amount_usd, effective_date]
period:
  column: effective_date
  start: 2026-07-01
  end: 2026-08-01          # exclusive
drift:
  max_pct: 20
  columns: [row_count, control_total, distinct_customers]
```

---

## Where to place the gate

At **every boundary**, not just the first:

```
source system  ->[GATE]-> raw extract  ->[GATE]-> transformed  ->[GATE]-> report
```

Each gate answers a different question: did the extract come out whole; did the transformation
preserve the totals; does the report agree with the transformation. A single gate at the front
catches extraction failures and nothing else, and transformation bugs are at least as common.

---

## Degraded mode

Without Python, every check is a spreadsheet operation: `COUNTA` for row count, `SUM` for control
total, `COUNTIF`/conditional formatting for duplicates, a pivot for period completeness, and a
side-by-side against the prior period for drift. Same thresholds, same three verdicts, same blocking
behaviour. The script saves time; the checks and their declared thresholds are the skill.

---

## Related skills

- `tie-out` — the downstream proof this gate protects
- `warehouse-sql` — where extracts come from, and the query defects that cause failures
- `sheets-bridge` — schema pinning is the sheet-specific version of check 7
- `pipeline-change-control` — the route for a recorded override or a threshold change
- `reconciliation` — where undetected bad data shows up as phantom differences
