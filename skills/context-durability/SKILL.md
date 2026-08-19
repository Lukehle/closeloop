---
name: context-durability
description: Survive context compaction during long finance work - checkpoint state to disk before it can be lost, detect that a compaction has already happened, and recover without silently re-deriving a different number. Use before any long-running reconciliation, multi-account flux, large model audit, or multi-day close, and immediately whenever you suspect the conversation has been summarized. Trigger on "compact", "autocompaction", "context limit", "long session", "where was I", "did I already check", "resume", "continue where we left off", or any task that will iterate over many accounts, files, or periods.
---

# Context durability

A long session gets **compacted**: earlier conversation is replaced by a summary, and recent context
is kept. This is normal and usually harmless.

It is not harmless in finance, for one specific reason:

> **Re-deriving a number does not fail loudly. It silently produces a different number.**

A lost variable in code throws an error. A lost running total in finance work gets recomputed with a
slightly different scope — one exclusion forgotten, one threshold remembered wrong — and the second
answer looks exactly as confident as the first. Nobody finds out until a tie-out fails three steps
later, or until nobody finds out at all.

So the rule is not "avoid compaction." Compaction is unavoidable on long work. The rule is:

> **Anything you would have to re-derive must be on disk before you need it again.**

---

## What evaporates

Compaction keeps a summary. Summaries keep conclusions and drop bookkeeping. These are the things
that reliably disappear, and every one of them is load-bearing in finance work:

| Lost | Why it hurts |
|---|---|
| **Thresholds you stated but did not write down** | You restate them after seeing results — which inverts the whole point of `tie-out` |
| **Exclusions you applied** | "Excluded intercompany and voids" becomes "excluded intercompany". The total moves and nothing errors |
| **Running totals held in reasoning** | Recomputed over a subtly different set |
| **The already-checked list** | "I've done accounts 4000–4200" is exactly the kind of bookkeeping a summary drops. You then redo work, or skip work, and cannot tell which |
| **Partially built matching sets** | A half-completed reconciliation match cascade is unrecoverable from a summary |
| **Why you rejected something** | The rejected alternative comes back and gets re-litigated |
| **Which staged actions you already prepared** | Worst case: a second staged accrual for the same item |

Conclusions survive compaction. **The scope that made them true does not.**

---

## The checkpoint

Write it before you need it. It is small, cheap, and it is the difference between resuming and
restarting.

```markdown
# CHECKPOINT | AR subledger-to-GL | 2026-07 | written 2026-08-19T15:04Z

## Scope and thresholds  (STATED BEFORE RESULTS - do not restate from memory)
Materiality:          greater of $5,000 or 2% of account balance
Investigation floor:  $500
Excluded:             status IN ('void','draft')  -> 61 rows, $0 net
Excluded:             intercompany counterparties -> 340 rows, $1,204,551
Date basis:           effective_date, America/New_York
Snapshot:             bq FOR SYSTEM_TIME AS OF 2026-08-05T09:00Z

## Done  (do not redo - re-running is not idempotent)
- [x] Pulled both sides independently (queries/ar-aging.sql, queries/gl-1200.sql)
- [x] Footed side A: 12,441,208.33 over 14,481 rows
- [x] Footed side B: 12,441,520.11 (GL 1200)
- [x] Match rules 1-3 applied: 14,402 auto-matched

## In progress
Rule 4 (amount-only) proposals: reviewed 61 of 79. Resume at proposal #62.
Accepted so far: 58. Rejected: 3 (see exceptions.md).

## Open / not yet done
- [ ] Rules 5-7
- [ ] Age the residual exceptions
- [ ] Roll-forward proof
- [ ] Emit tie-out block

## Running figures  (recompute ONLY from artifacts, never from memory)
Residual unmatched: 79 rows, $223.78   (source: runs/unmatched.csv)
```

Two properties matter more than the format:

1. **Thresholds and exclusions sit at the top**, marked as stated-before-results. That is what stops
   post-compaction you from quietly reconstructing a friendlier scope.
2. **Every running figure names the artifact it came from.** A number in a checkpoint with no source
   is just another thing to re-derive.

---

## When to checkpoint

Do not wait for a warning. Checkpoint at these points, whether or not compaction seems near:

