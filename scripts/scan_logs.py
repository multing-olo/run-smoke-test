#!/usr/bin/env python3
"""Scan log files or stdin for common fatal-error signals."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Iterable, TextIO


DEFAULT_PATTERNS = (
    r"\bfatal\b",
    r"\bpanic(?:ked)?\b",
    r"\btraceback \(most recent call last\)",
    r"\bunhandled (?:exception|rejection)\b",
    r"\bsegmentation fault\b",
    r"\bout of memory\b",
    r"\buncaught exception\b",
)

SECRET_PATTERN = re.compile(
    r"(?i)([\"']?(?:token|password|passwd|secret|authorization|"
    r"api[-_]?key|signature|credential)[\"']?)(\s*[:=]\s*)"
    r"([\"']?)([^\"',;\s}]+)([\"']?)"
)


def sanitize(line: str) -> str:
    sanitized = re.sub(
        r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+",
        "Bearer [REDACTED]",
        line.rstrip(),
    )
    return SECRET_PATTERN.sub(r"\1\2\3[REDACTED]\5", sanitized)


def scan_stream(
    stream: TextIO,
    source: str,
    patterns: list[re.Pattern[str]],
    ignores: list[re.Pattern[str]],
    max_findings: int,
    findings: list[dict[str, object]],
) -> None:
    for line_number, line in enumerate(stream, start=1):
        if any(pattern.search(line) for pattern in ignores):
            continue
        matched = [pattern.pattern for pattern in patterns if pattern.search(line)]
        if matched:
            findings.append(
                {
                    "source": source,
                    "line": line_number,
                    "patterns": matched,
                    "excerpt": sanitize(line)[:500],
                }
            )
            if len(findings) >= max_findings:
                return


def input_streams(paths: Iterable[str]) -> Iterable[tuple[str, TextIO]]:
    for item in paths:
        if item == "-":
            yield "stdin", sys.stdin
            continue
        path = Path(item)
        stream = path.open("r", encoding="utf-8", errors="replace")
        try:
            yield str(path), stream
        finally:
            stream.close()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scan logs for common fatal-error signals."
    )
    parser.add_argument("paths", nargs="*", default=["-"])
    parser.add_argument(
        "--pattern",
        action="append",
        default=[],
        help="Additional case-insensitive regular expression",
    )
    parser.add_argument(
        "--ignore",
        action="append",
        default=[],
        help="Ignore matching lines; repeat as needed",
    )
    parser.add_argument("--max-findings", type=int, default=20)
    args = parser.parse_args()

    try:
        if args.max_findings < 1:
            raise ValueError("max-findings must be positive")
        patterns = [
            re.compile(value, re.IGNORECASE)
            for value in (*DEFAULT_PATTERNS, *args.pattern)
        ]
        ignores = [re.compile(value, re.IGNORECASE) for value in args.ignore]
    except (ValueError, re.error) as exc:
        print(
            json.dumps(
                {"name": "Fatal log scan", "status": "BLOCKED", "reason": str(exc)},
                ensure_ascii=False,
                indent=2,
            )
        )
        return 2

    findings: list[dict[str, object]] = []
    errors: list[str] = []
    try:
        for source, stream in input_streams(args.paths):
            scan_stream(
                stream,
                source,
                patterns,
                ignores,
                args.max_findings,
                findings,
            )
            if len(findings) >= args.max_findings:
                break
    except OSError as exc:
        errors.append(str(exc))

    if errors:
        status = "BLOCKED"
        reason = "One or more log sources could not be read"
        exit_code = 2
    elif findings:
        status = "FAIL"
        reason = f"Found {len(findings)} fatal-error signal(s)"
        exit_code = 1
    else:
        status = "PASS"
        reason = "No configured fatal-error signals found"
        exit_code = 0

    print(
        json.dumps(
            {
                "name": "Fatal log scan",
                "status": status,
                "blocking": True,
                "reason": reason,
                "findings": findings,
                "errors": errors,
                "finding_limit_reached": len(findings) >= args.max_findings,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
