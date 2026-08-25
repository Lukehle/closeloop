---
name: finance-quorum
description: Adversarial multi-perspective review of a number, model, automation, or deliverable before a human relies on it - independent reviewers each trying to break it from a different angle, then a ruling. Degrades across three tiers so it works on a fully-featured harness or a locked-down Enterprise seat. Use as the review gate before anything is reported, staged for posting, sent, or published. Trigger on "review this", "check my work", "before I send this", "second opinion on the numbers", "defensible to audit", "stress test the model", "what could be wrong here".
---

# Finance quorum

A review gate that asks "does this look right?" will say yes. The question is worthless because it
invites confirmation.

This skill runs the **opposite**: independent passes each **trying to break** the work from a
different angle, then a ruling that survives the attempts. It is the substitute for up-tiering a
model on a policy-restricted seat, and it is a better control than a single capable reviewer even
when up-tiering is available — because the failure modes are orthogonal, not correlated.

---

## When to run it

| Run it | Skip it |
|---|---|
| Before a figure goes to a board, investor, lender, or auditor | Exploratory analysis nobody will rely on |
| Before staging a journal entry over materiality | Work already covered by a passing `tie-out` on a routine, unchanged rec |
| Before a new automation produces its first reported number | Formatting and presentation changes |
| Before changing a metric definition or a threshold | Reruns of an unchanged, previously-quorumed process |
| When a number is surprising, and when it is suspiciously unsurprising | |

That last row matters. A figure that lands exactly on plan deserves the same scrutiny as one that
misses — "too good" and "too clean" are both signals.

---

## The lenses

Seat **3 to 5**, chosen for the specific subject. Each gets one job and is told to **find the
failure**, not to assess quality. Generic reviewer roles produce generic findings.

The standing four for finance work:

| Lens | Its question | Hunts for |
|---|---|---|
| **Tie-out adversary** | "Prove this number is wrong." | Unproven figures, thresholds set after the result, missing `NOT CHECKED` scope, control totals that were never independently sourced |
| **Period and cutoff adversary** | "Show me this is in the wrong period." | `BETWEEN` on timestamps, trandate vs postingperiod, timezone boundaries, open-period extracts, prior-period restatement |
| **Definition adversary** | "Show me this measures something other than what it claims." | Metric definition drift, moving denominators in churn, unlagged CAC, mixed sign conventions, ARR that does not reconcile to revenue |
| **Downstream adversary** | "Who gets hurt if this is wrong, and how late do they find out?" | Blast radius, irreversibility, whether the error is self-correcting or compounds, who has already been told |

Add subject-specific lenses as the work demands — a **disclosure adversary** for anything published
(PII, aggregation thresholds, customer identification), a **control adversary** for anything an
auditor will test, a **stage adversary** for benchmark claims (is this a mid-market benchmark applied
to a seed company?).

**Rule: name lenses from how *this* work could actually fail.** "Correctness reviewer" finds
nothing. "Show me this number is in the wrong period" finds the cutoff bug.

---

## The three tiers

Use the highest tier your seat supports. **The gate never gets skipped for lack of capability** — it
degrades.

### Tier 1 — parallel subagents (full harness)

Run each lens as an independent agent that cannot see the others' findings, then a separate pass to
rule on the pooled findings. Independence is the whole value: reviewers who see each other's work
converge, and convergence is what you are trying to avoid.

- Reviewers: capable tier, high effort
- Each returns structured findings: `{claim, evidence, severity, how_to_verify}`
- **Every finding must cite re-checkable evidence** — a cell, a query, a row count, a quoted figure.
  A finding that cannot be re-checked is an opinion and dies at the ruling.

### Tier 2 — sequential passes (subagents available, no parallelism)

Same lenses, run one at a time, each with a **fresh, deliberately cleared context**. Do not let a
later pass see earlier findings; that is what makes them independent rather than sequential
agreement.

### Tier 3 — single-context structured review (most restricted seat)

You run every lens yourself, explicitly and one at a time, writing findings down before moving to the
next lens. This is weaker than Tiers 1-2 and you should say so in the output — but it is far stronger
than one undirected read, because naming the lens forces a specific search rather than a general
impression.

Discipline that makes Tier 3 work:

