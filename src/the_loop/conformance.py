"""Deterministic contract conformance for the portable v0.1 pack.

This module proves repository-local package, adapter, Setup, Doctor and scenario
contracts. It deliberately does not claim live model or harness behavior.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Callable, Mapping

from .doctor import run_doctor
from .setup import SUPPORTED_HARNESSES, apply_install, load_adapter_manifests, plan_install


SCHEMA_VERSION = "1.0"
REQUIRED_SKILLS = frozenset(
    {
        "the-loop-setup",
        "the-loop-doctor",
        "the-loop",
        "the-loop-auto",
        "strategize",
        "spec-pack",
        "build",
        "test",
        "resolve",
        "health-check",
        "audit",
        "close",
    }
)
REQUIRED_SCENARIOS = frozenset(
    {
        "setup",
        "doctor",
        "explicit-loop",
        "verified-provider-route",
        "permission-denial",
        "provider-failure-fallback",
        "attended-code-lifecycle",
        "attended-noncode-lifecycle",
        "health-check-feeder",
        "audit-feeder",
        "auto-green",
        "auto-halt-recover-close",
    }
)
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


def _adapter_errors(harness: str, manifest: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    if set(manifest) != REQUIRED_ADAPTER_KEYS:
        errors.append("adapter keys do not match the portable contract")
    if manifest.get("schema_version") != SCHEMA_VERSION:
        errors.append("adapter schema version is unsupported")
    if manifest.get("harness") != harness:
        errors.append("adapter harness identity does not match its path")

    permission = manifest.get("permission_model")
    if not isinstance(permission, Mapping):
        errors.append("permission model is missing")
    else:
        if permission.get("allow_bypass") is not False:
            errors.append("permission bypass must remain disabled")
        if permission.get("preserve_denial") is not True:
            errors.append("host permission denial must be preserved")

    fallback = manifest.get("fallback")
    if not isinstance(fallback, Mapping):
        errors.append("bundled fallback contract is missing")
    elif (
        fallback.get("provider") != "bundled"
        or fallback.get("mode") != "sequential"
        or fallback.get("preserve_authority") is not True
        or fallback.get("preserve_denial") is not True
    ):
        errors.append("bundled fallback weakens portable authority or denial semantics")

    explicit = manifest.get("explicit_invocation")
    implicit = manifest.get("implicit_invocation")
    delegation = manifest.get("delegation")
    for label, value in (("explicit", explicit), ("implicit", implicit), ("delegation", delegation)):
        if not isinstance(value, Mapping) or value.get("behavior_status") != "unverified":
            errors.append(f"{label} behavior must remain unverified before a live probe")
    if isinstance(delegation, Mapping) and delegation.get("on_unavailable") != "sequential":
        errors.append("unavailable delegation must use the sequential fallback")
    return errors


def _load_scenarios(repository: Path) -> tuple[list[dict[str, Any]], list[str]]:
    path = repository / "tests" / "fixtures" / "conformance" / "scenarios.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        scenarios = value["scenarios"]
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        return [], [f"scenario matrix is unreadable: {exc.__class__.__name__}"]
    if not isinstance(scenarios, list):
        return [], ["scenario matrix must contain a list"]
    identifiers = [item.get("id") for item in scenarios if isinstance(item, Mapping)]
    errors: list[str] = []
    if len(scenarios) != 12 or len(identifiers) != 12 or len(set(identifiers)) != 12:
        errors.append("scenario matrix must contain twelve unique records")
    if set(identifiers) != REQUIRED_SCENARIOS:
        errors.append("scenario matrix does not match the required v0.1 set")
    for item in scenarios:
        if not isinstance(item, Mapping):
            errors.append("scenario record is not an object")
            continue
        if not item.get("expected_artifacts") or not item.get("safety_assertions"):
            errors.append(f"scenario {item.get('id', '<unknown>')} lacks evidence or safety assertions")
    return [dict(item) for item in scenarios if isinstance(item, Mapping)], errors


def _source_skill_errors(repository: Path) -> list[str]:
    root = repository / ".agents" / "skills"
    found = {
        path.parent.name
        for path in root.glob("*/SKILL.md")
        if path.is_file() and not path.is_symlink() and not path.parent.is_symlink()
    }
    missing = sorted(REQUIRED_SKILLS - found)
    extra = sorted(found - REQUIRED_SKILLS)
    errors: list[str] = []
    if missing:
        errors.append("missing required skills: " + ", ".join(missing))
    if extra:
        errors.append("unexpected v0.1 skills: " + ", ".join(extra))
    return errors


def run_contract_conformance(
    repository_root: Path | str,
    project_root: Path | str,
    *,
    executable_finder: Callable[[str], str | None] = shutil.which,
    checked_at: str | None = None,
) -> dict[str, Any]:
    """Run the shared 4-by-12 contract matrix without invoking a provider."""

    repository = Path(repository_root).resolve(strict=True)
    projects = Path(project_root).resolve(strict=False)
    projects.mkdir(parents=True, exist_ok=True)
    scenarios, scenario_errors = _load_scenarios(repository)
    skill_errors = _source_skill_errors(repository)
    manifest_reports = load_adapter_manifests(repository)

    harness_reports: dict[str, dict[str, Any]] = {}
    passed = 0
    failed = 0
    for harness in SUPPORTED_HARNESSES:
        errors = list(scenario_errors) + list(skill_errors)
        manifest_report = manifest_reports[harness]
        if manifest_report["status"] != "verified":
            errors.append(manifest_report["error"])
            manifest: Mapping[str, Any] = {}
        else:
            manifest = manifest_report["manifest"]
            errors.extend(_adapter_errors(harness, manifest))

        install_result = "not_run"
        discovery_status = "failed"
        behavior_status = "unverified"
        doctor_outcome = "not_run"
        collisions: list[dict[str, Any]] = []
        receipt_id: str | None = None
        if not errors:
            target = projects / harness
            target.mkdir(mode=0o700, parents=True, exist_ok=True)
            home = target / "synthetic-home"
            home.mkdir(mode=0o700, exist_ok=True)
            try:
                plan = plan_install(
                    repository,
                    target,
                    repository,
                    harnesses=[harness],
                    executable_finder=executable_finder,
                )
                receipt = apply_install(plan, actor="conformance", source_version="0.1.0")
                install_result = receipt["result"]
                receipt_id = receipt["receipt_id"]
                doctor = run_doctor(
                    repository,
                    target,
                    user_home=home,
                    executable_finder=executable_finder,
                    version_reader=lambda _path: "synthetic",
                    checked_at=checked_at,
                )
                discovery_status = doctor["harnesses"][harness]["discovery"]
                behavior_status = doctor["harnesses"][harness]["behavior"]
                doctor_outcome = doctor["harnesses"][harness]["outcome"]
                collisions = doctor["harnesses"][harness]["collisions"]
                if install_result != "complete":
                    errors.append("Setup did not produce a complete receipt")
                if discovery_status != "verified":
                    errors.append("Doctor did not verify package discovery")
                if behavior_status != "unverified":
                    errors.append("synthetic discovery must not claim live behavior")
                if doctor_outcome != "behavior_unverified" or collisions:
                    errors.append("Setup produced a colliding or otherwise unready discovery result")
            except Exception as exc:  # the report must stay truthful on any contract failure
                errors.append(f"Setup or Doctor failed: {exc.__class__.__name__}: {exc}")

        status = "contract_passed" if not errors else "contract_failed"
        scenario_results = [
            {
                "id": scenario["id"],
                "status": status,
                "evidence": list(scenario.get("expected_artifacts", [])),
                "errors": list(errors),
            }
            for scenario in scenarios
        ]
        passed += sum(item["status"] == "contract_passed" for item in scenario_results)
        failed += sum(item["status"] == "contract_failed" for item in scenario_results)
        harness_reports[harness] = {
            "install_result": install_result,
            "receipt_id": receipt_id,
            "discovery_status": discovery_status,
            "behavior_status": behavior_status,
            "doctor_outcome": doctor_outcome,
            "collisions": collisions,
            "scenarios": scenario_results,
        }

    total = passed + failed
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": "contract_conformance",
        "live_behavior_claim": False,
        "harnesses": harness_reports,
        "summary": {"passed": passed, "failed": failed, "total": total},
    }
