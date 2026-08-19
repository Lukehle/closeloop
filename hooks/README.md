# closeloop hooks — optional, off by default

Two PreToolUse guards that enforce `finance-guardrails` mechanically instead of by memory.

**They are not enabled by installing the pack.** Two reasons:

1. A managed Enterprise seat may not permit hooks at all. The pack must be fully functional without
   them, and it is — the same rules are enforced as checklist items inside the `finance-guardrails`
   skill.
2. A guard you did not deliberately enable is a guard you will disable the first time it surprises
   you. Enabling should be a decision.

| Hook | Event | Blocks |
|---|---|---|
| `finance-pii-guard.cjs` | `PreToolUse` on `Write`, `Edit` | Writes containing bank/card numbers, tax identifiers, private keys, cloud credentials, or connection strings with embedded passwords |
| `irreversible-action-guard.cjs` | `PreToolUse` on `Bash`, `PowerShell` | Commands that post, submit, transmit, send, deploy, push, or destructively drop — forcing them to be staged for a human |

---

## Enabling

Add to `.claude/settings.json` in the project, or `~/.claude/settings.json` for all projects. Adjust
the paths to wherever you cloned the repo.

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "node /absolute/path/to/closeloop/hooks/finance-pii-guard.cjs"
          }
        ]
      },
      {
        "matcher": "Bash|PowerShell",
        "hooks": [
          {
            "type": "command",
            "command": "node /absolute/path/to/closeloop/hooks/irreversible-action-guard.cjs"
          }
        ]
      }
    ]
  }
}
```

Requires Node.js on `PATH`. Verify with `node --version`.

---

## Testing before you trust them

Both guards read a JSON payload on stdin and exit `0` to allow or `2` to block. Test directly:

```bash
# should BLOCK - destructive DDL
echo '{"tool_input":{"command":"bq query \"DROP TABLE finance.staging\""}}' \
  | node hooks/irreversible-action-guard.cjs; echo "exit=$?"

# should ALLOW - an ordinary read query
echo '{"tool_input":{"command":"bq query --dry_run \"SELECT 1\""}}' \
  | node hooks/irreversible-action-guard.cjs; echo "exit=$?"

# should ALLOW - the deliberate human-approval marker
echo '{"tool_input":{"command":"git push origin main  # closeloop:approved"}}' \
  | node hooks/irreversible-action-guard.cjs; echo "exit=$?"

# should BLOCK - a connection string carrying a password
echo '{"tool_input":{"file_path":"/x/n.md","content":"postgres://svc:hunter2@db.internal/fin"}}' \
  | node hooks/finance-pii-guard.cjs; echo "exit=$?"

# should ALLOW - ordinary financial figures are not PII
echo '{"tool_input":{"file_path":"/x/r.md","content":"AR balance 12,441,520.11 over 14882 rows"}}' \
  | node hooks/finance-pii-guard.cjs; echo "exit=$?"
```

Expected: `2`, `0`, `0`, `2`, `0`.

---

## Design notes

**Scoped deliberately narrow.** `irreversible-action-guard` matches command shapes that are
unambiguously irreversible or outward-facing. It does not attempt to catch everything: a guard that
fires constantly gets switched off, and a switched-off guard protects nothing. The skill-level rail
stays the primary control; this is a backstop.

**The PII guard Luhn-checks card candidates.** Finance files are full of long numbers — amounts,
invoice ids, transaction ids. Without a check-digit test, every one of them would trip the rule and
the guard would be unusable. It also exempts this pack's own `SKILL.md` / `README.md` files and any
path under a `fixtures/` directory, since those legitimately describe the patterns they match.

**The approved-execution escape hatch.** Appending `# closeloop:approved` to a command lets a
human-authorised execution through `irreversible-action-guard`. It must be typed deliberately;
nothing infers it. This exists so the rail can be *satisfied* — a human decided, and the record shows
they decided — rather than routed around by disabling the hook.

**Do not defeat the PII guard by splitting a value across lines.** If it fires on legitimate
content, widen the rule in the file. A guard you work around is worse than no guard, because it
creates the impression of protection.

> Worth knowing: while this pack was being written, an unrelated secret-guard hook on the author's
> machine blocked an earlier draft of *this file*, because the draft used a literal private-key
> header as a test example. That is the intended behaviour — a guard that exempts documentation by
> pattern would be trivially bypassed by writing your secret into a file called `README.md`. The
> example was changed rather than the guard.

---

## Related

- `skills/finance-guardrails/SKILL.md` — Rails 1 and 5, which these enforce, and which apply
  whether or not the hooks are running
- `ENTERPRISE.md` — what to expect on a policy-managed seat
