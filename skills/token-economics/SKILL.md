---
name: token-economics
description: Cost and context discipline for running Claude Code on a managed Enterprise or Team seat - model routing under policy restrictions, cache-TTL discipline, context hygiene, subagent isolation, MCP tool-bloat trimming, and the data-tier hierarchy that keeps large financial extracts out of context entirely. Use when work is slow, expensive, hitting limits, or about to process a large dataset. Trigger on "token", "context", "expensive", "hitting limits", "usage limit", "slow", "compact", "too many tokens", "cost", "optimize the session", "large extract".
---

# Token economics

On a metered plan this is money. On a managed Enterprise seat it is **quota and admin-set spend
caps** — the constraint arrives as a limit you hit mid-close rather than an invoice, which is worse,
because it hits when you are busiest.

The rule that governs everything below:

> **Never put data into context that a script could reduce first.**

Finance work is unusually exposed here because the artifacts are large — GL extracts, aging reports,
transaction detail. A single careless read of a full-year GL can consume more context than an entire
close's worth of reasoning.

**Measure before optimizing.** Run `usage-audit` first; this skill is the doctrine, that one is the
instrument. Optimizing from intuition is how people spend an afternoon saving nothing.

---

## The data-tier hierarchy

Applies to every "look at this data" task. **Try tiers in order and stop at the first that works.**

| Tier | Method | Typical context cost |
|---|---|---|
| **1** | **Aggregate at source.** `GROUP BY` in the warehouse; return the 40 rows you need | tens of tokens |
| **2** | **Script it locally.** Python reduces the file and prints distilled JSON | ~100-300 tokens |
| **3** | **Targeted read.** `Grep`/`head` for the specific rows, never the whole file | hundreds |
| **4** | **Subagent.** Delegate the bulk read; only the conclusion returns to your context | the summary only |
| **5** | **Read it into context.** Only when the task genuinely needs every row | thousands to tens of thousands |

Worked example — "why did July opex jump?":

```
Tier 5 (wrong): read gl_july.csv (180,000 rows) into context
                -> tens of thousands of tokens, and the answer was 5 rows

Tier 1 (right): SELECT account, SUM(amount), COUNT(*)
                FROM gl WHERE period='2026-07' GROUP BY account
                HAVING ABS(SUM(amount) - prior) > 25000
                -> 6 rows. Then pull detail for only those accounts.
```

The cost difference is roughly two orders of magnitude, and the Tier 1 answer is *better* — it is
reproducible, it is a saved query artifact, and it applies the materiality gate mechanically instead
of by eye.

**Never paste a large extract into the conversation.** Write it to a file and process it. This is
the single highest-value habit in the skill.

---

## Model routing under policy

The general principle — cheap tier for mechanical work, capable tier pinned for review gates — has to
survive a seat where an admin may have restricted which models you can use.

| Work | Tier | If the seat is pinned to one model |
|---|---|---|
| Bulk extraction, formatting, renaming, mechanical edits | cheapest available | Use lower reasoning effort and tighter prompts |
| Building, analysis, ordinary close work | mid | This is the default; nothing changes |
| **Review gates** — anything that becomes a reported number | most capable available | **Compensate with process, not model**: run the check twice from different angles, or use `finance-quorum` |

**The review gate is the one place not to economize.** A wrong number costs more than every token
you saved getting to it. When policy prevents up-tiering for review, the correct substitute is
`finance-quorum` degraded mode — a structured adversarial self-review — not skipping the gate.

Do not set a global subagent-model override. It forces every subagent to one tier and defeats the
routing entirely.

---

## Cache discipline

**A cache read costs roughly a tenth of a fresh input token.** This is the largest single lever
available, and it is mostly about *not* doing things:

- **Do not reorder or edit early context.** The cache matches on a prefix — changing something near
  the start invalidates everything after it. Rewriting `CLAUDE.md` mid-session throws away the whole
  cached prefix.
- **Front-load the stable material** (instructions, definitions, schemas) and keep the volatile
  material late.
