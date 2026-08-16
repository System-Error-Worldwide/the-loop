#!/usr/bin/env python3
"""Command-line entry point for read-only THE LOOP diagnostics."""

from __future__ import annotations

import argparse
import json
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
            stderr=subprocess.STDOUT,
            check=False,
            text=True,
            timeout=1.5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    line = result.stdout.splitlines()[0].strip() if result.stdout else ""
    return line[:200] or None


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read-only THE LOOP compatibility diagnostics.")
    parser.add_argument("--repository-root", type=Path, default=ROOT)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--user-home", type=Path)
    parser.add_argument("--probe", action="store_true", help="Request behavior probes when an adapter provides one.")
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
    try:
        report = run_doctor(
            args.repository_root,
            args.project_root,
            user_home=args.user_home,
            version_reader=_version,
            behavior_probe=None,
        )
        if args.probe:
            report["probe_note"] = "No adapter-declared behavior probe was available; behavior remains unverified."
        _emit(report, as_json=args.json)
    except (OSError, ValueError, SetupError) as exc:
        print(f"DOCTOR BLOCKED: {exc}", file=sys.stderr)
        return 2
    return {"ready": 0, "warning": 1, "blocked": 2}[report["overall_status"]]


if __name__ == "__main__":
    raise SystemExit(main())
