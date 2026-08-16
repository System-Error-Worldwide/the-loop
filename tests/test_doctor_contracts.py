from __future__ import annotations

import importlib.util
import os
import shutil
import sys
import tempfile
import time
import unittest
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from the_loop.doctor import run_doctor  # noqa: E402
from the_loop.setup import apply_install, plan_install  # noqa: E402


FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "installation"
CLI_PATH = ROOT / "scripts" / "the_loop_doctor.py"
CLI_SPEC = importlib.util.spec_from_file_location("the_loop_doctor_cli", CLI_PATH)
assert CLI_SPEC and CLI_SPEC.loader
DOCTOR_CLI = importlib.util.module_from_spec(CLI_SPEC)
CLI_SPEC.loader.exec_module(DOCTOR_CLI)


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


def _verified_probe(
    harness: str,
    version: str,
    evidence_id: str,
    environment_digest: str,
    *,
    capability: str = "portable-skill-invocation",
) -> dict[str, str]:
    return {
        "status": "verified",
        "evidence_id": evidence_id,
        "harness": harness,
        "harness_version": version,
        "scope": "project",
        "capability": capability,
        "permission_outcome": "allowed",
        "environment_digest": environment_digest,
        "observed_at": "2026-08-16T12:00:00Z",
    }


def _install_pack(project: Path, harnesses: list[str] | None = None) -> None:
    plan = plan_install(
        ROOT,
        project,
        ROOT,
        harnesses=harnesses or ["codex"],
        executable_finder=_finder("codex", "claude", "kimi", "opencode"),
    )
    apply_install(plan, actor="doctor-test", source_version="0.1.0")


