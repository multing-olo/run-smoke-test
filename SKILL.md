---
name: run-smoke-tests
description: Run safe, evidence-based smoke tests for local applications, APIs, deployed services, and critical UI paths. Use when the user asks to perform a smoke test, deployment verification, startup validation, health check, release gate check, post-deployment sanity check, or a quick validation that a build is basically usable.
---

# Run Smoke Tests

## Objective

Determine whether the target is basically operational and ready for the next
validation stage. Return `PASS`, `FAIL`, `BLOCKED`, or `PASS WITH WARNINGS`
using observable, sanitized evidence.

Keep the scope narrow. Verify representative critical paths; do not treat a
smoke test as complete regression, performance, or security testing.

## Establish scope

Identify from the request and available project instructions:

- target: local source, running process, container, API, or deployed UI;
- environment: local, test, staging, or production;
- startup or attachment method;
- release-blocking health, API, and UI paths;
- available test identity or credentials;
- permitted side effects;
- time budget.

Inspect `AGENTS.md`, project documentation, manifests, container configuration,
CI configuration, existing tests, and example environment files before
choosing commands. Treat discovered commands as candidates until project
instructions or safe execution confirms them.

Ask only when missing information materially changes safety, scope, or the
release decision. Never ask the user to paste secrets into chat.

Keep target-specific values at runtime. Do not persist discovered URLs, ports,
credentials, absolute paths, startup commands, test identities, or expected
business values in this Skill. Treat bundled commands, health paths, status
ranges, timeouts, and error patterns as portable defaults or candidates; let
project instructions and explicit runtime arguments override them.

## Load references conditionally

- Read [references/safety-policy.md](references/safety-policy.md) before
  starting a service, contacting a non-local target, using credentials, or
  running any check with possible side effects.
- Read [references/test-strategies.md](references/test-strategies.md) when
  selecting checks for a detected project type or target.
- Read [references/report-schema.md](references/report-schema.md) before
  producing the final report.

Keep reference loading one level deep. Do not search for additional guidance
unless the selected reference or project instructions require it.

## Discover the project

Use read-only inspection first. Optionally run:

```bash
python3 scripts/detect_project.py <project-root>
```

Use the output as evidence for project classification and command candidates,
not as authority over explicit project instructions.

If the repository contains multiple services, identify the requested service
and its prerequisites. Report ambiguity when choosing the wrong service would
change the result.

## Build the smoke plan

Select the smallest applicable set:

1. Build or startup.
2. Process liveness and readiness.
3. Core dependency reachability.
4. Critical read-only API behavior.
5. One low-side-effect critical UI path.
6. Fatal-error log scan.

Define before execution for every check:

- name and layer;
- exact target;
- concrete assertion;
- blocking or non-blocking status;
- timeout;
- evidence to retain;
- prerequisite checks.

Do not use vague assertions such as “looks good.” Prefer assertions such as
“`GET /health` returns 2xx within 3 seconds and JSON field `status` equals
`ok`.”

## Route specialized work

When a subtask clearly matches another available Skill, load and follow that
Skill for the subtask. Retain responsibility for smoke-test scope, assertions,
evidence, safety, and the overall result.

Use a browser-focused Skill for interactive UI paths when available. Use
product- or format-specific Skills only when their capability is part of the
selected smoke path. Do not assume a Skill or connector exists. Apply a safe
fallback or mark the affected check `BLOCKED` when a required capability is
unavailable.

Do not allow a delegated subtask to expand the test scope or declare the whole
release ready.

## Execute safely

Run cheap, read-only, and low-risk checks first. Apply a timeout to every
process and network request.

For HTTP checks, optionally run:

```bash
python3 scripts/probe_http.py \
  https://example.test/health \
  --expect-status 200-299 \
  --json-field status=ok \
  --timeout 3 \
  --retries 2
```

For logs, optionally run:

```bash
python3 scripts/scan_logs.py application.log
```

Interpret helper exit codes consistently:

- `0`: check passed;
- `1`: check ran and failed;
- `2`: check was blocked or invalid.

Stop checks whose prerequisites fail or are blocked. Mark them `BLOCKED`; do
not count them as executed failures or passes.

Do not fix defects, alter application code, deploy changes, or broaden the
task unless the user explicitly requests remediation.

## Capture evidence

Record for every check:

- expected result;
- actual result;
- status;
- duration;
- sanitized command, request identity, response summary, log excerpt, or
  screenshot;
- failure or blocking reason;
- cleanup state.

Remove tokens, passwords, cookies, authorization headers, connection strings,
and unnecessary personal data. Prefer concise excerpts over full logs.

## Clean up

Stop only processes started by this run. Remove only temporary resources whose
exact identities were recorded by this run.

Never use broad process-name termination, recursive deletion on unresolved
paths, or cleanup based on unvalidated variables. Report cleanup failure as a
warning and preserve enough identity for manual cleanup without exposing
secrets.

## Decide

Normalize collected checks with:

```bash
python3 scripts/normalize_results.py results.json
```

Apply these definitions:

- `PASS`: every blocking check passed with sufficient evidence.
- `FAIL`: at least one blocking check ran and failed.
- `BLOCKED`: no blocking failure was observed, but at least one blocking check
  could not run or lacks sufficient evidence.
- `PASS WITH WARNINGS`: every blocking check passed, while only non-blocking
  failures, blocks, or cleanup warnings remain.

Prioritize `FAIL` over `BLOCKED` when both exist. Never count skipped,
unavailable, or unobserved behavior as passed.

## Report

Follow [references/report-schema.md](references/report-schema.md). Lead with the
overall result, target, environment, and duration. Include:

1. a compact check table;
2. sanitized failure evidence;
3. blocked and skipped checks with reasons;
4. cleanup status;
5. scope exclusions;
6. the smallest useful next action.

State the evidence boundary. Do not claim that the system is fully correct,
secure, or production-ready merely because the smoke test passed.
