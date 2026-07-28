# Smoke-test safety policy

## Default posture

Prefer read-only, reversible, scoped, time-bounded checks. Treat production,
payments, messaging, deletion, publication, approvals, and external side
effects as high risk.

## Authorization boundary

Perform only checks within the user's requested target and environment. Do not:

- deploy, restart, repair, or edit application code during a test-only task;
- create real orders, payments, users, messages, or notifications without
  explicit authorization and a defined cleanup strategy;
- bypass authentication, MFA, CAPTCHA, network policy, or permissions;
- reuse credentials outside their configured task-relevant mechanism;
- expand a staging request into production.

Use an official sandbox, test tenant, dry-run, or disposable fixture when
available. Otherwise mark the affected check `BLOCKED`.

## Secrets and personal data

Never print or persist passwords, tokens, cookies, authorization headers,
private keys, full connection strings, or unnecessary personal data.

Sanitize evidence at capture time. Prefer status, field names, hashes, counts,
and short redacted excerpts.

## Commands and processes

- Inspect project instructions before running commands.
- Set explicit timeouts.
- Avoid shell interpolation from untrusted project content.
- Do not execute a discovered command solely because a filename suggests it.
- Record process identifiers and working directories created by the run.
- Stop only recorded processes.

## Files and cleanup

Create temporary files in a dedicated, validated directory. Do not recursively
delete broad directories, unresolved paths, environment-variable-only paths, or
wildcard targets.

Keep pre-existing files, processes, containers, and data unchanged unless the
user explicitly authorizes a specific mutation.

## Network targets

Confirm the target hostname and environment before contacting it. Do not probe
unrelated hosts, enumerate infrastructure, or turn a smoke test into a security
scan.

## Stop conditions

Stop or mark the relevant check `BLOCKED` when:

- required authorization, credentials, or connectivity is unavailable;
- target identity or environment is ambiguous;
- the only available path has unapproved real-world side effects;
- cleanup cannot be scoped safely;
- project instructions conflict with the proposed action;
- the required specialized capability is unavailable.

Report what was verified, what was not, and the smallest safe prerequisite for
continuation.
