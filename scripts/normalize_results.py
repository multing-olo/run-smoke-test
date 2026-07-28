#!/usr/bin/env python3
"""Normalize smoke-check results into one release-gate decision."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


STATUS_ALIASES = {
    "PASS": "PASS",
    "PASSED": "PASS",
    "OK": "PASS",
    "SUCCESS": "PASS",
    "FAIL": "FAIL",
    "FAILED": "FAIL",
    "ERROR": "FAIL",
    "BLOCKED": "BLOCKED",
    "SKIPPED": "BLOCKED",
    "NOT_RUN": "BLOCKED",
    "NOT RUN": "BLOCKED",
    "UNKNOWN": "BLOCKED",
    "WARNING": "WARNING",
    "WARN": "WARNING",
}


def load_payload(path: str) -> Any:
    if path == "-":
        return json.load(sys.stdin)
    with Path(path).open("r", encoding="utf-8") as stream:
        return json.load(stream)


def normalize_check(check: Any, index: int) -> dict[str, Any]:
    if not isinstance(check, dict):
        raise ValueError(f"Check {index} is not an object")
    raw_status = str(check.get("status", "UNKNOWN")).strip().upper()
    status = STATUS_ALIASES.get(raw_status)
    if status is None:
        raise ValueError(f"Check {index} has unsupported status: {raw_status}")
    normalized = dict(check)
    normalized["name"] = str(check.get("name", f"Check {index + 1}"))
    normalized["status"] = status
    normalized["blocking"] = bool(check.get("blocking", True))
    return normalized


def decide(checks: list[dict[str, Any]]) -> str:
    if not checks:
        return "BLOCKED"
    blocking = [check for check in checks if check["blocking"]]
    non_blocking = [check for check in checks if not check["blocking"]]

    if not blocking:
        return "BLOCKED"
    if any(check["status"] == "FAIL" for check in blocking):
        return "FAIL"
    if any(check["status"] in {"BLOCKED", "WARNING"} for check in blocking):
        return "BLOCKED"
    if any(
        check["status"] in {"FAIL", "BLOCKED", "WARNING"}
        for check in non_blocking
    ):
        return "PASS WITH WARNINGS"
    return "PASS"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Normalize smoke-check JSON into one decision."
    )
    parser.add_argument("path", nargs="?", default="-", help="JSON file or -")
    args = parser.parse_args()

    try:
        payload = load_payload(args.path)
        raw_checks = payload.get("checks") if isinstance(payload, dict) else payload
        if not isinstance(raw_checks, list):
            raise ValueError("Input must be a JSON array or an object with checks[]")
        checks = [
            normalize_check(check, index) for index, check in enumerate(raw_checks)
        ]
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        print(
            json.dumps(
                {"overall": "BLOCKED", "reason": str(exc), "checks": []},
                ensure_ascii=False,
                indent=2,
            )
        )
        return 2

    overall = decide(checks)
    counts = Counter(check["status"] for check in checks)
    result = {
        "overall": overall,
        "counts": {
            "total": len(checks),
            "blocking": sum(1 for check in checks if check["blocking"]),
            "non_blocking": sum(1 for check in checks if not check["blocking"]),
            **dict(sorted(counts.items())),
        },
        "checks": checks,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return {"PASS": 0, "PASS WITH WARNINGS": 0, "FAIL": 1, "BLOCKED": 2}[overall]


if __name__ == "__main__":
    raise SystemExit(main())
