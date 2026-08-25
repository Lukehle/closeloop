# closeloop

**Corporate finance automation skills for Claude Code.** Month-end close, reconciliation, flux
analysis, three-statement integrity, SaaS metrics, warehouse SQL, live financial artifacts, and
measured token economics.

Built for a **Finance Automation Manager** working in a warehouse-and-spreadsheet stack
(BigQuery / Snowflake, Google Sheets, Excel, Python, Notion) — not for buy-side deal work.

> Every finance skill pack on GitHub today is buy-side: DCF, comps, CIM, deal sourcing. This one is
> the other half of the job — the recurring, controls-bound, evidence-producing work that finance
> operations actually runs on.

---

## Why this exists

Three constraints shaped every skill in this pack.

**1. It has to survive a managed seat.** On a Claude Enterprise/Team plan, admins enforce tool
permissions, file-access restrictions, allowed MCP servers, and which models a seat may use. So no
skill here depends on an MCP server, hardcodes a model alias, writes outside the working directory,
or assumes a network install. Every skill has a **Degraded mode** section stating what it does when
a capability is unavailable. See [ENTERPRISE.md](ENTERPRISE.md).

**2. Numbers need proof, not vibes.** "The query ran" is not "the number is right." The
[`tie-out`](skills/tie-out/SKILL.md) skill makes every deliverable ship a source → transformation →
control total → GL-agreement chain with an explicit variance against a materiality threshold.
Nothing leaves this pack unproven.

**3. Skills are lazy-loaded, so breadth is cheap.** A skill body only enters context when invoked;
the resident cost is its one-line index description. That is why this is 20 sharp skills rather than
5 fat ones — and why [`token-economics`](skills/token-economics/SKILL.md) treats a well-scoped skill
as a *saving*, not an overhead.

---

## Install

**As a plugin (recommended):**

```
/plugin marketplace add Lukehle/closeloop
/plugin install closeloop
```

**As plain skills:**

```bash
git clone https://github.com/Lukehle/closeloop.git
cd closeloop
./install.sh          # macOS / Linux / Git Bash
# or
pwsh ./install.ps1    # Windows PowerShell
```

The installer copies `skills/*` into `~/.claude/skills/`. Nothing is overwritten without a prompt.

**Optional project rails:** copy [`docs/CLAUDE.md.template`](docs/CLAUDE.md.template) into your
finance working folder as `CLAUDE.md` to make the guardrails standing instructions rather than
skills you have to remember to invoke.

---

## The 20 skills

### Layer 0 — Spine

Every other skill defers to these three. They hold the invariants so the domain skills stay short.

| Skill | What it enforces |
|---|---|
| [`finance-guardrails`](skills/finance-guardrails/SKILL.md) | The approval rail (automate up to the post/send/submit button — a human clicks it), single-writer-per-zone, as-of pinning, materiality thresholds, no PII or credentials in artifacts, immutable run log |
| [`tie-out`](skills/tie-out/SKILL.md) | Verification before completion, for numbers. Source → transformation → control total → GL agreement, with variance vs threshold. Exit codes are checked, not piped away |
| [`context-durability`](skills/context-durability/SKILL.md) | Surviving context compaction: checkpoint scope and thresholds to disk before they can be lost, detect that a summarization already happened, and recover without silently re-deriving a different number |

### Layer 1 — Close & reconciliation

| Skill | Use it for |
|---|---|
| [`close-orchestrator`](skills/close-orchestrator/SKILL.md) | Month-end close as a resumable, ledger-driven run. The ledger is the recovery map; postings are staged, never executed |
| [`reconciliation`](skills/reconciliation/SKILL.md) | Bank, subledger↔GL, deferred revenue, intercompany. Matching rules, tolerance bands, exception triage, roll-forward proof |
| [`flux-analysis`](skills/flux-analysis/SKILL.md) | MoM / QoQ / vs-budget variance with driver decomposition and commentary that cites the transactions behind the swing |

### Layer 2 — Statements, models & SaaS

| Skill | Use it for |
|---|---|
| [`three-statement`](skills/three-statement/SKILL.md) | BS / IS / CF integrity — balance check, indirect CF tie to balance-sheet deltas, retained-earnings roll, statement linkages |
| [`saas-metrics`](skills/saas-metrics/SKILL.md) | Canonical definitions plus stage-aware benchmarks, and the ARR↔GL-revenue reconciliation dashboards silently get wrong |
| [`startup-board-pack`](skills/startup-board-pack/SKILL.md) | What an early-stage SaaS board actually reads: cash and runway framing, cohort story, stage-appropriate benchmarks |
| [`model-audit`](skills/model-audit/SKILL.md) | Deterministic spreadsheet integrity checks first (hardcodes in formula rows, broken ranges, circulars, sign conventions), reasoning second |

### Layer 3 — Data & pipelines

| Skill | Use it for |
|---|---|
| [`netsuite`](skills/netsuite/SKILL.md) | SuiteQL and saved-search extraction, period/subsidiary/book structure, JE staging (never posting), revenue schedules, warehouse replication |
| [`warehouse-sql`](skills/warehouse-sql/SKILL.md) | BigQuery / Snowflake for finance: point-in-time correctness, close-cutoff and timezone traps, cost-aware querying, reproducible query artifacts |
| [`sheets-bridge`](skills/sheets-bridge/SKILL.md) | Google Sheets as a real interface: schema pinning, single-writer-per-range, never overwrite human-entered cells |
| [`data-quality-gate`](skills/data-quality-gate/SKILL.md) | Boundary validation that blocks the pipeline — control totals, duplicate keys, period completeness, drift vs prior run |
| [`pipeline-change-control`](skills/pipeline-change-control/SKILL.md) | Change management an auditor can read: what changed, who approved, evidence, rollback, run log |

