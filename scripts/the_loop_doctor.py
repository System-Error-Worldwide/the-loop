#!/usr/bin/env python3
"""Command-line entry point for read-only THE LOOP diagnostics."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from the_loop.doctor import run_doctor  # noqa: E402
from the_loop.setup import SetupError  # noqa: E402


def _version(executable: str) -> str | None:
    try:
        result = subprocess.run(
            [executable, "--version"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            text=True,
            timeout=1.5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    stdout_lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if stdout_lines:
        return stdout_lines[0][:200]
    stderr_lines = [
        line.strip()
        for line in result.stderr.splitlines()
        if line.strip() and not line.lstrip().lower().startswith(("warning:", "error:"))
    ]
    return stderr_lines[0][:200] if stderr_lines else None


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read-only THE LOOP compatibility diagnostics.")
    parser.add_argument("--repository-root", type=Path, default=ROOT)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--user-home", type=Path, default=Path.home())
    parser.add_argument("--codex-home", type=Path)
    parser.add_argument("--kimi-code-home", type=Path)
    parser.add_argument("--dsh-home", type=Path)
    parser.add_argument("--dsh-agents-home", type=Path)
    parser.add_argument("--json", action="store_true")
    return parser


def _emit(report: dict, *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(report, indent=2, sort_keys=True))
        return
    print(f"DOCTOR {report['overall_status'].upper()}")
    for harness, result in report["harnesses"].items():
        print(f"{harness}: {result['outcome']} (discovery={result['discovery']}, behavior={result['behavior']})")
    print(f"config: {report['config']['status']}")


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    environment = {
        key: value
        for key, value in {
            "CODEX_HOME": str(args.codex_home) if args.codex_home else os.environ.get("CODEX_HOME"),
            "KIMI_CODE_HOME": str(args.kimi_code_home) if args.kimi_code_home else os.environ.get("KIMI_CODE_HOME"),
            "DSH_HOME": str(args.dsh_home) if args.dsh_home else os.environ.get("DSH_HOME"),
            "DSH_AGENTS_HOME": (
                str(args.dsh_agents_home)
                if args.dsh_agents_home
                else os.environ.get("DSH_AGENTS_HOME")
            ),
        }.items()
        if value
    }
    try:
        report = run_doctor(
            args.repository_root,
            args.project_root,
            user_home=args.user_home,
            version_reader=_version,
            behavior_probe=None,
            environment=environment,
        )
        _emit(report, as_json=args.json)
    except (OSError, ValueError, SetupError) as exc:
        print(f"DOCTOR BLOCKED: {exc}", file=sys.stderr)
        return 2
    return {"ready": 0, "warning": 1, "blocked": 2}[report["overall_status"]]


if __name__ == "__main__":
    raise SystemExit(main())
