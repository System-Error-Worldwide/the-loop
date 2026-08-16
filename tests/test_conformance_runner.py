from __future__ import annotations

import json
import sys
import tempfile
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from the_loop.conformance import run_contract_conformance  # noqa: E402


def synthetic_finder(name: str) -> str:
    return f"/synthetic/bin/{name}"


class ConformanceRunnerContracts(unittest.TestCase):
    def test_four_harnesses_each_cover_twelve_contract_scenarios(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            started = time.monotonic()
            report = run_contract_conformance(
                ROOT,
                Path(directory),
                executable_finder=synthetic_finder,
                checked_at="2026-08-16T12:00:00Z",
            )
            elapsed = time.monotonic() - started

        self.assertEqual("contract_conformance", report["kind"])
        self.assertFalse(report["live_behavior_claim"])
        self.assertEqual(
            {"codex", "claude_code", "kimi_code", "opencode"},
            set(report["harnesses"]),
        )
        self.assertEqual({"passed": 48, "failed": 0, "total": 48}, report["summary"])
        for harness, evidence in report["harnesses"].items():
            with self.subTest(harness=harness):
                self.assertEqual(12, len(evidence["scenarios"]))
                self.assertEqual({"contract_passed"}, {item["status"] for item in evidence["scenarios"]})
                self.assertEqual("verified", evidence["discovery_status"])
                self.assertEqual("unverified", evidence["behavior_status"])
                self.assertEqual("behavior_unverified", evidence["doctor_outcome"])
                self.assertEqual([], evidence["collisions"])
                self.assertEqual("complete", evidence["install_result"])
        self.assertLess(elapsed, 10.0)

    def test_contract_failure_is_reported_and_cannot_become_false_green(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory) / "repository"
            project = Path(directory) / "projects"
            repository.mkdir()
            for relative in (".agents", "adapters", "tests/fixtures/conformance"):
                source = ROOT / relative
                destination = repository / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                if source.is_dir():
                    import shutil

                    shutil.copytree(source, destination)
            manifest = repository / "adapters" / "codex" / "adapter.json"
            data = json.loads(manifest.read_text(encoding="utf-8"))
            data["permission_model"]["allow_bypass"] = True
            manifest.write_text(json.dumps(data), encoding="utf-8")

            report = run_contract_conformance(
                repository,
                project,
                executable_finder=synthetic_finder,
                checked_at="2026-08-16T12:00:00Z",
            )

        self.assertGreater(report["summary"]["failed"], 0)
        self.assertNotEqual(report["summary"]["total"], report["summary"]["passed"])
        self.assertTrue(any(item["status"] == "contract_failed" for item in report["harnesses"]["codex"]["scenarios"]))


if __name__ == "__main__":
    unittest.main()
