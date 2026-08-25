#!/usr/bin/env python3
"""Blocking data-quality gate for the closeloop data-quality-gate skill.

Runs the seven boundary checks against a CSV extract using thresholds declared
up front in a config file, and exits non-zero when the data must not proceed.

Thresholds are declared in config, never inferred from the data being checked -
a gate that derives its own thresholds from the sample it is testing cannot fail.

Usage:
    python dq_check.py --data extract.csv --config dq/ar_extract.yaml \\
        [--prior runs/2026-06/extract.csv] [--dim customer_id=dim_customer.csv]

Exit codes:
    0  PASS   - every check within threshold
    1  WARN   - anomalies recorded, data may proceed
    2  BLOCK  - a check failed; the pipeline must stop
    3  ERROR  - the gate itself could not run (missing file, bad config)

Config is YAML when PyYAML is available, and JSON otherwise - the same key
names work in both, so a locked-down seat with no PyYAML loses nothing.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from collections import Counter
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation

PASS, WARN, BLOCK = "PASS", "WARN", "BLOCK"


def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        text = fh.read()
    if path.endswith((".yaml", ".yml")):
        try:
            import yaml
        except ImportError:
            raise RuntimeError(
                "ERROR: config is YAML but PyYAML is unavailable. Convert the config "
                "to JSON (same keys) or install PyYAML.")
        return yaml.safe_load(text)
    return json.loads(text)


def read_csv(path: str) -> tuple[list[str], list[dict]]:
    with open(path, "r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        rows = list(reader)
        return (reader.fieldnames or []), rows


def to_decimal(raw: str | None) -> Decimal | None:
    """Parse a spreadsheet-formatted number. Returns None if not parseable.

    Handles currency symbols, thousands separators, and accounting negatives
    written as (1,234.56) - all of which arrive as text from real extracts.
    """
    if raw is None:
        return None
    s = str(raw).strip()
    if s == "":
        return None
    neg = s.startswith("(") and s.endswith(")")
    if neg:
        s = s[1:-1]
    s = s.replace("$", "").replace(",", "").replace(" ", "").strip()
    if s in ("", "-"):
        return None
    try:
        value = Decimal(s)
    except InvalidOperation:
        return None
    return -value if neg else value


def parse_date(raw: str | None) -> date | None:
    if not raw:
        return None
    s = str(raw).strip()[:10]
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


class Gate:
    def __init__(self) -> None:
        self.results: list[dict] = []

    def add(self, verdict, check, detail, **extra):
        self.results.append({"verdict": verdict, "check": check,
                             "detail": detail, **extra})

    @property
    def verdict(self) -> str:
        verdicts = {r["verdict"] for r in self.results}
        if BLOCK in verdicts:
            return BLOCK
        if WARN in verdicts:
            return WARN
        return PASS


def check_row_count(gate: Gate, rows: list[dict], cfg: dict) -> bool:
    n = len(rows)
    if n == 0:
        gate.add(BLOCK, "row_count",
                 "extract is empty - far more often a broken query, a permissions "
                 "failure, or a wrong date filter than a genuinely empty period",
                 actual=0)
        return False
    bounds = cfg.get("row_count")
    if not bounds:
        gate.add(PASS, "row_count", f"{n} rows (no bounds configured)", actual=n)
        return True
    lo, hi = bounds.get("min"), bounds.get("max")
    if (lo is not None and n < lo) or (hi is not None and n > hi):
        gate.add(BLOCK, "row_count",
                 f"{n} rows outside expected bounds [{lo}, {hi}]", actual=n)
        return False
    gate.add(PASS, "row_count", f"{n} rows within [{lo}, {hi}]", actual=n)
    return True


def check_control_total(gate: Gate, rows: list[dict], cfg: dict) -> None:
    spec = cfg.get("control_total")
    if not spec:
        return
    col = spec["column"]
    total = Decimal("0")
    unparseable = 0
    for r in rows:
        v = to_decimal(r.get(col))
        if v is None:
            unparseable += 1
        else:
            total += v
    if unparseable:
        gate.add(BLOCK, "control_total",
                 f"{unparseable} row(s) have an unparseable {col}; the total is "
                 f"understated by an unknown amount", unparseable=unparseable)
        return
    expected = spec.get("expected")
    if expected is None:
        gate.add(WARN, "control_total",
                 f"sum({col}) = {total} - no expected value configured, so this is "
                 f"recorded but not verified", actual=str(total))
        return
    expected = Decimal(str(expected))
    tol = Decimal(str(spec.get("tolerance", 0)))
    diff = abs(total - expected)
    if diff > tol:
        gate.add(BLOCK, "control_total",
                 f"sum({col}) = {total}, expected {expected}, variance {diff} "
                 f"exceeds tolerance {tol}",
                 actual=str(total), expected=str(expected), variance=str(diff))
    else:
        gate.add(PASS, "control_total",
                 f"sum({col}) = {total} matches source within {tol}",
                 actual=str(total))


def check_duplicates(gate: Gate, rows: list[dict], cfg: dict) -> None:
    grain = cfg.get("grain")
    if not grain:
        return
    keys = Counter(tuple(r.get(c, "") for c in grain) for r in rows)
    dupes = {k: v for k, v in keys.items() if v > 1}
    if dupes:
        sample = list(dupes.items())[:5]
        gate.add(BLOCK, "duplicate_keys",
                 f"{len(dupes)} duplicated key(s) on grain {grain} - a fan-out join "
                 f"or an append-instead-of-replace re-run. Sample: {sample}",
                 duplicate_count=len(dupes))
    else:
        gate.add(PASS, "duplicate_keys", f"grain {grain} unique across {len(rows)} rows")


def check_not_null(gate: Gate, rows: list[dict], cfg: dict) -> None:
    cols = cfg.get("not_null", [])
    join_keys = set(cfg.get("grain", []) or []) | set(cfg.get("join_keys", []) or [])
    for col in cols:
        nulls = sum(1 for r in rows if not str(r.get(col, "")).strip())
        if not nulls:
            gate.add(PASS, "not_null", f"{col}: no nulls")
            continue
        if col in join_keys:
            gate.add(BLOCK, "not_null",
                     f"{col}: {nulls} null(s) in a join key - these rows will vanish "
                     f"silently in the next join rather than error", nulls=nulls)
        else:
            gate.add(BLOCK, "not_null",
                     f"{col}: {nulls} null(s); SUM skips nulls so downstream totals "
                     f"will be quietly short", nulls=nulls)


def check_period(gate: Gate, rows: list[dict], cfg: dict) -> None:
    spec = cfg.get("period")
    if not spec:
        return
    col = spec["column"]
    start, end = parse_date(spec.get("start")), parse_date(spec.get("end"))
    if not (start and end):
        gate.add(WARN, "period", "period bounds not parseable; skipped")
        return

    seen: set[date] = set()
    outside = 0
    unparseable = 0
    for r in rows:
        d = parse_date(r.get(col))
        if d is None:
            unparseable += 1
            continue
        if d < start or d >= end:      # half-open interval, deliberately
            outside += 1
        else:
            seen.add(d)

    if unparseable:
        gate.add(BLOCK, "period",
                 f"{unparseable} row(s) have an unparseable {col}", unparseable=unparseable)
    if outside:
        gate.add(BLOCK, "period",
                 f"{outside} row(s) fall outside [{start}, {end}) - check the date "
                 f"column used and the timezone conversion", outside=outside)

    expected_days = {start + timedelta(days=i) for i in range((end - start).days)}
    missing = sorted(expected_days - seen)
    if missing:
        shown = [d.isoformat() for d in missing[:10]]
        gate.add(WARN, "period",
                 f"{len(missing)} calendar day(s) with no rows: {shown}"
                 f"{' ...' if len(missing) > 10 else ''} - confirm these are genuinely "
                 f"non-business days", missing_days=len(missing))
    elif not outside and not unparseable:
        gate.add(PASS, "period",
                 f"all {len(expected_days)} days in [{start}, {end}) present")


def check_referential(gate: Gate, rows: list[dict], dims: dict[str, str], cfg: dict) -> None:
    amount_col = (cfg.get("control_total") or {}).get("column")
    for col, dim_path in dims.items():
        if not os.path.exists(dim_path):
            gate.add(BLOCK, "referential_integrity",
                     f"dimension file for {col} not found: {dim_path}")
            continue
        _, dim_rows = read_csv(dim_path)
        valid = {str(r.get(col, "")).strip() for r in dim_rows}
        orphan_rows = [r for r in rows
                       if str(r.get(col, "")).strip() and
                       str(r.get(col, "")).strip() not in valid]
        if not orphan_rows:
            gate.add(PASS, "referential_integrity", f"{col}: all values resolve")
            continue
        value = Decimal("0")
        if amount_col:
            for r in orphan_rows:
                v = to_decimal(r.get(amount_col))
                if v is not None:
                    value += v
        gate.add(BLOCK, "referential_integrity",
                 f"{col}: {len(orphan_rows)} orphan row(s)"
                 + (f" worth {value}" if amount_col else "")
                 + " - either a dimension that has not loaded yet, or bad source data",
                 orphans=len(orphan_rows), orphan_value=str(value))


def check_drift(gate: Gate, rows: list[dict], header: list[str],
                prior_path: str | None, cfg: dict) -> None:
    if not prior_path:
        return
    if not os.path.exists(prior_path):
        gate.add(WARN, "drift", f"prior run not found at {prior_path}; drift not checked")
        return

    prior_header, prior_rows = read_csv(prior_path)

    new_cols = [c for c in header if c not in prior_header]
    gone_cols = [c for c in prior_header if c not in header]
    if new_cols or gone_cols:
        gate.add(BLOCK, "drift",
                 f"schema changed - added {new_cols}, removed {gone_cols}. The data "
                 f"contract changed and nobody said so",
                 added=new_cols, removed=gone_cols)

    max_pct = Decimal(str((cfg.get("drift") or {}).get("max_pct", 20)))

    def pct_change(now: Decimal, before: Decimal) -> Decimal | None:
        if before == 0:
            return None
        return (now - before) / before * 100

    rc = pct_change(Decimal(len(rows)), Decimal(len(prior_rows)))
    if rc is not None:
        verdict = BLOCK if abs(rc) > max_pct else PASS
        gate.add(verdict, "drift",
                 f"row count {len(prior_rows)} -> {len(rows)} ({rc:+.1f}%)",
                 pct=float(rc))

    spec = cfg.get("control_total")
    if spec:
        col = spec["column"]
        def total(rs):
            t = Decimal("0")
            for r in rs:
                v = to_decimal(r.get(col))
                if v is not None:
                    t += v
            return t
        ct = pct_change(total(rows), total(prior_rows))
        if ct is not None:
            verdict = BLOCK if abs(ct) > max_pct else PASS
            gate.add(verdict, "drift", f"sum({col}) {ct:+.1f}% vs prior run",
                     pct=float(ct))

    for col in (cfg.get("drift") or {}).get("distinct_columns", []):
        now_n = len({str(r.get(col, "")) for r in rows})
        before_n = len({str(r.get(col, "")) for r in prior_rows})
        dc = pct_change(Decimal(now_n), Decimal(before_n))
        if dc is not None:
            verdict = BLOCK if abs(dc) > max_pct else PASS
            gate.add(verdict, "drift",
                     f"distinct {col} {before_n} -> {now_n} ({dc:+.1f}%)", pct=float(dc))


def main() -> int:
    ap = argparse.ArgumentParser(description="closeloop blocking data-quality gate")
    ap.add_argument("--data", required=True, help="CSV extract to validate")
    ap.add_argument("--config", required=True, help="YAML or JSON threshold config")
    ap.add_argument("--prior", help="prior-run CSV for drift comparison")
    ap.add_argument("--dim", action="append", default=[],
                    metavar="COL=dim.csv",
                    help="referential check, repeatable (e.g. customer_id=dim_customer.csv)")
    args = ap.parse_args()

    try:
        cfg = load_config(args.config)
        if not isinstance(cfg, dict):
            raise ValueError("config root must be an object/mapping")
        header, rows = read_csv(args.data)

        dims: dict[str, str] = {}
        for pair in args.dim:
            if "=" not in pair:
                raise ValueError(f"--dim expects COL=path, got {pair!r}")
            col, path = pair.split("=", 1)
            dims[col] = path

        gate = Gate()

        # Check 1 gates the rest: every later check is meaningless on an empty or
        # wrong-sized extract, so stop here rather than emit misleading passes.
        if check_row_count(gate, rows, cfg):
            check_control_total(gate, rows, cfg)
            check_duplicates(gate, rows, cfg)
            check_referential(gate, rows, dims, cfg)
            check_period(gate, rows, cfg)
            check_not_null(gate, rows, cfg)
            check_drift(gate, rows, header, args.prior, cfg)

        report = {
            "data": args.data,
            "rows": len(rows),
            "verdict": gate.verdict,
            "checks": gate.results,
        }
        print(json.dumps(report, indent=2))

        counts = Counter(r["verdict"] for r in gate.results)
        print(f"\n# {gate.verdict}: {counts[PASS]} pass, {counts[WARN]} warn, "
              f"{counts[BLOCK]} block", file=sys.stderr)
        if gate.verdict == BLOCK:
            print("# Pipeline must stop. A BLOCK is cleared by a human who understands "
                  "the cause and records the override - not by re-running.", file=sys.stderr)

        return {PASS: 0, WARN: 1, BLOCK: 2}[gate.verdict]
    except Exception as exc:  # noqa: BLE001 - fail closed on invalid gate/config
        print(f"ERROR: gate could not run: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
