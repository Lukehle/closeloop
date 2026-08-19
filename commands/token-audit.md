---
description: Measure actual Claude Code token usage and report concrete cuts
---

# /token-audit

$ARGUMENTS

Run the **usage-audit** skill.

1. Execute `scripts/usage_audit.py` with any window given in `$ARGUMENTS` (default 7 days). Capture
   the exit code; `2` means no transcripts were found, not that usage was zero.
2. Report the actual token counts from the transcripts' usage blocks — input, output, cache-read,
   cache-creation — plus the cache-read share and the split by model.
3. Present the rankings: largest tool results, most re-read files, tool distribution, MCP calls by
   server.
4. Give only recommendations the measurements support. **Do not add generic efficiency advice.** If
   a dimension measured fine, say nothing about it.
5. Point to the specific `token-economics` technique that addresses the top finding.

Then: change one thing, work normally, re-run, and compare. Do not change three things at once —
that tells you nothing about which one worked.
