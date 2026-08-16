"""Portable, transactional installer for THE LOOP skill packages."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Iterable, Mapping

from .validation import ContractError, validate_record, validate_relative_path


SCHEMA_VERSION = "1.0"
SUPPORTED_HARNESSES = ("codex", "claude_code", "kimi_code", "opencode")
ADAPTER_DIRECTORIES = {
    "codex": "codex",
    "claude_code": "claude_code",
    "kimi_code": "kimi_code",
    "opencode": "opencode",
}
REQUIRED_ADAPTER_KEYS = frozenset(
    {
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
)


class SetupError(RuntimeError):
    """A precise, fail-closed installation error."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _canonical_root(path_value: Path | str, *, label: str) -> Path:
    path = Path(path_value)
    if path.is_symlink():
        raise SetupError(f"{label} must not be a symlink")
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise SetupError(f"{label} is not accessible: {exc}") from exc
    if not resolved.is_dir():
        raise SetupError(f"{label} must be a directory")
    return resolved


def _safe_destination(root: Path, relative: str, *, allow_final_symlink: bool = False) -> Path:
    try:
        normalized = validate_relative_path(relative, path="$.destination")
    except ContractError as exc:
        raise SetupError(str(exc)) from exc
    if normalized == ".":
        raise SetupError("destination must name a path below the target root")
    candidate = root / normalized
    current = root
    parts = PurePosixPath(normalized).parts
    for index, part in enumerate(parts):
        current = current / part
        if current.is_symlink():
            if allow_final_symlink and index == len(parts) - 1:
                break
            raise SetupError(f"destination crosses symlink: {normalized}")
    try:
        resolved = candidate.parent.resolve(strict=False) / candidate.name
    except OSError as exc:
        raise SetupError(f"destination cannot be resolved: {normalized}: {exc}") from exc
    if not resolved.is_relative_to(root):
        raise SetupError(f"destination escapes target root: {normalized}")
    return candidate


def _digest_path(path: Path) -> str | None:
    if not path.exists() and not path.is_symlink():
        return None
    digest = hashlib.sha256()
    if path.is_symlink():
        digest.update(b"link\0")
        digest.update(os.readlink(path).encode("utf-8", "surrogateescape"))
        return digest.hexdigest()
    if path.is_file():
        digest.update(b"file\0")
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
    if not path.is_dir():
        raise SetupError(f"unsupported filesystem object: {path}")
    digest.update(b"directory\0")
    for child in sorted(path.rglob("*"), key=lambda item: item.relative_to(path).as_posix()):
        relative = child.relative_to(path).as_posix().encode("utf-8", "surrogateescape")
        if child.is_symlink():
            raise SetupError(f"skill package contains a symlink: {child}")
        if child.is_dir():
            digest.update(b"d\0" + relative + b"\0")
        elif child.is_file():
            digest.update(b"f\0" + relative + b"\0")
            with child.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
        else:
            raise SetupError(f"skill package contains an unsupported object: {child}")
    return digest.hexdigest()


def _validate_adapter(manifest: Any, harness: str) -> dict[str, Any]:
    if not isinstance(manifest, dict):
        raise SetupError("adapter manifest must be a JSON object")
    missing = sorted(REQUIRED_ADAPTER_KEYS - set(manifest))
    if missing:
        raise SetupError("adapter manifest missing keys: " + ", ".join(missing))
    if manifest["schema_version"] != SCHEMA_VERSION:
        raise SetupError("adapter manifest schema_version must be 1.0")
    if manifest["harness"] != harness:
        raise SetupError(f"adapter harness must be {harness}")
    for field in ("display_name",):
        if not isinstance(manifest[field], str) or not manifest[field]:
            raise SetupError(f"adapter field {field} must be a non-empty string")
    for field in ("executables", "project_skill_roots", "user_skill_roots"):
        value = manifest[field]
        if not isinstance(value, list) or not value or not all(isinstance(item, str) and item for item in value):
            raise SetupError(f"adapter field {field} must be a non-empty string array")
    if not all(isinstance(manifest[field], Mapping) for field in (
        "explicit_invocation",
        "implicit_invocation",
        "permission_model",
        "delegation",
        "fallback",
    )):
        raise SetupError("adapter capability fields must be objects")
    return manifest


