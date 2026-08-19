---
description: Prove a number end-to-end against its source and the general ledger
---

# /tieout

$ARGUMENTS

Run the **tie-out** skill against the figure named in `$ARGUMENTS`.

1. **Declare scope and threshold first**, before looking at any result. Threshold-then-result means
   you tested something; result-then-threshold means you rationalized something.
2. Pull both sides **independently**. Deriving both from the same extract proves only that
   arithmetic works.
3. Foot each side to itself — detail to header, row counts reconciled after documented exclusions.
4. Compare; measure the variance in absolute and percentage terms.
5. Explain every difference above the investigation floor, item by item, with dates and amounts.
6. State what was **not** checked.
7. Emit the full tie-out block. The result is PASS, FAIL, or UNVERIFIED — nothing else.

If a script or query is involved, capture its exit code rather than piping it into a filter.

Do not widen a threshold to convert a FAIL into a PASS.
