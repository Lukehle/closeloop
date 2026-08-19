---
name: reconciliation
description: Build and run account reconciliations - bank, AR/AP subledger to GL, deferred revenue, prepaid and accrual schedules, intercompany, and clearing accounts. Covers matching rules, tolerance bands, exception triage, roll-forward proof, and the aging of unresolved items. Use when reconciling any account, designing a recurring rec, or investigating why a rec does not clear. Trigger on "reconcile", "reconciliation", "rec", "doesn't tie", "subledger to GL", "bank rec", "clearing account", "unreconciled items", "roll forward".
---

# Reconciliation

A reconciliation is a **proof that two independently maintained records agree**, plus a complete
explanation of every difference. It is not a variance report and it is not a plausibility check.

The two tests every rec must pass:

1. **Agreement** — the two balances agree, or every difference is identified, explained, and owned.
2. **Roll-forward** — opening balance + activity − clearing = closing balance, and closing agrees to
   the independent source.

A rec that passes agreement but fails roll-forward is hiding compensating errors. Run both.

Load `finance-guardrails` and `tie-out` first — this skill produces `tie-out` blocks as its output.

---

## Anatomy of a reconciliation

```
Balance per independent source        (bank statement / subledger / counterparty)
  +/- reconciling items               (each identified, dated, aged, owned)
  = Balance per general ledger
```

Every reconciling item needs five fields. An item missing any of them is not reconciled, it is
merely noticed:

| Field | Why |
|---|---|
| **Amount** | The difference it explains |
| **Date arising** | Drives the aging, which is the real risk signal |
| **Reason** | Timing, error, unrecorded, in-transit, disputed, unidentified |
| **Owner** | A named person who will clear it |
| **Expected clearing** | A date. "Next month" is not a date |

**`unidentified` is a legitimate reason and must be used honestly.** An unidentified difference
labelled "timing" is a lie that will survive several closes and then become a write-off nobody can
explain.

---

## Reconciliation types and their specific traps

### Bank reconciliation

Match: bank statement ↔ GL cash account.

Standard reconciling items: deposits in transit, outstanding checks, bank fees and interest not yet
booked, NSF returns, wires posted to the wrong entity.

Traps:
- **Stale outstanding checks.** Anything over 90 days needs a decision — void and reissue, or
  escheat. A check outstanding 18 months is not a reconciling item, it is unclaimed property.
- **Same-amount transposition.** Two errors of equal and opposite value net to zero. Match on
  *count* as well as amount; a rec that balances with the wrong number of items is not clean.
- **Cash is zero-tolerance.** No materiality threshold applies. Every cent is explained.

### Subledger to GL (AR, AP, fixed assets, inventory)

Match: subledger detail total ↔ GL control account balance.

Traps:
- **Direct GL postings that bypass the subledger.** These are the most common cause and the hardest
  to see. Query the GL for entries to the control account whose source is *not* the subledger module.
  Any such entry is a finding, not just a difference.
- **Timing at the cutoff boundary.** Effective date vs posting date is the usual culprit — an item
  effective 07-31 posted 08-01 appears in one side and not the other.
- **Multi-currency.** The subledger may hold transaction currency while the GL holds functional.
  Reconcile in functional currency at the same rate, and reconcile the FX difference separately.

### Deferred revenue roll-forward

```
Opening deferred balance
  + new billings deferred
  - revenue recognized this period
  +/- contract modifications
  +/- FX on non-functional-currency contracts
  = Closing deferred balance          -> must agree to GL and to the contract-level schedule
```

Traps:
- **Recognized revenue must tie to the income statement**, not merely to a schedule. Two ties, both
  required.
- **Contract modifications are where this breaks.** An upsell mid-term reallocates the transaction
  price across performance obligations; if the schedule was not rebuilt, the roll-forward will foot
  while the underlying allocation is wrong.
- **This is also the ARR reconciliation boundary.** See `saas-metrics` — the deferred roll-forward is
  the bridge between the billing system and ASC 606 revenue, and it is exactly where dashboard ARR
  and GL revenue diverge.

### Intercompany

Match: entity A's receivable ↔ entity B's payable.

Traps:
- **Zero-tolerance, always.** Intercompany must eliminate exactly at consolidation. A residual
  balance flows straight to consolidated equity.
- **FX asymmetry.** Both sides must use the same rate and the same rate date, or the difference is
  structural and will recur every period.
