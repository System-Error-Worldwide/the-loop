"""Read-only compatibility and installation diagnostics for THE LOOP."""

from __future__ import annotations

import json
import os
import platform
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Mapping

from .setup import SUPPORTED_HARNESSES, load_adapter_manifests
from .validation import ContractError, check_private_permissions, validate_record, validate_relative_path


SCHEMA_VERSION = "1.0"
FRONTMATTER_FIELDS = frozenset({"name", "description", "license", "compatibility"})
BEHAVIOR_STATES = frozenset({"verified", "failed", "denied", "unverified"})


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _portable_root(value: str, *, project_root: Path, user_home: Path | None) -> tuple[Path | None, str]:
    variables = {
        "$HOME/": (user_home, ""),
        "$CODEX_HOME/": (user_home, ".codex/"),
        "$KIMI_CODE_HOME/": (user_home, ".kimi-code/"),
    }
    for prefix, (base, replacement) in variables.items():
        if value.startswith(prefix):
            display = replacement + value[len(prefix) :]
            if base is None:
                return None, value
            normalized = validate_relative_path(display, path="$.user_skill_roots")
            return _safe_read_path(base, normalized), value
    normalized = validate_relative_path(value, path="$.project_skill_roots")
    return _safe_read_path(project_root, normalized), value


def _safe_read_path(root: Path, relative: str) -> Path:
    candidate = root / relative
    current = root
    for part in PurePosixPath(relative).parts:
        current = current / part
        if current.is_symlink():
            raise ContractError(relative, "unsafe_path", "skill root crosses a symlink")
    resolved = candidate.resolve(strict=False)
    if not resolved.is_relative_to(root):
        raise ContractError(relative, "unsafe_path", "skill root escapes its configured base")
    return candidate


def _frontmatter(path: Path) -> tuple[str | None, str | None]:
    try:
        text = path.read_text(encoding="utf-8")
    except PermissionError:
        return None, "permission_denied"
    except OSError:
        return None, "unreadable"
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, "invalid_frontmatter"
    values: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if not line.startswith((" ", "\t")) and ":" in line:
            key, value = line.split(":", 1)
            values[key.strip()] = value.strip().strip('"\'')
    else:
        return None, "invalid_frontmatter"
    if not FRONTMATTER_FIELDS.issubset(values) or not all(values[field] for field in FRONTMATTER_FIELDS):
        return None, "invalid_frontmatter"
    if values["name"] != path.parent.name:
        return values["name"], "name_mismatch"
    return values["name"], None


def _inspect_roots(
    manifest: Mapping[str, Any],
    project_root: Path,
    user_home: Path | None,
) -> tuple[list[str], list[dict[str, Any]], list[dict[str, Any]], str, list[str]]:
    configured = list(manifest["project_skill_roots"]) + list(manifest["user_skill_roots"])
    roots: list[str] = []
    skills: list[dict[str, Any]] = []
    issues: list[str] = []
    denied = False
    for configured_root in configured:
        try:
            path, display = _portable_root(configured_root, project_root=project_root, user_home=user_home)
        except (ContractError, OSError) as exc:
            roots.append(configured_root)
            issues.append(f"unsafe skill root {configured_root}: {exc}")
            denied = True
            continue
        roots.append(configured_root if path is None else display)
        if path is None or not path.exists():
            continue
        try:
            entries = sorted(path.iterdir(), key=lambda item: item.name)
        except PermissionError:
            issues.append(f"permission denied reading {display}")
            denied = True
            continue
        except OSError as exc:
            issues.append(f"failed reading {display}: {exc.__class__.__name__}")
            continue
        for package in entries:
            if package.is_symlink() or not package.is_dir():
                continue
            skill_file = package / "SKILL.md"
            if not skill_file.is_file() or skill_file.is_symlink():
                continue
            name, error = _frontmatter(skill_file)
            skills.append(
                {
                    "name": name or package.name,
                    "source": f"{display}/{package.name}",
                    "status": error or "verified",
                }
            )
            if error:
                issues.append(f"{display}/{package.name}: {error}")
                denied = denied or error == "permission_denied"

    sources: dict[str, list[str]] = {}
    for skill in skills:
        if skill["status"] == "verified":
            sources.setdefault(skill["name"], []).append(skill["source"])
    collisions = [
        {"name": name, "sources": locations, "winner": locations[0]}
        for name, locations in sorted(sources.items())
        if len(locations) > 1
    ]
    if denied:
        discovery = "denied"
    elif any(skill["status"] != "verified" for skill in skills) or not any(
        skill["status"] == "verified" for skill in skills
    ):
        discovery = "failed"
    else:
        discovery = "verified"
    return roots, skills, collisions, discovery, issues


def _check_config(project_root: Path) -> dict[str, Any]:
    path = project_root / ".the-loop" / "config.json"
    if not path.exists():
        return {"status": "not_configured", "path": ".the-loop/config.json", "kill_switches": []}
    if path.is_symlink():
        return {"status": "permission_denied", "path": ".the-loop/config.json", "issues": ["config is a symlink"], "kill_switches": []}
    try:
        check_private_permissions(path, directory=False)
    except ContractError as exc:
        return {"status": "permission_denied", "path": ".the-loop/config.json", "issues": [str(exc)], "kill_switches": []}
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
        validate_record("config", config)
    except (OSError, json.JSONDecodeError, ContractError) as exc:
        return {"status": "invalid", "path": ".the-loop/config.json", "issues": [str(exc)], "kill_switches": []}
    kill_switches = []
    for value in config["kill_switches"]:
        candidate = Path(value)
        if not candidate.is_absolute():
            candidate = project_root / value
        kill_switches.append({"path": value, "visible": candidate.exists() or candidate.is_symlink()})
    return {"status": "verified", "path": ".the-loop/config.json", "issues": [], "kill_switches": kill_switches}


