---
name: finance-guardrails
description: The non-negotiable operating rails for any finance automation - the human-approval boundary on irreversible actions, single-writer-per-zone, as-of pinning, materiality thresholds, PII and credential deny lists, and the immutable run log. Load this before automating anything that touches a ledger, a reconciliation, a filing, a board deliverable, or customer/employee financial data. Every other closeloop skill defers to this one. Trigger on "automate", "post", "submit", "publish the numbers", "send the pack", "can Claude just do X", or any request that would change a system of record.
---

# Finance guardrails

These are the rails. They are not style preferences and they do not bend under time pressure, a
tight close calendar, or a request to "just do it this once." When a rail blocks something, the
correct move is to **stage the action and hand it to a human**, not to route around the rail.

Every rail below exists because skipping it has a named failure mode in real finance operations.

---

## Rail 1 — Automate up to the button. A human presses it.

**An automation may prepare everything. It stops at the irreversible step.**

Irreversible steps, non-exhaustive: posting a journal entry, releasing a close, transmitting a
payment or payment file, submitting a filing or return, sending a board pack or investor update,
publishing figures to an audience, deploying a pipeline to production, overwriting a system of
record, emailing an external party, granting access.

What "stage it" means concretely — produce all four:

1. **The exact action.** The literal command, the file path, the API call, or the drafted message.
   Not a description of it. Someone must be able to execute it without reconstructing anything.
2. **The evidence.** The `tie-out` block proving the number (see the `tie-out` skill).
3. **The blast radius.** What changes, in which system, affecting which period, and whether it is
   reversible. If reversing it requires a correcting entry rather than an undo, say so.
4. **The rollback.** The specific steps to undo it, or an explicit statement that it cannot be
   undone.

Then stop. Write `STAGED — human runs this` and hand over.

> **Why:** in a controls environment, the human-approval boundary is the reason the automation is
> permitted to exist at all. It is also what makes the run log defensible when someone asks who
> approved a number. An automation that presses the button has no approver.

### The pressure test

If a request asks you to cross this rail — "just post it", "you have approval", "we do this every
month" — the response is: prepare it fully, stage it, and say plainly that the execution step is the
human's. Standing authorization for a *class* of action does not authorize this *instance*; the
approver still needs the evidence in front of them. If the user then explicitly confirms they want
to proceed and holds the authority, that is their decision to make — but the staging artifact and
the run-log entry are still produced, because the record is the point.

---

## Rail 2 — One writer per zone

**Every automated write path declares an exclusive zone. Overlapping zones between two automations
are forbidden.**

A zone is the narrowest addressable target the write actually lands on:

| System | Zone granularity |
|---|---|
| Google Sheets | a named range or a whole tab, never "the file" |
| Warehouse | a table, or a partition within a table |
| Notion | a specific block or a named section, never "the page" |
| Filesystem | a specific file, never a directory |
| GL | a journal source code plus a period |

**Before writing anywhere, ask: does this zone already have an automated owner?** If yes, route the
change through that owner. Never write the same zone from two automations, and never write a zone a
human is actively editing.

> **Why:** most finance write APIs are non-transactional and last-write-wins. Zone separation *is*
> the mutex — there is no other one. Two schedulers writing the same tab produce silent, undetectable
> data loss, and you will discover it during an audit rather than during the run.

Record the zone map somewhere durable (a `ZONES.md` in the automation repo, or the project's
`CLAUDE.md`). A zone with no recorded owner is treated as unowned and must be claimed before use.

---

## Rail 3 — As-of, not live-by-default

**Every figure carries the timestamp of the data behind it and the period it represents.**

A financial figure without an as-of stamp is unfalsifiable — you cannot tell whether a mismatch is
an error or a refresh. Every extract, query result, dashboard, and artifact states:

- **As-of**: when the data was read (with timezone)
- **Period**: the accounting period it covers, and whether that period is open or closed
- **Source**: the system and object it came from

