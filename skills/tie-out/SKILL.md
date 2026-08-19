---
name: tie-out
description: Prove a number end-to-end before anyone relies on it - source, transformation, control total, agreement to the general ledger or an external statement, with variance measured against a stated threshold. Use whenever a figure will be shown to a human, published, sent, or used for a decision, and whenever a query, extract, script, or model "ran successfully". Running is not proving. Trigger on "tie out", "does this number tie", "reconcile to GL", "check the numbers", "is this right", "verify the report", or before any deliverable leaves your hands.
---

# Tie-out

**"The query ran" is not "the number is right."** Mechanism success is not substance success. A
pipeline that completes, a script that exits 0, a dashboard that renders, a file that saves — none
of these are evidence about the figure. The only evidence is agreement with an independent source.

This skill produces that evidence in a fixed, auditable shape.

---

## The core discipline

Before you report any number, you must be able to answer four questions **with artifacts, not
recollection**:

1. **Where did it come from?** Named system, named object, as-of timestamp.
2. **What happened to it?** Every filter, join, aggregation, currency conversion, and manual
   adjustment between source and output.
3. **Does it foot?** Does the total of the detail equal the reported total, and does the row count
   match expectation?
4. **Does it agree?** Does it match an independent source — the GL, a bank statement, a prior-period
   roll-forward, a vendor portal — within a threshold you stated in advance?

If you cannot answer all four, the number is **unverified**. Label it that way. An unverified number
presented as verified is the single most damaging thing this pack can produce.

---

## The tie-out block

Every deliverable ships one. This is the fixed format — do not improvise a variant.

```
TIE-OUT | AR subledger to GL | period 2026-07 | as-of 2026-08-19T14:20Z

SOURCE
  A  bq://finance.ar_open_items    WHERE close_period = '2026-07'    rows 14,882
  B  sheets:GL_Extract!A1:H4200    revision 412, account 1200        rows 4,199

TRANSFORM
  A  sum(amount_usd) after fx conversion at 2026-07-31 month-end rate
     excluded: status IN ('void','draft')            -> 61 rows, $0 net
     excluded: intercompany counterparties           -> 340 rows, $1,204,551

CONTROL TOTALS
  A  detail sum        12,441,208.33   row count 14,481   (14,882 - 61 - 340) OK
  A  header/summary    12,441,208.33   MATCH
  B  GL account 1200   12,441,520.11

AGREEMENT
  variance            311.78          0.0025% of balance
  threshold           greater of $5,000 or 2%          -> $248,824
  result              PASS

  variance explained: 3 items posted 2026-08-01 with a 2026-07-31 effective date;
  listed in ./close-runs/2026-07/ar-timing.csv

NOT CHECKED
  - unapplied cash ($88,140) - owned by the cash rec, out of scope here
  - credit memos issued after 2026-08-15 - period not yet closed

RESULT  PASS (with the 2 scope exclusions above)
```

**Every section is mandatory.** A tie-out block with no `NOT CHECKED` section is a red flag — it
claims total coverage, which is almost never true.

---

## Threshold before result. Always.

State the threshold **before** you look at the variance. This is not a formality:

- Threshold first, then result → you tested something
- Result first, then threshold → you rationalized something

If the variance exceeds the threshold, the result is **FAIL**. A FAIL is a finding to investigate,
not a number to widen the threshold around. Widening a threshold to make a variance pass is a
falsification of the control, and it will be visible to anyone reading the run log.

The only legitimate reason to change a threshold is a documented decision made *outside* the run,
recorded in `pipeline-change-control`, with a stated rationale.

---

## Exit codes are evidence. Do not throw them away.

When a tie-out depends on a script, query, or test, **capture the exit code**. Piping output into a
filter destroys it:

```bash
# WRONG - always exits 0 because head's status wins; a failure reads as a pass
python recon.py | head -50

# RIGHT - capture status, then look at output
python recon.py > recon.out 2>&1; status=$?
head -50 recon.out
echo "exit=$status"
[ $status -eq 0 ] || echo "TIE-OUT BLOCKED: recon.py failed"
```

The same applies to `tail`, `grep`, `tee`, and `| head`. In PowerShell, check `$LASTEXITCODE`
immediately — before any other command runs, because it is overwritten.

> **Why this rule exists:** a filtered command that swallows a non-zero exit produces a clean-looking
> transcript over a failed run. The report says "checks passed." Nothing passed.

---

## The tells that a tie-out is fake

Watch for these in your own output. Each one means stop and redo the work:

| Tell | What it actually means |
|---|---|
| "The reconciliation completed successfully" | You reported the mechanism, not the substance |
| "The numbers look reasonable" | No threshold was stated, so nothing was tested |
| "Variance is immaterial" with no figure | Immaterial against what? Name the number |
| A total with no row count | You cannot tell a missing-rows bug from a correct result |
| Source described as "the report" or "the system" | Not addressable; nobody can re-run this |
| No as-of timestamp | The result is not reproducible, and a mismatch is undiagnosable |
| Every account passes on the first run | Suspect the test, not the data |
| A prior-period figure carried forward unchecked | It was right once; that is not evidence about now |

---

## Working procedure

1. **Declare scope and threshold.** What is in, what is out, what tolerance governs. Write it down
   before touching data.
2. **Pull both sides independently.** The whole point is independence. Deriving both sides from the
   same extract proves only that arithmetic works.
3. **Foot each side to itself.** Detail sums to header; row counts reconcile to expectation after
   documented exclusions.
4. **Compare, and measure the variance** in both absolute and percentage terms.
5. **Explain the variance, item by item, down to the investigation floor.** "Timing differences" is
   not an explanation; three named items with dates and amounts is.
6. **State what you did not check.**
7. **Emit the block.** PASS, FAIL, or UNVERIFIED — those are the only three results.

---

## Degraded mode

This skill needs no tooling. With no shell, no warehouse client, and no Python, the procedure is
identical and manual: pull both sides by hand, foot them, compare, and write the block. The block
format is the deliverable, and it is legible on any seat.

If you cannot obtain an independent second source at all, the honest result is **UNVERIFIED**, with
a statement of what source would be needed. Never substitute a plausibility check for an agreement
check and call it a tie-out.

---

## Related skills

- `finance-guardrails` — Rail 1 requires a tie-out block to accompany every staged action
- `reconciliation` — builds the recurring recs that this skill proves
- `data-quality-gate` — catches the upstream problems that make a tie-out fail
- `three-statement` — the tie-out rules specific to BS/IS/CF linkage
