---
name: saas-metrics
description: Canonical SaaS metric definitions, stage-aware benchmarks, and the ARR-to-GL-revenue reconciliation that dashboards silently get wrong. Covers ARR/MRR and the ARR bridge, NRR and GRR, logo vs revenue churn, CAC payback, LTV:CAC, magic number, Rule of 40, burn multiple, runway, and cohort retention. Use when defining, computing, reviewing, or reporting any SaaS operating metric. Trigger on "ARR", "MRR", "NRR", "GRR", "churn", "CAC", "LTV", "magic number", "Rule of 40", "burn multiple", "runway", "cohort", "SaaS metrics", "why doesn't ARR match revenue".
---

# SaaS metrics

Two failure modes dominate SaaS reporting, and this skill exists to prevent both:

1. **Undefined metrics.** Two teams compute "churn" differently, both are defensible, and the board
   sees a number nobody can reproduce. Every metric here gets one written definition.
2. **The ARR–revenue gap treated as a mystery.** Dashboard ARR pulls MRR from the billing system;
   the income statement reports revenue recognized under ASC 606. They will not match, **by design**.
   A board-ready dashboard *reconciles* them. One that hides the gap is not board-ready.

Load `tie-out` first — every metric reported must tie to a closed GL figure or state that it cannot.

---

## The ARR ↔ GL revenue reconciliation

This is the most important section in the skill. Run it every period.

```
ARR (billing system, point-in-time, annualized contract value)
  ÷ 12                                       -> implied monthly
  - contracts billed but not yet started      (ARR counts them; revenue does not)
  - contracts ended but still in the snapshot (timing of the ARR cut)
  +/- ramp deals                              (ARR at full rate; revenue recognized on the ramp)
  +/- multi-element allocation                (ASC 606 reallocates across obligations)
  - non-recurring components                  (services, setup, usage overage - in revenue, not ARR)
  +/- FX                                      (ARR at spot or plan rate; revenue at recognition rate)
  = expected monthly recurring revenue
  vs. GL subscription revenue for the month   -> explain the residual
```

Threshold: residual under **2% of monthly recurring revenue**, every item over the investigation
floor explained. A persistent unexplained residual means the ARR definition and the revenue policy
have drifted apart, and one of them is wrong.

**Deferred revenue is the audit trail for this.** The deferred roll-forward (see `reconciliation`)
is the bridge between billings and recognized revenue; if the reconciliation above fails, the
deferred roll is where you find out why.

---

## Definitions — pick one and write it down

Ambiguity is the enemy. For each metric, the choices below are real choices; make them explicitly,
record them, and never silently change one. A definition change mid-year invalidates every trend
line, so if you must change one, restate history and say so.

### ARR / MRR

**ARR** = annualized value of committed recurring contracts in force at a point in time.

Decisions you must record:
- Contracted or live? (signed-but-not-started counted, or not)
- Usage-based revenue: excluded, or included at trailing-3-month run rate?
- Services, setup, overage: **excluded** — they are not recurring
- Month-to-month customers: included at current rate, or excluded?
- FX: spot at measurement date, or fixed plan rate for the year? (Plan rate makes trends readable;
  spot makes the tie to revenue easier. State which.)

### The ARR bridge

Report ARR as a bridge, never as a single number:

```
Opening ARR
  + New            (new logos)
  + Expansion      (existing customers, increased spend)
  - Contraction    (existing customers, reduced spend, still customers)
  - Churn          (customers fully lost)
  = Closing ARR
```

Rules: a customer appears in exactly one bucket per period. Downgrade-to-zero is churn, not
contraction. Reactivation after a full lapse is new, not expansion — unless you define a
reactivation window, in which case write the window down.

### Retention

```
NRR = (opening cohort ARR + expansion - contraction - churn) / opening cohort ARR
GRR = (opening cohort ARR - contraction - churn) / opening cohort ARR     [expansion excluded, capped at 100%]

Logo churn    = customers lost / opening customers
Revenue churn = ARR lost / opening ARR
```

Both must be measured on a **fixed cohort** — the customers present at the start of the period,
tracked forward. Measuring against a moving denominator that includes new customers dilutes churn
and makes it look better than it is. That is the most common way retention gets overstated.

