#!/usr/bin/env python3
"""Command-line entry point for the portable THE LOOP installer."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from the_loop.setup import (  # noqa: E402
    SUPPORTED_HARNESSES,
    SetupError,
    apply_install,
    plan_install,
    rollback_install,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Plan, apply, or roll back a THE LOOP installation.")
    parser.add_argument("--source-root", type=Path, default=ROOT)
    parser.add_argument("--target-root", type=Path)
    parser.add_argument("--repository-root", type=Path, default=ROOT)
    parser.add_argument(
        "--harness",
        action="append",
        choices=SUPPORTED_HARNESSES,
    )
    parser.add_argument("--scope", choices=("project", "user"), default="project")
    parser.add_argument("--mode", choices=("copy", "link"), default="copy")
    parser.add_argument("--prove-link-support", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--approve-destination", action="append", default=[])
    parser.add_argument("--actor")
    parser.add_argument("--source-version")
    parser.add_argument("--rollback-receipt", type=Path)
    parser.add_argument("--json", action="store_true")
    return parser


def _emit(value: dict, *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(value, indent=2, sort_keys=True))
        return
    if "approval_required" in value:
        print(f"INSTALL PLAN: {len(value['operations'])} operations")
        print(f"TARGET: {value['target_root']}")
        print("APPROVAL REQUIRED: " + (", ".join(value["approval_required"]) or "none"))
    else:
        print(f"INSTALL {str(value['result']).upper()}: receipt {value['receipt_id']}")


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.rollback_receipt is not None:
            receipt = json.loads(args.rollback_receipt.read_text(encoding="utf-8"))
            result = rollback_install(receipt, target_root=args.target_root)
            _emit(result, as_json=args.json)
            return 0 if result["result"] == "rolled_back" else 1
        if args.target_root is None:
            raise SetupError("--target-root is required")
        plan = plan_install(
            args.source_root,
            args.target_root,
            args.repository_root,
            harnesses=args.harness,
            scope=args.scope,
            mode=args.mode,
            prove_link_support=args.prove_link_support,
        )
        if not args.apply:
            _emit(plan, as_json=args.json)
            return 0
        if not args.actor or not args.source_version:
            raise SetupError("--actor and --source-version are required with --apply")
        receipt = apply_install(
            plan,
            actor=args.actor,
            source_version=args.source_version,
            approved_destinations=args.approve_destination,
        )
        _emit(receipt, as_json=args.json)
        return 0
    except (OSError, ValueError, SetupError) as exc:
        print(f"SETUP FAILED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
