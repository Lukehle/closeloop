---
name: startup-board-pack
description: Assemble board, investor-update, and exec reporting packs for an early-stage or growth-stage SaaS company - the narrative arc a board actually reads, cash and runway framing, the metric set by stage, cohort and bridge storytelling, and how to present a miss. Use when building a board deck, monthly investor update, exec review pack, or QBR. Trigger on "board pack", "board deck", "investor update", "board meeting", "exec review", "QBR", "monthly reporting package", "what do I show the board".
---

# Startup board pack

A board pack is a **decision document**, not a data dump. Its job is to get a small number of
important decisions made and to keep the board from being surprised.

The governing rule:

> **No surprises.** A board that learns about a problem in the meeting learns two things: the
> problem, and that you sit on problems. The second is more expensive. Bad news goes early,
> quantified, with a plan.

Load `saas-metrics` for definitions and `tie-out` for the proof obligation. Every number in a board
pack must be tied out to closed figures before it leaves the building.

---

## The arc

Board attention decays fast. Order by importance, not by chronology or by org chart.

| # | Section | Length | Contains |
|---|---|---|---|
| 1 | **The ask** | 1 slide | What you need from the board *today*. Decisions, approvals, intros. Put it first, not last |
| 2 | **Scoreboard** | 1 slide | 6-10 metrics, actual vs plan vs prior, with a plain-language verdict per line |
| 3 | **Cash and runway** | 1 slide | Cash, net burn, runway in months, next raise timing. Never buried |
| 4 | **Growth** | 2-3 slides | ARR bridge, pipeline, retention/cohorts, the one thing driving or blocking growth |
| 5 | **What changed** | 1-2 slides | Material variances vs plan with drivers and forward implication (from `flux-analysis`) |
| 6 | **Risks** | 1 slide | Top 3, each with an owner, a mitigation, and a trigger point |
| 7 | **Functional updates** | as needed | Product, GTM, people — short |
| 8 | **Appendix** | unbounded | Full statements, detailed metrics, definitions, backup |

Sections 1-3 must survive on their own. Assume some readers get no further.

---

## The scoreboard

One slide, 6-10 lines. Every line: **actual, plan, prior period, and a verdict.**

```
                        Actual    Plan     Prior     vs Plan    Verdict
ARR                     $4.82M    $5.10M   $4.61M     (5.5%)    Behind - new logos light
Net new ARR             $210K     $290K    $255K      (27.6%)   Behind - see growth section
NRR (TTM)               104%      108%     106%       (4 pts)   Watch - contraction in SMB
Gross margin            76%       75%      75%        +1 pt     On track
Net burn                $412K     $455K    $388K      +9.5%     Better than plan
Runway                  14.2 mo   13.0 mo  15.1 mo    +1.2 mo   On track
Cash                    $5.85M    $5.92M   $6.26M     (1.2%)    On track
Headcount               47        50       45         (3)       Behind on hiring - deliberate
```

The verdict column is the value. A board reading a table without verdicts has to derive your
judgment, and different members will derive different ones.

**Use exactly four verdicts:** `On track`, `Watch`, `Behind`, `At risk`. Define them once — for
instance, `Watch` = within 10% of plan but trending wrong; `Behind` = missed plan, plan for recovery
exists; `At risk` = missed plan, no credible recovery inside the period. Consistency across meetings
is what makes them meaningful.

---

## Cash and runway

For a startup this is the slide that matters most, and it is the one most often softened.

State plainly:

```
Cash on hand (2026-07-31)                      $5,850,000
Net burn, trailing 3-month average               $412,000/mo
Runway at current burn                              14.2 months
Runway at plan burn (hiring resumes Q4)             11.8 months
Zero-cash date at current burn                  2026-10-02
Next raise: target open 2026-12, close 2026-Q2 (leaves ~6 months buffer)
```

Rules:
- **Show runway on both current and planned burn.** Planned burn is usually higher; the gap is the
  real decision.
