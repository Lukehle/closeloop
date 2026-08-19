---
name: flux-analysis
description: Variance and flux analysis with driver decomposition - month-over-month, quarter-over-quarter, year-over-year, and actual-vs-budget/forecast - producing commentary that cites the specific transactions and drivers behind each swing rather than restating the arithmetic. Use for close review, board prep, budget-vs-actual reviews, and any "why did this move" question. Trigger on "flux", "variance", "why did X change", "budget vs actual", "BvA", "explain the movement", "MoM", "QoQ", "bridge", "walk me from X to Y".
---

# Flux analysis

Flux analysis answers **why a number moved**, with evidence. It is not a restatement of the
difference.

The distinction that matters:

> ❌ "Professional fees increased $42K (31%) versus prior month."
> That is the arithmetic. The reader already had it.
>
> ✅ "Professional fees rose $42K to $178K, driven by $38K of one-time diligence work from Hartman
> LLP (invoices #4471, #4488) related to the Series B, plus $4K of recurring drift as the new
> employment-counsel retainer started 07-01. The $38K does not recur; run-rate professional fees
> going forward are ~$140K/month."
> That is analysis: named driver, named evidence, recurring versus one-time, forward implication.

Load `tie-out` first — you cannot explain a movement in a number that has not been proven.

---

## Every flux comment has four parts

Enforce all four. A comment missing any of them is incomplete:

1. **Magnitude** — absolute and percentage, and which one governs the materiality judgment
2. **Driver** — the *specific* cause, decomposed if there are several, with each quantified
3. **Evidence** — the transactions, contracts, headcount changes, or rate changes behind it, named
4. **Forward implication** — recurring or one-time, and what the go-forward run rate is

Part 4 is the one most often skipped and the one management actually reads. A variance that changes
the forecast matters more than a variance that does not, regardless of size.

---

## Materiality gates — declare before you run

```
Investigate:  variance > greater of $25,000 or 10% of the prior-period balance
Floor:        variances under $5,000 aggregate into "other", never itemized
Always:       revenue, gross margin %, headcount cost, cash - any movement, any size
Never skip:   an account that moved to or from zero (a new or discontinued activity)
Sign flips:   any account that changed sign - always investigated regardless of magnitude
```

Two rules people forget:

- **A small variance can be a large finding.** Two offsetting errors of $200K each net to zero and
  pass every threshold. When an account is unusually *flat* against a period with known activity,
  that is itself a flag.
- **Percentages on small bases are noise.** A $400 account moving to $1,200 is +200% and means
  nothing. Gate on the absolute first, then the percentage.

---

## Driver decomposition

Do not report a single blended variance when it decomposes. Decompose to the level where each piece
has a distinct cause and a distinct owner.

### Price / volume / mix (revenue and COGS)

```
Total variance
  = Volume effect     (Δ units × prior price)
  + Price effect      (Δ price × current units)
  + Mix effect        (shift between products/segments at different margins)
  + FX effect         (rate change on non-functional-currency revenue)
```

The pieces must sum to the total. If they do not, the decomposition is wrong — do not force it with
a plug. Compute FX separately at constant currency and report both actual and constant-currency
growth; for a company with meaningful international revenue, hiding FX inside "price" is misleading.

### Rate / volume (personnel)

```
Total variance
  = Headcount effect  (Δ FTE × prior average cost)
  + Rate effect       (Δ average cost × current FTE)
  + Timing effect     (partial-month starts, leavers, retro adjustments)
  + Mix effect        (senior/junior composition, geography)
```

Personnel is usually the largest opex line and the most decomposable. Tie headcount to the HR system
roster as of period end, not to a recollection of who joined.

### Recurring / one-time (every opex line)

The single most useful split. Every variance is classified:

| Class | Meaning | Forecast impact |
|---|---|---|
| **Recurring** | New run-rate level | Update the forecast |
| **One-time** | Does not repeat | Do not update the forecast; note the clean run rate |
| **Timing** | Shifted between periods | Reverses next period; state which period it lands in |
| **Correction** | Prior-period error now fixed | Note whether prior periods need restating |

A flux pack without this classification cannot be used for forecasting, which is most of its value.

---

## The bridge

For any material aggregate — ARR, revenue, EBITDA, cash, headcount — build a bridge rather than a
list. A bridge is the analysis; a variance table is the input to it.

```
July EBITDA bridge (June -> July), $K

  June EBITDA                          (412)
  + Revenue growth                       +88
  + Gross margin improvement             +21
  - Personnel (3 new starters)           (47)
  - Professional fees (one-time)         (38)
  - Marketing (campaign timing)          (12)
  + Other, net                            +6
  = July EBITDA                        (394)

  Of the (394): one-time items total (38). Clean run-rate EBITDA is (356).
```

Rules: the bridge must foot exactly; every bar is a named driver not a category label; "other, net"
must stay under the investigation floor or it gets broken out; and the one-time reconciliation at
the bottom is mandatory.

Render bridges as waterfall charts — see `fin-artifact` for the visual conventions (baseline anchors,
sign colors, cumulative connector lines).

---

## Where the evidence comes from

| Variance in | Look at |
|---|---|
| Revenue | Contract-level detail, new/expansion/churn split, billing vs recognized (see `saas-metrics`) |
| COGS / gross margin | Hosting and infrastructure detail, support headcount, one-time credits, customer mix |
| Personnel | HR roster deltas at period end, comp changes, bonus and commission accruals, capitalized labor |
| Professional fees | Invoice-level with vendor and matter |
| Marketing | Campaign-level spend, timing of committed programs |
| Any account | The GL detail for the account, filtered to the period, sorted by absolute amount descending |

**Start from the largest transactions.** In almost every account, three to five transactions explain
most of a material variance. Pull the GL detail sorted by magnitude and the drivers usually announce
themselves.

---

## Anti-patterns

| Comment | Why it fails |
|---|---|
| "Increase due to higher spend" | Restates the direction. No driver |
| "Timing differences" (unquantified) | Which items, what amounts, landing in which period? |
| "In line with expectations" | Whose expectations, and against which number? |
| "Due to increased business activity" | Content-free; applies to any variance ever written |
| "Will normalize next month" | An unfalsifiable prediction with no mechanism |
| Commentary written before the account was tied out | You are explaining a number that may be wrong |

---

## Degraded mode

Without query access, request the GL detail extract for the accounts over the materiality gate and
do the decomposition from that. The gates, the decomposition math, and the four-part comment
structure are all manual-friendly. State in the output which accounts you could not obtain detail
for — an unexplained material variance is a finding to report, not a gap to paper over.

---

## Related skills

- `tie-out` — prove the number before explaining its movement
- `close-orchestrator` — flux lives in phase 4
- `saas-metrics` — the revenue-side decomposition and the ARR bridge
- `fin-artifact` — waterfall/bridge rendering conventions
- `startup-board-pack` — where flux commentary ends up