def _check_state(project_root: Path) -> dict[str, Any]:
    path = project_root / ".the-loop"
    if not path.exists() and not path.is_symlink():
        return {"status": "not_configured", "path": ".the-loop", "issues": []}
    try:
        check_private_permissions(path, directory=True)
    except ContractError as exc:
        return {"status": "permission_denied", "path": ".the-loop", "issues": [str(exc)]}
    return {"status": "verified", "path": ".the-loop", "issues": []}


def _outcome(installed: bool, discovery: str, behavior: str, collisions: list[dict[str, Any]]) -> str:
    if not installed:
        return "not_installed"
    if discovery == "denied":
        return "permission_denied"
    if discovery != "verified":
        return "not_discoverable"
    if collisions:
        return "collision"
    if behavior == "verified":
        return "ready"
    return f"behavior_{behavior}"


def run_doctor(
    repository_root: Path | str,
    project_root: Path | str,
    *,
    user_home: Path | str | None = None,
    executable_finder: Callable[[str], str | None] = shutil.which,
    version_reader: Callable[[str], str | None] | None = None,
    behavior_probe: Callable[[str, Mapping[str, Any]], Any] | None = None,
    checked_at: str | None = None,
) -> dict[str, Any]:
    """Inspect adapter, discovery, permission and behavior state without writing."""

    repository = Path(repository_root).resolve(strict=True)
    project = Path(project_root).resolve(strict=True)
    home = Path(user_home).resolve(strict=True) if user_home is not None else None
    reports = load_adapter_manifests(repository)
    timestamp = checked_at or _utc_now()
    harness_reports: dict[str, dict[str, Any]] = {}
    for harness in SUPPORTED_HARNESSES:
        adapter = reports[harness]
        if adapter["status"] != "verified":
            kind = "adapter_missing" if "missing" in str(adapter["error"]) else "adapter_invalid"
            harness_reports[harness] = {
                "adapter_status": "failed",
                "installed": False,
                "version": None,
                "discovery": "unverified",
                "behavior": "unverified",
                "skill_roots": [],
                "skills": [],
                "collisions": [],
                "checked_at": timestamp,
                "evidence_id": None,
                "outcome": kind,
                "issues": [str(adapter["error"])],
            }
            continue
        manifest = adapter["manifest"]
        executable = None
        for name in manifest["executables"]:
            executable = executable_finder(name)
            if executable:
                break
        installed = executable is not None
        version = version_reader(executable) if executable and version_reader else None
        roots, skills, collisions, discovery, issues = _inspect_roots(manifest, project, home)
        behavior = "unverified"
        evidence_id = None
        if installed and discovery == "verified" and behavior_probe is not None:
            try:
                probe_result = behavior_probe(harness, manifest)
                if isinstance(probe_result, Mapping):
                    behavior = probe_result.get("status")
                    evidence_id = probe_result.get("evidence_id")
                else:
                    behavior = probe_result
            except PermissionError:
                behavior = "denied"
            except Exception as exc:  # Probe failures are evidence, not Doctor failures.
                behavior = "failed"
                issues.append(f"behavior probe failed: {exc.__class__.__name__}")
            if not isinstance(behavior, str) or behavior not in BEHAVIOR_STATES:
                behavior = "failed"
                evidence_id = None
                issues.append("behavior probe returned an invalid status")
            if evidence_id is not None:
                try:
                    parsed_evidence = uuid.UUID(str(evidence_id))
                    if parsed_evidence.version != 4 or str(parsed_evidence) != evidence_id:
                        raise ValueError
                except (AttributeError, TypeError, ValueError):
                    behavior = "failed"
                    evidence_id = None
                    issues.append("behavior probe returned an invalid evidence_id")
        harness_reports[harness] = {
            "adapter_status": "verified",
            "installed": installed,
            "version": version,
            "discovery": discovery,
            "behavior": behavior,
            "skill_roots": roots,
            "skills": skills,
            "collisions": collisions,
            "checked_at": timestamp,
            "evidence_id": evidence_id,
            "outcome": _outcome(installed, discovery, behavior, collisions),
            "issues": issues,
        }
    config = _check_config(project)
    state = _check_state(project)
    blocking = (
        any(item["adapter_status"] == "failed" or item["discovery"] == "denied" for item in harness_reports.values())
        or state["status"] == "permission_denied"
        or config["status"] in {"permission_denied", "invalid"}
    )
    ready = any(item["outcome"] == "ready" for item in harness_reports.values())
    return {
        "schema_version": SCHEMA_VERSION,
        "checked_at": timestamp,
        "overall_status": "blocked" if blocking else ("ready" if ready else "warning"),
        "runtime": {"implementation": platform.python_implementation(), "version": platform.python_version()},
        "state": state,
        "config": config,
        "harnesses": harness_reports,
    }