- **One-sided postings.** Someone booked the receivable and nobody booked the payable. Match on
  transaction reference, not just amount.

### Clearing and suspense accounts

Match: balance ↔ zero (or a stated, approved expected balance).

Traps:
- **A clearing account should clear.** A persistent non-zero balance means the process feeding it is
  broken. Fix the process; do not reconcile the symptom every month forever.
- **Age every item.** Anything over 60 days in a clearing account is a finding to escalate.

---

## Matching rules — write them down, in order

Matching is a cascade. State the rules explicitly and apply them in sequence, most specific first:

```
1. Exact:      reference number + amount + date        -> auto-match
2. Strong:     reference number + amount               -> auto-match
3. Amount+date: amount + date within +/- 3 days        -> auto-match, flag for sampling
4. Amount only: exact amount, unique in both sets      -> propose, human confirms
5. Fuzzy:      amount within tolerance, near date      -> propose, human confirms
6. Many-to-one: sum of N items = 1 item                -> propose, show the composition
7. Unmatched                                            -> exception queue
```

**Tolerance applies to matching, never to the total.** A $0.02 rounding tolerance on individual line
matching is reasonable. A $0.02 tolerance on whether the account reconciles is not — the rec must
foot exactly, with every accepted rounding difference itemized and summed into an explicit
"rounding" reconciling item.

Never let a fuzzy match auto-clear. Rules 4-7 propose; a human confirms.

---

## Exception triage

Sort exceptions by **risk**, which is not the same as size:

| Priority | Criteria |
|---|---|
| **P1** | Any cash or intercompany difference; anything over materiality; anything aged >90 days; anything in a clearing account >60 days |
| **P2** | Over the investigation floor; aged 30-90 days; recurring across 2+ periods |
| **P3** | Under the investigation floor and under 30 days — aggregate, note the total, do not itemize |

**A recurring exception is a process defect, not a reconciling item.** If the same difference type
appears three periods running, the deliverable is a root-cause fix routed through
`pipeline-change-control`, not a fourth month of the same explanation.

---

## Output

Every rec produces a `tie-out` block (see the `tie-out` skill) plus:

```markdown
## Reconciling items | AR subledger to GL | 2026-07

| # | Amount | Arising | Age | Reason | Owner | Clears by |
|---|--------|---------|-----|--------|-------|-----------|
| 1 | 311.78 | 2026-07-31 | 19d | timing - effective 07-31, posted 08-01 | me | cleared 08-01 |
| 2 | (88.00) | 2026-05-12 | 99d | unidentified | J. Rivera | 2026-08-31 |

Total reconciling items: 223.78
Aged >90 days: 88.00 (1 item) - P1, escalated 2026-08-19

## Roll-forward
Opening 11,904,220.55 + activity 849,410.33 - clearing (312,110.77) = 12,441,520.11
Closing agrees to GL 1200: MATCH

## Not reconciled
Unapplied cash $88,140 - out of scope, owned by the cash rec
```

---

## Checkpointing a long rec

A rec over thousands of items will outlive its context. Per `context-durability`, write a checkpoint
**before** starting the match cascade and every ~10 proposals through rules 4-7.

The three things that must be on disk, because a summary will drop them:

1. **The tolerance and the exclusions**, written down before any matching ran
2. **Which match rules have been applied**, and the counts each produced
3. **The residual set as a file** (`runs/unmatched.csv`), not as a number in the conversation

A half-completed match cascade cannot be reconstructed from a summary. If you resume without a
checkpoint, the honest move is to restart the cascade from rule 1 — re-running rules against a
recorded artifact is cheap; guessing which proposals you already accepted is not.

**Never re-accept a proposal you may have already accepted.** Duplicate clearing is silent and it
foots.

---

## Degraded mode

With no shell or warehouse access, the matching cascade is applied manually in a spreadsheet and the
output format is unchanged. The rules above are the value; the automation is convenience. State in
the tie-out block that matching was manual and give the sample rate you used for verification.

---

## Related skills

- `tie-out` — the proof format this skill emits
- `close-orchestrator` — schedules recs into phase 2 and enforces the gate
- `data-quality-gate` — catches the extract problems that cause phantom differences
- `netsuite` — where the subledger and GL sides come from
- `pipeline-change-control` — the route for fixing a recurring exception at the source