- **Before starting a loop** over many accounts, files, periods, or entities — write the full work
  list, not just the current item
- **Every ~10 items** through a long loop, updating only the position and the running figures
- **Immediately after stating scope and thresholds**, before looking at a single result
- **Before any large read** that will consume a lot of context
- **At every phase boundary** (`close-orchestrator` already does this via `LEDGER.md`)
- **Before ending a session**, even mid-task — especially mid-task

Checkpointing costs a few hundred tokens. Re-deriving a reconciliation costs a session, and may cost
a wrong number.

---

## Detecting that it already happened

You will not always be told. Treat these as evidence that the conversation was summarized:

- You cannot recall a specific figure, exclusion, or file path that you clearly established earlier
- You are about to ask the user something you already know the answer to
- A summary block appears in context where the original exchange used to be
- Your recollection of the work list is round and tidy in a way real work never is
- The session has run long and you are unsure whether a step completed

**When in doubt, assume it happened.** The cost of an unnecessary checkpoint read is trivial. The
cost of continuing on reconstructed scope is a wrong number.

---

## Recovery protocol

Run this in order. Do not skip to step 4 because you feel oriented — feeling oriented is the failure
mode, not the all-clear.

1. **Stop. Do not continue the task yet.** The strongest instinct after compaction is to press on
   from what the summary implies. That instinct is what produces the different number.
2. **Read the checkpoint and the ledger from disk.** Not the summary of them. The files.
3. **Re-read the stated thresholds and exclusions verbatim.** Do not restate them. If they are not
   written down anywhere, treat every result computed under them as **UNVERIFIED** and redo the
   scope declaration explicitly before continuing.
4. **Verify the frontier.** For the last item marked done, confirm its artifact exists and its
   figures match what the checkpoint claims. A `done` you cannot verify gets reopened.
5. **Recompute running figures from artifacts**, never from the summary. If the checkpoint says
   `$223.78 (source: runs/unmatched.csv)`, open the file.
6. **Resume at the first item that is not done.** Never re-run a completed step — in finance,
   re-running produces duplicate accruals and double-counted adjustments, not a no-op.
7. **Say in the deliverable that a compaction occurred** and what was re-verified. Per
   `finance-guardrails` Rail 7, an unstated recovery is an unstated risk.

If there is no checkpoint and no ledger, the honest position is that the in-flight work is lost.
Restart the task with an explicit scope declaration and a checkpoint. Reconstructing from a summary
and presenting the result as continuous is the one thing not to do.

---

## What never lives only in context

Keep these on disk from the moment they exist:

- Thresholds, materiality gates, and tolerances
- Exclusions and scope decisions, with their row counts and values
- The work list, and which items are complete
- Every control total and row count
- Staged actions already prepared (so you never stage the same accrual twice)
- Rejected alternatives and why
- The as-of timestamp and snapshot identifier

Anything on this list that exists only in the conversation is one compaction away from becoming a
guess that looks like a fact.

---

## Relationship to token-economics

These pull in opposite directions and both are right:

- `token-economics` says **keep context small** — clear, compact, do not load what you can reduce
- this skill says **do not lose state**

They reconcile in one move: **externalize state, then clear freely.** A checkpoint on disk is what
makes context disposable. Without it, clearing is destructive and you end up hoarding context
instead — which is slower, more expensive, *and* still loses everything the moment compaction fires.

`close-orchestrator` is this skill applied to a whole close: the ledger exists precisely so that
context can be thrown away between phases at no cost.

---

## Degraded mode

Needs nothing. A checkpoint is a Markdown file, and on a seat with no file writes it is a message in
the conversation that the user can hold, or a Notion block (see `notion-publish`).

If nothing at all can be written, say so before starting long work and keep the batches small enough
to finish inside one context — a 40-account flux becomes four 10-account passes, each producing a
stated result before the next begins. Small finished units survive; one large unfinished unit does
not.

---

## Related skills

- `close-orchestrator` — the ledger is this pattern at close scale
- `token-economics` — why externalizing state is what makes clearing safe
- `tie-out` — recovery is this discipline applied to your own working state
- `finance-guardrails` — Rail 6 (run log) and Rail 7 (say what you did not do)
- `reconciliation`, `flux-analysis`, `model-audit` — the long-running skills that checkpoint
