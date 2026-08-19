---
name: close-orchestrator
description: Run month-end, quarter-end, or year-end close as a resumable, ledger-driven process - a durable progress ledger that survives context loss, dependency-aware task ordering, evidence captured per task, and postings staged for human approval rather than executed. Use when starting, resuming, monitoring, or designing a close. Trigger on "close", "month-end", "start the close", "where are we in close", "close checklist", "close calendar", "resume the close", "day 3 of close", or any request to coordinate multi-step period-end work.
---

# Close orchestrator

A close is a long-running, interruptible, dependency-ordered process where **the ledger is the
recovery map, not your memory**. This skill runs it that way.

The failure mode this prevents: a close that runs for four days across many sessions, loses context,
and gets re-done from a half-remembered state — producing duplicate entries, skipped reconciliations,
and a completion claim nobody can verify.

Load `finance-guardrails` first. Rails 1 (approval), 3 (as-of), 6 (run log), and 7 (say what you did
not do) govern every step here.

---

## The ledger is the source of truth

Before any close work, create or open the run directory:

```
close-runs/<period>/
  LEDGER.md          <- authoritative state; trust this over recollection
  runlog.md          <- append-only, per guardrails Rail 6
  tasks/<id>/        <- evidence per task: queries, extracts, tie-out blocks
  staged/            <- prepared-but-not-executed actions awaiting a human
  SUMMARY.md         <- written only at the end
```

### LEDGER.md format

```markdown
# Close 2026-07 | opened 2026-08-01 | target close 2026-08-07

## State
current_phase: 2 (subledger close)
blocked: none
last_updated: 2026-08-19T14:22Z

## Tasks
| id | task | phase | depends_on | status | evidence | owner |
|----|------|-------|-----------|--------|----------|-------|
| C01 | Cut off AP invoice entry | 1 | - | done | tasks/C01/ | AP |
| C02 | Bank rec - operating | 2 | C01 | done | tasks/C02/ tie-out PASS | me |
| C03 | AR subledger to GL | 2 | C01 | done | tasks/C03/ tie-out PASS $312 var | me |
| C04 | Deferred revenue roll | 2 | C03 | in_progress | tasks/C04/ | me |
| C05 | Accrual JEs | 3 | C02,C03,C04 | staged | staged/C05-accruals.md | me -> Controller |
| C06 | Flux commentary | 4 | C05 | blocked | - | me |
```

**Status vocabulary — use exactly these six:**

| Status | Means |
|---|---|
| `pending` | Not started, dependencies not yet met |
| `ready` | Dependencies met, not started |
| `in_progress` | Started, incomplete |
| `staged` | Prepared in full, **awaiting a human to execute** — this is a terminal state for the automation |
| `done` | Completed **and** evidence exists **and** tie-out passed |
| `blocked` | Cannot proceed; the reason is recorded in the ledger |

`done` requires all three conditions. A task marked `done` with no evidence directory is a ledger
defect, and the correct fix is to reopen it, not to backfill the evidence.

---

## Resume protocol

Every session that touches an open close **starts here**, before doing any work:

1. **Read `LEDGER.md`.** Not your memory of it, not the summary, the file.
2. **Read the last 20 lines of `runlog.md`** to see what actually happened most recently.
3. **Verify the frontier.** For the last task marked `done`, confirm its evidence directory exists
   and its tie-out says PASS. A `done` you cannot verify is reopened as `in_progress`.
4. **Resume at the first task that is not `done` or `staged`.**
5. **Never re-run a `done` task.** In finance, re-running is not idempotent — it produces duplicate
   accruals and double-counted adjustments.

> This is the single most important behavior in the skill. Context loss is normal in a multi-day
> close. Ledger-first resumption is what makes it survivable.

---

## Phase model

Order tasks into phases by dependency, not by convention. A typical shape:

