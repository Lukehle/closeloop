---
name: sheets-bridge
description: Treat Google Sheets (or Excel) as a real finance interface rather than a dumping ground - schema pinning, single-writer-per-range zone contracts, never overwriting human-entered cells, versioned snapshots, and safe pull/push patterns. Use when reading from or writing to a spreadsheet that humans also edit. Trigger on "Google Sheets", "push to the sheet", "update the tab", "read the spreadsheet", "the sheet broke", "someone overwrote", "sync to sheets", "export to Excel".
---

# Sheets bridge

Spreadsheets are where finance actually works, and they are also the most fragile integration
surface in the stack: no schema enforcement, no transactions, last-write-wins, and a human editing
the same file at the same time as your automation.

Every rule here exists to stop the same failure: **an automation silently destroying work a human
did.** That failure is usually discovered weeks later, and by then the original values are gone.

Load `finance-guardrails` — Rail 2 (single writer per zone) is the governing rule here, and this
skill is its most important application.

---

## The zone contract

**Before writing anything, declare the zone.** A zone is a specific named range or tab, never a file.

Record it where the next person will find it — a `ZONES.md` in the automation repo, and a header
comment in the sheet itself:

```markdown
# Zone map - FY26 Reporting Workbook

| Zone | Owner | Written by | Cadence | Humans may edit? |
|---|---|---|---|---|
| `Actuals!A1:M500` | finance-automation | close pipeline | monthly, day 4 | NO - overwritten |
| `Actuals!N:R` | Controller | humans | ad hoc | YES - never touched by automation |
| `Budget!A1:M500` | FP&A | humans | quarterly | YES - read-only to automation |
| `Metrics!A1:H80` | finance-automation | metrics refresh | daily 06:00 | NO - overwritten |
| `Commentary!A:D` | Controller | humans | monthly | YES - read-only to automation |
```

Rules:
- **One automated writer per zone. Never two.** There is no locking mechanism in the Sheets API, so
  zone separation *is* the mutex.
- **An automation-owned zone is fully owned.** It gets overwritten wholesale; humans are told not to
  edit it, and the sheet says so in row 1.
- **A human-owned zone is read-only to automation. Always.** No exceptions, no "just this once".
- **Never write to an undeclared zone.** If a zone has no recorded owner, claim it explicitly before
  writing, and add it to the map.

### Make ownership visible in the sheet

Automation-owned tabs get a banner in row 1 and a distinct tab colour:

```
A1: ⚠ AUTO-GENERATED - overwritten by the close pipeline on day 4. Do not edit.
    Last written 2026-08-19T06:00Z | run 2026-08-close | source bq://finance.gl_summary
```

A person who edits an automation-owned cell has been warned in the only place they were ever going
to look.

---

## Schema pinning

Column position is not a contract. Someone will insert a column, and every position-based read
silently shifts by one — producing wrong numbers rather than an error, which is the worst kind of
failure.

**Read by header name, and validate the header row before reading a single value:**

```python
EXPECTED = ["period", "account", "account_name", "amount_usd", "entity"]

header = rows[0]
missing = [c for c in EXPECTED if c not in header]
extra   = [c for c in header if c not in EXPECTED]
if missing:
    raise SystemExit(f"SCHEMA DRIFT: missing columns {missing}. Refusing to read.")
if extra:
    print(f"WARNING: unexpected columns {extra} - reading by name, ignoring these")

idx = {name: header.index(name) for name in EXPECTED}
# ... use idx["amount_usd"], never rows[i][3]
```

**Fail loudly on drift. Never guess.** A read that silently adapts to a changed schema will produce a
plausible wrong number, and plausible wrong numbers are the ones that reach a board deck.

---

## Reading: the traps

