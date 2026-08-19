---
name: three-statement
description: Balance sheet, income statement, and cash flow statement integrity - the balance check, indirect cash flow tie to balance-sheet deltas, retained-earnings roll-forward, working-capital linkages, and the standard breakpoints where a three-statement model or a reported set of financials stops articulating. Use when building, reviewing, or debugging financial statements or a three-statement model, and whenever the statements must foot before anything downstream uses them. Trigger on "balance sheet", "income statement", "P&L", "cash flow statement", "doesn't balance", "three-statement", "statements don't tie", "retained earnings", "working capital".
---

# Three-statement integrity

The three statements are one system, not three reports. Every figure on the cash flow statement is
derived from a change on the balance sheet or a line on the income statement. When they stop
articulating, the break is always locatable — this skill is the search order.

Load `tie-out` first. Every check below emits a PASS/FAIL with a stated threshold.

---

## The four structural checks

Run these in order. Do not proceed past a FAIL — a downstream check on broken inputs produces
misleading results.

### 1. The balance check

```
Assets = Liabilities + Equity        (both periods, exactly)
```

Threshold: **exact.** Not "within rounding." If your system carries cents, it balances to the cent.
An out-of-balance balance sheet is never a materiality question.

### 2. Retained earnings roll-forward

```
Opening RE + Net income - Dividends/distributions +/- Prior-period adjustments = Closing RE
```

The `Net income` in this roll **must equal** the bottom line of the income statement for the same
period. This single check catches most statement-linkage errors, because it is where the income
statement physically connects to the balance sheet.

If it fails, the usual causes are: an equity entry booked directly to RE without flowing through the
P&L, an OCI item misclassified into RE, or a period-boundary mismatch.

### 3. Cash flow ties to the balance sheet

```
Net change in cash (per CF statement) = Closing cash (BS) - Opening cash (BS)
```

Threshold: **exact.** Include restricted cash and cash equivalents consistently on both sides — a
mismatch here is very often a definitional inconsistency rather than an arithmetic error.

### 4. Indirect cash flow reconstructs from BS deltas

Every line in the operating and investing sections traces to a balance-sheet movement:

```
Cash from operations
  Net income                              <- IS bottom line (same figure as check 2)
  + Depreciation & amortization           <- accumulated D&A delta (+ disposals)
  + Stock-based compensation              <- APIC delta attributable to SBC
  +/- Deferred taxes                      <- deferred tax asset/liability delta
  - Increase in AR                        <- -(closing AR - opening AR), gross of bad debt
  - Increase in prepaid                   <- -(closing - opening)
  + Increase in AP                        <- +(closing - opening)
  + Increase in accrued liabilities       <- +(closing - opening)
  + Increase in deferred revenue          <- +(closing - opening)  <-- the SaaS one
```

Working-capital sign convention, which is where people slip: **an asset increase is a cash outflow;
a liability increase is a cash inflow.** Deferred revenue rising is cash *in* — for a SaaS company
this is often the largest single operating cash item and the reason a business can be
loss-making and cash-generative simultaneously.

---

## The standard breakpoints

When statements do not articulate, check these in this order. This ordering reflects frequency.

| # | Breakpoint | Symptom | Test |
|---|---|---|---|
| 1 | **Non-cash item omitted from CF** | CF change ≠ BS cash change | Sum SBC, D&A, impairments, non-cash lease expense; confirm each appears |
| 2 | **Working-capital sign error** | CF off by exactly 2× a WC delta | Recompute each WC line; a 2× error is always a sign flip |
| 3 | **Gross vs net movement** | BS delta ≠ CF line for AR or fixed assets | AR delta must be gross of the bad-debt provision; PP&E needs additions and disposals separately, not net |
| 4 | **Acquisition/disposal balances** | Assets jump with no cash line | An acquisition adds balances without operating cash flow — must sit in investing, and the acquired working capital must be excluded from operating |
| 5 | **FX translation** | Small persistent unexplained residual | CTA is not a cash flow. It gets its own reconciling line; it never nets into operating |
| 6 | **Period boundary** | Closing ≠ next opening | The prior period was restated, or the model pulls opening from the wrong column |
| 7 | **Circular reference** | Interest depends on debt depends on cash depends on interest | Break it: compute interest on the *opening* or average balance, or use a documented iterative switch |
| 8 | **Plug** | It balances but you cannot say why | Someone added a plug. Find it and delete it |

**On plugs:** a plug is not a fix, it is a concealment. If a model contains a balancing plug, the
correct action is to locate the real break and remove the plug — and to note in the review that
results produced while the plug existed are unreliable.

---

## Reviewing a three-statement model

Beyond the arithmetic, check the construction:

- [ ] **One input cell per assumption.** An assumption entered in two places will disagree.
- [ ] **No hardcodes inside formula rows.** A typed constant in a calculated row is the single most
      common model defect — see `model-audit` for the mechanical detection.
- [ ] **Consistent formulas across a row.** A row where column K differs structurally from J is
      almost always an error, not an intentional exception.
- [ ] **Sign conventions declared and consistent.** Expenses positive-and-subtracted, or
      negative-and-added — pick one, state it, never mix within a statement.
- [ ] **Historicals locked.** Actuals should not be formula-driven off assumptions.
- [ ] **Circularity handled explicitly.** Either broken by design or controlled with a documented
      iterative switch and a convergence check. Never left implicit.
- [ ] **The balance check is visible on the sheet**, not buried. If a model does not show its own
      balance check, add one before doing anything else with it.

---

## SaaS-specific statement notes

- **Deferred revenue is the pivot.** It links billings (cash) to revenue (ASC 606). Reconciling it is
  simultaneously a balance-sheet control and the bridge between dashboard ARR and GL revenue — see
  `saas-metrics` and the deferred-revenue section of `reconciliation`.
- **Capitalized commissions (ASC 340-40)** sit as a contract asset amortized over the expected
  benefit period. They depress cash relative to P&L in a growth period; the amortization is a
  non-cash add-back.
- **Capitalized software** moves engineering cost from opex to an intangible with its own
  amortization. It flatters EBITDA. When reporting a Rule of 40 or a burn multiple, state whether
  capitalization is included — it materially changes the answer, and comparability with benchmarks
  depends on it.
- **SBC is the largest non-cash item** at most venture-backed SaaS companies. Every EBITDA-style
  metric must state whether it is before or after SBC.

---

## Output

```
STATEMENT INTEGRITY | period 2026-07 | as-of 2026-08-19T14:20Z

1. Balance check          A 48,220,115.02 = L+E 48,220,115.02        PASS (exact)
2. RE roll-forward        11,204,880 + (1,412,004) - 0 = 9,792,876   PASS
   NI per roll (1,412,004) = IS net income (1,412,004)               PASS
3. CF ties to BS cash     net change (884,120) = 6,110,447-6,994,567 PASS (exact)
4. Indirect CF rebuild    all 9 lines trace to BS deltas             PASS
                          largest: deferred revenue +1,209,880

NOT CHECKED
  - OCI/CTA detail: single-entity, no foreign subsidiaries this period
  - Segment statements: not prepared

RESULT  PASS
```

---

## Degraded mode

Every check here is arithmetic on figures you can read off the statements. No tooling required. With
a spreadsheet available, build the four checks as visible formulas on the sheet so they re-run
themselves — a check that lives only in a chat transcript does not protect next month's close.

---

## Related skills

- `tie-out` — the output format
- `reconciliation` — the account-level proofs feeding the statements
- `model-audit` — mechanical detection of the construction defects listed above
- `saas-metrics` — where statement figures meet operating metrics
- `flux-analysis` — explaining the movements once the statements foot