def load_adapter_manifests(repository_root: Path | str) -> dict[str, dict[str, Any]]:
    """Load every supported adapter through the public generic manifest interface."""

    root = _canonical_root(repository_root, label="repository root")
    reports: dict[str, dict[str, Any]] = {}
    for harness in SUPPORTED_HARNESSES:
        relative = Path("adapters") / ADAPTER_DIRECTORIES[harness] / "adapter.json"
        path = root / relative
        if not path.is_file() or path.is_symlink():
            reports[harness] = {
                "status": "failed",
                "path": relative.as_posix(),
                "error": "adapter manifest missing",
                "manifest": None,
            }
            continue
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"))
            manifest = _validate_adapter(manifest, harness)
        except json.JSONDecodeError as exc:
            reports[harness] = {
                "status": "failed",
                "path": relative.as_posix(),
                "error": f"adapter manifest JSON is invalid: {exc.msg}",
                "manifest": None,
            }
        except (OSError, SetupError) as exc:
            reports[harness] = {
                "status": "failed",
                "path": relative.as_posix(),
                "error": str(exc),
                "manifest": None,
            }
        else:
            reports[harness] = {
                "status": "verified",
                "path": relative.as_posix(),
                "error": None,
                "manifest": manifest,
            }
    return reports


def detect_harnesses(
    manifests: Mapping[str, Mapping[str, Any]],
    *,
    executable_finder: Callable[[str], str | None] = shutil.which,
) -> dict[str, dict[str, Any]]:
    """Detect each harness without requiring all supported harnesses."""

    detected: dict[str, dict[str, Any]] = {}
    for harness in SUPPORTED_HARNESSES:
        report = manifests.get(harness)
        if report is None or report.get("status") != "verified":
            detected[harness] = {
                "installed": False,
                "executable": None,
                "adapter_status": "failed",
                "error": "adapter manifest unavailable" if report is None else report.get("error"),
            }
            continue
        manifest = report["manifest"]
        executable = None
        for name in manifest["executables"]:
            executable = executable_finder(name)
            if executable is not None:
                break
        detected[harness] = {
            "installed": executable is not None,
            "executable": executable,
            "adapter_status": "verified",
            "error": None,
        }
    return detected


def _skill_packages(source_root: Path) -> list[Path]:
    skills_root = source_root / ".agents" / "skills"
    if not skills_root.is_dir() or skills_root.is_symlink():
        raise SetupError("source root has no safe .agents/skills directory")
    packages = [item for item in skills_root.iterdir() if item.is_dir() and not item.is_symlink() and (item / "SKILL.md").is_file()]
    if not packages:
        raise SetupError("source root contains no portable skill packages")
    return sorted(packages, key=lambda item: item.name)


def _adapter_roots(manifest: Mapping[str, Any], scope: str) -> list[str]:
    field = "project_skill_roots" if scope == "project" else "user_skill_roots"
    roots: list[str] = []
    for value in manifest[field]:
        if scope == "user":
            prefixes = {
                "$HOME/": "",
                "$CODEX_HOME/": ".codex/",
                "$KIMI_CODE_HOME/": ".kimi-code/",
            }
            matched = next((prefix for prefix in prefixes if value.startswith(prefix)), None)
            if matched is None:
                raise SetupError(f"user skill root has an unsupported portable variable: {value}")
            value = prefixes[matched] + value[len(matched) :]
        try:
            roots.append(validate_relative_path(value, path=f"$.{field}"))
        except ContractError as exc:
            raise SetupError(str(exc)) from exc
    return roots


