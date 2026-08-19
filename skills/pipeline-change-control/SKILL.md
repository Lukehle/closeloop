---
name: pipeline-change-control
description: Change management for finance automations that an auditor can read - what changed, who approved it, what evidence exists, how to roll it back, and the run log that proves it. Covers threshold changes, gate overrides, new automations, decommissioning, and stakeholder rollout. Use before changing any automation that produces a reported number, and whenever a data-quality BLOCK is overridden. Trigger on "change the pipeline", "update the automation", "override the gate", "adjust the threshold", "deploy the change", "SOX", "audit trail", "who approved", "roll out to the team".
---

# Pipeline change control

An automation that produces a reported number is a **control**. Changing it changes the control, and
the change needs the same evidence trail the control itself has.

This is not bureaucracy for its own sake. It answers two questions that will be asked, usually
months later and usually by someone outside finance:

1. *"Why did this number change between periods?"*
2. *"Who decided that, and on what basis?"*

An automation that cannot answer both is a finding waiting to happen.

Load `finance-guardrails` — Rails 1 (approval), 6 (run log), and 7 (say what you did not do) are the
foundation here.

---

## What requires a change record

| Change | Record required | Approver |
|---|---|---|
| Materiality or tolerance threshold | **Yes** — always | Controller |
| Overriding a data-quality `BLOCK` | **Yes** — always | Controller |
| A metric definition (`saas-metrics`) | **Yes** — plus history restatement | Controller + whoever presents it |
| Logic that changes a reported figure | **Yes** | Controller |
| A new automation touching the GL or a report | **Yes** | Controller |
| Adding a validation check | Yes, lightweight | Owner |
| Decommissioning an automation | **Yes** | Controller |
| Formatting, comments, refactor with identical output | No — but prove output is identical |
| A one-off ad-hoc analysis | No |

The test: **could this change the number someone already relied on?** If yes, it needs a record. If
you are unsure, it needs a record — the cost of an unnecessary record is two minutes.

---

## The change record

```markdown
# CHG-2026-08-003 | AR aging tolerance change

## What
Raise the AR subledger-to-GL matching tolerance from $0.01 to $1.00 per line item.

## Why
The new payment processor settles in gross amounts and books fees separately,
producing sub-dollar rounding on ~400 lines/month. Each is genuinely immaterial;
the volume makes manual clearing consume ~3 hours per close.

## Blast radius
- Affects: AR subledger-to-GL reconciliation only
- Maximum aggregate impact: 400 lines x $1.00 = $400/month worst case,
  against an AR balance of ~$12.4M (0.003%)
- Does NOT change the account-level tolerance, which stays exact.
  Line matching may round; the account must still foot exactly

## Evidence
- analysis/2026-08-rounding-distribution.md - 3 months of the difference
  distribution, max observed single difference $0.94
- Backtest: re-ran Jun and Jul with the new tolerance. Both still foot
  exactly at account level; manual clearing drops from 412 lines to 6

## Alternatives considered
- Fix at source (processor to settle net): raised with the vendor, no ETA
- Auto-book the differences to a fee account: rejected, misclassifies fees
  as rounding and loses the fee visibility Finance wants

## Rollback
Set `tolerance: 0.01` in dq/ar_extract.yaml and re-run. No data migration.
Prior-period results are unaffected - the change is prospective only.

## Approval
Proposed:  <name>, 2026-08-19
Approved:  ______________  Date: __________
Effective: period 2026-08 onward (prospective; prior periods not restated)
```

**`Alternatives considered` is not padding.** It is the section that shows the change was reasoned
rather than convenient, and it is the first thing a reviewer reads to judge whether to trust the
rest.

---

## Overriding a data-quality BLOCK

A `BLOCK` from `data-quality-gate` is cleared by a human who understands the cause — **never by
re-running until it passes**. Re-running until green is how a real data problem becomes a reported
number.

```markdown
# OVR-2026-08-011 | DQ BLOCK override - AR extract row count

## The block
row_count 12,104 below the configured minimum of 14,000

## Root cause
A pricing migration on 2026-08-02 consolidated 2,900 line items into parent
records. The row count drop is real and expected; the control total is unchanged
at $12,441,520.11 and still ties exactly.

## Why proceeding is safe
The control total - the check that actually protects the number - passed exactly.
Row count is a shape check, and the shape legitimately changed.

## Follow-up (required, not optional)
Update row_count bounds to [11,500, 13,500] via CHG-2026-08-012 before the next
close, so this override is not needed again. An override that recurs is a
threshold that is wrong.

## Approval
Override by: ______________  Date: __________
```

**A recurring override is a defect in the threshold, not a routine step.** The second time the same
override is needed, the deliverable is a threshold change, not another override.

---

## The run log

Per `finance-guardrails` Rail 6, every automated run appends an entry. Change records connect to it
by id, which is what makes a number traceable to the logic that produced it:

```
2026-08-19T06:00Z  run=ar-recon-2026-07  chg=CHG-2026-08-003  gate=PASS
                   control_total=12,441,520.11  variance=311.78  result=PASS
2026-08-19T14:22Z  run=ar-recon-2026-07  ovr=OVR-2026-08-011   gate=BLOCK->override
                   approved_by=<controller>  reason="pricing migration, see OVR"
```

Given any reported figure you can now reach: the run that produced it, the version of the logic in
force, every override applied, and who approved each. That chain is the entire point.

---

## Rolling out to people

A technically correct automation that surprises its stakeholders fails anyway. For anything that
changes what someone else sees:

1. **Tell people before, not after.** Who is affected, what changes, when, and what they should do
   differently. One paragraph.
2. **Run parallel for one cycle** where feasible. Old and new side by side, differences explained.
   This is where you discover the requirement nobody wrote down.
3. **Name an owner and a fallback.** Who fixes it at 6am on close day, and what happens if the
   automation is down — the manual path must still exist and be known.
4. **Document at the point of use.** A runbook nobody can find is a runbook that does not exist. Put
   it where the work happens (see `notion-publish`).
5. **Set a review date.** Automations rot: sources change, definitions drift, the business
   reorganises. An automation with no review date will still be running three years after its logic
   stopped being right.

---

## Decommissioning

Turning an automation off needs a record as much as turning one on. State: what consumed its output,
what replaces it, whether historical outputs remain accessible, and who was told. An automation
silently switched off leaves a report that quietly stops updating — and someone will keep reading it.

---

## Degraded mode

Entirely procedural — Markdown files in the automation repo, or a Notion database, or a shared
folder. No tooling required. The template and the approval boundary are the value.

The minimum viable version, if nothing else is possible: a single append-only `CHANGES.md` in the
repo, one entry per change, with what/why/blast-radius/rollback/approver. That is enough to answer
both questions at the top of this skill.

---

## Related skills

- `finance-guardrails` — Rails 1, 6, 7
- `data-quality-gate` — the source of `BLOCK` verdicts requiring override records
- `tie-out` — the evidence a change record cites
- `close-orchestrator` — the run log this connects to
- `notion-publish` — publishing runbooks where the work happens