1. **Write the lens question down first**, verbatim, before looking at the work.
2. **Hunt only for that failure.** Do not fix anything, do not assess overall quality.
3. **Record findings before switching lenses**, including "nothing found for this lens."
4. **Never skip a lens because an earlier one found something big.** The lenses are orthogonal;
   a big finding in one says nothing about the others.
5. **Rule at the end, in a separate pass**, against the pooled list.

---

## The ruling

Findings are not conclusions. Rule on each:

| Verdict | Meaning |
|---|---|
| **CONFIRMED** | Evidence re-checked and reproduces. Must be fixed before release |
| **PLAUSIBLE** | Cannot be reproduced with available information, but the mechanism is real. Record it as a known unknown in the deliverable |
| **REFUTED** | Re-check shows the concern does not apply. Record why, so the next review does not re-litigate it |

Then one of three outcomes:

- **PASS** — no CONFIRMED findings. Release, with any PLAUSIBLE items disclosed.
- **PASS WITH FIXES** — CONFIRMED findings fixed, fixes verified, release.
- **BLOCK** — a CONFIRMED finding cannot be resolved. Do not release. State what is needed.

**A quorum that finds nothing on its first run should be suspected.** Either the lenses were too
generic, or they were not genuinely trying to break the work. Re-run with sharper lenses before
accepting a clean result on something material.

---

## Output

```
QUORUM | July board pack revenue figures | Tier 2 (sequential, 4 lenses)

CONFIRMED (1)
  Period adversary: ARR snapshot taken 2026-08-04 while the July period was still
  open in NetSuite. Two contracts totalling $84K posted 08-05 with July effective
  dates and are absent from the pack.
  Evidence: NetSuite period status log; SuiteQL re-run 08-19 returns $4.904M vs
  the $4.820M in the pack.
  -> FIX: re-pull post-close, restate the ARR bridge and the scoreboard.

PLAUSIBLE (1)
  Definition adversary: NRR uses a fixed cohort, but reactivations within 90 days
  are counted as expansion rather than new. Defensible, but undocumented - if the
  board benchmarks against peers who treat it as new, NRR reads ~2pts favourable.
  -> Not blocking. Document the convention on the definitions page.

REFUTED (1)
  Tie-out adversary: suspected double-count of the Contoso renewal across new and
  expansion. Re-checked the ARR bridge detail - it appears once, in expansion.
  Recorded so this is not re-litigated next quarter.

LENSES RUN: tie-out, period/cutoff, definition, downstream
LENSES NOT RUN: disclosure (no customer-level detail in this pack)

VERDICT  BLOCK - the CONFIRMED period finding changes the headline ARR figure.
         Re-run after the July restatement.

Tier 2 was used because parallel subagents are unavailable on this seat; the
reviews were sequential with cleared context, which is weaker than independent
parallel review.
```

Stating the tier and its limitation is required. A reader must know how strong the gate that passed
this actually was.

---

## Degraded mode

Tier 3 **is** the degraded mode, and it needs nothing but discipline. If you are the only reviewer in
a single context, the value comes entirely from naming the lens before you look — that converts a
vague "review this" into four specific searches.

---

## Going deeper

This skill is the finance-facing instance of a general pattern. The full mechanics — lens design,
the adversarial verify phase and how to read its survival rate, judge panels and dissent rulings,
degradation tiers, plus a tested library for dedup/tallying/ruling/requorum diffing — live in the
companion pack:

> **[claude-quorum](https://github.com/Lukehle/claude-quorum)** — 10 skills, runnable workflows,
> `tools/quorum-lib.mjs`
> `/plugin marketplace add Lukehle/claude-quorum`

Its `CALIBRATION.md` records what the design is actually based on: a retrospective over ~21
production runs, in which the separate adversarial Verify phase was the measured differentiator
(survival uniform at ~86%) and dissent-honoring convergence was the only family-invariant.

---

## Related skills

- `tie-out` — the first lens's ammunition
- `finance-guardrails` — the release boundary this gate protects
- `token-economics` — why this substitutes for up-tiering on a restricted seat
- `pipeline-change-control` — where a CONFIRMED finding becomes a change record
- `startup-board-pack` — the pre-send checklist this gate backs