| Trap | What happens | Defence |
|---|---|---|
| **Formatted numbers as strings** | `"$1,234.56"` and `"(500)"` arrive as text | Parse explicitly: strip `$`, `,`, and convert `(x)` to `-x`. Never `float()` blindly |
| **Locale decimals** | `1.234,56` in a European locale | Read the raw unformatted value where the API offers it |
| **Dates as serial numbers** | `45678` instead of a date | Request unformatted values and convert with the sheet's epoch |
| **Merged cells** | Only the top-left holds a value; the rest are empty | Detect merges and forward-fill deliberately, or reject the range |
| **Hidden rows** | Filtered-out rows still come back in an API read | Decide explicitly whether they are in scope — usually they are |
| **Trailing blank rows** | Thousands of empty rows past the data | Bound the read to the last populated row |
| **Error cells** | `#REF!` arrives as a string, sums to nothing | Scan for error values and fail; do not treat them as zero |
| **Precision** | Sheets carries ~15 significant digits | Do currency arithmetic in the warehouse or in Python `Decimal`, not in the sheet |

---

## Writing: the discipline

1. **Snapshot before writing.** Copy the target range to an archive tab or a versioned file first.
   Cheap insurance, and the only thing that saves you when a write goes wrong.
2. **Write the whole zone, not scattered cells.** One batch update to a declared range is atomic in
   practice and reviewable; a hundred single-cell writes half-fail and leave the sheet inconsistent.
3. **Never `clear()` a tab that contains a human zone.** Clear only your declared range.
4. **Stamp every write.** As-of, run id, and source, in the banner. Per `finance-guardrails` Rail 3,
   a figure without an as-of is unfalsifiable.
5. **Verify by reading back.** Per `tie-out`, "the write returned 200" is not "the sheet has the
   right values." Read the range back and check the control total against what you intended to
   write. This catches range-offset errors, partial writes, and type coercion.

```python
resp = write_range(sheet_id, "Actuals!A1:M500", values)
readback = read_range(sheet_id, "Actuals!A1:M500")
written_total = sum_column(readback, "amount_usd")
if abs(written_total - intended_total) > Decimal("0.01"):
    raise SystemExit(
        f"WRITE VERIFY FAILED: sheet holds {written_total}, intended {intended_total}")
```

---

## Versioning

Sheets version history is not an audit trail — it is not queryable, not exportable in bulk, and it
expires. For anything a control depends on:

```
sheets-snapshots/
  2026-07/Actuals_2026-08-04T060012Z.csv
  2026-07/Metrics_2026-08-04T060012Z.csv
```

Snapshot before each automated write and after each close. When someone asks in November what the
sheet said on August 4th, this is the only thing that can answer.

---

## When a sheet should not be the interface

Push back when a spreadsheet is the wrong tool. Move to the warehouse when:

- Row count exceeds ~50,000 (performance and precision both degrade)
- Multiple people write concurrently to overlapping ranges
- The data feeds a control that must be reproducible years later
- The same transformation is rebuilt by hand each period
- Formulas have grown past the point where anyone can audit them (see `model-audit`)

A spreadsheet is an excellent *interface* to warehouse data. It is a poor *system of record*.

---

## Degraded mode

**No Sheets API access:** produce a CSV plus explicit import instructions naming the exact target
range, and state the control total the person should see after import so they can verify it landed
correctly. The zone contract still applies — say which range they are authorised to overwrite.

**Excel instead of Sheets:** every rule transfers unchanged. Use named ranges as the zone mechanism
and `openpyxl` for programmatic access; see `model-audit` for workbook integrity.

**Read-only access:** the reading traps and schema pinning still apply. Writes become staged CSV
outputs for a human to import, per `finance-guardrails` Rail 1.

---

## Related skills

- `finance-guardrails` — Rail 2, the zone invariant
- `tie-out` — the read-back verification pattern
- `warehouse-sql` — where the data should live if the sheet is straining
- `data-quality-gate` — validating sheet data before it feeds anything
- `model-audit` — auditing the formulas already in the workbook
