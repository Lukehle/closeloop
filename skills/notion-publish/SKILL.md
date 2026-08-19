---
name: notion-publish
description: Publish finance runbooks, close documentation, metric definitions, and change records into Notion under a stable single-writer zone contract, so automated updates never destroy human edits. Use when documenting a process, publishing a runbook, mirroring a close summary, or maintaining a definitions page that both people and automations touch. Trigger on "Notion", "publish the runbook", "document this process", "update the wiki", "close documentation", "metric definitions page".
---

# Notion publish

Notion is where finance documentation actually gets read, which makes it worth writing to properly.
It is also a shared surface where humans edit continuously, so the same invariant that governs
spreadsheets governs it: **one writer per zone.**

Load `finance-guardrails` — Rail 2 is the governing rule.

---

## The zone contract

An automation writes to **a named section within a page**, never to a whole page and never to a
database a human curates.

Mark the boundary in the document itself, so a human editing the page can see where they are:

```markdown
## Metric definitions

<!-- closeloop:zone:metric-definitions START - auto-generated, do not edit by hand -->
| Metric | Definition | Owner | Source |
|---|---|---|---|
| ARR | ... | FP&A | billing |
<!-- closeloop:zone:metric-definitions END -->

## Notes and open questions
<!-- human zone - automation never writes below this line -->
```

Rules:
- **Replace between the markers. Never touch anything outside them.**
- If the markers are missing, **stop**. Do not guess where the zone was; a wrong guess overwrites
  human writing. Ask, or create a fresh zone at the end of the page.
- One automation owns a zone. Two automations writing the same zone is the forbidden case.
- **Human zones are read-only to automation. Always.**
- Record the zone map in `ZONES.md` alongside the sheet zones — one map for all shared surfaces.

---

## What belongs in Notion

| Publish | Do not publish |
|---|---|
| Runbooks and process documentation | Raw financial data extracts |
| Metric definitions (the canonical list) | Anything from the `finance-guardrails` Rail 5 deny list |
| Close calendars and task ownership | Credentials, connection strings, tokens |
| Change records and decision logs | Large data dumps — link to the source instead |
| Close summaries and post-mortems | Duplicate copies of anything that lives elsewhere |
| Zone maps and system inventories | Individually-identifying compensation or customer detail |

**Notion is a search index and a knowledge surface, not a system of record.** If a figure matters,
it lives in the warehouse or the GL and Notion links to it. A number pasted into a wiki page is
stale the moment it lands and will be quoted back to you six months later.

---

## Runbook template

The document that determines whether an automation survives its author leaving:

```markdown
# Runbook: AR subledger-to-GL reconciliation

**Owner:** <name>   **Backup:** <name>   **Review by:** 2027-02-01
**Runs:** monthly, close day 3, 06:00 ET
**Zones written:** Sheets `Actuals!A1:M500`; Notion `closeloop:zone:ar-recon-status`

## What it does
One paragraph. What question it answers and what it produces.

## Inputs
| Source | Object | Access | Owner |
|---|---|---|---|
| NetSuite | AR aging saved search #1284 | SuiteQL, read-only | Accounting |
| BigQuery | finance.gl_summary | service account | Data |

## How to run it
Exact commands. Not a description of the commands.

## How to tell it worked
The tie-out block shows PASS and the control total matches the NetSuite AR aging
report exactly. Anything else is a failure, including a clean-looking run.

## When it fails
| Symptom | Likely cause | Fix |
|---|---|---|
| Row count BLOCK | period still open in NetSuite | wait for AP/AR lock, re-run |
| Control total variance | direct GL postings bypassing the subledger | query GL for non-subledger source entries |

## The manual fallback
What a human does if the automation is down on close day. This section is the
reason the runbook exists - write it as if the author is unreachable.

## Change history
| Date | Change | Record |
|---|---|---|
| 2026-08-19 | tolerance $0.01 -> $1.00 | CHG-2026-08-003 |
```

The **manual fallback** and **how to tell it worked** sections are the two that get skipped and the
two that matter. An automation with no documented fallback is a single point of failure with a
runbook attached.

---

## Writing discipline

1. **Read before writing.** Always. Someone may have edited inside your zone despite the marker; if
   so, preserve their text elsewhere on the page and flag it rather than deleting it.
2. **Never delete a page.** Archive it. Deletion in a shared workspace destroys other people's
   context, and Notion's trash is not an audit trail.
3. **Stamp the zone** with as-of and run id, same as any other automated write.
4. **Verify by reading back**, per `tie-out`. "The API returned 200" is not "the page says the right
   thing" — Notion block updates partially fail more often than you would expect.
5. **Keep it short.** A runbook nobody finishes is a runbook nobody follows.

---

## Degraded mode

**No Notion access:** emit publish-ready Markdown with the zone markers included, plus the target
page and section. A human pastes it into the zone. The contract still holds because it is written
into the document.

**Read-only access:** the same, plus a diff of what would change, so the human pasting it can see
the delta rather than re-reading the whole page.

The zone contract, the runbook template, and the read-before-write discipline are the skill. The API
is convenience.

---

## Related skills

- `finance-guardrails` — Rail 2, the zone invariant
- `sheets-bridge` — the same contract applied to spreadsheets; share one `ZONES.md`
- `pipeline-change-control` — change records that get published here
- `close-orchestrator` — close summaries and calendars
- `saas-metrics` — the canonical definitions this publishes
