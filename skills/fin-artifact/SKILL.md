---
name: fin-artifact
description: Build financial dashboards and reporting artifacts backed by BigQuery, Google Sheets, or a warehouse extract - in two tiers, an as-of snapshot by default and a live connector mode when the organization exposes one. Carries the finance visualization conventions - ARR and cash bridges, cohort heatmaps, actual-vs-budget variance bands, sign conventions, benchmark bands, suppression rules. Use when building any chart, dashboard, board visual, or data-backed page for financial data. Trigger on "dashboard", "build a chart", "visualize", "live artifact", "board visual", "waterfall", "bridge chart", "cohort chart", "financial dashboard", "make it live".
---

# Financial artifacts

Two things distinguish a financial artifact from a generic dashboard: **the numbers must be
provable**, and **the as-of must be explicit**. Everything below follows from those.

Load `dataviz` and `artifact-design` for general visual craft — this skill covers only what is
specific to financial data. It does not replace them.

---

## Tier 1 — the as-of snapshot (default)

**Build this unless liveness is explicitly required.** Data pulled at build time, baked into a
self-contained page, stamped with the as-of.

Why this is the default rather than a fallback:

- **A board number that silently changes is a defect.** If the deck said $4.82M on Tuesday and reads
  $4.79M on Thursday because a late invoice posted, you have created a credibility problem, not a
  freshness feature.
- **It is reproducible.** Six months later the page still shows what was reported, which is the
  whole basis of an audit trail.
- **It needs no runtime capability**, so it works on the most restricted seat.
- **It can be shared**, which a connector-backed page cannot (see below).

Every snapshot artifact carries a provenance footer. Not optional:

```
As-of 2026-08-19 14:20 ET  |  Period Jul 2026 (closed)
Source bq://finance.gl_summary snapshot 2026-08-05T09:00Z  |  Run 2026-07-close
Tie-out PASS - subscription revenue agrees to GL 4100 within $0.00
```

---

## Tier 2 — live connector mode (conditional)

A published artifact can call **the viewer's claude.ai connectors** via the `mcp` runtime capability.
Two hard constraints follow, and both are commonly discovered too late:

1. **The source must be a claude.ai connector on the organization's account.** A BigQuery or Sheets
   MCP server configured locally on your laptop is *not* reachable from a published page. If your
   org has not exposed BigQuery as a connector, live mode is unavailable regardless of your local
   setup.
2. **A page declaring connector access cannot be shared publicly.** It is a viewer-consented grant,
   so each viewer authenticates as themselves. For financial data that is the correct security
   posture — and it is also a distribution constraint. A board pack that only opens for people with
   warehouse credentials is not a board pack.

Before writing a single connector call, **load the `artifact-capabilities` skill** and read its type
definitions. Then:

- **Observe one real request/response pair per tool before publishing.** Never guess argument names
  or result encoding. If you cannot safely observe one, say so at publish time rather than shipping a
  guessed shape.
- **Learn the shape, discard the values.** Real figures never become placeholder content in the page.
- Handle `null` from `claude.use("mcp")` — that is the unavailable case, and the page must degrade to
  its snapshot rather than render empty.
- Drive freshness UI from the result's cache timestamp, and **show it**. A live page that cannot say
  how stale it is, is worse than a snapshot that can.

**When live mode is right:** an operational monitor someone watches during the day — cash position,
collections, pipeline, daily bookings. **When it is wrong:** anything reported, sent, or presented.

---

## Chart conventions for financial data

### Bridges / waterfalls — the highest-value financial chart

Use for any movement between two states: ARR, revenue, EBITDA, cash, headcount.

- Anchor bars (opening, closing) sit on the baseline; movement bars float
- Connector lines between bars — without them the eye cannot follow the cumulative
- Consistent sign colour: increases one hue, decreases another, anchors neutral. Never red/green
  alone — pair with position and label so it survives colourblindness and greyscale printing
- **Label every bar with its value.** A bridge the reader must estimate from axis position has
  failed at its one job
- The bars must sum exactly to the endpoint. If they do not, the decomposition is wrong — fix the
  analysis, never plug the chart
- "Other" stays below the investigation floor or gets broken out

### Cohort heatmaps

- Rows = cohort (acquisition month), columns = periods since acquisition
- **Show cohort size** beside each row. 120% retention on 4 customers is one upsell
- **Suppress cells under 5 entities** — noise, and per `finance-guardrails` Rail 5 potentially
  identifying
- Mark immature periods explicitly rather than truncating them; silently dropping the incomplete tail
  biases the curve upward
- Sequential colour scale, not diverging — unless you are showing variance against a target, which
  is a different chart

### Actual vs budget / forecast

- **Plot the variance, not two lines the reader has to subtract mentally**
- Band the acceptable range so "on track" is visible without arithmetic
- State the comparison basis in the title: "vs Plan (Board approved 2026-01)" — plan versions
  multiply, and an unlabelled "plan" is unreconcilable later