- **Give a zero-cash date, not just a month count.** A date is concrete; "14 months" is abstract.
- **Never present runway on a single month's burn.** Use a trailing 3-month average and say so.
- **If runway is under 12 months, it goes in section 1 as an ask,** not in section 3 as information.

---

## Stage-appropriate framing

The same number means different things at different stages. Always frame against your stage, and say
which stage you are framing against.

| Stage | Board mostly cares about | Metrics that are *not* yet meaningful |
|---|---|---|
| Pre-seed / seed | Evidence of product-market fit, qualitative learning, runway | LTV:CAC, magic number, cohort NRR — the n is too small |
| Series A | Repeatable acquisition, early retention, burn multiple trend | Long-horizon LTV, mature cohort curves |
| Series B | Efficiency at scale — CAC payback, NRR, Rule of 40, magic number | — most metrics now apply |
| Series C+ | Rule of 40, FCF path, segment-level economics | — |

**Do not report a metric your data cannot support.** LTV:CAC computed on 11 customers with 5 months
of history is a made-up number wearing a suit. Say "not yet meaningful at n=11" instead. Boards
respect that; they do not respect a number that falls apart under one question.

---

## Presenting a miss

There is a shape to this and it works:

1. **The number, first and unhedged.** "We closed $210K net new ARR against a $290K plan. We missed
   by 28%."
2. **Why, decomposed.** "Two of the three enterprise deals we planned slipped: Acme ($55K, now
   signed 08-14) and Northwind ($40K, verbal commit, contracting). The third, Delta ($30K), we lost
   to a competitor on integration depth."
3. **Recurring or one-time.** "Two are timing; one is a real loss. Adjusted for the slips, we were
   ~$45K light, which is 15% not 28%."
4. **What changes.** "August already has $95K of the slipped ARR closed. We are holding the Q4
   number. The Delta loss goes to the product roadmap discussion in section 7."
5. **The trigger.** "If September net new is under $240K, we cut the Q4 hiring plan by three roles.
   That decision point is 10-05."

Never lead with the explanation. Lead with the number. Explaining before disclosing reads as
managing the board, and boards notice.

---

## Charts that earn their slide

Per `fin-artifact` for rendering conventions:

- **ARR bridge (waterfall)** — the single best growth visual. New / expansion / contraction / churn.
- **Cohort retention heatmap** — with cohort sizes shown, small cells suppressed.
- **Cash and runway line** — actual to date, projected forward on both burn scenarios, zero-cash
  date marked.
- **Actual vs plan with a variance band** — not two lines the reader has to subtract mentally.
- **Rule of 40 scatter over time** — growth on one axis, margin on the other, your path traced.

Charts that do not earn a slide: pie charts of revenue mix, dual-axis anything, 3D effects,
month-by-month tables of every GL account, and any chart whose caption is a restatement of its title.

---

## Pre-send checklist

- [ ] Every number ties out to closed figures (`tie-out` blocks exist and PASS)
- [ ] Metric definitions are unchanged from last period, or the change is flagged and history
      restated
- [ ] The ask slide contains actual asks, not a summary
- [ ] Runway appears in the first three slides
- [ ] Every miss has a driver, a classification, and a trigger point
- [ ] No customer-identifying detail below the aggregation threshold (`finance-guardrails` Rail 5)
- [ ] No employee compensation detail
- [ ] Appendix contains the definitions page
- [ ] **Sending is a human action.** Per Rail 1, this skill assembles and stages the pack. A human
      sends it

---

## Degraded mode

Entirely a reasoning and structure skill. With no tooling it produces the pack outline, the
scoreboard structure, the framing, and the drafted commentary — the numbers come from wherever you
can get them, with unverified figures explicitly marked as such.

---

## Related skills

- `saas-metrics` — definitions and benchmarks for the scoreboard
- `flux-analysis` — section 5 commentary
- `three-statement` — the appendix statements and their integrity checks
- `fin-artifact` — building the pack as a live or snapshot artifact
- `finance-guardrails` — Rails 1 and 5 govern sending and disclosure
