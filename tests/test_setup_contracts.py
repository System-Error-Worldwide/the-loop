from __future__ import annotations

import json
import stat
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from the_loop.setup import (  # noqa: E402
    SetupError,
    apply_install,
    detect_harnesses,
    load_adapter_manifests,
    plan_install,
    rollback_install,
)
from the_loop.validation import validate_record  # noqa: E402


FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "installation"


def _finder(*installed: str):
    paths = {name: f"/synthetic/bin/{name}" for name in installed}
    return paths.get


class SetupContractTests(unittest.TestCase):
    def test_loads_exact_four_generic_adapter_manifests(self) -> None:
        manifests = load_adapter_manifests(FIXTURE_ROOT)
        self.assertEqual(set(manifests), {"codex", "claude_code", "kimi_code", "opencode"})
        self.assertTrue(all(item["status"] == "verified" for item in manifests.values()))

    def test_detects_installed_harnesses_independently(self) -> None:
        manifests = load_adapter_manifests(FIXTURE_ROOT)
        detected = detect_harnesses(manifests, executable_finder=_finder("codex", "opencode"))
        self.assertTrue(detected["codex"]["installed"])
        self.assertFalse(detected["claude_code"]["installed"])
        self.assertFalse(detected["kimi_code"]["installed"])
        self.assertTrue(detected["opencode"]["installed"])

    def test_detection_checks_each_declared_executable_once(self) -> None:
        manifests = load_adapter_manifests(FIXTURE_ROOT)
        calls = []

        def finder(name):
            calls.append(name)
            return f"/synthetic/bin/{name}"

        detect_harnesses(manifests, executable_finder=finder)
        self.assertEqual(calls, ["codex", "claude", "kimi", "opencode"])

    def test_dry_run_is_read_only_and_deduplicates_shared_roots(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "project"
            target.mkdir()
            before = sorted(path.relative_to(target) for path in target.rglob("*"))
            plan = plan_install(
                FIXTURE_ROOT / "source",
                target,
                FIXTURE_ROOT,
                harnesses=["codex", "kimi_code", "opencode"],
                executable_finder=_finder("codex", "kimi", "opencode"),
            )
            after = sorted(path.relative_to(target) for path in target.rglob("*"))
            destinations = [item["destination"] for item in plan["operations"] if item["action"] == "copy"]
            self.assertEqual(before, after)
            self.assertEqual(destinations.count(".agents/skills/example"), 1)
            self.assertEqual(plan["approval_required"], [])

    def test_collision_requires_exact_destination_approval(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "project"
            collision = target / ".agents" / "skills" / "example"
            collision.mkdir(parents=True)
            (collision / "SKILL.md").write_text("unknown\n", encoding="utf-8")
            plan = plan_install(
                FIXTURE_ROOT / "source",
                target,
                FIXTURE_ROOT,
                harnesses=["codex"],
                executable_finder=_finder("codex"),
            )
            self.assertEqual(plan["approval_required"], [".agents/skills/example"])
            with self.assertRaisesRegex(SetupError, "exact approval"):
                apply_install(plan, actor="tester", source_version="0.1")
            receipt = apply_install(
                plan,
                actor="tester",
                source_version="0.1",
                approved_destinations=[".agents/skills/example"],
            )
            self.assertEqual(receipt["result"], "complete")

    def test_link_mode_requires_explicit_proof(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "project"
            target.mkdir()
            with self.assertRaisesRegex(SetupError, "link support"):
                plan_install(
                    FIXTURE_ROOT / "source",
                    target,
                    FIXTURE_ROOT,
                    harnesses=["codex"],
                    mode="link",
                    executable_finder=_finder("codex"),
                )

    def test_proven_link_mode_applies_and_rolls_back_the_link_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "project"
            target.mkdir()
            plan = plan_install(
                FIXTURE_ROOT / "source",
                target,
                FIXTURE_ROOT,
                harnesses=["codex"],
                mode="link",
                prove_link_support=True,
                executable_finder=_finder("codex"),
            )
            receipt = apply_install(plan, actor="tester", source_version="0.1")
            installed = target / ".agents" / "skills" / "example"
            self.assertTrue(installed.is_symlink())
            rollback_install(receipt, target_root=target)
            self.assertFalse(installed.exists())
            self.assertTrue((FIXTURE_ROOT / "source" / ".agents" / "skills" / "example" / "SKILL.md").is_file())

    def test_apply_emits_schema_valid_receipt_and_rollback_removes_unchanged_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "project"
            target.mkdir()
            plan = plan_install(
                FIXTURE_ROOT / "source",
                target,
                FIXTURE_ROOT,
                harnesses=["codex"],
                executable_finder=_finder("codex"),
            )
            receipt = apply_install(plan, actor="tester", source_version="0.1")
            validate_record("install_receipt", receipt)
            receipt_path = target / ".the-loop" / "installs" / f"{receipt['receipt_id']}.json"
            self.assertTrue(receipt_path.is_file())
            self.assertTrue((target / ".agents" / "skills" / "example" / "SKILL.md").is_file())
            result = rollback_install(receipt, target_root=target)
            self.assertEqual(result["result"], "rolled_back")
            self.assertFalse((target / ".agents" / "skills" / "example").exists())

    def test_receipt_directories_are_owner_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "project"
            target.mkdir()
            plan = plan_install(
                FIXTURE_ROOT / "source",
                target,
                FIXTURE_ROOT,
                harnesses=["codex"],
                executable_finder=_finder("codex"),
            )
            apply_install(plan, actor="tester", source_version="0.1")
            self.assertEqual(stat.S_IMODE((target / ".the-loop").stat().st_mode), 0o700)
            self.assertEqual(stat.S_IMODE((target / ".the-loop" / "installs").stat().st_mode), 0o700)

    def test_rollback_preserves_changed_receipt_owned_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "project"
            target.mkdir()
            plan = plan_install(
                FIXTURE_ROOT / "source",
                target,
                FIXTURE_ROOT,
                harnesses=["codex"],
                executable_finder=_finder("codex"),
            )
            receipt = apply_install(plan, actor="tester", source_version="0.1")
            installed = target / ".agents" / "skills" / "example" / "SKILL.md"
            installed.write_text("user change\n", encoding="utf-8")
            result = rollback_install(receipt, target_root=target)
            self.assertEqual(result["result"], "partial")
            self.assertEqual(installed.read_text(encoding="utf-8"), "user change\n")

    def test_interrupted_apply_restores_pre_existing_destination(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "project"
            collision = target / ".agents" / "skills" / "example"
            collision.mkdir(parents=True)
            original = collision / "SKILL.md"
            original.write_text("original\n", encoding="utf-8")
            plan = plan_install(
                FIXTURE_ROOT / "source",
                target,
                FIXTURE_ROOT,
                harnesses=["codex"],
                executable_finder=_finder("codex"),
            )

            def fail(stage, operation):
                if stage == "after_operation" and operation["destination"] == ".agents/skills/example":
                    raise RuntimeError("synthetic interruption")

            with self.assertRaisesRegex(RuntimeError, "synthetic interruption"):
                apply_install(
                    plan,
                    actor="tester",
                    source_version="0.1",
                    approved_destinations=[".agents/skills/example"],
                    fault_injector=fail,
                )
            self.assertEqual(original.read_text(encoding="utf-8"), "original\n")
            self.assertFalse((target / ".the-loop" / "installs").exists())

    def test_receipt_write_failure_restores_promoted_backup(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "project"
            collision = target / ".agents" / "skills" / "example"
            collision.mkdir(parents=True)
            original = collision / "SKILL.md"
            original.write_text("original\n", encoding="utf-8")
            plan = plan_install(
                FIXTURE_ROOT / "source",
                target,
                FIXTURE_ROOT,
                harnesses=["codex"],
                executable_finder=_finder("codex"),
            )

            def fail(stage, operation):
                if stage == "before_receipt_write":
                    raise RuntimeError("synthetic receipt failure")

            with self.assertRaisesRegex(RuntimeError, "synthetic receipt failure"):
                apply_install(
                    plan,
                    actor="tester",
                    source_version="0.1",
                    approved_destinations=[".agents/skills/example"],
                    fault_injector=fail,
                )
            self.assertEqual(original.read_text(encoding="utf-8"), "original\n")
            self.assertFalse((target / ".the-loop" / "installs").exists())

    def test_receipt_rollback_restores_approved_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "project"
            collision = target / ".agents" / "skills" / "example"
            collision.mkdir(parents=True)
            original = collision / "SKILL.md"
            original.write_text("original\n", encoding="utf-8")
            plan = plan_install(
                FIXTURE_ROOT / "source",
                target,
                FIXTURE_ROOT,
                harnesses=["codex"],
                executable_finder=_finder("codex"),
            )
            receipt = apply_install(
                plan,
                actor="tester",
                source_version="0.1",
                approved_destinations=[".agents/skills/example"],
            )
            result = rollback_install(receipt, target_root=target)
            self.assertEqual(result["result"], "rolled_back")
            self.assertEqual(original.read_text(encoding="utf-8"), "original\n")

    def test_rollback_refuses_tampered_replacement_backup(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "project"
            collision = target / ".agents" / "skills" / "example"
            collision.mkdir(parents=True)
            original = collision / "SKILL.md"
            original.write_text("original\n", encoding="utf-8")
            plan = plan_install(
                FIXTURE_ROOT / "source",
                target,
                FIXTURE_ROOT,
                harnesses=["codex"],
                executable_finder=_finder("codex"),
            )
            receipt = apply_install(
                plan,
                actor="tester",
                source_version="0.1",
                approved_destinations=[".agents/skills/example"],
            )
            backup = target / ".the-loop" / "installs" / f"{receipt['receipt_id']}.backup" / ".agents" / "skills" / "example" / "SKILL.md"
            backup.write_text("tampered backup\n", encoding="utf-8")
            installed_before = original.read_text(encoding="utf-8")
            result = rollback_install(receipt, target_root=target)
            self.assertEqual(result["result"], "partial")
            self.assertEqual(original.read_text(encoding="utf-8"), installed_before)

    def test_missing_or_malformed_adapter_fails_precisely(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "adapters" / "codex").mkdir(parents=True)
            (root / "adapters" / "codex" / "adapter.json").write_text("{}\n", encoding="utf-8")
            manifests = load_adapter_manifests(root)
            self.assertEqual(manifests["codex"]["status"], "failed")
            self.assertIn("missing keys", manifests["codex"]["error"])
            self.assertEqual(manifests["opencode"]["status"], "failed")
            self.assertIn("missing", manifests["opencode"]["error"])

    def test_plan_and_receipt_capture_no_prompts_or_environment(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "project"
            target.mkdir()
            plan = plan_install(
                FIXTURE_ROOT / "source",
                target,
                FIXTURE_ROOT,
                harnesses=["codex"],
                executable_finder=_finder("codex"),
            )
            receipt = apply_install(plan, actor="tester", source_version="0.1")
            serialized = json.dumps({"plan": plan, "receipt": receipt})
            self.assertNotIn("prompt", serialized.lower())
            self.assertNotIn("environment", serialized.lower())


if __name__ == "__main__":
    unittest.main()