- **Long gaps break the cache.** Related work done in one sitting is materially cheaper than the same
  work spread across a day. For a close, that argues for working a phase through rather than dipping
  in and out.
- **Do not re-read files you have already read.** The harness tracks file state; re-reading a file
  you just edited pays full price for information you already have.

---

## Context hygiene

| Situation | Action |
|---|---|
| Finished a close phase, starting the next | `/clear`, then re-open `LEDGER.md`. The ledger exists precisely so context is disposable |
| Long session, still on the same task | `/compact` at a natural boundary you choose, rather than letting it happen mid-reconciliation |
| Exploratory dead end | `/clear` — abandoned exploration is pure carry cost |
| About to process a big dataset | Reduce it first (tiers above), do not clear-and-reload |

**Compact at a boundary you choose.** An automatic compaction mid-reconciliation can lose the
half-built state; a deliberate one between phases loses nothing, because the ledger holds the state.
This is another reason `close-orchestrator` is ledger-driven.

**Clearing is only safe once state is externalized.** These two skills pull in opposite directions
and both are right: this one says keep context small, `context-durability` says do not lose state.
They reconcile in one move — checkpoint to disk, then clear freely. Without a checkpoint you end up
hoarding context to avoid losing it, which is slower, more expensive, *and* still loses everything
the moment compaction fires anyway. Read `context-durability` before any long run.

---

## MCP and tool bloat

Every connected MCP server's tool definitions sit in context for the whole session, whether used or
not. On a heavily-connected setup this is a large fixed cost paid on every single request.

- **Disconnect servers you are not using this session.** Check with `/context`.
- Prefer deferred tool loading where the harness supports it — schemas load on demand.
- When loading deferred tools, **batch them into one call**. Each separate lookup is a wasted
  round-trip.
- A server with 40 tools you use 2 of is a bad trade; ask whether a script would do.

---

## Skills are a saving, not a cost

Counter-intuitive but load-bearing: **a skill body only enters context when invoked.** The resident
cost of an installed skill is its one-line description in the index.

So a well-scoped skill *reduces* tokens — it gets the right approach on the first attempt instead of
three exploratory passes. The optimization is not "install fewer skills"; it is:

- Keep skill **descriptions** tight — those are always resident
- Keep skill **bodies** focused; push depth into `references/` that load only when needed
- Delete skills you never invoke — they cost an index line and add routing ambiguity

---

## Subagent isolation

A subagent's tool output stays in the subagent's context. Only its conclusion returns to yours.

Use one when: scanning many files for a pattern, reading a large extract to answer a specific
question, or running an independent verification pass. Do not use one when: the task is small, or you
need the intermediate detail — you will pay to have it re-explained.

---

## Anti-patterns

| Anti-pattern | Cost | Instead |
|---|---|---|
| Reading a full GL extract into context | Enormous | Aggregate at source (Tier 1) |
| Re-reading a file after editing it | Full re-read | The edit already succeeded or it errored |
| Pasting a CSV into the conversation | Enormous, and unreproducible | Write to a file, script it |
| Keeping every MCP server connected | Fixed cost per request | Disconnect unused |
| Letting auto-compaction fire mid-task | Lost state, re-derivation | Compact deliberately at a boundary |
| Re-deriving what the ledger already records | Repeated every session | Read the ledger |
| "Be more efficient" as a plan | Zero, achieves nothing | Run `usage-audit`, fix the top item |

---

## Degraded mode

Every technique here is procedural. `/clear`, `/compact`, and `/context` are core commands, not
capabilities an admin removes. If model routing is restricted, the compensating control is process —
verify twice, use `finance-quorum` — rather than accepting a weaker review.

---

## Related skills

- `usage-audit` — measure first; this skill is doctrine, that one is the instrument
- `warehouse-sql` — Tier 1 in practice, and the same aggregate-at-source logic for warehouse cost
- `finance-quorum` — the review-gate substitute when up-tiering is not permitted
- `close-orchestrator` — the ledger that makes context disposable