### Benchmark bands (SaaS metrics)

- Draw the stage-appropriate range as a band, plot your value against it
- **Label the stage in the chart.** A mid-market band on a seed-stage company is misleading even
  when the numbers are right (see `saas-metrics`)
- Cite the benchmark source and vintage in a caption

### Time series

- Zero baseline for anything additive (revenue, cash, headcount). Truncating the axis to dramatize a
  trend is the most common chart lie in finance
- Truncation is acceptable for rates and ratios, where zero is not meaningful — say so in the axis
  label
- Mark period boundaries and any definition change with an annotation. A metric that changed
  definition mid-series needs a visible break, not a smooth line

### Never

Dual axes (they encode an arbitrary relationship as a visual correlation), pie charts for anything
with more than three slices or any time dimension, 3D effects, and any chart whose caption restates
its title instead of stating the takeaway.

---

## Sign conventions

Pick one, state it in the page, never mix within a view:

| Convention | Reads well for |
|---|---|
| Expenses **positive**, subtracted in the roll-up | P&L tables that mirror the statements |
| Expenses **negative**, added in the roll-up | Bridges and waterfalls, where direction is the point |

For cash flows, **outflows negative, always** — a cash chart with positive outflows will be misread
by someone, and that someone will be in a board meeting.

Wrap negatives in parentheses in tables (accounting convention), use a minus sign in charts (reads
correctly at small sizes and in labels).

---

## Numbers in the page

- **Right-align all numerics.** Tabular figures (`font-variant-numeric: tabular-nums`) so digits
  align across rows
- Thousands separators always; consistent decimal places within a column
- State units once in the header (`$K`, `$M`, `%`), not on every cell
- **Do not show more precision than the number has.** An ARR figure derived from a rounded extract
  displayed to the cent is a false precision claim
- Percentages: state whether a change is percentage points or percent. "NRR fell 4%" and "NRR fell 4
  points" are different claims and the difference matters

---

## Suppression and disclosure

Before publishing, per `finance-guardrails` Rail 5:

- [ ] No customer-identifying detail below the aggregation threshold (5+ entities, none over 50%)
- [ ] No employee compensation detail, no individually-identifying pay figures
- [ ] No account numbers, tax IDs, or credentials anywhere in the page or its source
- [ ] Suppressed cells are **marked as suppressed**, not silently blank — a blank reads as zero
- [ ] Publishing is a deliberate step. Artifacts start private; sharing is the user's decision, and
      distributing financial data is exactly the kind of action that gets confirmed first

---

## Build checklist

- [ ] Every figure has a `tie-out` block behind it, and the page says PASS
- [ ] As-of, period, and period status (open/closed) are visible on the page
- [ ] Source and snapshot identifier in the footer
- [ ] Tier stated — snapshot or live; if live, the freshness indicator works and the null path
      degrades to snapshot
- [ ] Metric definitions available in the page (a definitions panel, or a link)
- [ ] Charts obey the conventions above; bridges foot exactly
- [ ] Suppression checklist clean
- [ ] Renders in both light and dark, and prints legibly in greyscale — board packs get printed
- [ ] Self-contained: no external CDN, font, or script requests

---

## Degraded mode

**No artifact publishing:** produce a self-contained local HTML file with identical content. Every
convention above applies to a local file exactly as it does to a published page.

**No connector access:** Tier 1, which is the default anyway. State in the footer that the page is a
snapshot, so nobody assumes it refreshes.

**No warehouse access at build time:** build the page against a CSV extract someone provides, and
carry the extract's own as-of rather than the build time. Those are different timestamps and
conflating them misstates the data's age.

---

## Going deeper

This skill is the finance-facing summary. The full craft — hand-built SVG charting under a strict
CSP, bridge/cohort/variance/uncertainty/flow chart design, financial table layout, theming,
accessibility, interaction patterns, and a tested dependency-free chart kit — lives in the companion
pack:

> **[chartroom](https://github.com/Lukehle/chartroom)** — 27 skills plus `chartkit.js`
> `/plugin marketplace add Lukehle/chartroom`

Reach for it when you are actually building the page rather than deciding what belongs on it. Of
particular use here: `bridge-charts` (the ARR and cash bridges this skill calls for, with a footing
check in code), `financial-tables`, `chart-annotation`, and `artifact-testing`.

---

## Related skills

- `artifact-capabilities` — required reading before any connector call
- `dataviz`, `artifact-design` — general visual craft this skill sits on top of
- `tie-out` — the proof behind every figure on the page
- `saas-metrics` — definitions and benchmark bands
- `flux-analysis` — the bridges this skill renders
- `startup-board-pack` — what goes on which slide
- `warehouse-sql` / `sheets-bridge` — where the data comes from
