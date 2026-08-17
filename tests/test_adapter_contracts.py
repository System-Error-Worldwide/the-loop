from __future__ import annotations

import copy
import json
import re
import unittest
from pathlib import Path, PurePosixPath
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ADAPTERS_ROOT = ROOT / "adapters"
FIXTURES_ROOT = ROOT / "tests" / "fixtures" / "adapters"

EXPECTED = {
    "codex": {
        "display_name": "Codex",
        "executables": ["codex"],
        "project_skill_roots": [".agents/skills"],
        "user_skill_roots": ["$CODEX_HOME/skills", "$HOME/.agents/skills"],
        "explicit_invocation": ("selector", "$<skill-name>"),
        "forbidden_flags": ["--dangerously-bypass-approvals-and-sandbox"],
    },
    "claude_code": {
        "display_name": "Claude Code",
        "executables": ["claude"],
        "project_skill_roots": [".claude/skills"],
        "user_skill_roots": ["$HOME/.claude/skills"],
        "explicit_invocation": ("slash_command", "/<skill-name>"),
        "forbidden_flags": [
            "--dangerously-skip-permissions",
            "--allow-dangerously-skip-permissions",
        ],
    },
    "kimi_code": {
        "display_name": "Kimi Code",
        "executables": ["kimi"],
        "project_skill_roots": [".kimi-code/skills", ".agents/skills"],
        "user_skill_roots": ["$KIMI_CODE_HOME/skills", "$HOME/.agents/skills"],
        "explicit_invocation": ("slash_command", "/skill:<skill-name>"),
        "forbidden_flags": ["--yolo", "--yes", "--auto-approve", "--afk", "--auto", "--print"],
    },
    "opencode": {
        "display_name": "OpenCode",
        "executables": ["opencode"],
        "project_skill_roots": [".opencode/skills", ".agents/skills", ".claude/skills"],
        "user_skill_roots": [
            "$HOME/.config/opencode/skills",
            "$HOME/.agents/skills",
            "$HOME/.claude/skills",
        ],
        "explicit_invocation": ("tool", "skill(<skill-name>)"),
        "forbidden_flags": [],
    },
    "deepseek_harness": {
        "display_name": "DeepSeek Harness",
        "executables": ["dsh"],
        "project_skill_roots": [".dsh/skills", ".agents/skills"],
        "user_skill_roots": ["$DSH_HOME/skills", "$DSH_AGENTS_HOME/skills"],
        "explicit_invocation": ("slash_command", "/<skill-name>"),
        "forbidden_flags": [],
    },
}

REQUIRED_KEYS = {
    "schema_version",
    "harness",
    "display_name",
    "executables",
    "project_skill_roots",
    "user_skill_roots",
    "explicit_invocation",
    "implicit_invocation",
    "permission_model",
    "delegation",
    "fallback",
}

NESTED_KEYS = {
    "explicit_invocation": {"kind", "template", "behavior_status"},
    "implicit_invocation": {"basis", "behavior_status", "requires_harness_probe"},
    "permission_model": {"surface", "preserve_denial", "allow_bypass", "forbidden_flags"},
    "delegation": {"availability", "on_unavailable", "behavior_status"},
    "fallback": {"provider", "mode", "preserve_authority", "preserve_denial"},
}

COMMAND_RE = re.compile(r"^[a-z][a-z0-9_-]*$")
VARIABLE_ROOT_RE = re.compile(r"^\$[A-Z][A-Z0-9_]*/(?:[^/]+/)*[^/]+$")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def adapter_paths(root: Path = ADAPTERS_ROOT) -> list[Path]:
    if not root.is_dir():
        return []
    return sorted(root.glob("*/adapter.json"))


def portable_root(value: object, *, project: bool) -> bool:
    if not isinstance(value, str) or "\\" in value or "//" in value:
        return False
    if value.startswith(("/", "file:")) or "/" + "Users/" in value or "/" + "home/" in value:
        return False
    if project:
        allowed_prefix = value.startswith(".") and not value.startswith(("..", "~/"))
    else:
        allowed_prefix = bool(VARIABLE_ROOT_RE.fullmatch(value))
    return allowed_prefix and ".." not in PurePosixPath(value).parts and value.endswith("/skills")