def _missing_directories(root: Path, relative: str) -> list[str]:
    missing: list[str] = []
    current = root
    parts: list[str] = []
    for part in PurePosixPath(relative).parts:
        parts.append(part)
        current = current / part
        if current.is_symlink():
            raise SetupError(f"destination root crosses symlink: {'/'.join(parts)}")
        if not current.exists():
            missing.append("/".join(parts))
        elif not current.is_dir():
            raise SetupError(f"destination root is not a directory: {'/'.join(parts)}")
    return missing


def plan_install(
    source_root: Path | str,
    target_root: Path | str,
    repository_root: Path | str,
    *,
    harnesses: Iterable[str] | None = None,
    scope: str = "project",
    mode: str = "copy",
    prove_link_support: bool = False,
    executable_finder: Callable[[str], str | None] = shutil.which,
) -> dict[str, Any]:
    """Return a deterministic, read-only installation plan."""

    source = _canonical_root(source_root, label="source root")
    target = _canonical_root(target_root, label="target root")
    repository = _canonical_root(repository_root, label="repository root")
    if scope not in {"project", "user"}:
        raise SetupError("scope must be project or user")
    if mode not in {"copy", "link"}:
        raise SetupError("mode must be copy or link")
    if mode == "link" and not prove_link_support:
        raise SetupError("link support must be explicitly proven for the filesystem and harness")
    if mode == "link" and source.stat().st_dev != target.stat().st_dev:
        raise SetupError("link support is not proven across different filesystems")

    manifest_reports = load_adapter_manifests(repository)
    detected = detect_harnesses(manifest_reports, executable_finder=executable_finder)
    selected = list(dict.fromkeys(harnesses or [key for key, value in detected.items() if value["installed"]]))
    if not selected:
        raise SetupError("setup_blocked: no supported harness found")
    unknown = sorted(set(selected) - set(SUPPORTED_HARNESSES))
    if unknown:
        raise SetupError("unsupported harness: " + ", ".join(unknown))
    for harness in selected:
        if manifest_reports[harness]["status"] != "verified":
            raise SetupError(f"adapter manifest unavailable for {harness}: {manifest_reports[harness]['error']}")
        if not detected[harness]["installed"]:
            raise SetupError(f"selected harness is not installed: {harness}")

    packages = _skill_packages(source)
    roots: list[str] = []
    for harness in selected:
        candidates = _adapter_roots(manifest_reports[harness]["manifest"], scope)
        preferred = ".agents/skills" if ".agents/skills" in candidates else candidates[0]
        roots.append(preferred)
    roots = list(dict.fromkeys(roots))

    operations: list[dict[str, Any]] = []
    planned_directories: set[str] = set()
    for skill_root in roots:
        for missing in _missing_directories(target, skill_root):
            if missing not in planned_directories:
                planned_directories.add(missing)
                operations.append(
                    {
                        "action": "mkdir",
                        "source": None,
                        "source_digest": None,
                        "destination": missing,
                        "pre_existing_digest": None,
                        "collision": False,
                        "approval_required": False,
                        "rollback_action": "remove_if_unchanged",
                    }
                )
        for package in packages:
            relative = f"{skill_root}/{package.name}"
            destination = _safe_destination(target, relative)
            source_digest = _digest_path(package)
            existing_digest = _digest_path(destination)
            if existing_digest == source_digest:
                action = "skip"
                rollback_action = "none"
            else:
                action = mode
                rollback_action = "restore_if_unchanged" if existing_digest is not None else "remove_if_unchanged"
            operations.append(
                {
                    "action": action,
                    "source": str(package),
                    "source_digest": source_digest,
                    "destination": relative,
                    "pre_existing_digest": existing_digest,
                    "collision": existing_digest is not None and existing_digest != source_digest,
                    "approval_required": existing_digest is not None and existing_digest != source_digest,
                    "rollback_action": rollback_action,
                }
            )

    deduplicated: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for operation in operations:
        key = (operation["action"], operation["destination"])
        if key not in seen:
            seen.add(key)
            deduplicated.append(operation)
    approval_required = sorted(item["destination"] for item in deduplicated if item["approval_required"])
    identity = target.stat()
    return {
        "schema_version": SCHEMA_VERSION,
        "source_root": str(source),
        "target_root": str(target),
        "target_identity": [identity.st_dev, identity.st_ino],
        "scope": scope,
        "mode": mode,
        "harnesses": selected,
        "install_roots": roots,
        "detected_harnesses": detected,
        "operations": deduplicated,
        "approval_required": approval_required,
    }


