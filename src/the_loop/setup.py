"""Portable, transactional installer for THE LOOP skill packages."""

from __future__ import annotations

import hashlib
import json
import os
import re
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
CANONICAL_DOCUMENTATION_ROOT = "https://github.com/System-Error-Worldwide/the-loop/blob/main/"
_CANONICAL_DOCUMENTATION_LINK = re.compile(
    r"(\]\()" + re.escape(CANONICAL_DOCUMENTATION_ROOT) + r"((?:protocols|schemas|scripts)/[^)]+)(\))"
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


def _rewrite_documentation_links(content: str, local_root: str) -> str:
    return _CANONICAL_DOCUMENTATION_LINK.sub(
        lambda match: match.group(1) + local_root + match.group(2) + match.group(3),
        content,
    )


def _installed_package_digest(package: Path, local_root: str) -> str:
    digest = hashlib.sha256()
    digest.update(b"directory\0")
    for child in sorted(package.rglob("*"), key=lambda item: item.relative_to(package).as_posix()):
        relative_value = child.relative_to(package).as_posix()
        relative = relative_value.encode("utf-8", "surrogateescape")
        if child.is_symlink():
            raise SetupError(f"skill package contains a symlink: {child}")
        if child.is_dir():
            digest.update(b"d\0" + relative + b"\0")
        elif child.is_file():
            digest.update(b"f\0" + relative + b"\0")
            if relative_value == "SKILL.md":
                transformed = _rewrite_documentation_links(child.read_text(encoding="utf-8"), local_root)
                digest.update(transformed.encode("utf-8"))
            else:
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


def _toolkit_files(repository_root: Path) -> list[str]:
    """Return the exact public runtime inventory copied into an installation."""

    patterns = (
        (".agents/skills", {".md"}),
        ("adapters", {".json"}),
        ("protocols", {".md"}),
        ("schemas", {".json", ".md"}),
        ("scripts", {".py"}),
        ("src/the_loop", {".py"}),
    )
    files: list[str] = []
    for directory, suffixes in patterns:
        root = repository_root / directory
        if not root.is_dir() or root.is_symlink():
            raise SetupError(f"repository has no safe toolkit directory: {directory}")
        for path in sorted(root.rglob("*")):
            if path.is_symlink():
                raise SetupError(f"toolkit source contains a symlink: {path.relative_to(repository_root)}")
            if path.is_file() and path.suffix in suffixes:
                files.append(path.relative_to(repository_root).as_posix())
    license_path = repository_root / "LICENSE"
    if license_path.is_file() and not license_path.is_symlink():
        files.append("LICENSE")
    required = {
        "adapters/codex/adapter.json",
        "adapters/claude_code/adapter.json",
        "adapters/kimi_code/adapter.json",
        "adapters/opencode/adapter.json",
        ".agents/skills/the-loop-setup/SKILL.md",
        ".agents/skills/the-loop-doctor/SKILL.md",
        "protocols/stage-contracts.md",
        "schemas/config.schema.json",
        "scripts/the_loop_setup.py",
        "scripts/the_loop_doctor.py",
        "src/the_loop/setup.py",
        "src/the_loop/doctor.py",
        "src/the_loop/validation.py",
    }
    missing = sorted(required - set(files))
    if missing:
        raise SetupError("repository toolkit is incomplete: " + ", ".join(missing))
    return sorted(files)


def _toolkit_digest(repository_root: Path, files: Iterable[str], *, skill_link_root: str | None = None) -> str:
    digest = hashlib.sha256()
    digest.update(b"directory\0")
    normalized = sorted(files)
    directories: set[str] = set()
    for relative in normalized:
        parent = PurePosixPath(relative).parent
        while str(parent) != ".":
            directories.add(parent.as_posix())
            parent = parent.parent
    entries = [(value, "d") for value in directories] + [(value, "f") for value in normalized]
    for relative, kind in sorted(entries):
        encoded = relative.encode("utf-8", "surrogateescape")
        digest.update(kind.encode("ascii") + b"\0" + encoded + b"\0")
        if kind == "f":
            path = repository_root / relative
            if skill_link_root is not None and relative.startswith(".agents/skills/") and relative.endswith("/SKILL.md"):
                transformed = _rewrite_documentation_links(path.read_text(encoding="utf-8"), skill_link_root)
                digest.update(transformed.encode("utf-8"))
            else:
                with path.open("rb") as handle:
                    for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                        digest.update(chunk)
    return digest.hexdigest()


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
            installed_link_root = "../../../.the-loop/toolkit/"
            installed_digest = _installed_package_digest(package, installed_link_root)
            existing_digest = _digest_path(destination)
            if existing_digest == installed_digest:
                action = "skip"
                rollback_action = "none"
            else:
                action = "copy" if mode == "link" and installed_digest != source_digest else mode
                rollback_action = "restore_if_unchanged" if existing_digest is not None else "remove_if_unchanged"
            operations.append(
                {
                    "action": action,
                    "source": str(package),
                    "source_digest": source_digest,
                    "installed_digest": installed_digest,
                    "installed_link_root": installed_link_root,
                    "destination": relative,
                    "pre_existing_digest": existing_digest,
                    "collision": existing_digest is not None and existing_digest != installed_digest,
                    "approval_required": existing_digest is not None and existing_digest != installed_digest,
                    "rollback_action": rollback_action,
                }
            )

    toolkit_files = _toolkit_files(repository)
    toolkit_relative = ".the-loop/toolkit"
    for missing_directory in _missing_directories(target, ".the-loop"):
        if missing_directory not in planned_directories:
            planned_directories.add(missing_directory)
            operations.append(
                {
                    "action": "mkdir",
                    "source": None,
                    "source_digest": None,
                    "destination": missing_directory,
                    "pre_existing_digest": None,
                    "collision": False,
                    "approval_required": False,
                    "rollback_action": "none",
                }
            )
    toolkit_destination = _safe_destination(target, toolkit_relative)
    toolkit_source_digest = _toolkit_digest(repository, toolkit_files)
    toolkit_installed_link_root = "../../../"
    toolkit_installed_digest = _toolkit_digest(
        repository,
        toolkit_files,
        skill_link_root=toolkit_installed_link_root,
    )
    toolkit_existing_digest = _digest_path(toolkit_destination)
    operations.append(
        {
            "action": "skip" if toolkit_existing_digest == toolkit_installed_digest else "copy",
            "source": str(repository),
            "source_digest": toolkit_source_digest,
            "installed_digest": toolkit_installed_digest,
            "installed_link_root": toolkit_installed_link_root,
            "destination": toolkit_relative,
            "pre_existing_digest": toolkit_existing_digest,
            "collision": toolkit_existing_digest is not None and toolkit_existing_digest != toolkit_installed_digest,
            "approval_required": toolkit_existing_digest is not None and toolkit_existing_digest != toolkit_installed_digest,
            "rollback_action": (
                "none"
                if toolkit_existing_digest == toolkit_installed_digest
                else "restore_if_unchanged"
                if toolkit_existing_digest is not None
                else "remove_if_unchanged"
            ),
            "toolkit_files": toolkit_files,
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


_DIRECTORY_FLAGS = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
_READ_FLAGS = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)


def _identity(info: os.stat_result) -> tuple[int, int]:
    return info.st_dev, info.st_ino


class _RootBinding:
    """A retained target descriptor plus a fresh-path namespace identity chain."""

    def __init__(self, target: Path):
        if not target.is_absolute() or target == Path(target.anchor):
            raise SetupError("target root must be a non-root absolute directory")
        self.path = target
        self.parts = target.parts[1:]
        self.identities: list[tuple[int, int]] = []
        descriptor = os.open(target.anchor, _DIRECTORY_FLAGS)
        try:
            for part in self.parts:
                child = os.open(part, _DIRECTORY_FLAGS, dir_fd=descriptor)
                os.close(descriptor)
                descriptor = child
                self.identities.append(_identity(os.fstat(descriptor)))
            self.fd = descriptor
        except BaseException:
            os.close(descriptor)
            raise

    def assert_current(self) -> None:
        descriptor = os.open(self.path.anchor, _DIRECTORY_FLAGS)
        try:
            for index, part in enumerate(self.parts):
                child = os.open(part, _DIRECTORY_FLAGS, dir_fd=descriptor)
                os.close(descriptor)
                descriptor = child
                if _identity(os.fstat(descriptor)) != self.identities[index]:
                    raise SetupError("target root namespace identity changed after planning")
            if _identity(os.fstat(descriptor)) != _identity(os.fstat(self.fd)):
                raise SetupError("target root identity changed after planning")
        except (FileNotFoundError, NotADirectoryError, OSError) as exc:
            if isinstance(exc, SetupError):
                raise
            raise SetupError(f"target root namespace changed after planning: {exc}") from exc
        finally:
            os.close(descriptor)

    def close(self) -> None:
        os.close(self.fd)


class _DestinationBinding:
    """A retained destination-parent descriptor whose canonical chain is rechecked."""

    def __init__(self, root: _RootBinding, relative: str):
        normalized = validate_relative_path(relative, path="$.destination")
        parts = PurePosixPath(normalized).parts
        if not parts or normalized == ".":
            raise SetupError("destination must name a path below the target root")
        self.root = root
        self.relative = normalized
        self.name = parts[-1]
        self.parent_parts = parts[:-1]
        self.parent_identities: list[tuple[int, int]] = []
        descriptor = os.dup(root.fd)
        try:
            for part in self.parent_parts:
                child = os.open(part, _DIRECTORY_FLAGS, dir_fd=descriptor)
                os.close(descriptor)
                descriptor = child
                self.parent_identities.append(_identity(os.fstat(descriptor)))
            self.parent_fd = descriptor
        except BaseException:
            os.close(descriptor)
            raise

    def assert_current(self) -> None:
        self.root.assert_current()
        descriptor = os.dup(self.root.fd)
        try:
            for index, part in enumerate(self.parent_parts):
                child = os.open(part, _DIRECTORY_FLAGS, dir_fd=descriptor)
                os.close(descriptor)
                descriptor = child
                if _identity(os.fstat(descriptor)) != self.parent_identities[index]:
                    raise SetupError(f"destination namespace changed after validation: {self.relative}")
            if _identity(os.fstat(descriptor)) != _identity(os.fstat(self.parent_fd)):
                raise SetupError(f"destination parent identity changed after validation: {self.relative}")
        except (FileNotFoundError, NotADirectoryError, OSError) as exc:
            if isinstance(exc, SetupError):
                raise
            raise SetupError(f"destination namespace changed after validation: {self.relative}: {exc}") from exc
        finally:
            os.close(descriptor)

    def close(self) -> None:
        os.close(self.parent_fd)


def _entry_stat(parent_fd: int, name: str) -> os.stat_result | None:
    try:
        return os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        return None


def _directory_digest_entries(directory_fd: int, prefix: str = "") -> list[tuple[str, str, bytes | None]]:
    entries: list[tuple[str, str, bytes | None]] = []
    for name in sorted(os.listdir(directory_fd)):
        relative = f"{prefix}/{name}" if prefix else name
        info = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        if stat.S_ISLNK(info.st_mode):
            raise SetupError(f"installed directory contains a symlink: {relative}")
        if stat.S_ISDIR(info.st_mode):
            child = os.open(name, _DIRECTORY_FLAGS, dir_fd=directory_fd)
            try:
                entries.append((relative, "d", None))
                entries.extend(_directory_digest_entries(child, relative))
            finally:
                os.close(child)
        elif stat.S_ISREG(info.st_mode):
            descriptor = os.open(name, _READ_FLAGS, dir_fd=directory_fd)
            try:
                chunks: list[bytes] = []
                while True:
                    chunk = os.read(descriptor, 1024 * 1024)
                    if not chunk:
                        break
                    chunks.append(chunk)
            finally:
                os.close(descriptor)
            entries.append((relative, "f", b"".join(chunks)))
        else:
            raise SetupError(f"installed directory contains an unsupported object: {relative}")
    return entries


def _digest_entry_at(parent_fd: int, name: str) -> str | None:
    info = _entry_stat(parent_fd, name)
    if info is None:
        return None
    digest = hashlib.sha256()
    if stat.S_ISLNK(info.st_mode):
        digest.update(b"link\0")
        digest.update(os.readlink(name, dir_fd=parent_fd).encode("utf-8", "surrogateescape"))
        return digest.hexdigest()
    if stat.S_ISREG(info.st_mode):
        digest.update(b"file\0")
        descriptor = os.open(name, _READ_FLAGS, dir_fd=parent_fd)
        try:
            while True:
                chunk = os.read(descriptor, 1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
        finally:
            os.close(descriptor)
        return digest.hexdigest()
    if not stat.S_ISDIR(info.st_mode):
        raise SetupError(f"unsupported filesystem object: {name}")
    digest.update(b"directory\0")
    descriptor = os.open(name, _DIRECTORY_FLAGS, dir_fd=parent_fd)
    try:
        for relative, kind, content in sorted(_directory_digest_entries(descriptor), key=lambda item: item[0]):
            encoded = relative.encode("utf-8", "surrogateescape")
            digest.update(kind.encode("ascii") + b"\0" + encoded + b"\0")
            if content is not None:
                digest.update(content)
    finally:
        os.close(descriptor)
    return digest.hexdigest()


def _copy_toolkit(repository: Path, destination: Path, files: Iterable[str], *, skill_link_root: str) -> None:
    destination.mkdir(mode=0o700)
    for relative in files:
        source = repository / relative
        output = destination / relative
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, output, follow_symlinks=False)
        if relative.startswith(".agents/skills/") and relative.endswith("/SKILL.md"):
            transformed = _rewrite_documentation_links(output.read_text(encoding="utf-8"), skill_link_root)
            output.write_text(transformed, encoding="utf-8")


def _stage_copy(operation: Mapping[str, Any], transaction: Path, index: int) -> str:
    name = f"stage-{index:04d}"
    destination = transaction / name
    source = Path(operation["source"])
    if operation.get("toolkit_files") is not None:
        if list(operation["toolkit_files"]) != _toolkit_files(source):
            raise SetupError("toolkit inventory changed after planning")
        if _toolkit_digest(source, operation["toolkit_files"]) != operation["source_digest"]:
            raise SetupError("toolkit source changed after planning")
        _copy_toolkit(
            source,
            destination,
            operation["toolkit_files"],
            skill_link_root=operation["installed_link_root"],
        )
    else:
        if _digest_path(source) != operation["source_digest"]:
            raise SetupError(f"source changed after planning: {operation['destination']}")
        shutil.copytree(source, destination, symlinks=False)
        skill_file = destination / "SKILL.md"
        if skill_file.is_file():
            transformed = _rewrite_documentation_links(
                skill_file.read_text(encoding="utf-8"),
                operation["installed_link_root"],
            )
            skill_file.write_text(transformed, encoding="utf-8")
    if _digest_path(destination) != operation["installed_digest"]:
        raise SetupError(f"staged output does not match its planned installed digest: {operation['destination']}")
    return name


def _private_directory_info(descriptor: int, *, label: str) -> None:
    info = os.fstat(descriptor)
    if hasattr(os, "getuid") and info.st_uid != os.getuid():
        raise SetupError(f"private install directory is not owned by the current user: {label}")
    if stat.S_IMODE(info.st_mode) & 0o077:
        raise SetupError(f"private install directory grants group or other access: {label}")


def _open_or_create_private(binding: _DestinationBinding) -> tuple[int, bool]:
    binding.assert_current()
    created = False
    if _entry_stat(binding.parent_fd, binding.name) is None:
        os.mkdir(binding.name, mode=0o700, dir_fd=binding.parent_fd)
        created = True
    descriptor = os.open(binding.name, _DIRECTORY_FLAGS, dir_fd=binding.parent_fd)
    _private_directory_info(descriptor, label=binding.relative)
    binding.assert_current()
    return descriptor, created


def _write_json_stage(transaction: Path, name: str, value: Mapping[str, Any]) -> None:
    path = transaction / name
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def _remove_private(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def _conditional_rollback(
    applied: list[dict[str, Any]],
    transaction: Path,
    transaction_fd: int,
) -> list[str]:
    incomplete: list[str] = []
    for index, entry in reversed(list(enumerate(applied))):
        operation = entry["operation"]
        binding: _DestinationBinding = entry["binding"]
        destination = operation["destination"]
        quarantine = f"rollback-{index:04d}"
        current = _entry_stat(binding.parent_fd, binding.name)
        removed = current is None
        if current is not None:
            try:
                os.rename(binding.name, quarantine, src_dir_fd=binding.parent_fd, dst_dir_fd=transaction_fd)
            except OSError:
                incomplete.append(destination)
                continue
            quarantined_digest = _digest_entry_at(transaction_fd, quarantine)
            if quarantined_digest != entry["result_digest"]:
                if _entry_stat(binding.parent_fd, binding.name) is None:
                    os.rename(quarantine, binding.name, src_dir_fd=transaction_fd, dst_dir_fd=binding.parent_fd)
                incomplete.append(destination)
                continue
            _remove_private(transaction / quarantine)
            removed = True
        backup_name = entry.get("backup_name")
        if removed and backup_name is not None:
            if _digest_entry_at(transaction_fd, backup_name) != operation["pre_existing_digest"]:
                incomplete.append(destination)
                continue
            if _entry_stat(binding.parent_fd, binding.name) is not None:
                incomplete.append(destination)
                continue
            os.rename(backup_name, binding.name, src_dir_fd=transaction_fd, dst_dir_fd=binding.parent_fd)
        try:
            binding.assert_current()
        except SetupError:
            incomplete.append(destination)
    return list(dict.fromkeys(incomplete))


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
    approvals = set(approved_destinations)
    required = set(plan.get("approval_required", []))
    missing = sorted(required - approvals)
    if missing:
        raise SetupError("exact approval required for: " + ", ".join(missing))
    root = _RootBinding(target)
    identity = os.fstat(root.fd)
    if list(plan.get("target_identity", [])) != [identity.st_dev, identity.st_ino]:
        root.close()
        raise SetupError("target root identity changed after planning")
    receipt_id = str(uuid.uuid4())
    transaction = Path(tempfile.mkdtemp(prefix=f"the-loop-install-{receipt_id}-", dir=target.parent))
    transaction_fd = os.open(transaction, _DIRECTORY_FLAGS)
    applied: list[dict[str, Any]] = []
    receipt_operations: list[dict[str, Any]] = []
    operation_bindings: list[_DestinationBinding] = []
    installs_binding: _DestinationBinding | None = None
    installs_fd: int | None = None
    installs_created = False
    backups_promoted = False
    cleanup_transaction = True
    try:
        root.assert_current()
        for index, operation in enumerate(plan["operations"]):
            binding = _DestinationBinding(root, operation["destination"])
            operation_bindings.append(binding)
            binding.assert_current()
            action = operation["action"]
            current_digest = _digest_entry_at(binding.parent_fd, binding.name)
            if current_digest != operation["pre_existing_digest"]:
                raise SetupError(f"destination changed after planning: {operation['destination']}")
            source = Path(operation["source"]) if operation["source"] else None
            if source is not None and operation.get("toolkit_files") is None and _digest_path(source) != operation["source_digest"]:
                raise SetupError(f"source changed after planning: {operation['destination']}")
            stage_name = _stage_copy(operation, transaction, index) if action == "copy" else None
            if fault_injector:
                fault_injector("before_operation", operation)
            for retained_binding in operation_bindings:
                retained_binding.assert_current()
            backup_name: str | None = None
            if action == "mkdir":
                mode = 0o700 if operation["destination"] == ".the-loop" else 0o755
                os.mkdir(binding.name, mode=mode, dir_fd=binding.parent_fd)
            elif action == "skip":
                pass
            else:
                if current_digest is not None:
                    if operation["destination"] not in approvals:
                        raise SetupError(f"exact approval required for: {operation['destination']}")
                    backup_name = f"backup-{index:04d}"
                    os.rename(binding.name, backup_name, src_dir_fd=binding.parent_fd, dst_dir_fd=transaction_fd)
                assert source is not None
                if action == "copy":
                    assert stage_name is not None
                    os.rename(stage_name, binding.name, src_dir_fd=transaction_fd, dst_dir_fd=binding.parent_fd)
                elif action == "link":
                    os.symlink(str(source), binding.name, dir_fd=binding.parent_fd)
                else:
                    raise SetupError(f"unsupported planned action: {action}")
            binding.assert_current()
            result_digest = _digest_entry_at(binding.parent_fd, binding.name)
            if action == "copy" and result_digest != operation["installed_digest"]:
                raise SetupError(f"copied output does not match its planned installed digest: {operation['destination']}")
            if action == "link" and (result_digest is None or os.readlink(binding.name, dir_fd=binding.parent_fd) != str(source)):
                raise SetupError(f"linked output does not match its planned source: {operation['destination']}")
            if action != "skip":
                applied.append(
                    {
                        "operation": operation,
                        "binding": binding,
                        "backup_name": backup_name,
                        "result_digest": result_digest,
                    }
                )
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
            for retained_binding in operation_bindings:
                retained_binding.assert_current()
            if _digest_entry_at(binding.parent_fd, binding.name) != result_digest:
                raise SetupError(f"destination changed during installation: {operation['destination']}")

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
        state_binding = _DestinationBinding(root, ".the-loop")
        operation_bindings.append(state_binding)
        state_fd = os.open(state_binding.name, _DIRECTORY_FLAGS, dir_fd=state_binding.parent_fd)
        try:
            _private_directory_info(state_fd, label=".the-loop")
        finally:
            os.close(state_fd)
        installs_binding = _DestinationBinding(root, ".the-loop/installs")
        operation_bindings.append(installs_binding)
        installs_fd, installs_created = _open_or_create_private(installs_binding)
        if fault_injector:
            fault_injector(
                "before_receipt_write",
                {"action": "receipt", "destination": f".the-loop/installs/{receipt_id}.json"},
            )
        for retained_binding in operation_bindings:
            retained_binding.assert_current()
        backup_entries = [entry for entry in applied if entry.get("backup_name") is not None]
        if backup_entries:
            backup_tree = transaction / "backup-tree"
            backup_tree.mkdir(mode=0o700)
            for entry in backup_entries:
                output = backup_tree / entry["operation"]["destination"]
                output.parent.mkdir(parents=True, exist_ok=True)
                os.rename(transaction / entry["backup_name"], output)
            os.rename("backup-tree", f"{receipt_id}.backup", src_dir_fd=transaction_fd, dst_dir_fd=installs_fd)
            backups_promoted = True
        receipt_stage = f"receipt-{receipt_id}.json"
        _write_json_stage(transaction, receipt_stage, receipt)
        installs_binding.assert_current()
        os.rename(receipt_stage, f"{receipt_id}.json", src_dir_fd=transaction_fd, dst_dir_fd=installs_fd)
        os.fsync(installs_fd)
        for retained_binding in operation_bindings:
            retained_binding.assert_current()
        return receipt
    except BaseException as exc:
        if backups_promoted and installs_fd is not None:
            try:
                os.rename(f"{receipt_id}.backup", "backup-tree", src_dir_fd=installs_fd, dst_dir_fd=transaction_fd)
                for index, entry in enumerate(applied):
                    if entry.get("backup_name") is None:
                        continue
                    source = transaction / "backup-tree" / entry["operation"]["destination"]
                    if source.exists() or source.is_symlink():
                        os.rename(source, transaction / entry["backup_name"])
            except OSError:
                pass
        incomplete = _conditional_rollback(applied, transaction, transaction_fd)
        if installs_fd is not None:
            try:
                os.unlink(f"{receipt_id}.json", dir_fd=installs_fd)
            except FileNotFoundError:
                pass
            if installs_created:
                os.close(installs_fd)
                installs_fd = None
                try:
                    os.rmdir(installs_binding.name, dir_fd=installs_binding.parent_fd)  # type: ignore[union-attr]
                except OSError:
                    incomplete.append(".the-loop/installs")
        if incomplete:
            cleanup_transaction = False
            names = ", ".join(dict.fromkeys(incomplete))
            raise SetupError(
                f"rollback_incomplete: {names}; recovery artifacts retained at {transaction}; original failure: {exc}"
            ) from exc
        raise
    finally:
        if installs_fd is not None:
            os.close(installs_fd)
        for binding in operation_bindings:
            binding.close()
        os.close(transaction_fd)
        root.close()
        if cleanup_transaction:
            shutil.rmtree(transaction, ignore_errors=True)


def rollback_install(receipt: Mapping[str, Any], *, target_root: Path | str | None = None) -> dict[str, Any]:
    """Roll back unchanged outputs owned by one validated receipt."""

    validate_record("install_receipt", receipt)
    configured_target = Path(receipt["target_root"])
    target = _canonical_root(target_root or configured_target, label="target root")
    if target != configured_target.resolve(strict=True):
        raise SetupError("target root does not match receipt")
    root = _RootBinding(target)
    transaction = Path(tempfile.mkdtemp(prefix=f"the-loop-rollback-{receipt['receipt_id']}-", dir=target.parent))
    transaction_fd = os.open(transaction, _DIRECTORY_FLAGS)
    bindings: list[_DestinationBinding] = []
    skipped = False
    try:
        root.assert_current()
        for index, operation in reversed(list(enumerate(receipt["operations"]))):
            action = operation["rollback_action"]
            if action == "none":
                continue
            binding = _DestinationBinding(root, operation["destination"])
            bindings.append(binding)
            binding.assert_current()
            if _digest_entry_at(binding.parent_fd, binding.name) != operation["resulting_digest"]:
                skipped = True
                continue
            backup_binding: _DestinationBinding | None = None
            if action == "restore_if_unchanged":
                backup_relative = f".the-loop/installs/{receipt['receipt_id']}.backup/{operation['destination']}"
                try:
                    backup_binding = _DestinationBinding(root, backup_relative)
                except (FileNotFoundError, NotADirectoryError, OSError):
                    skipped = True
                    continue
                bindings.append(backup_binding)
                backup_binding.assert_current()
                if _digest_entry_at(backup_binding.parent_fd, backup_binding.name) != operation["pre_existing_digest"]:
                    skipped = True
                    continue
            quarantine = f"rollback-{index:04d}"
            os.rename(binding.name, quarantine, src_dir_fd=binding.parent_fd, dst_dir_fd=transaction_fd)
            try:
                binding.assert_current()
            except SetupError:
                if _entry_stat(binding.parent_fd, binding.name) is None:
                    os.rename(quarantine, binding.name, src_dir_fd=transaction_fd, dst_dir_fd=binding.parent_fd)
                raise
            if _digest_entry_at(transaction_fd, quarantine) != operation["resulting_digest"]:
                if _entry_stat(binding.parent_fd, binding.name) is None:
                    os.rename(quarantine, binding.name, src_dir_fd=transaction_fd, dst_dir_fd=binding.parent_fd)
                skipped = True
                continue
            _remove_private(transaction / quarantine)
            if backup_binding is not None:
                if _entry_stat(binding.parent_fd, binding.name) is not None:
                    skipped = True
                    continue
                os.rename(
                    backup_binding.name,
                    binding.name,
                    src_dir_fd=backup_binding.parent_fd,
                    dst_dir_fd=binding.parent_fd,
                )
                binding.assert_current()

        result = dict(receipt)
        result["result"] = "partial" if skipped else "rolled_back"
        validate_record("install_receipt", result)
        installs_binding = _DestinationBinding(root, ".the-loop/installs")
        bindings.append(installs_binding)
        installs_binding.assert_current()
        installs_fd = os.open(installs_binding.name, _DIRECTORY_FLAGS, dir_fd=installs_binding.parent_fd)
        try:
            _private_directory_info(installs_fd, label=".the-loop/installs")
            stage_name = f"receipt-{receipt['receipt_id']}.json"
            _write_json_stage(transaction, stage_name, result)
            os.rename(stage_name, f"{receipt['receipt_id']}.json", src_dir_fd=transaction_fd, dst_dir_fd=installs_fd)
            os.fsync(installs_fd)
        finally:
            os.close(installs_fd)
        if not skipped:
            backup_root = _DestinationBinding(root, f".the-loop/installs/{receipt['receipt_id']}.backup")
            bindings.append(backup_root)
            if _entry_stat(backup_root.parent_fd, backup_root.name) is not None:
                backup_root.assert_current()
                os.rename(backup_root.name, "spent-backup", src_dir_fd=backup_root.parent_fd, dst_dir_fd=transaction_fd)
                root.assert_current()
                _remove_private(transaction / "spent-backup")
        root.assert_current()
        return result
    finally:
        for binding in bindings:
            binding.close()
        os.close(transaction_fd)
        root.close()
        shutil.rmtree(transaction, ignore_errors=True)
