---
name: model-audit
description: Audit a spreadsheet or financial model for correctness defects - hardcoded constants inside formula rows, inconsistent formulas across a row, broken references, circular dependencies, sign-convention violations, unprotected inputs, and error values. Runs deterministic mechanical checks first via openpyxl, then reasoned review of what the machine cannot see. Use before trusting, inheriting, shipping, or building on any workbook. Trigger on "audit this model", "check this spreadsheet", "review the model", "is this model right", "inherited a workbook", "formula errors", "model integrity", "xlsx review".
---

# Model audit

Spreadsheet errors are not rare and they are not random. Decades of field audits put the rate of
material errors in operational spreadsheets high enough that "assume defects until proven otherwise"
is the correct default. The defects also cluster into a small taxonomy, which means most of them are
mechanically detectable.

**Order of operations: machine first, human second.** Run the deterministic checks before reading
any formulas. Reasoning about a model you have not mechanically scanned wastes the expensive pass on
things a script finds for free — and misses the ones you would never notice by eye.

---

## Step 1 — Mechanical scan

```bash
python scripts/audit_workbook.py path/to/model.xlsx > audit.json 2>audit.err; status=$?
echo "exit=$status"; head -5 audit.err
```

Capture the exit code. Exit `0` = clean, `1` = findings, `2` = could not read the file. Per
`tie-out`, never pipe this into a filter that swallows the status.

The script reports, per sheet:

| Check | Defect it catches |
|---|---|
| `hardcode_in_formula_row` | A typed constant sitting in a row that is otherwise formulas — the single most common material defect |
| `inconsistent_row_formula` | One cell in a row whose formula structure differs from its neighbours |
| `error_values` | `#REF!`, `#VALUE!`, `#DIV/0!`, `#N/A`, `#NAME?`, `#NUM!`, `#NULL!` |
| `external_link` | Formulas pointing at other workbooks — a silent staleness source |
| `cross_sheet_density` | Sheets with unusually heavy cross-sheet references (fragility signal) |
| `merged_cells` | Merged ranges inside data regions (breaks references and sorting) |
| `hidden_content` | Hidden rows, columns, and sheets — where things get buried |
| `volatile_functions` | `INDIRECT`, `OFFSET`, `TODAY`, `NOW`, `RAND` — non-reproducible or slow |
| `no_protection` | Input cells indistinguishable from calculated cells |
| `deep_nesting` | Formulas nested past a readable depth |

Findings come back with sheet, cell, severity, and the formula text.

---

## Step 2 — Reasoned review

The machine cannot judge whether a model is *correct*, only whether it is *well-formed*. This pass
covers what needs judgment.

### Structure

- [ ] **One assumption, one cell.** Any assumption entered twice will eventually disagree.
      Cross-check duplicated constants across sheets.
- [ ] **Inputs, calculations, and outputs are visually distinguishable** — by colour convention,
      by sheet, or both. If you cannot tell an input from a formula at a glance, neither can the next
      person, and they will overwrite one.
- [ ] **Historicals are locked and not formula-driven** off forward assumptions.
- [ ] **Time axis is consistent.** Every schedule runs on the same period grid in the same direction.
      A schedule that runs left-to-right against a model that runs top-to-bottom is a joins-waiting-
      to-break.

### Logic

- [ ] **Sign conventions declared and honoured.** Expenses positive-and-subtracted or
      negative-and-added — one convention, stated, never mixed within a statement.
- [ ] **Growth rates apply to the right base.** A rate applied to a total when it should apply to a
      component is a classic silent error.
- [ ] **Circularity is explicit.** Broken by design (interest on opening or average balance) or
      controlled with a documented iterative switch and a convergence check.
- [ ] **No plugs.** A balancing figure with no derivation is a concealment, not a fix.
- [ ] **Edge cases behave.** Zero denominators, negative balances, a period with no activity, the
      first and last periods of the model.

### Financial correctness

- [ ] The balance check, RE roll, and cash-flow tie all hold — run `three-statement`.
- [ ] Metric formulas match their written definitions — run `saas-metrics`.
- [ ] Any figure claimed to come from the GL actually ties — run `tie-out`.

