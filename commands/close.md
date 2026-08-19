---
description: Start or resume a month-end close run using the closeloop ledger protocol
---

# /close

$ARGUMENTS

Run the **close-orchestrator** skill.

1. Load `finance-guardrails` first — Rails 1, 3, 6, and 7 govern every step.
2. Determine the period from `$ARGUMENTS`, or ask if it is ambiguous.
3. **If a run already exists at `close-runs/<period>/`, this is a resume.** Follow the resume
   protocol exactly: read `LEDGER.md`, read the tail of `runlog.md`, verify the frontier task's
   evidence exists and its tie-out says PASS, then resume at the first task that is not `done` or
   `staged`. Do not re-run a `done` task — in finance, re-running is not idempotent.
4. If no run exists, scaffold `close-runs/<period>/` and build the task list with phases and
   dependencies.
5. Work the first unblocked task. Every phase-2 task produces a `tie-out` block.
6. Postings, locks, and releases are **staged**, never executed.

Report: current phase, what moved this session, what is staged awaiting a human, what is blocked.
