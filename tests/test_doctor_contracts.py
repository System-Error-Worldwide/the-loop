from __future__ import annotations

import os
import sys
import tempfile
import time
import unittest
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from the_loop.doctor import run_doctor  # noqa: E402


FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "installation"


def _finder(*installed: str):
    paths = {name: f"/synthetic/bin/{name}" for name in installed}
    return paths.get


def _skill(root: Path, name: str, *, valid: bool = True) -> None:
    directory = root / name
    directory.mkdir(parents=True, exist_ok=True)
    if valid:
        content = (
            "---\n"
            f"name: {name}\n"
            "description: Synthetic skill.\n"
            "license: MIT\n"
            "compatibility: Codex, Claude Code, Kimi Code and OpenCode\n"
            "---\n\n# Synthetic\n"
        )
    else:
        content = "# Missing frontmatter\n"
    (directory / "SKILL.md").write_text(content, encoding="utf-8")


def _snapshot(root: Path):
    result = []
    for path in sorted(root.rglob("*")):
        info = path.lstat()
        result.append((path.relative_to(root).as_posix(), info.st_mode, info.st_size, path.read_bytes() if path.is_file() else None))
    return result


class DoctorContractTests(unittest.TestCase):
    def test_reports_all_four_harnesses_and_keeps_absence_separate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            _skill(project / ".agents" / "skills", "example")
            report = run_doctor(
                FIXTURE_ROOT,
                project,
                executable_finder=_finder("codex"),
                version_reader=lambda path: "1.2.3",
                checked_at="2026-08-16T12:00:00Z",
            )
            self.assertEqual(set(report["harnesses"]), {"codex", "claude_code", "kimi_code", "opencode"})
            self.assertTrue(report["harnesses"]["codex"]["installed"])
            self.assertEqual(report["harnesses"]["codex"]["version"], "1.2.3")
            self.assertFalse(report["harnesses"]["claude_code"]["installed"])
            self.assertEqual(report["harnesses"]["claude_code"]["outcome"], "not_installed")

    def test_discovery_and_behavior_are_independent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            _skill(project / ".agents" / "skills", "example")
            report = run_doctor(
                FIXTURE_ROOT,
                project,
                executable_finder=_finder("codex"),
                checked_at="2026-08-16T12:00:00Z",
            )
            codex = report["harnesses"]["codex"]
            self.assertEqual(codex["discovery"], "verified")
            self.assertEqual(codex["behavior"], "unverified")
            self.assertEqual(codex["outcome"], "behavior_unverified")

    def test_reports_collision_sources_and_winning_precedence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            home = project / "home"
            _skill(project / ".agents" / "skills", "example")
            _skill(home / ".codex" / "skills", "example")
            report = run_doctor(
                FIXTURE_ROOT,
                project,
                user_home=home,
                executable_finder=_finder("codex"),
                checked_at="2026-08-16T12:00:00Z",
            )
            collision = report["harnesses"]["codex"]["collisions"][0]
            self.assertEqual(collision["name"], "example")
            self.assertEqual(collision["winner"], ".agents/skills/example")
            self.assertEqual(len(collision["sources"]), 2)

    def test_invalid_frontmatter_is_not_discoverable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            _skill(project / ".agents" / "skills", "broken", valid=False)
            report = run_doctor(
                FIXTURE_ROOT,
                project,
                executable_finder=_finder("codex"),
                checked_at="2026-08-16T12:00:00Z",
            )
            codex = report["harnesses"]["codex"]
            self.assertEqual(codex["discovery"], "failed")
            self.assertEqual(codex["outcome"], "not_discoverable")
            self.assertEqual(codex["skills"][0]["status"], "invalid_frontmatter")

    def test_behavior_probe_preserves_verified_denied_failed_and_unverified(self) -> None:
        expected = {
            "codex": "verified",
            "claude_code": "denied",
            "kimi_code": "failed",
            "opencode": "unverified",
        }
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            for root in (".agents/skills", ".claude/skills", ".kimi-code/skills", ".opencode/skills"):
                _skill(project / root, "example")
            report = run_doctor(
                FIXTURE_ROOT,
                project,
                executable_finder=_finder("codex", "claude", "kimi", "opencode"),
                behavior_probe=lambda harness, manifest: expected[harness],
                checked_at="2026-08-16T12:00:00Z",
            )
            self.assertEqual({key: value["behavior"] for key, value in report["harnesses"].items()}, expected)

    def test_behavior_probe_can_attach_typed_evidence_without_changing_status(self) -> None:
        evidence_id = str(uuid.uuid4())
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            _skill(project / ".agents" / "skills", "example")
            report = run_doctor(
                FIXTURE_ROOT,
                project,
                executable_finder=_finder("codex"),
                behavior_probe=lambda harness, manifest: {"status": "verified", "evidence_id": evidence_id},
                checked_at="2026-08-16T12:00:00Z",
            )
            self.assertEqual(report["harnesses"]["codex"]["behavior"], "verified")
            self.assertEqual(report["harnesses"]["codex"]["evidence_id"], evidence_id)

    def test_missing_and_malformed_manifests_are_precise(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "adapters" / "codex").mkdir(parents=True)
            (root / "adapters" / "codex" / "adapter.json").write_text("not json", encoding="utf-8")
            report = run_doctor(root, root, executable_finder=_finder(), checked_at="2026-08-16T12:00:00Z")
            self.assertEqual(report["harnesses"]["codex"]["outcome"], "adapter_invalid")
            self.assertIn("JSON", report["harnesses"]["codex"]["issues"][0])
            self.assertEqual(report["harnesses"]["opencode"]["outcome"], "adapter_missing")

    @unittest.skipUnless(hasattr(os, "chmod"), "permission mode test requires chmod")
    def test_unsafe_config_permissions_are_reported_without_writes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            state = project / ".the-loop"
            state.mkdir(mode=0o700)
            config = state / "config.json"
            config.write_text("{}\n", encoding="utf-8")
            config.chmod(0o644)
            report = run_doctor(
                FIXTURE_ROOT,
                project,
                executable_finder=_finder(),
                checked_at="2026-08-16T12:00:00Z",
            )
            self.assertEqual(report["config"]["status"], "permission_denied")

    def test_unsafe_state_directory_permissions_are_reported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            state = project / ".the-loop"
            state.mkdir(mode=0o755)
            report = run_doctor(
                FIXTURE_ROOT,
                project,
                executable_finder=_finder(),
                checked_at="2026-08-16T12:00:00Z",
            )
            self.assertEqual(report["state"]["status"], "permission_denied")

    def test_doctor_is_read_only_and_completes_well_below_ten_seconds(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            _skill(project / ".agents" / "skills", "example")
            before = _snapshot(project)
            started = time.monotonic()
            run_doctor(
                FIXTURE_ROOT,
                project,
                executable_finder=_finder("codex"),
                checked_at="2026-08-16T12:00:00Z",
            )
            elapsed = time.monotonic() - started
            self.assertEqual(_snapshot(project), before)
            self.assertLess(elapsed, 1.0)


if __name__ == "__main__":
    unittest.main()