def validate_manifest(manifest: object, source: str = "adapter") -> list[str]:
    errors: list[str] = []
    if not isinstance(manifest, dict):
        return [f"{source}: manifest must be an object"]

    keys = set(manifest)
    if keys != REQUIRED_KEYS:
        errors.append(f"{source}: keys differ: missing={sorted(REQUIRED_KEYS - keys)} extra={sorted(keys - REQUIRED_KEYS)}")

    for key, expected_keys in NESTED_KEYS.items():
        value = manifest.get(key)
        if not isinstance(value, dict) or set(value) != expected_keys:
            errors.append(f"{source}: {key} keys must be {sorted(expected_keys)}")

    if manifest.get("schema_version") != "1.0":
        errors.append(f"{source}: schema_version must be 1.0")
    harness = manifest.get("harness")
    if harness not in EXPECTED:
        errors.append(f"{source}: unknown harness {harness!r}")

    executables = manifest.get("executables")
    if not isinstance(executables, list) or not executables or len(executables) != len(set(executables)):
        errors.append(f"{source}: executables must be a non-empty unique list")
    elif any(not isinstance(command, str) or not COMMAND_RE.fullmatch(command) for command in executables):
        errors.append(f"{source}: executables must be portable command names without arguments")

    for key, project in (("project_skill_roots", True), ("user_skill_roots", False)):
        roots = manifest.get(key)
        if not isinstance(roots, list) or not roots or len(roots) != len(set(roots)):
            errors.append(f"{source}: {key} must be a non-empty unique list")
        elif any(not portable_root(root, project=project) for root in roots):
            errors.append(f"{source}: {key} contains a non-portable root")

    explicit = manifest.get("explicit_invocation")
    if isinstance(explicit, dict):
        if "<skill-name>" not in str(explicit.get("template", "")):
            errors.append(f"{source}: explicit invocation must contain <skill-name>")
        if explicit.get("behavior_status") != "unverified":
            errors.append(f"{source}: explicit behavior must remain unverified")

    implicit = manifest.get("implicit_invocation")
    if isinstance(implicit, dict):
        if implicit.get("basis") != "description" or implicit.get("behavior_status") != "unverified":
            errors.append(f"{source}: implicit behavior must be description-based and unverified")
        if implicit.get("requires_harness_probe") is not True:
            errors.append(f"{source}: implicit behavior must require a harness probe")

    permissions = manifest.get("permission_model")
    if isinstance(permissions, dict):
        if permissions.get("preserve_denial") is not True or permissions.get("allow_bypass") is not False:
            errors.append(f"{source}: permission policy must preserve denial and forbid bypass")
        forbidden = permissions.get("forbidden_flags")
        if not isinstance(forbidden, list) or len(forbidden) != len(set(forbidden)):
            errors.append(f"{source}: forbidden_flags must be a unique list")
        elif any(not isinstance(flag, str) or not flag.startswith("--") for flag in forbidden):
            errors.append(f"{source}: forbidden_flags must contain long option names")

    delegation = manifest.get("delegation")
    if isinstance(delegation, dict):
        if (
            delegation.get("availability") != "optional"
            or delegation.get("on_unavailable") != "sequential"
            or delegation.get("behavior_status") != "unverified"
        ):
            errors.append(f"{source}: delegation must be optional, unverified, and degrade to sequential")

    fallback = manifest.get("fallback")
    if isinstance(fallback, dict):
        if (
            fallback.get("provider") != "bundled"
            or fallback.get("mode") != "sequential"
            or fallback.get("preserve_authority") is not True
            or fallback.get("preserve_denial") is not True
        ):
            errors.append(f"{source}: fallback must be bundled, sequential, and authority preserving")

    return errors


