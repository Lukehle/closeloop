#!/usr/bin/env python3
"""Measure real Claude Code usage from local session transcripts.

Reads the JSONL transcripts Claude Code writes under ~/.claude/projects and
reports actual token counts (input, output, cache-read, cache-creation) taken
from each assistant message's usage block - not character-count estimates.

It also ranks the largest tool results, which are what actually fill context,
and links each one back to the tool that produced it.

Privacy: this reads sizes, counts, tool names, and file paths. It never emits
message content, tool-result bodies, or prompt text - which matters, because
finance transcripts contain financial data.

Usage:
    python usage_audit.py [--days 7] [--project NAME] [--top 15]
                          [--sessions-dir PATH] [--json]

Exit codes:
    0  report produced
    2  no transcripts found in the window
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

# Tool results above this size are worth calling out individually.
LARGE_RESULT_CHARS = 20_000

# Only used for the size-ranking of tool results, which have no usage block of
# their own. Deliberately coarse, and labelled as an estimate in the output.
CHARS_PER_TOKEN = 4


def default_sessions_dir() -> str:
    return os.path.join(os.path.expanduser("~"), ".claude", "projects")


def iter_transcripts(root: str, project: str | None, cutoff: datetime):
    """Yield transcript paths modified since cutoff.

    Walks only as deep as needed and skips directories wholesale on mtime,
    because a busy projects tree is large and a naive recursive glob is slow.
    """
    if not os.path.isdir(root):
        return
    for namespace in sorted(os.listdir(root)):
        if project and project.lower() not in namespace.lower():
            continue
        ns_path = os.path.join(root, namespace)
        if not os.path.isdir(ns_path):
            continue
        for dirpath, _dirnames, filenames in os.walk(ns_path):
            for fn in filenames:
                if not fn.endswith(".jsonl"):
                    continue
                path = os.path.join(dirpath, fn)
                try:
                    mtime = datetime.fromtimestamp(
                        os.path.getmtime(path), tz=timezone.utc)
                except OSError:
                    continue
                if mtime >= cutoff:
                    yield namespace, path


def content_size(content) -> int:
    """Character length of a tool_result payload, list- or str-shaped."""
    if isinstance(content, str):
        return len(content)
    if isinstance(content, list):
        total = 0
        for block in content:
            if isinstance(block, dict):
                total += len(str(block.get("text", "")))
            else:
                total += len(str(block))
        return total
    return len(str(content)) if content is not None else 0


def short_target(tool: str, tool_input: dict) -> str:
    """A compact, non-sensitive label for what a tool call acted on."""
    if not isinstance(tool_input, dict):
        return ""
    for key in ("file_path", "path", "notebook_path"):
        if key in tool_input:
            return os.path.basename(str(tool_input[key]))
    if "pattern" in tool_input:
        return f"pattern:{str(tool_input['pattern'])[:40]}"
    if "command" in tool_input:
        cmd = str(tool_input["command"]).strip().split("\n")[0]
        return cmd[:60]
    if "url" in tool_input:
        return str(tool_input["url"])[:60]
    if "query" in tool_input:
        return f"query:{str(tool_input['query'])[:40]}"
    return ""


class Audit:
    def __init__(self) -> None:
        self.sessions: set[str] = set()
        self.namespaces: Counter = Counter()
        self.assistant_msgs = 0
        self.user_msgs = 0

        self.tok = Counter()          # input / output / cache_read / cache_creation
        self.by_model: dict[str, Counter] = defaultdict(Counter)

        self.tool_calls: Counter = Counter()
        self.tool_result_chars: Counter = Counter()      # by tool name
        self.large_results: list[dict] = []
        self.file_reads: Counter = Counter()
        self.mcp_calls: Counter = Counter()

        # tool_use_id -> (tool name, target label), to link a result to its call
        self._pending: dict[str, tuple[str, str]] = {}

    def ingest(self, namespace: str, path: str) -> None:
        try:
            fh = open(path, "r", encoding="utf-8", errors="replace")
        except OSError:
            return
        with fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue

                sid = rec.get("sessionId")
                if sid:
                    self.sessions.add(sid)
                self.namespaces[namespace] += 1

                msg = rec.get("message")
                if not isinstance(msg, dict):
                    continue
                rtype = rec.get("type")

                if rtype == "assistant":
                    self.assistant_msgs += 1
                    usage = msg.get("usage") or {}
                    model = msg.get("model") or "unknown"
                    counts = {
                        "input": int(usage.get("input_tokens") or 0),
                        "output": int(usage.get("output_tokens") or 0),
                        "cache_read": int(usage.get("cache_read_input_tokens") or 0),
                        "cache_creation": int(
                            usage.get("cache_creation_input_tokens") or 0),
                    }
                    for k, v in counts.items():
                        self.tok[k] += v
                        self.by_model[model][k] += v

                    for block in msg.get("content", []) or []:
                        if isinstance(block, dict) and block.get("type") == "tool_use":
                            name = block.get("name") or "unknown"
                            target = short_target(name, block.get("input") or {})
                            self.tool_calls[name] += 1
                            if name.startswith("mcp__"):
                                server = name.split("__")[1] if "__" in name else name
                                self.mcp_calls[server] += 1
                            if name in ("Read", "NotebookEdit") and target:
                                self.file_reads[target] += 1
                            bid = block.get("id")
                            if bid:
                                self._pending[bid] = (name, target)

                elif rtype == "user":
                    self.user_msgs += 1
                    content = msg.get("content")
                    if not isinstance(content, list):
                        continue
                    for block in content:
                        if not (isinstance(block, dict)
                                and block.get("type") == "tool_result"):
                            continue
                        size = content_size(block.get("content"))
                        name, target = self._pending.pop(
                            block.get("tool_use_id"), ("unknown", ""))
                        self.tool_result_chars[name] += size
                        if size >= LARGE_RESULT_CHARS:
                            self.large_results.append(
                                {"tool": name, "target": target, "chars": size,
                                 "est_tokens": size // CHARS_PER_TOKEN})

    def report(self, top: int, days: int) -> dict:
        self.large_results.sort(key=lambda r: r["chars"], reverse=True)
        total_result_chars = sum(self.tool_result_chars.values()) or 1
        top_share = sum(r["chars"] for r in self.large_results[:10]) / total_result_chars

        billed_input = self.tok["input"] + self.tok["cache_creation"]
        cacheable = billed_input + self.tok["cache_read"]
        cache_hit_rate = (self.tok["cache_read"] / cacheable) if cacheable else 0.0

        total_tools = sum(self.tool_calls.values()) or 1

        recs: list[str] = []

        # Only claim the big results are the priority when the measurement
        # actually supports it. A concentrated head is a different problem from
        # diffuse volume, and recommending "fix the top 10" when they are 2% of
        # the total would be asserting a priority the data contradicts.
        if self.large_results and top_share >= 0.25:
            biggest = self.large_results[0]
            recs.append(
                f"Tool-result volume is concentrated: the top 10 results are "
                f"{top_share:.0%} of the total, led by {biggest['tool']} on "
                f"{biggest['target'] or 'unnamed target'} (~{biggest['est_tokens']:,} "
                f"est. tokens). Reduce these at the source first - one fix moves "
                f"the number.")
        elif self.large_results:
            recs.append(
                f"Tool-result volume is diffuse: {len(self.large_results)} results "
                f"exceeded {LARGE_RESULT_CHARS:,} chars but the top 10 are only "
                f"{top_share:.0%} of the total. No single read is the problem, so "
                f"look at repetition (below) rather than at individual large reads.")

        heavy_reads = [(f, n) for f, n in self.file_reads.most_common(5) if n >= 3]
        if heavy_reads:
            f, n = heavy_reads[0]
            recs.append(
                f"'{f}' was read {n} times in the window. Re-reading a file you have "
                f"already read (or just edited) pays full price for information "
                f"already in context.")

        idle_servers = [s for s, n in self.mcp_calls.items() if n == 0]
        if self.mcp_calls and not idle_servers:
            low = [s for s, n in self.mcp_calls.items() if n <= 2]
            if low:
                recs.append(
                    f"MCP servers with almost no use in the window: {', '.join(low)}. "
                    f"Their tool definitions sit in context on every request whether "
                    f"called or not - disconnect what you are not using this session.")

        if cache_hit_rate < 0.5 and cacheable > 50_000:
            recs.append(
                f"Cache read share is {cache_hit_rate:.0%} of cacheable input. Cache "
                f"reads cost a fraction of fresh input, so a low share usually means "
                f"early context is being invalidated (edited instructions mid-session) "
                f"or work is spread across long gaps.")

        read_share = self.tool_calls.get("Read", 0) / total_tools
        if read_share > 0.35:
            recs.append(
                f"Read is {read_share:.0%} of all tool calls. A read-heavy profile "
                f"usually means data is entering context that a warehouse GROUP BY or "
                f"a local script could have reduced first (token-economics tiers 1-2).")

        if not recs:
            recs.append(
                "No measurement in this window crossed a threshold worth acting on. "
                "Nothing to change.")

        return {
            "window_days": days,
            "sessions": len(self.sessions),
            "namespaces": dict(self.namespaces.most_common(10)),
            "messages": {"assistant": self.assistant_msgs, "user": self.user_msgs},
            "tokens_actual": {
                "input": self.tok["input"],
                "output": self.tok["output"],
                "cache_read": self.tok["cache_read"],
                "cache_creation": self.tok["cache_creation"],
                "billed_input_equivalent": billed_input,
                "cache_read_share": round(cache_hit_rate, 4),
            },
            "tokens_by_model": {m: dict(c) for m, c in self.by_model.items()},
            "tool_calls": dict(self.tool_calls.most_common(top)),
            "tool_result_volume_chars": dict(self.tool_result_chars.most_common(top)),
            "largest_results": self.large_results[:top],
            "most_read_files": dict(self.file_reads.most_common(top)),
            "mcp_calls_by_server": dict(self.mcp_calls.most_common(top)),
            "recommendations": recs,
        }


def render(rep: dict) -> str:
    t = rep["tokens_actual"]
    out = [
        f"USAGE AUDIT | {rep['window_days']} days | {rep['sessions']} sessions | "
        f"{sum(rep['tool_calls'].values()):,} tool calls (top {len(rep['tool_calls'])} shown)",
        "",
        "ACTUAL TOKENS (from transcript usage blocks, not estimates)",
        f"  input           {t['input']:>14,}",
        f"  cache creation  {t['cache_creation']:>14,}",
        f"  cache read      {t['cache_read']:>14,}   ({t['cache_read_share']:.0%} of cacheable input)",
        f"  output          {t['output']:>14,}",
        "",
        "TOKENS BY MODEL",
    ]
    for model, c in sorted(rep["tokens_by_model"].items(),
                           key=lambda kv: -(kv[1].get("output", 0))):
        out.append(f"  {model:<28} out {c.get('output', 0):>10,}  "
                   f"cache_read {c.get('cache_read', 0):>12,}")

    out += ["", "LARGEST TOOL RESULTS (estimated tokens; these fill context)"]
    if rep["largest_results"]:
        for i, r in enumerate(rep["largest_results"][:10], 1):
            out.append(f"  {i:>2}. ~{r['est_tokens']:>9,}  {r['tool']:<12} "
                       f"{r['target'][:52]}")
    else:
        out.append("  none above the large-result threshold")

    out += ["", "TOOL DISTRIBUTION"]
    total = sum(rep["tool_calls"].values()) or 1
    out.append("  " + "  ".join(f"{k} {v / total:.0%}"
                                for k, v in list(rep["tool_calls"].items())[:8]))

    if rep["most_read_files"]:
        out += ["", "MOST-READ FILES"]
        for f, n in list(rep["most_read_files"].items())[:8]:
            out.append(f"  {n:>3}x  {f}")

    if rep["mcp_calls_by_server"]:
        out += ["", "MCP CALLS BY SERVER"]
        for s, n in rep["mcp_calls_by_server"].items():
            out.append(f"  {n:>4}  {s}")

    out += ["", "RECOMMENDATIONS (each derived from a measurement above)"]
    for i, r in enumerate(rep["recommendations"], 1):
        out.append(f"  {i}. {r}")
    out += ["", "Change ONE thing, work normally, then re-run and compare."]
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description="closeloop usage audit")
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--project", help="substring match on the project namespace")
    ap.add_argument("--top", type=int, default=15)
    ap.add_argument("--sessions-dir", default=default_sessions_dir())
    ap.add_argument("--json", action="store_true", help="emit JSON only")
    args = ap.parse_args()

    cutoff = datetime.now(timezone.utc) - timedelta(days=args.days)
    audit = Audit()

    found = 0
    for namespace, path in iter_transcripts(args.sessions_dir, args.project, cutoff):
        audit.ingest(namespace, path)
        found += 1

    if not found:
        print(f"ERROR: no transcripts modified in the last {args.days} day(s) under "
              f"{args.sessions_dir}.\nPass --sessions-dir if your transcripts live "
              f"elsewhere, or use /context for a live view of the current session.",
              file=sys.stderr)
        return 2

    report = audit.report(args.top, args.days)
    report["transcripts_scanned"] = found

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(render(report))
        print(f"\n# {found} transcript file(s) scanned. No message content was read "
              f"or reported.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
