# Running closeloop on a managed Enterprise seat

On a Claude Enterprise or Team plan, an administrator can enforce policy across every seat in the
organization. That policy can restrict:

- **Tool permissions** — which tools a seat may call at all
- **File access** — deny rules on credentials, `.env` files, protected directories
- **MCP servers** — an allowlist; unlisted servers simply do not load
- **Models** — which models a seat may use, often pinning routine work to a cheaper tier
- **Spend** — per-organization and per-user caps
- **Compliance** — an org-level Compliance API over usage

Everything in this pack is written to survive all six. This document states exactly how.

---

## The portability contract

Every skill in `closeloop` obeys these rules. If you write a new skill for this pack, it must too.

| Rule | Why |
|---|---|
| **No MCP server is required** by any skill | An admin allowlist may exclude it, and locally-configured servers never reach a published artifact |
| **No model alias is hardcoded** | A managed seat may be pinned to one model. Skills say "review-tier model" and describe the fallback when only one tier is available |
| **No writes outside the working directory** | File-access deny rules commonly block `~`, `/etc`, and sibling directories |
| **No assumed network install** | `pip install` / `npm install` may be blocked. Scripts use the standard library, and name their optional dependency plus the degraded path when one is missing |
| **No secrets in files** | Credentials come from the environment or Application Default Credentials, never from a file this pack writes |
| **Hooks are opt-in** | Hooks may be disallowed by policy. Installation does not enable them; the pack is fully functional without them |
| **Every skill declares a Degraded mode** | The seat tells you what it can do; the skill must already know what to do about it |

---

## Capability matrix

What each layer needs, and what it does without it.

| Capability | Skills that use it | If unavailable |
|---|---|---|
| Bash / local shell | `model-audit`, `data-quality-gate`, `usage-audit`, `warehouse-sql` | Skills switch to guided manual procedures and produce the same output structure by hand |
| Python 3 + `openpyxl` | `model-audit` | Falls back to a structured manual review checklist over the same defect taxonomy |
| A warehouse client (`bq`, `snowsql`, or a Python driver) | `warehouse-sql` | Emits reviewed SQL plus a run-and-paste-back procedure instead of executing |
| Google Sheets access | `sheets-bridge` | Emits an export/import procedure with the same schema-pinning and single-writer guarantees |
| `Workflow` tool (parallel subagents) | `finance-quorum` | Degrades to sequential `Agent` passes, then to a single-context structured checklist |
| `Agent` tool (subagents) | `finance-quorum`, `close-orchestrator` | Runs the same passes inline, one at a time, with explicit context resets |
| Artifact publishing | `fin-artifact` | Produces a self-contained local HTML file with identical content |
| Artifact `mcp` runtime capability | `fin-artifact` live mode | Ships the as-of snapshot tier, which is the default anyway |
| Notion access | `notion-publish` | Emits publish-ready Markdown with the zone contract stated in the document |
| Hooks | The two optional guards | The same rules are enforced as skill-level checklists in `finance-guardrails` |

---

## Live artifacts: what actually works

`fin-artifact` builds in two tiers, and the tier you get depends on org policy.

**Tier 1 — as-of snapshot (always available, and the default).** Data is pulled at build time and
baked into a self-contained page with an explicit as-of timestamp. This needs no runtime capability
and works on the most restricted seat. For financial reporting it is usually the *correct* choice:
a board figure that silently changes between when you sent the deck and when it was read is a defect,
not a feature.

**Tier 2 — live connector mode (conditional).** A published artifact can call **the viewer's
claude.ai connectors** through the `mcp` runtime capability. Two things follow:

1. The data source must be exposed as a **claude.ai connector on the organization's account**.
   A BigQuery or Sheets MCP server configured locally on your laptop is *not* reachable from a
   published page.
2. A page that declares connector access **cannot be shared publicly** — it is a viewer-consented
   grant, so each viewer authenticates as themselves. That is the right security posture for
   financial data, and it is also a distribution constraint you should plan around.

If neither condition holds, `fin-artifact` ships Tier 1 and says so in the page footer. It never
silently degrades a page that claims to be live.

---

## Data handling

This pack assumes it is touching real financial data and behaves accordingly.

- **Never publish an artifact containing customer-identifying data, bank account numbers, tax IDs,
  employee compensation detail, or credentials.** `finance-guardrails` carries the full deny list and
  the aggregation thresholds that make a figure safe to show.
- **Observed data is not sample data.** When a skill learns the shape of a response, it uses the
  shape and discards the values. Real figures never become placeholder content in a template.
- **Local artifacts stay local by default.** Publishing is an explicit, separate step with its own
  confirmation, because publishing distributes.
- **Nothing in this pack sends, posts, submits, or deploys.** See the approval rail below.

---

## The approval rail

The single most important operating rule in this pack:

> **Automate up to the post / send / submit / deploy button. A human presses it.**

An automation may prepare a journal entry, draft the board pack, build the reconciliation, stage the
deploy command, and assemble every piece of supporting evidence. It stops at the irreversible step
and hands over a staged action: the exact command or the exact artifact, plus the tie-out proof that
justifies it.

This is not a limitation to route around. In a controls environment it is the reason the automation
is allowed to exist, and it is what makes the run log defensible when someone asks who approved the
number.

---

## Verifying your own seat

Before relying on a skill, check what your seat actually permits — read the live state rather than
assuming from documentation:

1. Run `/context` to see what is resident and what MCP servers loaded.
2. Run `/status` to see the active model and plan.
3. Ask for a trivial call against each capability you plan to depend on, and observe the real
   response rather than assuming the shape.
4. Run `/token-audit` (the `usage-audit` skill) to get measured numbers for your own usage instead of
   generic guidance.

If a capability is missing, the owning skill's Degraded mode section is the answer. You should not
have to improvise one.
