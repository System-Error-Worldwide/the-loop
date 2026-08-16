#!/usr/bin/env python3
"""Run the deterministic portable contract matrix."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from the_loop.conformance import run_contract_conformance  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, default=ROOT)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--checked-at")
    args = parser.parse_args()
    report = run_contract_conformance(
        args.repository_root,
        args.project_root,
        checked_at=args.checked_at,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["summary"]["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
