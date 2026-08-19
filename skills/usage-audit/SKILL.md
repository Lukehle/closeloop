---
name: usage-audit
description: Measure actual Claude Code usage from local session data and report concrete numbers - largest token sinks, which tools and files dominate, session and message counts, MCP overhead, and the specific changes that would cut the most. Produces measurements, never generic efficiency advice. Use before optimizing anything, when hitting usage limits, or to find out where the cost actually goes. Trigger on "token audit", "where are my tokens going", "usage audit", "why am I hitting limits", "measure my usage", "what's expensive", "/token-audit".
---

# Usage audit

**Measure, then optimize.** Optimizing from intuition reliably targets the wrong thing — people cut
the habit that feels wasteful rather than the one that is expensive.

This skill reads your own local session transcripts and reports numbers. It contains no advice that
is not derived from a measurement. If it cannot measure something, it says so rather than
substituting a guess.

---

## Run it

```bash
python scripts/usage_audit.py > usage.json 2>usage.err; status=$?
echo "exit=$status"; head -3 usage.err
```

Options:

```
--days N          look back N days (default 7)
--project PATH    audit one project namespace only
--top N           how many entries per ranking (default 15)
--sessions-dir P  override the transcript location
```

Exit codes: `0` report produced, `2` no transcripts found. Capture the status — per `tie-out`,
piping this into a filter throws away the signal.

---

## What it measures

All of it comes from local session transcript files, so it reflects **your** behaviour rather than
a generic profile.

| Measurement | What it tells you |
|---|---|
| **Actual tokens** — input, output, cache-read, cache-creation | Taken from each assistant message's usage block. These are real counts, not estimates |
| **Cache-read share of cacheable input** | The biggest single cost lever. A low share means early context is being invalidated or work is too spread out |
| **Tokens by model** | Whether routing is actually happening, or everything is running on one tier |
| **Largest tool results** | What fills context. Ranked, and linked back to the tool and target that produced each |
| Concentration of tool-result volume | Whether one read is the problem or the volume is diffuse — these need different fixes |
| Tool-call distribution | A `Read`-heavy profile suggests missed Tier 1/2 opportunities |
| **Most re-read files** | Re-reading a file you already read is pure waste |
| MCP calls by server | Whether connected servers earn their fixed context cost |

Token counts come from the transcripts' own usage blocks, so they are **actual**, not inferred.

The one exception is tool-result sizes: a tool result has no usage block of its own, so those are
estimated from character counts at roughly 4 characters per token and are labelled as estimates.
They are reliable for *ranking* — which is all you need to decide what to fix — and should not be
quoted as costs.

---

## Reading the report

Work top-down and **fix one thing at a time**, then re-measure. Fixing three things at once tells
you nothing about which one worked.

```
USAGE AUDIT | 7 days | 34 sessions | 4,182 tool calls

ACTUAL TOKENS (from transcript usage blocks, not estimates)
  input                  695,886
  cache creation     157,909,935
  cache read       6,226,822,363   (98% of cacheable input)
  output              17,643,007

TOKENS BY MODEL
  claude-fable-5      out 11,691,751   cache_read 4,040,136,028
  claude-opus-5       out  3,044,612   cache_read   916,419,417
  claude-sonnet-5     out  2,906,644   cache_read 1,270,266,918

LARGEST TOOL RESULTS (estimated tokens; these fill context)
   1. ~48,200  Read   gl_extract_2026-07.csv
   2. ~31,400  Bash   bq query (full result printed)
   3. ~22,900  Read   FY26_Model.xlsx

MOST-READ FILES
  228x  execution.rs
   88x  DECISIONS.md

RECOMMENDATIONS (each derived from a measurement above)
  1. Tool-result volume is diffuse: 41 results exceeded 20,000 chars but the top
     10 are only 2% of the total. No single read is the problem, so look at
     repetition rather than at individual large reads.
  2. 'execution.rs' was read 228 times in the window. Re-reading a file you have
     already read (or just edited) pays full price for information already in
     context.
```

**Every recommendation is conditional on its measurement.** The report will not tell you to fix the
largest reads when the largest reads are 2% of volume — a concentrated head and diffuse volume are
different problems with different fixes, and asserting a priority the data contradicts is exactly
the failure this skill exists to avoid.

Note in the example above: a 98% cache-read share is healthy, and no recommendation fires about it.
Silence on a dimension means it measured fine.

---

## What it deliberately does not do

- **No generic advice.** "Be concise", "use fewer tokens", "batch your calls" — none of that is here
  unless a measurement produced it.
- **No cost figures in currency.** Token estimates are approximate and pricing varies by plan and
  model; converting an estimate to dollars manufactures false precision.
- **No content is read or reported.** The script measures sizes and counts. It does not extract,
  store, or report the contents of your sessions — which matters, because finance transcripts contain
  financial data.

---

## The measurement loop

1. Run the audit. Record the top three sinks.
2. Change **one** thing, guided by `token-economics`.
3. Work normally for a few days.
4. Re-run. Compare. Keep the change if the number moved; revert it if it did not.

This is the same discipline as any other control in this pack: state the expectation, measure the
result, act on the variance. A "efficiency improvement" nobody measured is a belief.

---

## Degraded mode

**No Python or no shell:** use `/context` for a live view of what is resident right now — that alone
identifies MCP bloat and oversized files in the current session, which are usually two of the top
three problems. `/status` shows plan and model.

**Transcripts unavailable or in an unexpected location:** the script reports `no transcripts found`
and exits 2 rather than inventing a report. Pass `--sessions-dir` if you know where they are.

On a managed seat the org may also expose usage reporting to admins; that measures the same thing
from the other side and is worth asking for if you cannot measure locally.

---

## Related skills

- `token-economics` — the doctrine; this skill is the instrument that tells you which part to apply
- `warehouse-sql` — where most large-result problems get fixed