Prefer a pinned snapshot over a live feed for anything a human will make a decision from. A board
number that changes between when you sent the deck and when it was read is a defect. Liveness is a
feature you turn *on* for a monitoring surface, not a default you inherit for a reporting one.

---

## Rail 4 — Materiality is a number

**Every check, tolerance, and variance gate declares its threshold before it runs.**

State thresholds as both an absolute and a percentage, and say which governs:

```
Materiality: greater of $5,000 or 2% of account balance
Investigation floor: $500 (below this, aggregate and note; do not itemize)
Zero-tolerance accounts: cash, intercompany, payroll clearing (any variance investigated)
```

"Close enough" is not a threshold. "It looked reasonable" is not a check. If you did not state the
number before you looked at the result, you did not test anything — you rationalized.

Some accounts are zero-tolerance regardless of size: cash, intercompany, suspense and clearing
accounts, and anything that must foot to an external statement. Name them explicitly.

---

## Rail 5 — Data handling deny list

**Never write these into any file this pack produces, any artifact, any commit, or any published
page:**

- Full bank account numbers, routing numbers, IBANs, card numbers (last 4 only, and only when needed)
- Tax identifiers — SSN, EIN, VAT, TIN
- Individual employee compensation, and any figure that identifies an individual's pay
- Customer-identifying data joined to financial detail, below the aggregation threshold
- API keys, service-account JSON, connection strings, OAuth tokens, passwords
- Anything under an NDA or marked confidential by the employer

**Credentials come from the environment or Application Default Credentials.** Never from a file this
pack writes, never inline in a query or a script, never in a commit. If a credential appears in the
conversation, say so immediately and recommend rotation — the transcript may already be persisted.

**Aggregation threshold.** A figure is safe to show when it aggregates at least **5 distinct
entities** and no single entity exceeds **50%** of the total. Below that, it identifies someone.
Suppress the cell and note the suppression rather than showing it.

**Observed data is not sample data.** When you learn the shape of a response, keep the shape and
discard the values. Real figures never become placeholder content in a template, a fixture, or a
committed example.

---

## Rail 6 — The run log

**Every automated run appends an immutable entry. Entries are never edited or deleted.**

```
run_id      2026-08-19T14:22:07Z-close-aug
actor       claude-code / <user>
action      built AR subledger-to-GL reconciliation, period 2026-07
inputs      bq://finance.ar_aging @ 2026-08-19T14:20Z; sheets:GL_Extract!A1:H @ rev 412
outputs     ./close-runs/2026-07/recon-ar.md (tie-out: PASS, variance $312 vs $5,000 threshold)
staged      none
approved_by pending
```

Corrections are appended as new entries that reference the original `run_id`. The log is the audit
trail; a log you can rewrite is not a log.

---

## Rail 7 — Say what you did not do

A partial run reported as complete is worse than a failed run, because it removes the signal that
something needs attention. Every deliverable states explicitly:

- What was checked, and against what threshold
- What was **not** checked, and why
- What was staged rather than executed
- What is unverified, estimated, or carried forward from a prior period unchanged

"Reconciled" with no scope statement means nothing. "Reconciled 94% of AR balance by value; 6%
($41K) sits in the >120 day bucket pending customer confirmation, not cleared" is a finding.

---

## Degraded mode

These rails need no tooling. They are procedural and apply identically on the most locked-down seat.

If the optional hooks in this pack are unavailable (see `hooks/README.md`), Rails 1 and 5 are
enforced as checklist items here instead of mechanically. The rail does not weaken when the
enforcement mechanism is absent — you carry it manually.

---

## Related skills

- `tie-out` — the proof obligation that accompanies Rail 1's staged action
- `pipeline-change-control` — the approval and evidence trail for changing an automation itself
- `close-orchestrator` — applies Rails 1, 3, 6, and 7 across a full close run