class DoctorContractTests(unittest.TestCase):
    def test_cli_does_not_offer_an_inert_probe_flag(self) -> None:
        options = {
            option
            for action in DOCTOR_CLI._parser()._actions
            for option in action.option_strings
        }
        self.assertNotIn("--probe", options)

    @unittest.skipUnless(os.name == "posix", "synthetic executable requires POSIX shell")
    def test_version_reader_ignores_stderr_diagnostics_before_stdout_version(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / "fake-harness"
            executable.write_text(
                "#!/bin/sh\n"
                "echo 'WARNING: diagnostic before version' >&2\n"
                "echo 'fake-harness 1.2.3'\n",
                encoding="utf-8",
            )
            executable.chmod(0o700)
            self.assertEqual("fake-harness 1.2.3", DOCTOR_CLI._version(str(executable)))

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
            self.assertEqual(codex["pack_status"], "incomplete")
            self.assertEqual(codex["outcome"], "pack_incomplete")

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

    def test_untyped_verified_probe_fails_while_negative_states_are_preserved(self) -> None:
        expected = {
            "codex": "failed",
            "claude_code": "denied",
            "kimi_code": "failed",
            "opencode": "unverified",
        }
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            _install_pack(project, ["codex", "claude_code", "kimi_code", "opencode"])
            report = run_doctor(
                ROOT,
                project,
                executable_finder=_finder("codex", "claude", "kimi", "opencode"),
                version_reader=lambda _path: "1.2.3",
                behavior_probe=lambda harness, manifest: expected[harness],
                checked_at="2026-08-16T12:00:00Z",
            )
            self.assertEqual({key: value["behavior"] for key, value in report["harnesses"].items()}, expected)

    def test_behavior_probe_requires_complete_typed_matching_evidence(self) -> None:
        evidence_id = str(uuid.uuid4())
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            _install_pack(project)
            report = run_doctor(
                ROOT,
                project,
                executable_finder=_finder("codex"),
                version_reader=lambda _path: "1.2.3",
                behavior_probe=lambda harness, manifest: _verified_probe(
                    harness,
                    "1.2.3",
                    evidence_id,
                    manifest["_doctor_context"]["environment_digest"],
                ),
                checked_at="2026-08-16T12:00:00Z",
            )
            self.assertEqual(report["harnesses"]["codex"]["behavior"], "verified")
            self.assertEqual(report["harnesses"]["codex"]["evidence_id"], evidence_id)
            self.assertEqual(report["harnesses"]["codex"]["outcome"], "ready")
            self.assertEqual(report["harnesses"]["codex"]["pack_status"], "complete")

    def test_probe_and_pack_integrity_must_match_the_current_doctor_context(self) -> None:
        evidence_id = str(uuid.uuid4())
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            _install_pack(project)

            unrelated = run_doctor(
                ROOT,
                project,
                executable_finder=_finder("codex"),
                version_reader=lambda _path: "1.2.3",
                behavior_probe=lambda harness, manifest: _verified_probe(
                    harness,
                    "1.2.3",
                    evidence_id,
                    manifest["_doctor_context"]["environment_digest"],
                    capability="billing.charge",
                ),
                checked_at="2026-08-16T12:00:00Z",
            )
            self.assertEqual("failed", unrelated["harnesses"]["codex"]["behavior"])
            self.assertNotEqual("ready", unrelated["overall_status"])

            arbitrary_digest = run_doctor(
                ROOT,
                project,
                executable_finder=_finder("codex"),
                version_reader=lambda _path: "1.2.3",
                behavior_probe=lambda harness, _manifest: _verified_probe(
                    harness, "1.2.3", evidence_id, "0" * 64
                ),
                checked_at="2026-08-16T12:00:00Z",
            )
            self.assertEqual("failed", arbitrary_digest["harnesses"]["codex"]["behavior"])

            build = project / ".agents" / "skills" / "build" / "SKILL.md"
            build.write_text(
                "---\nname: build\ndescription: Synthetic.\nlicense: MIT\n"
                "compatibility: Codex, Claude Code, Kimi Code and OpenCode\n---\n\nNo behavior.\n",
                encoding="utf-8",
            )
            corrupted_skill = run_doctor(
                ROOT,
                project,
                executable_finder=_finder("codex"),
                version_reader=lambda _path: "1.2.3",
                behavior_probe=lambda harness, manifest: _verified_probe(
                    harness,
                    "1.2.3",
                    evidence_id,
                    manifest["_doctor_context"]["environment_digest"],
                ),
                checked_at="2026-08-16T12:00:00Z",
            )
            self.assertEqual("integrity_unverified", corrupted_skill["harnesses"]["codex"]["pack_status"])
            self.assertNotEqual("ready", corrupted_skill["overall_status"])

    def test_missing_toolkit_support_cannot_report_pack_complete(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            _install_pack(project)
            (project / ".the-loop" / "toolkit" / "protocols" / "run-state-leases.md").unlink()
            report = run_doctor(
                ROOT,
                project,
                executable_finder=_finder("codex"),
                version_reader=lambda _path: "1.2.3",
                checked_at="2026-08-16T12:00:00Z",
            )
            self.assertEqual("integrity_unverified", report["harnesses"]["codex"]["pack_status"])
            self.assertNotEqual("ready", report["overall_status"])

    def test_receipt_and_winning_packages_are_bound_to_the_same_install_target(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            installed = root / "installed"
            borrower = root / "borrower"
            installed.mkdir()
            borrower.mkdir()
            _install_pack(installed)
            shutil.copytree(installed / ".agents", borrower / ".agents")
            borrowed_installs = borrower / ".the-loop" / "installs"
            borrowed_installs.mkdir(parents=True, mode=0o700)
            receipt = next((installed / ".the-loop" / "installs").glob("*.json"))
            shutil.copy2(receipt, borrowed_installs / receipt.name)

            report = run_doctor(
                ROOT,
                borrower,
                executable_finder=_finder("codex"),
                version_reader=lambda _path: "1.2.3",
                checked_at="2026-08-16T12:00:00Z",
            )
            codex = report["harnesses"]["codex"]
            self.assertFalse((borrower / ".the-loop" / "toolkit").exists())
            self.assertEqual("integrity_unverified", codex["pack_status"])
            self.assertNotEqual("ready", codex["outcome"])
            self.assertNotEqual("ready", report["overall_status"])

    def test_uuid_status_only_probe_and_unrelated_skill_never_report_ready(self) -> None:
        evidence_id = str(uuid.uuid4())
        calls: list[str] = []
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            _skill(project / ".agents" / "skills", "unrelated")
            report = run_doctor(
                FIXTURE_ROOT,
                project,
                executable_finder=_finder("codex"),
                version_reader=lambda _path: None,
                behavior_probe=lambda harness, _manifest: calls.append(harness) or {"status": "verified", "evidence_id": evidence_id},
                checked_at="2026-08-16T12:00:00Z",
            )
        codex = report["harnesses"]["codex"]
        self.assertEqual("incomplete", codex["pack_status"])
        self.assertEqual("unverified", codex["behavior"])
        self.assertEqual("pack_incomplete", codex["outcome"])
        self.assertNotEqual("ready", report["overall_status"])
        self.assertEqual([], calls)

    def test_custom_codex_home_is_resolved_from_explicit_environment(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "project"
            project.mkdir()
            (root / "ordinary-home").mkdir()
            custom = root / "custom-codex"
            _skill(custom / "skills", "the-loop")
            report = run_doctor(
                FIXTURE_ROOT,
                project,
                user_home=root / "ordinary-home",
                environment={"CODEX_HOME": str(custom)},
                executable_finder=_finder("codex"),
                checked_at="2026-08-16T12:00:00Z",
            )
        sources = [item["source"] for item in report["harnesses"]["codex"]["skills"]]
        self.assertIn("$CODEX_HOME/skills/the-loop", sources)

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
