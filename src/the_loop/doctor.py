"""Read-only compatibility and installation diagnostics for THE LOOP."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Mapping

from .integrity import canonical_file_digest, load_release_integrity, release_integrity_errors
from .setup import SUPPORTED_HARNESSES, _digest_path, load_adapter_manifests
from .validation import ContractError, check_private_permissions, validate_record, validate_relative_path


SCHEMA_VERSION = "1.0"
FRONTMATTER_FIELDS = frozenset({"name", "description", "license", "compatibility"})
BEHAVIOR_STATES = frozenset({"verified", "failed", "denied", "unverified"})
REQUIRED_PACK_SKILLS = frozenset(
    {
        "audit",
        "bootstrap-agent-context",
        "build",
        "close",
        "decision-log",
        "feature-tracker",
        "handoff",
        "health-check",
        "idea-to-brief",
        "live-state-preflight",
        "portfolio-review",
        "pre-commit-review",
        "resolve",
        "retrospective",
        "session-summary",
        "spec-pack",
        "stack-summary",
        "strategize",
        "test",
        "the-loop",
        "the-loop-auto",
        "the-loop-autonomy",
        "the-loop-cloud",
        "the-loop-control",
        "the-loop-doctor",
        "the-loop-endless",
        "the-loop-parallel",
        "the-loop-setup",
        "the-loop-skill-creator",
        "the-loop-skill-planner",
        "the-loop-watch",
    }
)
PROBE_FIELDS = frozenset(
    {
        "status",
        "evidence_id",
        "harness",
        "harness_version",
        "scope",
        "capability",
        "permission_outcome",
        "environment_digest",
        "observed_at",
    }
)
EXPECTED_PROBE_CAPABILITY = "portable-skill-invocation"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _portable_root(
    value: str,
    *,
    project_root: Path,
    user_home: Path | None,
    environment: Mapping[str, str],
) -> tuple[Path | None, str]:
    configured_homes = {
        "CODEX_HOME": Path(environment["CODEX_HOME"]).resolve(strict=False)
        if environment.get("CODEX_HOME")
        else (user_home / ".codex" if user_home is not None else None),
        "KIMI_CODE_HOME": Path(environment["KIMI_CODE_HOME"]).resolve(strict=False)
        if environment.get("KIMI_CODE_HOME")
        else (user_home / ".kimi-code" if user_home is not None else None),
        "DSH_HOME": Path(environment["DSH_HOME"]).resolve(strict=False)
        if environment.get("DSH_HOME")
        else (user_home / ".dsh" if user_home is not None else None),
        "DSH_AGENTS_HOME": Path(environment["DSH_AGENTS_HOME"]).resolve(strict=False)
        if environment.get("DSH_AGENTS_HOME")
        else (user_home / ".agents" if user_home is not None else None),
    }
    variables = {
        "$HOME/": user_home,
        "$CODEX_HOME/": configured_homes["CODEX_HOME"],
        "$KIMI_CODE_HOME/": configured_homes["KIMI_CODE_HOME"],
        "$DSH_HOME/": configured_homes["DSH_HOME"],
        "$DSH_AGENTS_HOME/": configured_homes["DSH_AGENTS_HOME"],
    }
    for prefix, base in variables.items():
        if value.startswith(prefix):
            relative = value[len(prefix) :]
            if base is None:
                return None, value
            normalized = validate_relative_path(relative, path="$.user_skill_roots")
            return _safe_read_path(base, normalized), value
    normalized = validate_relative_path(value, path="$.project_skill_roots")
    return _safe_read_path(project_root, normalized), value


def _safe_read_path(root: Path, relative: str) -> Path:
    root = root.resolve(strict=False)
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
    environment: Mapping[str, str],
) -> tuple[list[str], list[dict[str, Any]], list[dict[str, Any]], str, list[str]]:
    configured = list(manifest["project_skill_roots"]) + list(manifest["user_skill_roots"])
    roots: list[str] = []
    skills: list[dict[str, Any]] = []
    issues: list[str] = []
    denied = False
    for configured_root in configured:
        try:
            path, display = _portable_root(
                configured_root,
                project_root=project_root,
                user_home=user_home,
                environment=environment,
            )
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
                    "_digest": _digest_path(package) if error is None else None,
                    "_path": package,
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


def _receipt_candidates(project: Path, user_home: Path | None, environment: Mapping[str, str]) -> list[Path]:
    bases = [project]
    if user_home is not None:
        bases.append(user_home)
    for variable in ("CODEX_HOME", "KIMI_CODE_HOME", "DSH_HOME", "DSH_AGENTS_HOME"):
        value = environment.get(variable)
        if value:
            bases.append(Path(value).resolve(strict=False))
    seen: set[Path] = set()
    receipts: list[Path] = []
    for base in bases:
        installs = base / ".the-loop" / "installs"
        if installs in seen or not installs.is_dir() or installs.is_symlink():
            continue
        seen.add(installs)
        try:
            check_private_permissions(installs, directory=True)
            entries = sorted(installs.glob("*.json"))
        except (ContractError, OSError):
            continue
        receipts.extend(path for path in entries if path.is_file() and not path.is_symlink())
    return receipts


def _pack_integrity(
    harness: str,
    skills: list[dict[str, Any]],
    *,
    project: Path,
    user_home: Path | None,
    environment: Mapping[str, str],
) -> tuple[str, str | None, str | None, list[str]]:
    """Bind a complete discovered pack to one unchanged Setup receipt."""

    verified = [item for item in skills if item["status"] == "verified"]
    winning: dict[str, dict[str, Any]] = {}
    for item in verified:
        winning.setdefault(item["name"], item)
    missing = sorted(REQUIRED_PACK_SKILLS - set(winning))
    if missing:
        return "incomplete", None, None, ["missing required skills: " + ", ".join(missing)]

    candidates: list[tuple[str, dict[str, Any], Path]] = []
    receipt_issues: list[str] = []
    for path in _receipt_candidates(project, user_home, environment):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            validate_record("install_receipt", value)
            check_private_permissions(path, directory=False)
        except (OSError, json.JSONDecodeError, ContractError) as exc:
            receipt_issues.append(f"invalid install receipt {path.name}: {exc}")
            continue
        if value["result"] != "complete" or harness not in value["harnesses"]:
            continue
        try:
            target = Path(value["target_root"]).resolve(strict=True)
        except OSError:
            continue
        try:
            receipt_base = path.parents[2].resolve(strict=True)
        except (IndexError, OSError):
            continue
        if receipt_base != target or path.name != f"{value['receipt_id']}.json":
            continue
        candidates.append((value["created_at"], value, target))

    for _created_at, receipt, target in sorted(candidates, key=lambda item: item[0], reverse=True):
        operations = receipt["operations"]
        toolkit = next(
            (item for item in operations if item["destination"] == ".the-loop/toolkit"),
            None,
        )
        toolkit_root = target / ".the-loop" / "toolkit"
        if (
            toolkit is None
            or _digest_path(toolkit_root) != toolkit["resulting_digest"]
            or release_integrity_errors(toolkit_root)
        ):
            continue
        approved_files, manifest_errors = load_release_integrity(toolkit_root)
        if approved_files is None or manifest_errors:
            continue
        operation_by_skill: dict[str, list[dict[str, Any]]] = {}
        for operation in operations:
            parts = PurePosixPath(operation["destination"]).parts
            if len(parts) >= 2 and parts[-2] == "skills":
                operation_by_skill.setdefault(parts[-1], []).append(operation)
        if not REQUIRED_PACK_SKILLS.issubset(set(operation_by_skill)):
            continue
        destinations_match = True
        for name in REQUIRED_PACK_SKILLS:
            winning_path = winning[name].get("_path")
            if not isinstance(winning_path, Path):
                destinations_match = False
                break
            matched = False
            for operation in operation_by_skill[name]:
                try:
                    operation_path = _safe_read_path(target, operation["destination"])
                    same_path = operation_path.resolve(strict=True) == winning_path.resolve(strict=True)
                except (ContractError, OSError):
                    same_path = False
                if same_path and winning[name].get("_digest") == operation["resulting_digest"]:
                    matched = True
                    break
            if not matched:
                destinations_match = False
                break
        if not destinations_match:
            continue
        package_integrity_failed = False
        for name in REQUIRED_PACK_SKILLS:
            relative = f".agents/skills/{name}/SKILL.md"
            package = winning[name].get("_path")
            try:
                names = sorted(item.name for item in package.iterdir()) if isinstance(package, Path) else []
                digest = (
                    canonical_file_digest(package / "SKILL.md", relative)
                    if isinstance(package, Path)
                    else None
                )
            except (OSError, UnicodeDecodeError):
                names = []
                digest = None
            if names != ["SKILL.md"] or digest != approved_files.get(relative):
                package_integrity_failed = True
                break
        if package_integrity_failed:
            continue
        pack_facts = {
            "receipt_id": receipt["receipt_id"],
            "toolkit_digest": toolkit["resulting_digest"],
            "skills": {
                name: winning[name]["_digest"] for name in sorted(REQUIRED_PACK_SKILLS)
            },
        }
        pack_digest = hashlib.sha256(
            json.dumps(pack_facts, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        return "complete", receipt["receipt_id"], pack_digest, []

    issues = receipt_issues or ["complete pack is not bound to an unchanged Setup receipt and toolkit"]
    return "integrity_unverified", None, None, issues


def _probe_environment_digest(
    *,
    harness: str,
    version: str,
    manifest: Mapping[str, Any],
    pack_digest: str,
) -> str:
    facts = {
        "schema_version": SCHEMA_VERSION,
        "harness": harness,
        "harness_version": version,
        "adapter": manifest,
        "pack_digest": pack_digest,
        "runtime": {
            "implementation": platform.python_implementation(),
            "version": platform.python_version(),
            "system": platform.system(),
            "machine": platform.machine(),
        },
    }
    return hashlib.sha256(
        json.dumps(facts, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


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


def _outcome(
    installed: bool,
    discovery: str,
    behavior: str,
    collisions: list[dict[str, Any]],
    *,
    pack_status: str,
    version: str | None,
) -> str:
    if not installed:
        return "not_installed"
    if discovery == "denied":
        return "permission_denied"
    if discovery != "verified":
        return "not_discoverable"
    if collisions:
        return "collision"
    if pack_status != "complete":
        return "pack_incomplete"
    if behavior == "verified":
        return "ready" if version else "version_unverified"
    return f"behavior_{behavior}"


def _verified_probe_error(
    value: Mapping[str, Any],
    *,
    harness: str,
    version: str | None,
    checked_at: str,
    environment_digest: str,
) -> str | None:
    if set(value) != PROBE_FIELDS:
        return "verified behavior probe must return the complete typed evidence contract"
    expected = {
        "status": "verified",
        "harness": harness,
        "harness_version": version,
        "scope": "project",
        "permission_outcome": "allowed",
        "observed_at": checked_at,
    }
    for field, expected_value in expected.items():
        if value.get(field) != expected_value:
            return f"verified behavior probe field {field} does not match the Doctor context"
    if value.get("capability") != EXPECTED_PROBE_CAPABILITY:
        return f"verified behavior probe capability must be {EXPECTED_PROBE_CAPABILITY}"
    digest = value.get("environment_digest")
    if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
        return "verified behavior probe environment_digest is invalid"
    if digest != environment_digest:
        return "verified behavior probe environment_digest does not match the Doctor context"
    return None


def run_doctor(
    repository_root: Path | str,
    project_root: Path | str,
    *,
    user_home: Path | str | None = None,
    executable_finder: Callable[[str], str | None] = shutil.which,
    version_reader: Callable[[str], str | None] | None = None,
    behavior_probe: Callable[[str, Mapping[str, Any]], Any] | None = None,
    environment: Mapping[str, str] | None = None,
    checked_at: str | None = None,
) -> dict[str, Any]:
    """Inspect adapter, discovery, permission and behavior state without writing."""

    repository = Path(repository_root).resolve(strict=True)
    project = Path(project_root).resolve(strict=True)
    home = Path(user_home).resolve(strict=True) if user_home is not None else None
    reports = load_adapter_manifests(repository)
    timestamp = checked_at or _utc_now()
    selected_environment = dict(environment or {})
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
                "pack_status": "unverified",
                "missing_skills": sorted(REQUIRED_PACK_SKILLS),
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
        roots, skills, collisions, discovery, issues = _inspect_roots(
            manifest,
            project,
            home,
            selected_environment,
        )
        verified_names = {item["name"] for item in skills if item["status"] == "verified"}
        missing_skills = sorted(REQUIRED_PACK_SKILLS - verified_names)
        pack_status, pack_receipt_id, pack_digest, integrity_issues = _pack_integrity(
            harness,
            skills,
            project=project,
            user_home=home,
            environment=selected_environment,
        )
        issues.extend(integrity_issues)
        environment_digest = (
            _probe_environment_digest(
                harness=harness,
                version=version,
                manifest=manifest,
                pack_digest=pack_digest,
            )
            if version is not None and pack_digest is not None
            else None
        )
        behavior = "unverified"
        evidence_id = None
        behavior_evidence = None
        if (
            installed
            and version is not None
            and discovery == "verified"
            and pack_status == "complete"
            and behavior_probe is not None
        ):
            try:
                probe_manifest = dict(manifest)
                probe_manifest["_doctor_context"] = {
                    "capability": EXPECTED_PROBE_CAPABILITY,
                    "environment_digest": environment_digest,
                    "pack_digest": pack_digest,
                    "receipt_id": pack_receipt_id,
                }
                probe_result = behavior_probe(harness, probe_manifest)
                if isinstance(probe_result, Mapping):
                    behavior = probe_result.get("status")
                    evidence_id = probe_result.get("evidence_id")
                    behavior_evidence = dict(probe_result)
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
            if behavior == "verified":
                if not isinstance(probe_result, Mapping):
                    behavior = "failed"
                    evidence_id = None
                    behavior_evidence = None
                    issues.append("verified behavior requires typed evidence")
                else:
                    probe_error = _verified_probe_error(
                        probe_result,
                        harness=harness,
                        version=version,
                        checked_at=timestamp,
                        environment_digest=environment_digest or "",
                    )
                    if probe_error:
                        behavior = "failed"
                        evidence_id = None
                        behavior_evidence = None
                        issues.append(probe_error)
            if evidence_id is not None:
                try:
                    parsed_evidence = uuid.UUID(str(evidence_id))
                    if parsed_evidence.version != 4 or str(parsed_evidence) != evidence_id:
                        raise ValueError
                except (AttributeError, TypeError, ValueError):
                    behavior = "failed"
                    evidence_id = None
                    issues.append("behavior probe returned an invalid evidence_id")
        public_skills = [
            {key: value for key, value in item.items() if not key.startswith("_")}
            for item in skills
        ]
        harness_reports[harness] = {
            "adapter_status": "verified",
            "installed": installed,
            "version": version,
            "discovery": discovery,
            "behavior": behavior,
            "skill_roots": roots,
            "skills": public_skills,
            "collisions": collisions,
            "pack_status": pack_status,
            "pack_receipt_id": pack_receipt_id,
            "pack_digest": pack_digest,
            "environment_digest": environment_digest,
            "missing_skills": missing_skills,
            "checked_at": timestamp,
            "evidence_id": evidence_id,
            "behavior_evidence": behavior_evidence,
            "outcome": _outcome(
                installed,
                discovery,
                behavior,
                collisions,
                pack_status=pack_status,
                version=version,
            ),
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