def validate_collection(manifests: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    identities: set[str] = set()
    display_names: set[str] = set()
    for index, manifest in enumerate(manifests):
        errors.extend(validate_manifest(manifest, f"adapter[{index}]"))
        harness = manifest.get("harness")
        display_name = manifest.get("display_name")
        if harness in identities:
            errors.append(f"adapter[{index}]: duplicate harness identity {harness!r}")
        if display_name in display_names:
            errors.append(f"adapter[{index}]: duplicate display identity {display_name!r}")
        if isinstance(harness, str):
            identities.add(harness)
        if isinstance(display_name, str):
            display_names.add(display_name)
    return errors


class AdapterContractTests(unittest.TestCase):
    def manifests(self) -> list[dict[str, Any]]:
        return [load_json(path) for path in adapter_paths()]

    def test_exact_adapter_set_is_present(self) -> None:
        paths = adapter_paths()
        found = {path.parent.name for path in paths}
        directories = {path.name for path in ADAPTERS_ROOT.iterdir() if path.is_dir()}
        self.assertEqual(set(EXPECTED), found)
        self.assertEqual(set(EXPECTED), directories)
        self.assertEqual(5, len(paths))

    def test_live_manifests_satisfy_shared_contract(self) -> None:
        manifests = self.manifests()
        self.assertEqual([], validate_collection(manifests))

    def test_documented_roots_and_invocations_are_exact(self) -> None:
        manifests = {manifest["harness"]: manifest for manifest in self.manifests()}
        for harness, expected in EXPECTED.items():
            with self.subTest(harness=harness):
                manifest = manifests[harness]
                self.assertEqual(expected["display_name"], manifest["display_name"])
                self.assertEqual(expected["executables"], manifest["executables"])
                self.assertEqual(expected["project_skill_roots"], manifest["project_skill_roots"])
                self.assertEqual(expected["user_skill_roots"], manifest["user_skill_roots"])
                kind, template = expected["explicit_invocation"]
                self.assertEqual(kind, manifest["explicit_invocation"]["kind"])
                self.assertEqual(template, manifest["explicit_invocation"]["template"])

    def test_permission_models_name_host_surface_and_never_enable_bypass(self) -> None:
        for manifest in self.manifests():
            with self.subTest(harness=manifest["harness"]):
                permission = manifest["permission_model"]
                self.assertIsInstance(permission["surface"], str)
                self.assertTrue(permission["surface"].strip())
                self.assertTrue(permission["preserve_denial"])
                self.assertFalse(permission["allow_bypass"])
                self.assertEqual(EXPECTED[manifest["harness"]]["forbidden_flags"], permission["forbidden_flags"])
                self.assertNotIn(" ", "".join(manifest["executables"]))

    def test_delegation_absence_uses_sequential_bundled_fallback(self) -> None:
        for manifest in self.manifests():
            with self.subTest(harness=manifest["harness"]):
                self.assertEqual("optional", manifest["delegation"]["availability"])
                self.assertEqual("sequential", manifest["delegation"]["on_unavailable"])
                self.assertEqual("bundled", manifest["fallback"]["provider"])
                self.assertEqual("sequential", manifest["fallback"]["mode"])

    def test_no_manifest_claims_live_behavior_proof(self) -> None:
        for manifest in self.manifests():
            with self.subTest(harness=manifest["harness"]):
                self.assertEqual("unverified", manifest["explicit_invocation"]["behavior_status"])
                self.assertEqual("unverified", manifest["implicit_invocation"]["behavior_status"])
                self.assertEqual("unverified", manifest["delegation"]["behavior_status"])

    def test_missing_key_fixture_is_rejected(self) -> None:
        errors = validate_manifest(load_json(FIXTURES_ROOT / "missing-key.json"), "missing-key")
        self.assertTrue(any("missing=['fallback']" in error for error in errors), errors)

    def test_unsafe_executable_fixture_is_rejected(self) -> None:
        errors = validate_manifest(load_json(FIXTURES_ROOT / "unsafe-executable.json"), "unsafe")
        self.assertTrue(any("without arguments" in error for error in errors), errors)

    def test_nonportable_root_fixture_is_rejected(self) -> None:
        errors = validate_manifest(load_json(FIXTURES_ROOT / "nonportable-root.json"), "nonportable")
        self.assertTrue(any("non-portable root" in error for error in errors), errors)

    def test_duplicate_identity_is_rejected(self) -> None:
        original = load_json(FIXTURES_ROOT / "valid-codex.json")
        duplicate = copy.deepcopy(original)
        duplicate["display_name"] = "Codex duplicate"
        errors = validate_collection([original, duplicate])
        self.assertTrue(any("duplicate harness identity" in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
