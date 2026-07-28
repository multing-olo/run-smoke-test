#!/usr/bin/env python3
"""Run a read-only HTTP smoke probe and emit a JSON result."""

from __future__ import annotations

import argparse
import json
import re
import time
import urllib.error
import urllib.request
from typing import Any


SENSITIVE_KEY = re.compile(
    r"(?i)(token|password|passwd|secret|authorization|api[-_]?key|"
    r"signature|credential)"
)
SECRET_VALUE = re.compile(
    r"(?i)([\"']?(?:token|password|passwd|secret|authorization|"
    r"api[-_]?key|signature|credential)[\"']?)(\s*[:=]\s*)"
    r"([\"']?)([^\"',;\s}]+)([\"']?)"
)


def sanitize_text(value: str) -> str:
    sanitized = re.sub(
        r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+",
        "Bearer [REDACTED]",
        value,
    )
    return SECRET_VALUE.sub(r"\1\2\3[REDACTED]\5", sanitized)


def sanitize_url(value: str) -> str:
    sanitized = re.sub(
        r"(?<=://)[^/@\s]+:[^/@\s]+@",
        "[REDACTED]@",
        value,
    )

    def redact_query(match: re.Match[str]) -> str:
        return f"{match.group(1)}{match.group(2)}=[REDACTED]"

    return re.sub(
        r"(?i)([?&])([^=&]*(?:token|password|passwd|secret|authorization|"
        r"api[-_]?key|signature|credential)[^=&]*)=[^&]*",
        redact_query,
        sanitized,
    )


def parse_status_spec(spec: str) -> set[int]:
    statuses: set[int] = set()
    for part in spec.split(","):
        token = part.strip()
        if not token:
            continue
        if "-" in token:
            start_text, end_text = token.split("-", 1)
            start, end = int(start_text), int(end_text)
            if start > end:
                raise ValueError(f"Invalid status range: {token}")
            statuses.update(range(start, end + 1))
        else:
            statuses.add(int(token))
    if not statuses:
        raise ValueError("At least one expected status is required")
    return statuses


def nested_value(payload: Any, path: str) -> Any:
    value = payload
    for segment in path.split("."):
        if isinstance(value, dict) and segment in value:
            value = value[segment]
        elif isinstance(value, list) and segment.isdigit():
            index = int(segment)
            if index >= len(value):
                raise KeyError(path)
            value = value[index]
        else:
            raise KeyError(path)
    return value


def parse_expected(value: str) -> Any:
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def make_result(
    status: str,
    url: str,
    duration_ms: int,
    reason: str,
    **details: Any,
) -> dict[str, Any]:
    return {
        "name": "HTTP probe",
        "status": status,
        "blocking": True,
        "target": sanitize_url(url),
        "duration_ms": duration_ms,
        "reason": reason,
        **details,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run a read-only HTTP smoke probe and emit JSON."
    )
    parser.add_argument("url")
    parser.add_argument("--expect-status", default="200-299")
    parser.add_argument("--contains", help="Require text in the response body")
    parser.add_argument(
        "--json-field",
        action="append",
        default=[],
        metavar="PATH=VALUE",
        help="Require a JSON field value; repeat as needed",
    )
    parser.add_argument("--timeout", type=float, default=5.0)
    parser.add_argument("--retries", type=int, default=1)
    parser.add_argument("--retry-delay", type=float, default=0.5)
    parser.add_argument("--max-body-bytes", type=int, default=1_000_000)
    args = parser.parse_args()

    try:
        expected_statuses = parse_status_spec(args.expect_status)
        expected_fields = []
        for assertion in args.json_field:
            if "=" not in assertion:
                raise ValueError(f"Invalid JSON assertion: {assertion}")
            path, expected = assertion.split("=", 1)
            if not path:
                raise ValueError("JSON field path cannot be empty")
            expected_fields.append((path, parse_expected(expected)))
        if args.timeout <= 0 or args.retries < 1 or args.retry_delay < 0:
            raise ValueError("Timeout and retries must be positive")
        if args.max_body_bytes < 1:
            raise ValueError("max-body-bytes must be positive")
    except ValueError as exc:
        print(
            json.dumps(
                make_result("BLOCKED", args.url, 0, str(exc)),
                ensure_ascii=False,
                indent=2,
            )
        )
        return 2

    last_network_error = ""
    for attempt in range(1, args.retries + 1):
        started = time.monotonic()
        status_code: int | None = None
        body_bytes = b""
        content_type = ""
        try:
            request = urllib.request.Request(
                args.url,
                method="GET",
                headers={"User-Agent": "run-smoke-tests/1.0"},
            )
            with urllib.request.urlopen(request, timeout=args.timeout) as response:
                status_code = response.status
                content_type = response.headers.get("Content-Type", "")
                body_bytes = response.read(args.max_body_bytes + 1)
        except urllib.error.HTTPError as exc:
            status_code = exc.code
            content_type = exc.headers.get("Content-Type", "") if exc.headers else ""
            body_bytes = exc.read(args.max_body_bytes + 1)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_network_error = str(exc)
            if attempt < args.retries:
                time.sleep(args.retry_delay)
                continue
            duration_ms = round((time.monotonic() - started) * 1000)
            print(
                json.dumps(
                    make_result(
                        "BLOCKED",
                        args.url,
                        duration_ms,
                        "Request could not complete",
                        attempts=attempt,
                        error=sanitize_text(last_network_error),
                    ),
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 2

        duration_ms = round((time.monotonic() - started) * 1000)
        truncated = len(body_bytes) > args.max_body_bytes
        body_bytes = body_bytes[: args.max_body_bytes]
        body = body_bytes.decode("utf-8", errors="replace")
        failures: list[str] = []

        if status_code not in expected_statuses:
            failures.append(
                f"Status {status_code} did not match {args.expect_status}"
            )
        if args.contains is not None and args.contains not in body:
            failures.append("Required text was not present")

        if expected_fields:
            try:
                payload = json.loads(body)
            except json.JSONDecodeError:
                failures.append("Response body was not valid JSON")
            else:
                for path, expected in expected_fields:
                    try:
                        actual = nested_value(payload, path)
                    except KeyError:
                        failures.append(f"JSON field '{path}' was missing")
                        continue
                    if actual != expected:
                        if SENSITIVE_KEY.search(path):
                            failures.append(
                                f"JSON field '{path}' did not match "
                                "(values redacted)"
                            )
                        else:
                            failures.append(
                                f"JSON field '{path}' was {actual!r}, "
                                f"expected {expected!r}"
                            )

        status = "FAIL" if failures else "PASS"
        reason = "; ".join(failures) if failures else "All assertions passed"
        result = make_result(
            status,
            args.url,
            duration_ms,
            reason,
            attempts=attempt,
            http_status=status_code,
            content_type=content_type,
            body_excerpt=sanitize_text(body[:500]),
            body_truncated=truncated or len(body) > 500,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if failures else 0

    print(
        json.dumps(
            make_result("BLOCKED", args.url, 0, "No request was attempted"),
            ensure_ascii=False,
            indent=2,
        )
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