def _remove_path(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def _copy_to(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination, symlinks=True)


def _atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
        directory_descriptor = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def _ensure_private_directory(path: Path) -> None:
    if path.is_symlink():
        raise SetupError(f"private install directory must not be a symlink: {path.name}")
    if not path.exists():
        path.mkdir(mode=0o700)
    info = path.stat()
    if not path.is_dir():
        raise SetupError(f"private install path is not a directory: {path.name}")
    if hasattr(os, "getuid") and info.st_uid != os.getuid():
        raise SetupError(f"private install directory is not owned by the current user: {path.name}")
    if stat.S_IMODE(info.st_mode) & 0o077:
        raise SetupError(f"private install directory grants group or other access: {path.name}")


def apply_install(
    plan: Mapping[str, Any],
    *,
    actor: str,
    source_version: str,
    approved_destinations: Iterable[str] = (),
    fault_injector: Callable[[str, Mapping[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """Apply one unchanged plan transactionally and emit its install receipt."""

    if not actor or not source_version:
        raise SetupError("actor and source_version must be non-empty")
    target = _canonical_root(plan.get("target_root", ""), label="target root")
    identity = target.stat()
    if list(plan.get("target_identity", [])) != [identity.st_dev, identity.st_ino]:
        raise SetupError("target root identity changed after planning")
    approvals = set(approved_destinations)
    required = set(plan.get("approval_required", []))
    missing = sorted(required - approvals)
    if missing:
        raise SetupError("exact approval required for: " + ", ".join(missing))
    receipt_id = str(uuid.uuid4())
    transaction = Path(tempfile.mkdtemp(prefix=f"the-loop-install-{receipt_id}-", dir=target.parent))
    backups = transaction / "backups"
    applied: list[tuple[Mapping[str, Any], Path | None]] = []
    receipt_operations: list[dict[str, Any]] = []
    receipt_path = target / ".the-loop" / "installs" / f"{receipt_id}.json"
    persistent_backup = target / ".the-loop" / "installs" / f"{receipt_id}.backup"
    state_root_existed = (target / ".the-loop").exists()
    installs_existed = (target / ".the-loop" / "installs").exists()
    try:
        for operation in plan["operations"]:
            destination = _safe_destination(target, operation["destination"], allow_final_symlink=True)
            action = operation["action"]
            current_digest = _digest_path(destination)
            if current_digest != operation["pre_existing_digest"]:
                raise SetupError(f"destination changed after planning: {operation['destination']}")
            source = Path(operation["source"]) if operation["source"] else None
            if source is not None and _digest_path(source) != operation["source_digest"]:
                raise SetupError(f"source changed after planning: {operation['destination']}")
            if fault_injector:
                fault_injector("before_operation", operation)
            backup: Path | None = None
            if action == "mkdir":
                destination.mkdir()
            elif action == "skip":
                pass
            else:
                if current_digest is not None:
                    if operation["destination"] not in approvals:
                        raise SetupError(f"exact approval required for: {operation['destination']}")
                    backup = backups / operation["destination"]
                    backup.parent.mkdir(parents=True, exist_ok=True)
                    os.replace(destination, backup)
                assert source is not None
                if action == "copy":
                    _copy_to(source, destination)
                elif action == "link":
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    os.symlink(source, destination, target_is_directory=True)
                else:
                    raise SetupError(f"unsupported planned action: {action}")
            applied.append((operation, backup))
            result_digest = _digest_path(destination)
            if action == "copy" and result_digest != operation["source_digest"]:
                raise SetupError(f"copied output does not match its planned source: {operation['destination']}")
            if action == "link" and (not destination.is_symlink() or Path(os.readlink(destination)) != source):
                raise SetupError(f"linked output does not match its planned source: {operation['destination']}")
            receipt_operations.append(
                {
                    "action": action,
                    "source_digest": operation["source_digest"],
                    "destination": operation["destination"],
                    "pre_existing_digest": operation["pre_existing_digest"],
                    "resulting_digest": result_digest,
                    "rollback_action": operation["rollback_action"],
                }
            )
            if fault_injector:
                fault_injector("after_operation", operation)

        receipt = {
            "schema_version": SCHEMA_VERSION,
            "receipt_id": receipt_id,
            "created_at": _utc_now(),
            "actor": actor,
            "source_version": source_version,
            "target_root": str(target),
            "harnesses": list(plan["harnesses"]),
            "operations": receipt_operations,
            "result": "complete",
        }
        validate_record("install_receipt", receipt)
        _ensure_private_directory(target / ".the-loop")
        _ensure_private_directory(target / ".the-loop" / "installs")
        if backups.exists():
            os.replace(backups, persistent_backup)
            os.chmod(persistent_backup, 0o700)
        if fault_injector:
            fault_injector(
                "before_receipt_write",
                {"action": "receipt", "destination": f".the-loop/installs/{receipt_id}.json"},
            )
        _atomic_json(receipt_path, receipt)
        return receipt
    except BaseException:
        for operation, backup in reversed(applied):
            destination = _safe_destination(target, operation["destination"], allow_final_symlink=True)
            if operation["action"] == "skip":
                continue
            if destination.exists() or destination.is_symlink():
                _remove_path(destination)
            if backup is not None and not backup.exists():
                backup = persistent_backup / operation["destination"]
            if backup is not None and backup.exists():
                destination.parent.mkdir(parents=True, exist_ok=True)
                os.replace(backup, destination)
        if persistent_backup.exists():
            shutil.rmtree(persistent_backup)
        if receipt_path.exists():
            receipt_path.unlink()
        if not installs_existed:
            try:
                receipt_path.parent.rmdir()
            except OSError:
                pass
        if not state_root_existed:
            try:
                (target / ".the-loop").rmdir()
            except OSError:
                pass
        raise
    finally:
        shutil.rmtree(transaction, ignore_errors=True)


def rollback_install(receipt: Mapping[str, Any], *, target_root: Path | str | None = None) -> dict[str, Any]:
    """Roll back unchanged outputs owned by one validated receipt."""

    validate_record("install_receipt", receipt)
    configured_target = Path(receipt["target_root"])
    target = _canonical_root(target_root or configured_target, label="target root")
    if target != configured_target.resolve(strict=True):
        raise SetupError("target root does not match receipt")
    backup_root = target / ".the-loop" / "installs" / f"{receipt['receipt_id']}.backup"
    skipped = False
    for operation in reversed(receipt["operations"]):
        action = operation["rollback_action"]
        if action == "none":
            continue
        destination = _safe_destination(target, operation["destination"], allow_final_symlink=True)
        if _digest_path(destination) != operation["resulting_digest"]:
            skipped = True
            continue
        backup = backup_root / operation["destination"]
        if action == "restore_if_unchanged" and _digest_path(backup) != operation["pre_existing_digest"]:
            skipped = True
            continue
        if destination.exists() or destination.is_symlink():
            _remove_path(destination)
        if action == "restore_if_unchanged":
            if not backup.exists() and not backup.is_symlink():
                skipped = True
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            os.replace(backup, destination)
    result = dict(receipt)
    result["result"] = "partial" if skipped else "rolled_back"
    validate_record("install_receipt", result)
    receipt_path = target / ".the-loop" / "installs" / f"{receipt['receipt_id']}.json"
    _atomic_json(receipt_path, result)
    if not skipped and backup_root.exists():
        shutil.rmtree(backup_root)
    return result
