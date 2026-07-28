#!/usr/bin/env python3
"""Detect common project signals without executing project code."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def read_json(path: Path, warnings: list[str]) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        warnings.append(f"Could not parse {path.name}: {exc}")
        return {}
    return value if isinstance(value, dict) else {}


def add_unique(items: list[Any], value: Any) -> None:
    if value not in items:
        items.append(value)


def detect(root: Path) -> dict[str, Any]:
    warnings: list[str] = []
    project_types: list[str] = []
    frameworks: list[str] = []
    signals: list[str] = []
    start_candidates: list[dict[str, str]] = []
    package_managers: list[str] = []

    file_signals = {
        "package.json": "node",
        "pyproject.toml": "python",
        "requirements.txt": "python",
        "Pipfile": "python",
        "pom.xml": "java-maven",
        "build.gradle": "java-gradle",
        "build.gradle.kts": "java-gradle",
        "go.mod": "go",
        "Cargo.toml": "rust",
        "Dockerfile": "container",
        "compose.yaml": "compose",
        "compose.yml": "compose",
        "docker-compose.yaml": "compose",
        "docker-compose.yml": "compose",
    }

    for filename, project_type in file_signals.items():
        if (root / filename).is_file():
            add_unique(signals, filename)
            add_unique(project_types, project_type)

    for lockfile, manager in (
        ("pnpm-lock.yaml", "pnpm"),
        ("yarn.lock", "yarn"),
        ("package-lock.json", "npm"),
        ("uv.lock", "uv"),
        ("poetry.lock", "poetry"),
    ):
        if (root / lockfile).is_file():
            add_unique(package_managers, manager)
            add_unique(signals, lockfile)
    node_managers = [
        manager for manager in package_managers if manager in {"pnpm", "yarn", "npm"}
    ]
    if len(node_managers) > 1:
        warnings.append(
            "Multiple Node lockfiles found; confirm the intended package manager."
        )

    package_path = root / "package.json"
    if package_path.is_file():
        package = read_json(package_path, warnings)
        scripts = package.get("scripts", {})
        script_runner = node_managers[0] if node_managers else "npm"
        if isinstance(scripts, dict):
            for script_name in ("start", "dev", "serve", "preview"):
                if isinstance(scripts.get(script_name), str):
                    start_candidates.append(
                        {
                            "source": "package.json",
                            "command": f"{script_runner} run {script_name}",
                            "reason": f"script '{script_name}' exists",
                        }
                    )
        dependencies: dict[str, Any] = {}
        for key in ("dependencies", "devDependencies"):
            value = package.get(key, {})
            if isinstance(value, dict):
                dependencies.update(value)
        framework_packages = {
            "next": "nextjs",
            "vite": "vite",
            "express": "express",
            "fastify": "fastify",
            "@nestjs/core": "nestjs",
            "react": "react",
            "vue": "vue",
            "svelte": "svelte",
        }
        for package_name, framework in framework_packages.items():
            if package_name in dependencies:
                add_unique(frameworks, framework)

    python_markers = ("manage.py", "app.py", "main.py", "wsgi.py", "asgi.py")
    for marker in python_markers:
        if (root / marker).is_file():
            add_unique(signals, marker)

    requirements = root / "requirements.txt"
    if requirements.is_file():
        try:
            content = requirements.read_text(encoding="utf-8").lower()
        except (OSError, UnicodeError) as exc:
            warnings.append(f"Could not read requirements.txt: {exc}")
            content = ""
        for token, framework in (
            ("fastapi", "fastapi"),
            ("flask", "flask"),
            ("django", "django"),
            ("uvicorn", "uvicorn"),
            ("gunicorn", "gunicorn"),
        ):
            if token in content:
                add_unique(frameworks, framework)

    if (root / "manage.py").is_file():
        add_unique(frameworks, "django")
        start_candidates.append(
            {
                "source": "manage.py",
                "command": "python3 manage.py runserver",
                "reason": "Django management entry point exists",
            }
        )
    if (root / "main.py").is_file() and "fastapi" in frameworks:
        start_candidates.append(
            {
                "source": "main.py",
                "command": "python3 -m uvicorn main:app",
                "reason": "FastAPI and main.py were detected",
            }
        )
    if any(value.startswith("java-") for value in project_types):
        if "java-maven" in project_types:
            start_candidates.append(
                {
                    "source": "pom.xml",
                    "command": "./mvnw spring-boot:run",
                    "reason": "Maven project detected; confirm wrapper and framework",
                }
            )
        if "java-gradle" in project_types:
            start_candidates.append(
                {
                    "source": "build.gradle",
                    "command": "./gradlew bootRun",
                    "reason": "Gradle project detected; confirm wrapper and framework",
                }
            )
    if "compose" in project_types:
        start_candidates.append(
            {
                "source": "compose configuration",
                "command": "docker compose up",
                "reason": "Compose configuration exists",
            }
        )

    return {
        "root": str(root),
        "project_types": project_types,
        "frameworks": frameworks,
        "package_managers": package_managers,
        "signals": signals,
        "start_candidates": start_candidates,
        "health_path_candidates": [
            "/health",
            "/healthz",
            "/ready",
            "/readiness",
            "/api/health",
        ],
        "warnings": warnings,
        "note": "Confirm candidates against project instructions before execution.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Detect common project signals without executing project code."
    )
    parser.add_argument("root", nargs="?", default=".", help="Project root")
    args = parser.parse_args()

    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        print(
            json.dumps(
                {"status": "BLOCKED", "reason": "Project root is not a directory"},
                ensure_ascii=False,
                indent=2,
            )
        )
        return 2

    result = detect(root)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