### Layer 4 — Deliverables & visualization

| Skill | Use it for |
|---|---|
| [`fin-artifact`](skills/fin-artifact/SKILL.md) | Financial artifacts in two tiers — as-of snapshot by default, live connector mode when the org exposes one. Carries the finance-viz rules (bridges, cohorts, variance bands, sign conventions) |
| [`notion-publish`](skills/notion-publish/SKILL.md) | Publishing runbooks and finance docs into Notion under a stable single-writer zone contract |

### Layer 5 — Tokenomics & harness

| Skill | Use it for |
|---|---|
| [`token-economics`](skills/token-economics/SKILL.md) | Enterprise-seat cost discipline: model routing, cache-TTL discipline, context hygiene, and the data-tier hierarchy (SQL → extract → script → agent → interactive) |
| [`usage-audit`](skills/usage-audit/SKILL.md) | Measures your actual usage from local session data and reports numbers. No "be efficient" advice — if it can't be measured it isn't here |
| [`finance-quorum`](skills/finance-quorum/SKILL.md) | Adversarial multi-perspective review of a number, model, or automation before a human sees it. Degrades across three tiers of harness capability |

---

## Commands

| Command | Runs |
|---|---|
| `/close` | Start or resume a month-end close run |
| `/tieout` | Prove a number end-to-end against its source and the GL |
| `/flux` | Variance analysis with driver decomposition and drafted commentary |
| `/board-pack` | Assemble a board or exec reporting pack |
| `/token-audit` | Measure actual token usage and report concrete cuts |

## Hooks (optional, **off by default**)

Two guards live in [`hooks/`](hooks/) and are **not** enabled by installation, because a managed
seat may not permit hooks and the pack must work without them:

- `finance-pii-guard.cjs` — blocks writes that would put account numbers, tax IDs, or credentials
  into a repo path
- `irreversible-action-guard.cjs` — intercepts post / submit / send / deploy commands and forces
  them to be staged for a human instead

See [hooks/README.md](hooks/README.md) to enable them deliberately.

---

## Design principles

1. **Automate up to the button; a human presses it.** Nothing in this pack posts a journal entry,
   sends a board pack, or submits a filing. It stages the action with the exact command and the
   evidence, and stops.
2. **One writer per zone.** Two automations must never write the same tab, range, table, or section.
   Zone separation is the mutex.
3. **As-of, not live-by-default.** A board number that silently changes under you is a bug. Data is
   pinned to an as-of timestamp unless liveness is explicitly requested.
4. **Materiality is a number, not a feeling.** Every check declares its threshold up front.
5. **Measure, don't assert.** Skills that make efficiency or quality claims must produce the
   measurement alongside the claim.
6. **Degrade, don't fail.** Every skill states what it does when the harness is locked down.

---

## Not in scope

No CRM skills, and no ERP beyond NetSuite — Sage Intacct, Dynamics, and SAP have different record
models and would need their own skills. No buy-side deal tooling (DCF, comps, CIM); that ground is
well covered elsewhere. No tax or audit opinions: these skills produce evidence and analysis, not
professional advice.

## Companion packs

| | |
|---|---|
| [**chartroom**](https://github.com/Lukehle/chartroom) | Artifacts, apps, UI/UX, and charts — SVG charting under a strict CSP, bridges, cohorts, variance, financial tables, live connector data, plus a tested chart kit. `fin-artifact` points there for build detail |
| [**claude-quorum**](https://github.com/Lukehle/claude-quorum) | The general form of `finance-quorum` — lens design, adversarial verification, judge panels, degradation tiers, and a tested library for the deterministic steps |

Use them together or separately; none depends on the others.

## Verification

The two scripts in this pack are tested rather than asserted:

```bash
python skills/model-audit/scripts/selftest.py     # 9 assertions, incl. a regression guard
python skills/data-quality-gate/scripts/dq_check.py --help
python skills/usage-audit/scripts/usage_audit.py --days 7
```

`model-audit`'s self-test plants known defects (a hardcode inside a formula row, a truncated SUM
range) alongside deliberately clean rows, and asserts the scanner catches every planted defect and
flags none of the clean ones. The truncated-range case is a regression guard: an earlier normalizer
stripped row numbers from references, which made `=SUM(B1:B9)` and `=SUM(D1:D8)` compare equal and
silently hid the most common range defect in real models.

## License

MIT — see [LICENSE](LICENSE).

---

Part of a family: [toolroom](https://github.com/Lukehle/toolroom) (the harness layer and umbrella - guard hooks, model routing, loops, skill routing, Enterprise runbook) - [closeloop](https://github.com/Lukehle/closeloop) (finance) - [chartroom](https://github.com/Lukehle/chartroom) (charts/artifacts) - [vaultkit](https://github.com/Lukehle/vaultkit) (vault memory + Notion) - [claude-quorum](https://github.com/Lukehle/claude-quorum) (verification).
