# Smoke-test report schema

## Required result states

- `PASS`: every blocking check passed with sufficient evidence.
- `FAIL`: at least one blocking check ran and failed.
- `BLOCKED`: no observed blocking failure takes precedence, but at least one
  blocking check could not run or lacks sufficient evidence.
- `PASS WITH WARNINGS`: every blocking check passed; only non-blocking failures,
  blocks, or cleanup warnings remain.

When both a blocking failure and a blocked check exist, report `FAIL` and retain
the blocked check in the table.

## Required report

```markdown
# Smoke Test Report

- Result: PASS | FAIL | BLOCKED | PASS WITH WARNINGS
- Target: <service, path, or URL>
- Environment: local | test | staging | production | unknown
- Duration: <total duration>
- Evidence boundary: <what this run did and did not observe>

| Check | Layer | Blocking | Assertion | Actual | Duration | Status |
| --- | --- | --- | --- | --- | --- | --- |
| ... | ... | yes/no | ... | ... | ... | ... |

## Evidence

- <sanitized failure or warning evidence>

## Blocked or skipped

- <check and reason, or "None">

## Cleanup

- <process and temporary-resource cleanup status>

## Excluded scope

- <regression, performance, security, or unrequested environments>

## Next action

<smallest useful action based on the result>
```

## Evidence rules

For each check retain:

- check identity and target;
- expected assertion;
- actual result;
- status and duration;
- sanitized command, status code, response summary, log excerpt, or screenshot;
- reason for failure, block, or skip;
- prerequisite relationship when applicable.

Do not include secrets or full raw logs. Do not infer an unobserved behavior
from another passing check.

## JSON input for result normalization

Use an array or an object containing `checks`:

```json
{
  "checks": [
    {
      "name": "Health endpoint",
      "layer": "readiness",
      "blocking": true,
      "status": "PASS",
      "expected": "GET /health returns 2xx and status=ok",
      "actual": "200 and status=ok",
      "duration_ms": 42
    },
    {
      "name": "Dashboard",
      "layer": "ui",
      "blocking": true,
      "status": "BLOCKED",
      "reason": "Test identity unavailable"
    }
  ]
}
```

Use `scripts/normalize_results.py` to produce the overall result. Treat
`SKIPPED`, `NOT_RUN`, and `UNKNOWN` as `BLOCKED`.
