#!/usr/bin/env node
/**
 * closeloop - irreversible finance action guard  (PreToolUse: Bash, PowerShell)
 *
 * Intercepts commands that would post, submit, send, transmit, or deploy, and
 * blocks them with instructions to stage the action for a human instead.
 * Enforces finance-guardrails Rail 1 mechanically.
 *
 * OFF BY DEFAULT. See hooks/README.md. The rail applies whether or not this
 * hook runs - it is enforced as a checklist item in the finance-guardrails
 * skill on seats where hooks are not permitted.
 *
 * Exit 0 = allow. Exit 2 with JSON on stderr = block.
 *
 * Scope note: this matches command shapes that are unambiguously irreversible
 * or outward-facing. It deliberately does NOT try to catch everything - a guard
 * that fires constantly gets disabled, and a disabled guard protects nothing.
 * The skill-level rail remains the primary control.
 */

'use strict';

let raw = '';
process.stdin.on('data', (c) => { raw += c; });
process.stdin.on('end', () => {
  let payload;
  try {
    payload = JSON.parse(raw || '{}');
  } catch {
    process.exit(0);
  }

  const input = payload.tool_input || {};
  const cmd = String(input.command || '').trim();
  if (!cmd) process.exit(0);

  const RULES = [
    {
      name: 'journal entry / period posting',
      re: /\b(post|submit)[-_ ]?(je|journal|entry|entries|batch)\b|\bclose[-_ ]?period\b|\block[-_ ]?period\b/i,
      note: 'Posting an entry or locking a period changes the system of record.',
    },
    {
      name: 'NetSuite / ERP write',
      re: /\b(netsuite|suitetalk|suiteql)\b[\s\S]{0,80}\b(POST|PUT|PATCH|DELETE|upsert|insert)\b/i,
      note: 'This writes to the ERP. Stage the entry instead.',
    },
    {
      name: 'payment or transfer',
      re: /\b(ach|wire|nacha|payment[-_ ]?file|pay[-_ ]?run|disburse|remit)\b[\s\S]{0,60}\b(send|submit|transmit|upload|post)\b/i,
      note: 'Transmitting a payment file moves money and is not reversible.',
    },
    {
      name: 'outbound email / message send',
      re: /\b(send[-_ ]?mail|sendmail|mailx|--send\b|gmail[\s\S]{0,30}\bsend\b|slack[\s\S]{0,30}\bpostMessage\b)/i,
      note: 'Sending distributes the numbers. A human sends.',
    },
    {
      name: 'production deploy',
      re: /\b(terraform\s+apply|kubectl\s+apply|helm\s+(install|upgrade)|serverless\s+deploy|wrangler\s+(deploy|publish)|gcloud\s+\w+\s+deploy)\b/i,
      note: 'Deploying changes a live system.',
    },
    {
      name: 'git push',
      re: /\bgit\s+push\b/i,
      note: 'Pushing publishes work outside this machine.',
    },
    {
      name: 'warehouse destructive DDL/DML',
      re: /\b(DROP\s+(TABLE|SCHEMA|DATASET)|TRUNCATE\s+TABLE|DELETE\s+FROM\s+\w+\s*(;|$))/i,
      note: 'This destroys data with no undo.',
    },
    {
      name: 'scheduled job registration',
      re: /\b(schtasks\s+\/create|crontab\s+[^-]|Register-ScheduledTask)\b/i,
      note: 'Registering a job makes something run unattended, repeatedly.',
    },
  ];

  for (const rule of RULES) {
    if (!rule.re.test(cmd)) continue;

    const reason =
      `closeloop irreversible-action-guard blocked this command.\n\n` +
      `Matched:  ${rule.name}\n` +
      `Command:  ${cmd.slice(0, 200)}${cmd.length > 200 ? ' ...' : ''}\n\n` +
      `${rule.note}\n\n` +
      `finance-guardrails Rail 1: automate up to the post/send/submit/deploy\n` +
      `button - a human presses it.\n\n` +
      `Stage it instead. A staged action carries all four of:\n` +
      `  1. The exact command or artifact (not a description of it)\n` +
      `  2. The tie-out block proving the numbers\n` +
      `  3. The blast radius - what changes, where, for which period, and\n` +
      `     whether reversing needs a correcting entry rather than an undo\n` +
      `  4. The rollback steps, or an explicit statement that there are none\n\n` +
      `Then write "STAGED - human runs this" and hand over. The approved action\n` +
      `must be executed by the human outside this guarded agent tool path;\n` +
      `command text is never treated as proof of approval.`;

    process.stderr.write(JSON.stringify({
      decision: 'block',
      reason,
      hookSpecificOutput: {
        hookEventName: 'PreToolUse',
        permissionDecision: 'deny',
        permissionDecisionReason: `irreversible-action-guard: ${rule.name}`,
      },
    }));
    process.exit(2);
  }

  process.exit(0);
});
