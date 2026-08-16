from __future__ import annotations

import json
import os
import re
import shutil
import stat
import subprocess
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


CANONICAL_DOCS = "https://github.com/System-Error-Worldwide/the-loop/blob/main/"
SOURCE_DOC_LINK = re.compile(r"(\]\()\.\./\.\./\.\./((?:protocols|schemas|scripts)/[^)]+)(\))")
MARKDOWN_LINK = re.compile(r"\[[^]]+\]\(([^)]+)\)")


def _canonicalize_skill_links(repository: Path) -> int:
    replacements = 0
    for skill_file in sorted((repository / ".agents" / "skills").glob("*/SKILL.md")):
        original = skill_file.read_text(encoding="utf-8")

        def replace(match):
            nonlocal replacements
            replacements += 1
            return match.group(1) + CANONICAL_DOCS + match.group(2) + match.group(3)

        skill_file.write_text(SOURCE_DOC_LINK.sub(replace, original), encoding="utf-8")
    return replacements


def _resolved_documentation_links(skills_root: Path) -> tuple[int, list[str]]:
    resolved = 0
    failures: list[str] = []
    for skill_file in sorted(skills_root.glob("*/SKILL.md")):
        for target in MARKDOWN_LINK.findall(skill_file.read_text(encoding="utf-8")):
            if target.startswith(CANONICAL_DOCS):
                failures.append(f"remote:{skill_file.parent.name}:{target}")
                continue
            if target.startswith(("http://", "https://", "mailto:")):
                continue
            path = (skill_file.parent / target.split("#", 1)[0]).resolve()
            resolved += 1
            if not path.exists():
                failures.append(f"missing:{skill_file.parent.name}:{target}")
    return resolved, failures


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
                ROOT,
                harnesses=["codex", "kimi_code", "opencode"],
                executable_finder=_finder("codex", "kimi", "opencode"),
            )
            after = sorted(path.relative_to(target) for path in target.rglob("*"))
            destinations = [item["destination"] for item in plan["operations"] if item["action"] == "copy"]
            self.assertEqual(before, after)
            self.assertEqual(destinations.count(".agents/skills/example"), 1)
            self.assertEqual(plan["approval_required"], [])

    def test_each_harness_uses_one_preferred_project_install_root(self) -> None:
        expected = {
            "codex": ".agents/skills/example",
            "claude_code": ".claude/skills/example",
            "kimi_code": ".agents/skills/example",
            "opencode": ".agents/skills/example",
        }
        executables = ("codex", "claude", "kimi", "opencode")
        for harness, destination in expected.items():
            with self.subTest(harness=harness), tempfile.TemporaryDirectory() as directory:
                target = Path(directory) / "project"
                target.mkdir()
                plan = plan_install(
                    FIXTURE_ROOT / "source",
                    target,
                    ROOT,
                    harnesses=[harness],
                    executable_finder=_finder(*executables),
                )
                copies = [
                    operation["destination"]
                    for operation in plan["operations"]
                    if operation["action"] == "copy" and operation["destination"] != ".the-loop/toolkit"
                ]
                self.assertEqual([destination], copies)

    def test_each_harness_uses_one_preferred_user_install_root(self) -> None:
        expected = {
            "codex": ".agents/skills/example",
            "claude_code": ".claude/skills/example",
            "kimi_code": ".agents/skills/example",
            "opencode": ".agents/skills/example",
        }
        executables = ("codex", "claude", "kimi", "opencode")
        for harness, destination in expected.items():
            with self.subTest(harness=harness), tempfile.TemporaryDirectory() as directory:
                target = Path(directory) / "home"
                target.mkdir()
                plan = plan_install(
                    FIXTURE_ROOT / "source",
                    target,
                    ROOT,
                    harnesses=[harness],
                    scope="user",
                    executable_finder=_finder(*executables),
                )
                copies = [
                    operation["destination"]
                    for operation in plan["operations"]
                    if operation["action"] == "copy" and operation["destination"] != ".the-loop/toolkit"
                ]
                self.assertEqual([destination], copies)

    def test_collision_requires_exact_destination_approval(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "project"
            collision = target / ".agents" / "skills" / "example"
            collision.mkdir(parents=True)
            (collision / "SKILL.md").write_text("unknown\n", encoding="utf-8")
            plan = plan_install(
                FIXTURE_ROOT / "source",
                target,
                ROOT,
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
                    ROOT,
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
                ROOT,
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
                ROOT,
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
                ROOT,
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
                ROOT,
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
                ROOT,
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
                ROOT,
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
                ROOT,
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
                ROOT,
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
                ROOT,
                harnesses=["codex"],
                executable_finder=_finder("codex"),
            )
            receipt = apply_install(plan, actor="tester", source_version="0.1")
            serialized = json.dumps({"plan": plan, "receipt": receipt})
            self.assertNotIn("prompt", serialized.lower())
            self.assertNotIn("environment", serialized.lower())

    def test_apply_rejects_project_root_replacement_without_writing_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            target = parent / "project"
            target.mkdir()
            displaced = parent / "original-project"
            plan = plan_install(
                FIXTURE_ROOT / "source",
                target,
                ROOT,
                harnesses=["codex"],
                executable_finder=_finder("codex"),
            )
            swapped = False

            def swap_root(stage, operation):
                nonlocal swapped
                if stage == "before_operation" and not swapped:
                    target.rename(displaced)
                    target.mkdir()
                    swapped = True

            with self.assertRaisesRegex(SetupError, "identity|namespace|changed"):
                apply_install(
                    plan,
                    actor="tester",
                    source_version="0.1",
                    fault_injector=swap_root,
                )
            self.assertEqual(list(target.iterdir()), [])
            self.assertFalse((displaced / ".agents" / "skills" / "example" / "SKILL.md").exists())

    def test_apply_rejects_intermediate_symlink_swap_without_external_write(self) -> None:
        if not hasattr(os, "symlink"):
            self.skipTest("symlinks unavailable")
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            target = parent / "project"
            target.mkdir()
            external = parent / "external"
            (external / "skills").mkdir(parents=True)
            parked = target / ".agents-parked"
            plan = plan_install(
                FIXTURE_ROOT / "source",
                target,
                ROOT,
                harnesses=["codex"],
                executable_finder=_finder("codex"),
            )
            swapped = False

            def swap_intermediate(stage, operation):
                nonlocal swapped
                if (
                    stage == "before_operation"
                    and operation["destination"] == ".agents/skills/example"
                    and not swapped
                ):
                    (target / ".agents").rename(parked)
                    (target / ".agents").symlink_to(external, target_is_directory=True)
                    swapped = True

            with self.assertRaisesRegex(SetupError, "symlink|namespace|changed|rollback_incomplete"):
                apply_install(
                    plan,
                    actor="tester",
                    source_version="0.1",
                    fault_injector=swap_intermediate,
                )
            self.assertEqual(list((external / "skills").iterdir()), [])

    def test_apply_rechecks_prior_destination_namespaces_before_later_operations(self) -> None:
        if not hasattr(os, "symlink"):
            self.skipTest("symlinks unavailable")
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            target = parent / "project"
            target.mkdir()
            external = parent / "external"
            (external / "skills").mkdir(parents=True)
            parked = target / ".agents-parked"
            plan = plan_install(
                FIXTURE_ROOT / "source",
                target,
                ROOT,
                harnesses=["codex"],
                executable_finder=_finder("codex"),
            )
            last_copy = [operation for operation in plan["operations"] if operation["action"] == "copy"][-1]

            def swap_prior_namespace(stage, operation):
                if stage == "before_operation" and operation is last_copy:
                    (target / ".agents").rename(parked)
                    (target / ".agents").symlink_to(external, target_is_directory=True)

            with self.assertRaisesRegex(SetupError, "namespace|symlink|rollback_incomplete"):
                apply_install(
                    plan,
                    actor="tester",
                    source_version="0.1",
                    fault_injector=swap_prior_namespace,
                )
            self.assertEqual(list((external / "skills").iterdir()), [])
            self.assertFalse((target / ".the-loop" / "installs").exists())

    def test_failed_apply_preserves_concurrent_change_and_reports_rollback_incomplete(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "project"
            target.mkdir()
            plan = plan_install(
                FIXTURE_ROOT / "source",
                target,
                ROOT,
                harnesses=["codex"],
                executable_finder=_finder("codex"),
            )
            marker = target / ".agents" / "skills" / "example" / "user-created.txt"

            def change_then_fail(stage, operation):
                if stage == "after_operation" and operation["destination"] == ".agents/skills/example":
                    marker.write_text("concurrent user content\n", encoding="utf-8")
                    raise RuntimeError("synthetic interruption")

            with self.assertRaisesRegex(SetupError, r"rollback_incomplete.*\.agents/skills/example"):
                apply_install(
                    plan,
                    actor="tester",
                    source_version="0.1",
                    fault_injector=change_then_fail,
                )
            self.assertEqual(marker.read_text(encoding="utf-8"), "concurrent user content\n")

    def test_applied_install_contains_offline_toolkit_and_runs_without_source(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            source = temporary / "source-checkout"
            shutil.copytree(
                ROOT,
                source,
                ignore=shutil.ignore_patterns(".git", "__pycache__", ".the-loop"),
            )
            target = temporary / "project"
            target.mkdir()
            plan = plan_install(
                source,
                target,
                source,
                harnesses=["codex"],
                executable_finder=_finder("codex"),
            )
            receipt = apply_install(plan, actor="tester", source_version="0.1")
            toolkit = target / ".the-loop" / "toolkit"
            required = (
                ".agents/skills/the-loop-setup/SKILL.md",
                ".agents/skills/the-loop-doctor/SKILL.md",
                "adapters/codex/adapter.json",
                "protocols/stage-contracts.md",
                "schemas/config.schema.json",
                "scripts/the_loop_setup.py",
                "scripts/the_loop_doctor.py",
                "scripts/run_conformance.py",
                "src/the_loop/setup.py",
                "src/the_loop/doctor.py",
                "src/the_loop/validation.py",
                "LICENSE",
            )
            self.assertEqual([relative for relative in required if not (toolkit / relative).is_file()], [])
            toolkit_operation = next(
                operation for operation in receipt["operations"] if operation["destination"] == ".the-loop/toolkit"
            )
            self.assertEqual(toolkit_operation["rollback_action"], "remove_if_unchanged")
            source.rename(temporary / "source-unavailable")
            completed = subprocess.run(
                [
                    sys.executable,
                    str(toolkit / "scripts" / "the_loop_doctor.py"),
                    "--repository-root",
                    str(toolkit),
                    "--project-root",
                    str(target),
                    "--json",
                ],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10,
            )
            self.assertIn(completed.returncode, {0, 1}, completed.stderr)
            report = json.loads(completed.stdout)
            self.assertIn(report["overall_status"], {"ready", "warning"})
            fake_bin = temporary / "bin"
            fake_bin.mkdir()
            fake_codex = fake_bin / "codex"
            fake_codex.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            fake_codex.chmod(0o755)
            second_target = temporary / "second-project"
            second_target.mkdir()
            environment = dict(os.environ)
            environment["PATH"] = str(fake_bin) + os.pathsep + environment.get("PATH", "")
            dry_run = subprocess.run(
                [
                    sys.executable,
                    str(toolkit / "scripts" / "the_loop_setup.py"),
                    "--target-root",
                    str(second_target),
                    "--harness",
                    "codex",
                    "--json",
                ],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10,
                env=environment,
            )
            self.assertEqual(dry_run.returncode, 0, dry_run.stderr)
            second_plan = json.loads(dry_run.stdout)
            self.assertEqual(Path(second_plan["target_root"]), second_target.resolve())
            self.assertIn(".the-loop/toolkit", [operation["destination"] for operation in second_plan["operations"]])

    def test_canonical_documentation_links_resolve_offline_in_root_and_toolkit_packages(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            source = temporary / "canonical-source"
            shutil.copytree(ROOT, source, ignore=shutil.ignore_patterns(".git", "__pycache__", ".the-loop"))
            self.assertEqual(_canonicalize_skill_links(source), 80)
            target = temporary / "project"
            target.mkdir()
            plan = plan_install(
                source,
                target,
                source,
                harnesses=["codex"],
                executable_finder=_finder("codex"),
            )
            apply_install(plan, actor="tester", source_version="0.1")
            source.rename(temporary / "source-unavailable")

            root_count, root_failures = _resolved_documentation_links(target / ".agents" / "skills")
            toolkit_count, toolkit_failures = _resolved_documentation_links(
                target / ".the-loop" / "toolkit" / ".agents" / "skills"
            )
            self.assertEqual(root_count, 80)
            self.assertEqual(toolkit_count, 80)
            self.assertEqual(root_failures, [])
            self.assertEqual(toolkit_failures, [])

    def test_transformed_digests_skip_identical_install_and_restore_approved_upgrade(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            source = temporary / "canonical-source"
            shutil.copytree(ROOT, source, ignore=shutil.ignore_patterns(".git", "__pycache__", ".the-loop"))
            self.assertEqual(_canonicalize_skill_links(source), 80)
            target = temporary / "project"
            target.mkdir()
            first = plan_install(
                source,
                target,
                source,
                harnesses=["codex"],
                executable_finder=_finder("codex"),
            )
            audit_plan = next(operation for operation in first["operations"] if operation["destination"] == ".agents/skills/audit")
            toolkit_plan = next(operation for operation in first["operations"] if operation["destination"] == ".the-loop/toolkit")
            self.assertNotEqual(audit_plan["installed_digest"], audit_plan["source_digest"])
            self.assertNotEqual(toolkit_plan["installed_digest"], toolkit_plan["source_digest"])
            first_receipt = apply_install(first, actor="tester", source_version="0.1")
            audit_receipt = next(
                operation for operation in first_receipt["operations"] if operation["destination"] == ".agents/skills/audit"
            )
            self.assertEqual(audit_receipt["resulting_digest"], audit_plan["installed_digest"])
            installed_skill = target / ".agents" / "skills" / "audit" / "SKILL.md"
            toolkit_skill = target / ".the-loop" / "toolkit" / ".agents" / "skills" / "audit" / "SKILL.md"
            original_installed = installed_skill.read_bytes()
            original_toolkit = toolkit_skill.read_bytes()

            identical = plan_install(
                source,
                target,
                source,
                harnesses=["codex"],
                executable_finder=_finder("codex"),
            )
            self.assertEqual(identical["approval_required"], [])
            self.assertEqual(
                [operation["action"] for operation in identical["operations"] if operation["destination"] == ".agents/skills/audit"],
                ["skip"],
            )
            self.assertEqual(
                [operation["action"] for operation in identical["operations"] if operation["destination"] == ".the-loop/toolkit"],
                ["skip"],
            )

            source_skill = source / ".agents" / "skills" / "audit" / "SKILL.md"
            source_skill.write_text(source_skill.read_text(encoding="utf-8") + "\nUpgrade proof.\n", encoding="utf-8")
            upgrade = plan_install(
                source,
                target,
                source,
                harnesses=["codex"],
                executable_finder=_finder("codex"),
            )
            self.assertEqual(upgrade["approval_required"], [".agents/skills/audit", ".the-loop/toolkit"])
            with self.assertRaisesRegex(SetupError, "exact approval"):
                apply_install(upgrade, actor="tester", source_version="0.2")
            upgraded = apply_install(
                upgrade,
                actor="tester",
                source_version="0.2",
                approved_destinations=upgrade["approval_required"],
            )
            self.assertNotEqual(installed_skill.read_bytes(), original_installed)
            self.assertNotEqual(toolkit_skill.read_bytes(), original_toolkit)
            result = rollback_install(upgraded, target_root=target)
            self.assertEqual(result["result"], "rolled_back")
            self.assertEqual(installed_skill.read_bytes(), original_installed)
            self.assertEqual(toolkit_skill.read_bytes(), original_toolkit)

    def test_transformed_install_still_revalidates_raw_source_digest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            source = temporary / "canonical-source"
            shutil.copytree(ROOT, source, ignore=shutil.ignore_patterns(".git", "__pycache__", ".the-loop"))
            self.assertEqual(_canonicalize_skill_links(source), 80)
            target = temporary / "project"
            target.mkdir()
            plan = plan_install(
                source,
                target,
                source,
                harnesses=["codex"],
                executable_finder=_finder("codex"),
            )
            source_skill = source / ".agents" / "skills" / "audit" / "SKILL.md"
            content = source_skill.read_text(encoding="utf-8")
            source_skill.write_text(
                content.replace(CANONICAL_DOCS, "../../../.the-loop/toolkit/", 1),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(SetupError, "source changed after planning"):
                apply_install(plan, actor="tester", source_version="0.1")
            self.assertFalse((target / ".agents" / "skills" / "audit").exists())


if __name__ == "__main__":
    unittest.main()