Report logo and revenue churn together. They diverge, and the divergence is the insight: if logo
churn is high while revenue churn is low, you are losing small customers — a go-to-market signal, not
a product-quality crisis.

### Efficiency

```
CAC          = fully-loaded S&M spend in period / new customers acquired in period
CAC payback  = CAC / (new ARR per customer × gross margin %)          -> months
LTV          = (ARR per customer × gross margin %) / annual revenue churn rate
LTV:CAC      = LTV / CAC
Magic number = (current-quarter ARR - prior-quarter ARR) × 4 / prior-quarter S&M spend
```

"Fully-loaded" means salaries, commissions, benefits, tools, programs, and allocated overhead — not
just program spend. Half-loaded CAC is the standard way this metric gets flattered.

Apply the S&M spend with a **lag matched to your sales cycle**. A 6-month cycle means this quarter's
new ARR was bought with spend from two quarters ago. Unlagged CAC in a period of changing spend is
close to meaningless.

### Capital efficiency

```
Rule of 40    = ARR growth rate % + profit margin %          (state which margin: EBITDA, FCF, or operating)
Burn multiple = net cash burn / net new ARR                  (lower is better)
Runway        = cash / trailing-3-month average net burn     (months)
```

Always state the margin basis for Rule of 40 and whether SBC and capitalized software are included.
Those two choices can move the score by 10+ points, which is the difference between a good number and
a great one. See `three-statement` for why.

---

## Stage-aware benchmarks (2026)

**Benchmarks are stage-dependent. Quoting a mid-market benchmark at a seed-stage company is
malpractice.** A 2.5× burn multiple is a Series B red flag and entirely normal pre-product-market-fit.

Directional mid-market reference points as of 2026:

| Metric | Best-in-class | Median / acceptable |
|---|---|---|
| NRR | 110%+ | ~101% (compressed from historical highs) |
| GRR | 90%+ | 85%+ |
| CAC payback | < 12 months | 12-18 months |
| LTV:CAC | > 3:1 | 2-3:1 |
| Rule of 40 | 40%+ (60%+ correlates with materially higher valuations) | 20-40% |
| Gross margin | 75-85% | 70-75% |
| Burn multiple | < 1.5× | 1.5-2.5× |

Two framing notes worth carrying into any board conversation: expansion revenue now drives roughly
40-50% of new ARR at scale, which is why NRR gets the weight it does; and NRR compression is an
industry-wide 2026 phenomenon, so a decline needs peer context before it is read as a company-specific
failure.

**Always caveat the stage.** Present benchmarks as "at our stage, the reference range is X" — never
as a bare target.

---

## Cohort retention

Build cohorts by acquisition month, track ARR forward, render as a heatmap (see `fin-artifact`).

Rules that keep cohorts honest:
- **Never mix logo and revenue cohorts on one chart.** They tell different stories.
- **Suppress cells below 5 customers** — small cohorts are noise and, per `finance-guardrails`, may
  identify individual customers.
- **Show the cohort size** alongside the percentage. 120% NRR on a 4-customer cohort is one upsell.
- **Do not truncate the immature tail** silently. Mark incomplete periods rather than dropping them;
  dropping them biases the curve upward.

---

## Reporting discipline

> **A dozen metrics everyone trusts beat thirty nobody reconciles.**

For each metric on a recurring report, hold: one written definition, one owner, one source system,
one reconciliation to the GL where applicable, and a stated as-of. A metric that fails any of the
five comes off the report until it passes.

---

## Degraded mode

Every definition and benchmark here is reference material — no tooling needed. Without warehouse
access, request the ARR bridge and cohort extract from the billing system owner and compute from
that; state in the output that the metric is unreconciled to the GL if you could not perform the
reconciliation at the top of this skill.

---

## Related skills

- `tie-out` — proving the metric against the GL
- `reconciliation` — the deferred revenue roll that underpins the ARR/revenue bridge
- `three-statement` — SBC, capitalized software, and capitalized commissions treatment
- `startup-board-pack` — how these land in front of a board
- `fin-artifact` — bridge, cohort heatmap, and benchmark-band rendering