### Stress tests

Change one input at a time and confirm the model responds sensibly:

| Test | Expected |
|---|---|
| Set growth to 0% | Revenue flat; the model still balances |
| Set growth to -50% | No `#DIV/0!`; cash goes negative rather than breaking |
| Set headcount to 0 | Personnel cost to zero; nothing else moves |
| Push out one period | Every schedule extends; no hardcoded end dates |
| Zero out a whole segment | Consolidation still foots |

A model that only works in its base case is a base case with formulas around it.

---

## Severity

| Severity | Definition | Action |
|---|---|---|
| **Critical** | Produces a wrong number that a decision would rely on — hardcode in a formula row, `#REF!` in a live path, a plug, broken statement linkage | Do not use the model until fixed |
| **High** | Correct today, fragile — inconsistent row formulas, external links, undocumented circularity | Fix before the next cycle |
| **Medium** | Maintainability and review cost — merged cells, hidden sheets, deep nesting, no protection | Fix opportunistically |
| **Low** | Style — naming, formatting, layout | Note only |

Report `Critical` findings first, with the cell reference and the formula text. A finding without a
cell reference is not actionable.

---

## Output

```
MODEL AUDIT | FY26_Operating_Model_v14.xlsx | 2026-08-19T14:20Z
Sheets 11 | formula cells 42,880 | mechanical findings 23

CRITICAL (3)
  Revenue!K44   hardcode 1,250,000 in a formula row (J44,L44 are =J43*(1+J$8))
                -> Q4 revenue does not respond to the growth assumption
  Cashflow!D18  =#REF!+D17
  Model balances only because Balance!F60 contains =F58-F59 (a plug)

HIGH (7)
  Opex!M22      formula differs from the rest of row 22 (SUM range stops at M21)
  3 external links to \\fileserver\shared\FY25_Model.xlsx (stale since 2026-02)
  ... (4 more)

MEDIUM (13) / LOW (0)   - see audit.json

REASONED REVIEW
  Sign convention mixed on the Opex sheet (rows 10-24 negative, 25-40 positive,
    both subtracted in the roll-up) -> Opex understated by 2x rows 25-40 = $1.88M
  Stress test "growth = 0%": PASS
  Stress test "growth = -50%": FAIL - Metrics!C12 divides by new customers, no guard

VERDICT  Do not use for decisions until the 3 Critical and the sign-convention
         finding are resolved.
```

---

## Checkpointing a large audit

The mechanical scan already checkpoints itself — it writes `audit.json`, which survives anything.
**Run it to a file, not to the conversation**, and read findings from the file. That single habit
removes most of the compaction risk in this skill.

The reasoned pass is the fragile part. Per `context-durability`:

- Work the structure / logic / financial-correctness sections **one at a time**, writing findings to
  a file as you close each one, including "nothing found in this section."
- Record each **stress test result as you run it**. A stress test you believe you ran is not a
  stress test.
- On a multi-sheet workbook, keep the sheet list with its completion state. "I reviewed the opex
  sheet" is exactly the bookkeeping a summary drops.

If you resume an audit and cannot tell which reasoned sections completed, redo them. Unlike a
reconciliation, re-reviewing is idempotent and cheap — the only cost is time, and the alternative is
a verdict that claims coverage it does not have.

---

## Degraded mode

**No Python or no openpyxl:** work through the taxonomy manually in this order, which front-loads the
highest-yield checks: (1) select all formula cells and look for constants — in Excel,
`F5 → Special → Formulas`, then compare against `Constants`; (2) trace precedents on every total;
(3) `Ctrl+~` to reveal all formulas and scan each row for structural breaks; (4) `Edit → Links` to
find external references; (5) unhide everything and re-scan.

**Google Sheets:** the same taxonomy applies. Export to `.xlsx` and run the script, or use
`Ctrl+~` and the manual order above.

The script is convenience. The taxonomy and the severity model are the skill.

---

## Related skills

- `three-statement` — statement-level integrity checks
- `saas-metrics` — verifying metric formulas against written definitions
- `tie-out` — proving model outputs against source data
- `data-quality-gate` — validating the data feeding the model