| Phase | Contains | Gate to next phase |
|---|---|---|
| **0 — Pre-close** | Calendar confirmed, cutoffs communicated, prior period locked, FX rates loaded | Prior period is closed and locked |
| **1 — Cutoff** | AP/AR entry cutoffs, payroll cutoff, inventory count, expense report deadline | Cutoffs enforced and confirmed by owners |
| **2 — Subledger close** | Bank recs, AR↔GL, AP↔GL, deferred revenue roll, prepaid/fixed-asset schedules, intercompany | Every rec has a PASS tie-out or a documented exception |
| **3 — Adjustments** | Accruals, reclasses, allocations, FX revaluation, true-ups | All entries **staged**, none posted by automation |
| **4 — Review** | Flux analysis, statement integrity checks, SaaS metric reconciliation | Statements balance; material variances explained |
| **5 — Report** | Board/exec pack, management reporting, metric refresh | Deliverables tie out to closed figures |
| **6 — Lock** | Period lock, archive of evidence, post-close notes | Human executes the lock |

**Do not start a phase until the prior phase's gate is satisfied.** Record the gate check in the run
log. A phase started early is how a reconciliation gets built on data that then moves.

---

## The staging rule (this is where closes go wrong)

**This skill never posts a journal entry, never locks a period, never releases a close.**

For every adjustment, produce a staged package in `staged/`:

```markdown
# STAGED - C05 July accruals | NOT POSTED

## Entry
| Account | Description | Debit | Credit |
|---|---|---|---|
| 6200 Professional fees | Accrue July legal - Hartman LLP | 18,400.00 | |
| 2150 Accrued liabilities | | | 18,400.00 |

## Basis
Engagement letter dated 2026-05-14, monthly retainer $18,400. July invoice not
received as of cutoff. Prior 3 months accrued at same amount and cleared exactly.

## Evidence
tasks/C05/hartman-engagement.pdf ref, tasks/C05/prior-accrual-clearing.md

## Reversal
Auto-reversing 2026-08-01. Confirm the reversal flag is set at entry.

## Blast radius
Period 2026-07 only. Increases July opex by $18.4K (0.4% of monthly opex).
Reversible via the auto-reversal; if posted without the flag, requires a manual
reversing entry in August.

## To execute
Post in NetSuite as JE, source code CLOSE-ACCRUAL, period Jul 2026, auto-reverse ON.

STAGED - human posts this. Approver: ______________  Date: __________
```

Then set the ledger status to `staged` and move on to the next unblocked task. Do not wait; do not
mark it `done`.

---

## Done-check for the whole close

The close is complete when **every** task is `done` or `staged`, and:

- [ ] Every reconciliation has a tie-out block with PASS, or a documented, owned exception
- [ ] The balance sheet balances (see `three-statement`)
- [ ] Cash flow ties to the change in cash on the balance sheet
- [ ] Every material flux is explained with evidence, not adjectives (see `flux-analysis`)
- [ ] Every staged entry is either posted-and-confirmed by a human, or explicitly deferred
- [ ] Reported metrics reconcile to the closed GL figures (see `saas-metrics`)
- [ ] `SUMMARY.md` lists what was done, what was staged, what was deferred, and what is unverified

Only then write `SUMMARY.md`. It must include a **Deferred and unverified** section — a close summary
with no such section is asserting perfection, and that assertion is almost never true.

---

## Degraded mode

- **No shell / no file writes:** keep the ledger as a single Markdown document in the conversation
  or in Notion (see `notion-publish`, and claim the zone). The resume protocol is unchanged: read the
  ledger before acting.
- **No subagents:** run tasks sequentially in the main context. Between phases, compact or clear
  context deliberately — the ledger is what carries state across the boundary, which is exactly why
  it exists.
- **No warehouse access:** tasks that need data become `blocked` with the specific query recorded, so
  a human can run it and drop the result into the task's evidence directory.

---

## Related skills

- `finance-guardrails` — the rails this skill operationalizes
- `tie-out` — the PASS/FAIL evidence every phase-2 task must produce
- `reconciliation` — the mechanics of the individual recs
- `flux-analysis` — phase 4
- `netsuite` — period/subsidiary structure and JE staging specifics
- `startup-board-pack` — phase 5
