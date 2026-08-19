#!/usr/bin/env node
/**
 * closeloop - finance PII / credential write guard  (PreToolUse: Write, Edit)
 *
 * Blocks writes that would put bank account numbers, tax identifiers, card
 * numbers, or credentials into a file. Enforces finance-guardrails Rail 5
 * mechanically instead of by memory.
 *
 * OFF BY DEFAULT. See hooks/README.md to enable. A managed Enterprise seat may
 * not permit hooks at all, which is why the same rules exist as a checklist in
 * the finance-guardrails skill - the rail does not weaken when the enforcement
 * mechanism is absent.
 *
 * Exit 0 = allow. Exit 2 with JSON on stderr = block.
 *
 * This is a backstop, not the primary control. Do not rely on it to catch a
 * pattern you did not think of, and do not defeat it by splitting a value
 * across lines. If it fires on legitimate content, widen the rule here rather
 * than working around it.
 */

'use strict';

let raw = '';
process.stdin.on('data', (c) => { raw += c; });
process.stdin.on('end', () => {
  let payload;
  try {
    payload = JSON.parse(raw || '{}');
  } catch {
    process.exit(0); // never block on a parse failure of our own input
  }

  const input = payload.tool_input || {};
  const text = [input.content, input.new_string, input.old_string]
    .filter((v) => typeof v === 'string')
    .join('\n');
  const filePath = String(input.file_path || input.path || '');

  if (!text) process.exit(0);

  // Files that are allowed to describe these patterns: this pack's own
  // documentation, and anything explicitly marked as a synthetic fixture.
  if (/[\\/](SKILL\.md|README\.md|ENTERPRISE\.md)$/i.test(filePath)) process.exit(0);
  if (/[\\/]fixtures?[\\/]/i.test(filePath)) process.exit(0);

  const RULES = [
    {
      name: 'US bank routing + account pair',
      // A 9-digit routing number adjacent to an 8-17 digit account number.
      re: /\b\d{9}\b[\s:,-]{1,6}\b\d{8,17}\b/,
    },
    {
      name: 'IBAN',
      re: /\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b/,
    },
    {
      name: 'US SSN',
      re: /\b(?!000|666|9\d\d)\d{3}-(?!00)\d{2}-(?!0000)\d{4}\b/,
    },
    {
      name: 'US EIN',
      re: /\b\d{2}-\d{7}\b(?=[\s\S]{0,40}\b(EIN|tax\s*id|employer\s*identification)\b)/i,
    },
    {
      name: 'payment card number',
      // 13-19 digits in card-ish grouping; Luhn-checked below to cut noise.
      re: /\b(?:\d[ -]?){13,19}\b/,
      luhn: true,
    },
    {
      name: 'private key block',
      re: /-----BEGIN (?:RSA |OPENSSH |EC |DSA |PGP )?PRIVATE KEY-----/,
    },
    {
      name: 'GCP service-account key',
      re: /"type"\s*:\s*"service_account"/,
    },
    {
      name: 'AWS access key id',
      re: /\b(?:AKIA|ASIA)[0-9A-Z]{16}\b/,
    },
    {
      name: 'API key or token assignment',
      re: /(?<![A-Za-z0-9_])(api[_-]?key|secret|token|password|passwd|client[_-]?secret)\s*[:=]\s*["']?[A-Za-z0-9+/=_.-]{16,}/i,
    },
    {
      name: 'database connection string with credentials',
      re: /\b(?:postgres|postgresql|mysql|mongodb(?:\+srv)?|snowflake):\/\/[^\s:@/]+:[^\s@/]+@/i,
    },
  ];

  function luhnValid(digits) {
    let sum = 0;
    let alt = false;
    for (let i = digits.length - 1; i >= 0; i--) {
      let n = Number(digits[i]);
      if (alt) {
        n *= 2;
        if (n > 9) n -= 9;
      }
      sum += n;
      alt = !alt;
    }
    return sum % 10 === 0;
  }

  for (const rule of RULES) {
    const m = text.match(rule.re);
    if (!m) continue;

    if (rule.luhn) {
      const digits = m[0].replace(/[^\d]/g, '');
      // Skip lengths that are almost always something else, and anything that
      // fails the check digit - most long numbers in finance files are amounts,
      // invoice ids, or transaction ids, not cards.
      if (digits.length < 13 || digits.length > 19 || !luhnValid(digits)) continue;
    }

    const reason =
      `closeloop finance-pii-guard blocked this write.\n\n` +
      `Matched rule: ${rule.name}\n` +
      `Target file:  ${filePath || '(unnamed)'}\n\n` +
      `finance-guardrails Rail 5: bank/card numbers, tax identifiers, and\n` +
      `credentials must never be written into a file this pack produces, a\n` +
      `commit, an artifact, or a published page.\n\n` +
      `Do instead:\n` +
      `  - Credentials: read from the environment or Application Default\n` +
      `    Credentials. Never from a file. If this value was pasted into the\n` +
      `    conversation, recommend rotation - the transcript may persist.\n` +
      `  - Account/card numbers: store the last 4 only, and only if needed.\n` +
      `  - Tax identifiers: reference the entity, not the identifier.\n\n` +
      `Do NOT split the value across lines to get past this guard. If the rule\n` +
      `is firing on legitimate content, widen it in hooks/finance-pii-guard.cjs.`;

    process.stderr.write(JSON.stringify({
      decision: 'block',
      reason,
      hookSpecificOutput: {
        hookEventName: 'PreToolUse',
        permissionDecision: 'deny',
        permissionDecisionReason: `finance-pii-guard: ${rule.name}`,
      },
    }));
    process.exit(2);
  }

  process.exit(0);
});
