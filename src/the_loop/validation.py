"""Standard-library JSON Schema and semantic contract validation.

The schema files are the public machine-readable contract. This module supports
the deliberately small JSON Schema vocabulary used by those files and adds the
cross-record invariants that JSON Schema cannot express safely on its own.
"""

from __future__ import annotations

import json
import os
import re
import stat
from datetime import datetime
from decimal import Decimal, InvalidOperation
from decimal import Decimal
from functools import lru_cache
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Mapping


SCHEMA_ROOT = Path(__file__).resolve().parents[2] / "schemas"
SCHEMA_FILES = {
    "config": "config.schema.json",
    "install_receipt": "install-receipt.schema.json",
    "run": "run.schema.json",
    "lease": "lease.schema.json",
    "grant": "grant.schema.json",
    "route": "route.schema.json",
    "evidence": "evidence.schema.json",
    "issue_ledger": "issue-ledger.schema.json",
    "audit_event": "audit-event.schema.json",
}

PERMANENT_INVARIANTS = frozenset(
    {
        "visible_authority",
        "audit_log",
        "evidence_required",
        "run_ownership",
        "leases",
        "external_kill_switch",
        "faithful_failure",
        "no_silent_elevation",
    }
)

ALLOWED_ENVIRONMENT_FIELDS = frozenset(
    {"harness", "harness_version", "platform", "platform_version", "python_version", "working_directory", "locale"}
)

RUN_TRANSITIONS = {
    "draft": frozenset({"ready", "cancelled"}),
    "ready": frozenset({"active", "cancelled"}),
    "active": frozenset(
        {
            "waiting_approval",
            "waiting_external",
            "blocked",
            "failed",
            "halted_kill_switch",
            "complete",
            "cancelled",
        }
    ),
    "waiting_approval": frozenset({"ready", "cancelled"}),
    "waiting_external": frozenset({"ready", "cancelled"}),
    "blocked": frozenset({"ready", "cancelled"}),
    "failed": frozenset({"ready", "cancelled"}),
    "halted_kill_switch": frozenset({"ready", "cancelled"}),
    "complete": frozenset(),
    "cancelled": frozenset(),
}

ISSUE_TRANSITIONS = {
    "open": frozenset({"acknowledged", "deferred"}),
    "acknowledged": frozenset({"resolving", "deferred"}),
    "resolving": frozenset({"verification_pending", "deferred"}),
    "verification_pending": frozenset({"closed", "reopened", "deferred"}),
    "reopened": frozenset({"resolving", "deferred"}),
    "deferred": frozenset({"acknowledged"}),
    "closed": frozenset({"reopened"}),
}

LEASE_FORBIDDEN_EVENT_TYPES = frozenset({"run_created", "authority_granted", "authority_revoked"})
LEASE_OPTIONAL_EVENT_TYPES = LEASE_FORBIDDEN_EVENT_TYPES | {"kill_switch_detected", "operation_reconciled"}
UNKNOWN_OUTCOME_PROJECTIONS = {
    "local": ("failed", "operation_outcome_unknown"),
    "external": ("waiting_external", "external_operation_outcome_unknown"),
}
STAGE_ORDER = ("strategize", "spec_pack", "build", "test", "resolve", "close")


class ContractError(ValueError):
    """A precise schema, invariant, ownership or filesystem contract error."""

    def __init__(self, path: str, code: str, message: str) -> None:
        self.path = path
        self.code = code
        self.message = message
        super().__init__(f"{path}: [{code}] {message}")


def _exhausted_budget_markers(run: Mapping[str, Any]) -> list[dict[str, Any]]:
    markers: list[dict[str, Any]] = []
    usage = run["usage"]
    budgets = run["budgets"]
    reason = run.get("terminal_reason")
    reason_code = reason.get("code") if isinstance(reason, Mapping) else None
    primary_budget = (
        reason_code.removeprefix("budget_reached:")
        if isinstance(reason_code, str) and reason_code.startswith("budget_reached:")
        else None
    )
    duration = Decimal(str(usage["duration_seconds"]))
    if duration > 0 and duration >= Decimal(str(budgets["max_duration_seconds"])):
        markers.append(
            {
                "budget": "max_duration_seconds",
                "stage": None,
                "limit": budgets["max_duration_seconds"],
                "observed": usage["duration_seconds"],
            }
        )
    attempt_limit = int(budgets["max_stage_attempts"])
    for stage in STAGE_ORDER:
        observed = int(usage["stage_attempts"][stage])
        if observed > 0 and observed >= attempt_limit:
            markers.append(
                {"budget": "max_stage_attempts", "stage": stage, "limit": attempt_limit, "observed": observed}
            )
    for field in ("mutations", "external_actions"):
        observed = int(usage[field])
        budget_field = f"max_{field}"
        limit = int(budgets[budget_field])
        if (observed > 0 or primary_budget == budget_field) and observed >= limit:
            markers.append({"budget": budget_field, "stage": None, "limit": limit, "observed": observed})
    cost_limit = budgets["max_cost_usd"]
    observed_cost = usage["cost_usd"]
    if observed_cost is None and primary_budget == "max_cost_usd" and cost_limit is not None:
        observed_cost = "0"
    if cost_limit is not None and observed_cost is not None:
        if (Decimal(observed_cost) > 0 or primary_budget == "max_cost_usd") and Decimal(
            observed_cost
        ) >= Decimal(cost_limit):
            markers.append(
                {"budget": "max_cost_usd", "stage": None, "limit": cost_limit, "observed": observed_cost}
            )
    return markers


def _next_budget_marker(event: Mapping[str, Any]) -> dict[str, Any] | None:
    run = event["projection"]["run"]
    markers = _exhausted_budget_markers(run)
    reason = run.get("terminal_reason")
    code = reason.get("code") if isinstance(reason, Mapping) else None
    if event["type"] == "budget_reached":
        try:
            index = markers.index(event["data"])
        except ValueError:
            return None
        return markers[index + 1] if index + 1 < len(markers) else None
    if isinstance(code, str) and (
        code.startswith("budget_reached:")
        or code in {unknown_code for _, unknown_code in UNKNOWN_OUTCOME_PROJECTIONS.values()}
    ):
        return markers[0] if markers else None
    return None


@lru_cache(maxsize=None)
def _load_schema(filename: str) -> dict[str, Any]:
    path = (SCHEMA_ROOT / filename).resolve()
    if not path.is_relative_to(SCHEMA_ROOT.resolve()):
        raise ContractError("$", "schema_ref", "schema reference escapes the schema directory")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError("$", "schema_load", f"cannot load {filename}: {exc}") from exc
    if not isinstance(value, dict):
        raise ContractError("$", "schema_load", f"{filename} is not a JSON object")
    return value


def _json_pointer(document: Any, pointer: str) -> Any:
    value = document
    if not pointer:
        return value
    if not pointer.startswith("/"):
        raise ContractError("$", "schema_ref", f"invalid JSON pointer #{pointer}")
    for raw_part in pointer[1:].split("/"):
        part = raw_part.replace("~1", "/").replace("~0", "~")
        try:
            value = value[int(part)] if isinstance(value, list) else value[part]
        except (KeyError, IndexError, ValueError, TypeError) as exc:
            raise ContractError("$", "schema_ref", f"unresolved JSON pointer #{pointer}") from exc
    return value


def _resolve_ref(ref: str, current_file: str) -> tuple[dict[str, Any], str]:
    file_part, separator, fragment = ref.partition("#")
    target_file = file_part or current_file
    target = _json_pointer(_load_schema(target_file), fragment if separator else "")
    if not isinstance(target, dict):
        raise ContractError("$", "schema_ref", f"schema reference {ref!r} is not an object")
    return target, target_file


def _type_matches(value: Any, expected: str) -> bool:
    if expected == "null":
        return value is None
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "string":
        return isinstance(value, str)
    if expected == "array":
        return isinstance(value, list)
    if expected == "object":
        return isinstance(value, dict)
    return False


def _validate_schema(value: Any, schema: Mapping[str, Any], current_file: str, path: str) -> None:
    if "$ref" in schema:
        target, target_file = _resolve_ref(str(schema["$ref"]), current_file)
        _validate_schema(value, target, target_file, path)

    if "const" in schema and value != schema["const"]:
        raise ContractError(path, "const", f"must equal {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        allowed = ", ".join(repr(item) for item in schema["enum"])
        raise ContractError(path, "enum", f"must be one of: {allowed}")

    for keyword in ("allOf", "anyOf", "oneOf"):
        if keyword not in schema:
            continue
        matches = 0
        failures: list[str] = []
        for option in schema[keyword]:
            try:
                _validate_schema(value, option, current_file, path)
                matches += 1
            except ContractError as exc:
                failures.append(exc.message)
        if keyword == "allOf" and matches != len(schema[keyword]):
            raise ContractError(path, "all_of", failures[0])
        if keyword == "anyOf" and matches == 0:
            raise ContractError(path, "any_of", "does not match any allowed shape: " + "; ".join(failures))
        if keyword == "oneOf" and matches != 1:
            raise ContractError(path, "one_of", f"must match exactly one shape; matched {matches}")

    expected_type = schema.get("type")
    if expected_type is not None:
        expected = [expected_type] if isinstance(expected_type, str) else expected_type
        if not any(_type_matches(value, item) for item in expected):
            raise ContractError(path, "type", f"expected {' or '.join(expected)}, got {type(value).__name__}")

    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            raise ContractError(path, "min_length", f"must contain at least {schema['minLength']} character(s)")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            raise ContractError(path, "max_length", f"must contain at most {schema['maxLength']} character(s)")
        if "pattern" in schema and re.search(schema["pattern"], value) is None:
            raise ContractError(path, "pattern", f"does not match required pattern {schema['pattern']!r}")
        if schema.get("format") == "date-time":
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError as exc:
                raise ContractError(path, "timestamp", "must be a valid RFC 3339 timestamp") from exc
            if parsed.tzinfo is None:
                raise ContractError(path, "timestamp", "must include a UTC offset")

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            raise ContractError(path, "minimum", f"must be at least {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            raise ContractError(path, "maximum", f"must be at most {schema['maximum']}")

    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            raise ContractError(path, "min_items", f"must contain at least {schema['minItems']} item(s)")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            raise ContractError(path, "max_items", f"must contain at most {schema['maxItems']} item(s)")
        if schema.get("uniqueItems"):
            encoded = [json.dumps(item, sort_keys=True, separators=(",", ":")) for item in value]
            if len(encoded) != len(set(encoded)):
                raise ContractError(path, "unique_items", "must not contain duplicate items")
        if "items" in schema:
            for index, item in enumerate(value):
                _validate_schema(item, schema["items"], current_file, f"{path}[{index}]")

    if isinstance(value, dict):
        required = schema.get("required", [])
        for key in required:
            if key not in value:
                raise ContractError(path, "required", f"missing required property {key!r}")
        properties = schema.get("properties", {})
        if "propertyNames" in schema:
            for key in value:
                _validate_schema(key, schema["propertyNames"], current_file, f"{path}.<property>")
        for key, item in value.items():
            item_path = f"{path}.{key}"
            if key in properties:
                _validate_schema(item, properties[key], current_file, item_path)
            else:
                additional = schema.get("additionalProperties", True)
                if additional is False:
                    raise ContractError(item_path, "additional_property", "property is not allowed")
                if isinstance(additional, dict):
                    _validate_schema(item, additional, current_file, item_path)


def validate_relative_path(value: str, *, path: str = "$") -> str:
    """Return a normalized portable relative path or raise ContractError."""

    if not isinstance(value, str) or not value:
        raise ContractError(path, "unsafe_path", "path must be a non-empty string")
    if "\x00" in value:
        raise ContractError(path, "unsafe_path", "path contains a NUL byte")
    if value.startswith("~"):
        raise ContractError(path, "unsafe_path", "home-relative paths are not allowed")
    if PureWindowsPath(value).is_absolute() or PurePosixPath(value.replace("\\", "/")).is_absolute():
        raise ContractError(path, "unsafe_path", "absolute paths are not allowed")
    normalized = value.replace("\\", "/")
    parts = PurePosixPath(normalized).parts
    if any(part == ".." for part in parts):
        raise ContractError(path, "unsafe_path", "parent traversal is not allowed")
    if any(part in ("", ".") for part in parts) and normalized not in (".",):
        normalized = PurePosixPath(normalized).as_posix()
    if normalized == ".":
        return normalized
    return PurePosixPath(normalized).as_posix()


def validate_configured_path(value: str, *, path: str = "$") -> str:
    """Return a safe configured path, preserving explicit absolute paths."""

    if not isinstance(value, str) or not value:
        raise ContractError(path, "unsafe_path", "path must be a non-empty string")
    if "\x00" in value:
        raise ContractError(path, "unsafe_path", "path contains a NUL byte")
    if value.startswith("~"):
        raise ContractError(path, "unsafe_path", "home-relative paths are not allowed")
    normalized = value.replace("\\", "/")
    if any(part == ".." for part in PurePosixPath(normalized).parts):
        raise ContractError(path, "unsafe_path", "parent traversal is not allowed")
    if PureWindowsPath(value).is_absolute():
        return PureWindowsPath(value).as_posix()
    if PurePosixPath(normalized).is_absolute():
        return PurePosixPath(normalized).as_posix()
    return validate_relative_path(value, path=path)


def resolve_safe_path(project_root: Path | str, relative_path: str, *, path: str = "$") -> Path:
    """Resolve a relative path and reject traversal through escaping symlinks."""

    root = Path(project_root).resolve(strict=True)
    normalized = validate_relative_path(relative_path, path=path)
    candidate = root / normalized
    resolved = candidate.resolve(strict=False)
    if not resolved.is_relative_to(root):
        raise ContractError(path, "unsafe_path", "resolved path escapes the project root")
    return resolved


def check_private_permissions(path_value: Path | str, *, directory: bool | None = None) -> None:
    """Require an owner-controlled, non-symlink path on supported POSIX hosts."""

    path = Path(path_value)
    if path.is_symlink():
        raise ContractError(str(path), "permissions", "symlink permissions are not accepted")
    try:
        info = path.stat()
    except OSError as exc:
        raise ContractError(str(path), "permissions", f"cannot inspect path: {exc}") from exc
    if hasattr(os, "getuid") and info.st_uid != os.getuid():
        raise ContractError(str(path), "permissions", "path is not owned by the current user")
    if stat.S_IMODE(info.st_mode) & 0o077:
        kind = "directory" if (directory if directory is not None else path.is_dir()) else "file"
        raise ContractError(str(path), "permissions", f"{kind} must not grant group or other access")


def validate_owner(actual: Mapping[str, Any] | None, expected: Mapping[str, Any], *, path: str = "$.owner") -> None:
    if actual is None:
        raise ContractError(path, "owner", "owner is required")
    required = ("harness", "actor", "session_id")
    mismatched = [key for key in required if actual.get(key) != expected.get(key)]
    if mismatched:
        raise ContractError(path, "owner", "owner mismatch for: " + ", ".join(mismatched))


def validate_transition(previous_status: str, next_status: str, *, kind: str = "run") -> None:
    transitions = RUN_TRANSITIONS if kind == "run" else ISSUE_TRANSITIONS if kind == "issue" else None
    if transitions is None:
        raise ContractError("$.status", "transition", f"unknown transition kind {kind!r}")
    if previous_status == next_status:
        return
    if previous_status not in transitions:
        raise ContractError("$.status", "transition", f"unknown {kind} status {previous_status!r}")
    if next_status not in transitions[previous_status]:
        raise ContractError(
            "$.status",
            "transition",
            f"invalid {kind} transition {previous_status!r} -> {next_status!r}",
        )


def parse_timestamp(value: str, path: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise ContractError(path, "timestamp", "must be a valid UTC timestamp") from exc


def _validate_config(record: Mapping[str, Any]) -> None:
    validate_relative_path(record["state_root"], path="$.state_root")
    for index, value in enumerate(record["kill_switches"]):
        validate_configured_path(value, path=f"$.kill_switches[{index}]")
    if record["lease_seconds"] <= record["heartbeat_seconds"]:
        raise ContractError("$.lease_seconds", "invariant", "must be greater than heartbeat_seconds")


def _validate_install_receipt(record: Mapping[str, Any]) -> None:
    validate_configured_path(record["target_root"], path="$.target_root")
    for index, operation in enumerate(record["operations"]):
        validate_relative_path(operation["destination"], path=f"$.operations[{index}].destination")
        if operation["action"] == "skip" and operation["rollback_action"] != "none":
            raise ContractError(
                f"$.operations[{index}].rollback_action",
                "invariant",
                "a skipped operation cannot have a rollback action",
            )


def _validate_recovery_authority(
    record: Mapping[str, Any],
    grant: Mapping[str, Any] | None,
) -> None:
    if grant is None:
        raise ContractError(
            "$.authority_grant_id",
            "authority",
            "explicit recovery requires a validated current grant record",
        )
    validate_record("grant", grant)
    if record["authority_grant_id"] != grant["grant_id"]:
        raise ContractError("$.authority_grant_id", "authority", "does not match the validated current grant")
    if grant["revoked_at"] is not None:
        raise ContractError("$.authority_grant_id", "authority", "validated grant is revoked")

    updated_at = parse_timestamp(record["updated_at"], "$.updated_at")
    if parse_timestamp(grant["confirmed_at"], "$.grant.confirmed_at") > updated_at:
        raise ContractError("$.authority_grant_id", "authority", "validated grant was confirmed after this recovery")
    if parse_timestamp(grant["expires_at"], "$.grant.expires_at") <= updated_at:
        raise ContractError("$.authority_grant_id", "authority", "validated grant is expired")

    scope = grant["scope"]
    exclusions = set(scope["exclusions"])
    asset_name = record["asset"]["name"]
    if asset_name in exclusions or "*" in exclusions:
        raise ContractError("$.authority_grant_id", "authority", "validated grant explicitly excludes this asset")
    if "local_write" in exclusions:
        raise ContractError("$.authority_grant_id", "authority", "validated grant explicitly excludes local writes")
    if "repository" in exclusions:
        raise ContractError("$.authority_grant_id", "authority", "validated grant explicitly excludes repository writes")

    allowed_assets = set(scope["assets"])
    if asset_name not in allowed_assets and "*" not in allowed_assets:
        raise ContractError("$.authority_grant_id", "authority", "validated grant does not cover this asset")
    allowed_actions = set(scope["actions"])
    if "local_write" not in allowed_actions and "*" not in allowed_actions:
        raise ContractError("$.authority_grant_id", "authority", "validated grant does not permit local writes")
    allowed_destinations = set(scope["destinations"])
    if "repository" not in allowed_destinations and "*" not in allowed_destinations:
        raise ContractError("$.authority_grant_id", "authority", "validated grant does not permit repository writes")


def _validate_usage_growth(record: Mapping[str, Any], previous: Mapping[str, Any]) -> None:
    previous_usage = previous.get("usage", {})
    for field in ("duration_seconds", "mutations", "external_actions"):
        if record["usage"][field] < previous_usage.get(field, 0):
            raise ContractError(f"$.usage.{field}", "invariant", "usage counters cannot decrease")
    previous_attempts = previous_usage.get("stage_attempts", {})
    for stage, attempts in record["usage"]["stage_attempts"].items():
        if attempts < previous_attempts.get(stage, 0):
            raise ContractError(
                f"$.usage.stage_attempts.{stage}",
                "invariant",
                "stage attempt counters cannot decrease",
            )
    previous_cost = previous_usage.get("cost_usd")
    current_cost = record["usage"]["cost_usd"]
    if previous_cost is not None:
        if current_cost is None or Decimal(current_cost) < Decimal(previous_cost):
            raise ContractError("$.usage.cost_usd", "invariant", "recorded cost cannot decrease or become unknown")


def _validate_known_reservation_rollback(
    run: Mapping[str, Any],
    previous_run: Mapping[str, Any],
    pending: Mapping[str, Any],
) -> None:
    reservation = pending["reservation"]
    expected_mutations = previous_run["usage"]["mutations"] - reservation["mutations"]
    expected_external = previous_run["usage"]["external_actions"] - reservation["external_actions"]
    if run["usage"]["mutations"] != expected_mutations:
        raise ContractError("$.projection.run.usage.mutations", "invariant", "must roll back the exact reservation")
    if run["usage"]["external_actions"] != expected_external:
        raise ContractError(
            "$.projection.run.usage.external_actions",
            "invariant",
            "must roll back the exact reservation",
        )
    if run["usage"]["cost_usd"] != reservation["prior_cost_usd"]:
        raise ContractError("$.projection.run.usage.cost_usd", "invariant", "must restore the exact prior cost")
    if run["stage"] != reservation["prior_stage"]:
        raise ContractError("$.projection.run.stage", "invariant", "must restore the exact prior stage")
    expected_attempts = dict(previous_run["usage"]["stage_attempts"])
    stage_attempt = reservation["stage_attempt"]
    if stage_attempt is not None:
        expected_attempts[stage_attempt] -= 1
    if run["usage"]["stage_attempts"] != expected_attempts:
        raise ContractError(
            "$.projection.run.usage.stage_attempts",
            "invariant",
            "must roll back the exact stage-attempt reservation",
        )
    try:
        reserved_cost = Decimal(reservation["cost_usd"])
        prior_cost = Decimal(reservation["prior_cost_usd"] or "0")
        projected_cost = Decimal(previous_run["usage"]["cost_usd"] or "0")
    except (InvalidOperation, TypeError) as exc:
        raise ContractError("$.projection.pending_operation.reservation", "invariant", "invalid cost reservation") from exc
    if projected_cost != prior_cost + reserved_cost:
        raise ContractError(
            "$.projection.pending_operation.reservation.cost_usd",
            "invariant",
            "must equal the cost added by the intent",
        )


def _validate_run(
    record: Mapping[str, Any],
    previous: Mapping[str, Any] | None,
    expected_owner: Mapping[str, Any] | None,
    expected_authority_grant: Mapping[str, Any] | None,
) -> None:
    validate_relative_path(record["asset"]["root"], path="$.asset.root")
    status = record["status"]
    waiting = {"waiting_approval", "waiting_external", "blocked", "failed", "halted_kill_switch", "cancelled"}
    if status == "active" and record["owner"] is None:
        raise ContractError("$.owner", "owner", "active run requires an owner")
    if status == "active" and record["stage"] is None:
        raise ContractError("$.stage", "invariant", "active run requires a stage")
    if status in waiting and record["terminal_reason"] is None:
        raise ContractError("$.terminal_reason", "invariant", f"{status} requires a terminal reason")
    if status in {"draft", "ready", "active", "complete"} and record["terminal_reason"] is not None:
        raise ContractError("$.terminal_reason", "invariant", f"{status} cannot carry a terminal reason")
    if status == "complete" and record["open_blocking_issues"] != 0:
        raise ContractError("$.open_blocking_issues", "invariant", "complete run cannot have blocking issues")
    terminal_reason = record["terminal_reason"]
    if terminal_reason is not None and terminal_reason["code"].startswith("budget_reached:"):
        budget = terminal_reason["code"].partition(":")[2]
        if budget not in record["budgets"]:
            raise ContractError("$.terminal_reason.code", "invariant", "names an unknown exhausted budget")
        if status != "failed":
            raise ContractError("$.status", "invariant", "budget exhaustion must leave the run failed")
        limit = record["budgets"][budget]
        if budget == "max_stage_attempts":
            exhausted = any(value >= limit for value in record["usage"]["stage_attempts"].values())
        elif budget == "max_cost_usd":
            observed_cost = record["usage"]["cost_usd"]
            exhausted = limit is None or (
                observed_cost is not None and Decimal(observed_cost) >= Decimal(limit)
            )
        else:
            exhausted = record["usage"][budget.removeprefix("max_")] >= limit
        if not exhausted:
            raise ContractError(
                "$.terminal_reason.code",
                "invariant",
                "budget terminal reason requires usage at its configured limit",
            )
        markers = _exhausted_budget_markers(record)
        if markers and markers[0]["budget"] != budget:
            raise ContractError(
                "$.terminal_reason.code",
                "invariant",
                "budget terminal reason violates stable primary priority",
            )
    if parse_timestamp(record["updated_at"], "$.updated_at") < parse_timestamp(record["created_at"], "$.created_at"):
        raise ContractError("$.updated_at", "invariant", "cannot precede created_at")
    if previous is not None:
        if (previous.get("status") == "active" or status == "active") and expected_owner is None:
            raise ContractError("$.owner", "owner_context", "updates from or to active require expected_owner")
        if record["run_id"] != previous.get("run_id"):
            raise ContractError("$.run_id", "invariant", "run_id is immutable")
        if record["created_at"] != previous.get("created_at"):
            raise ContractError("$.created_at", "invariant", "created_at is immutable")
        for field in ("asset", "mode", "objective", "done_gate", "budgets"):
            if record[field] != previous.get(field):
                raise ContractError(f"$.{field}", "invariant", f"{field} is immutable for one bounded mission")
        recovery_to_ready = record["status"] == "ready" and previous.get("status") in {
            "waiting_approval",
            "waiting_external",
            "blocked",
            "failed",
            "halted_kill_switch",
        }
        grant_changed = record["authority_grant_id"] != previous.get("authority_grant_id")
        if grant_changed and not recovery_to_ready:
            raise ContractError(
                "$.authority_grant_id",
                "invariant",
                "authority grant may change only during explicit recovery to ready",
            )
        if recovery_to_ready:
            _validate_recovery_authority(record, expected_authority_grant)
        _validate_usage_growth(record, previous)
        if parse_timestamp(record["updated_at"], "$.updated_at") < parse_timestamp(str(previous.get("updated_at")), "$.updated_at"):
            raise ContractError("$.updated_at", "invariant", "cannot move backwards")
        if expected_owner is not None and previous.get("status") == "active":
            validate_owner(previous.get("owner"), expected_owner)
            if record["owner"] is not None:
                validate_owner(record["owner"], expected_owner)
        validate_transition(str(previous.get("status")), status, kind="run")
    if status == "active" and expected_owner is not None:
        validate_owner(record["owner"], expected_owner)
    for capability, route in record["selected_routes"].items():
        _validate_route(route)
        if route["capability"] != capability:
            raise ContractError(
                f"$.selected_routes.{capability}.capability",
                "invariant",
                "route capability does not match its selected_routes key",
            )


def _validate_lease(record: Mapping[str, Any], expected_owner: Mapping[str, Any] | None) -> None:
    acquired = parse_timestamp(record["acquired_at"], "$.acquired_at")
    renewed = parse_timestamp(record["renewed_at"], "$.renewed_at")
    expires = parse_timestamp(record["expires_at"], "$.expires_at")
    if not acquired <= renewed < expires:
        raise ContractError("$.expires_at", "invariant", "lease timestamps must satisfy acquired_at <= renewed_at < expires_at")
    if expected_owner is not None:
        validate_owner(record["owner"], expected_owner)


def _validate_grant(record: Mapping[str, Any]) -> None:
    actual = frozenset(record["permanent_invariants"])
    if actual != PERMANENT_INVARIANTS:
        missing = sorted(PERMANENT_INVARIANTS - actual)
        extra = sorted(actual - PERMANENT_INVARIANTS)
        detail = []
        if missing:
            detail.append("missing " + ", ".join(missing))
        if extra:
            detail.append("unexpected " + ", ".join(extra))
        raise ContractError("$.permanent_invariants", "invariant", "; ".join(detail))
    if parse_timestamp(record["expires_at"], "$.expires_at") <= parse_timestamp(record["confirmed_at"], "$.confirmed_at"):
        raise ContractError("$.expires_at", "invariant", "must be later than confirmed_at")
    revoked_at = record["revoked_at"]
    revoked_by = record["revoked_by"]
    if (revoked_at is None) != (revoked_by is None):
        raise ContractError("$.revoked_at", "invariant", "revoked_at and revoked_by must both be set or both be null")
    if revoked_at is not None and parse_timestamp(revoked_at, "$.revoked_at") < parse_timestamp(record["confirmed_at"], "$.confirmed_at"):
        raise ContractError("$.revoked_at", "invariant", "cannot precede confirmed_at")


def _validate_route(record: Mapping[str, Any]) -> None:
    identities: dict[tuple[str, str], int] = {}
    for index, candidate in enumerate(record["candidates"]):
        identity = (candidate["provider"], candidate["source"])
        if identity in identities:
            raise ContractError(
                f"$.candidates[{index}].provider",
                "invariant",
                "candidate provider and source identity must be unique",
            )
        identities[identity] = index

    selected_identity = (record["selected_provider"], record["selected_source"])
    selected_index = identities.get(selected_identity)
    if selected_index is None:
        raise ContractError("$.selected_provider", "invariant", "selected provider is absent from candidates")
    selected = record["candidates"][selected_index]
    if selected["rejection_reasons"]:
        raise ContractError("$.selected_provider", "invariant", "selected candidate cannot have rejection reasons")
    if selected["provenance_type"] == "excluded":
        raise ContractError("$.selected_provider", "invariant", "an excluded candidate cannot be selected")
    if selected["provenance_type"] == "upstream-dependency" and selected["source"] != "installed":
        raise ContractError(
            "$.selected_source",
            "invariant",
            "an upstream dependency must be selected from the installed source",
        )
    if selected["behavior_status"] != "verified":
        raise ContractError(
            f"$.candidates[{selected_index}].behavior_status",
            "invariant",
            "selected candidate must have verified behavior",
        )
    if record["harness"] not in selected["compatibility"]:
        raise ContractError(
            f"$.candidates[{selected_index}].compatibility",
            "invariant",
            "selected candidate must include the active harness",
        )
    if not selected["capability_evidence"]:
        raise ContractError("$.selected_provider", "invariant", "selected candidate requires explicit capability evidence")
    if record["verified_at"] is None:
        raise ContractError("$.verified_at", "invariant", "verified selection requires a typed passing observation")
    matching = [
        observation
        for observation in selected["behavior_observations"]
        if observation["capability"] == record["capability"]
        and observation["harness"] == record["harness"]
        and observation["track"] == record["track"]
        and observation["environment_digest"] == record["environment_digest"]
    ]
    if not matching:
        raise ContractError(
            f"$.candidates[{selected_index}].behavior_observations",
            "invariant",
            "verified selection requires a matching typed behavior observation",
        )
    latest_at = max(parse_timestamp(item["observed_at"], "$.behavior_observations.observed_at") for item in matching)
    latest = [
        item
        for item in matching
        if parse_timestamp(item["observed_at"], "$.behavior_observations.observed_at") == latest_at
    ]
    if len(latest) != 1 or latest[0]["outcome"] != "passed":
        raise ContractError(
            f"$.candidates[{selected_index}].behavior_status",
            "invariant",
            "verified behavior requires one unique latest matching passing observation",
        )
    verified_at = parse_timestamp(record["verified_at"], "$.verified_at")
    if verified_at != latest_at:
        raise ContractError(
            "$.verified_at",
            "invariant",
            "verified_at must equal the latest matching passing observation time",
        )
    decided_at = parse_timestamp(record["decided_at"], "$.decided_at")
    age_seconds = (decided_at - latest_at).total_seconds()
    if age_seconds < 0:
        raise ContractError("$.decided_at", "invariant", "route decision cannot precede its behavior proof")
    # The schema fixes this self-described bound at one day; the decision
    # timestamp makes freshness deterministic without consulting wall time.
    behavior_max_age_seconds = record["behavior_max_age_seconds"]
    if age_seconds > behavior_max_age_seconds:
        raise ContractError(
            "$.verified_at",
            "stale_behavior",
            f"behavior proof exceeds the {behavior_max_age_seconds}-second maximum age",
        )

    for index, candidate in enumerate(record["candidates"]):
        if index == selected_index or candidate["source"] != "installed":
            continue
        required_reasons: list[str] = []
        if candidate["behavior_status"] == "failed":
            required_reasons.append("behavior_failed")
        elif candidate["behavior_status"] == "denied":
            required_reasons.append("behavior_denied")
        if record["harness"] not in candidate["compatibility"]:
            required_reasons.append(f"harness_incompatible:{record['harness']}")
        missing = [reason for reason in required_reasons if reason not in candidate["rejection_reasons"]]
        if missing:
            raise ContractError(
                f"$.candidates[{index}].rejection_reasons",
                "invariant",
                "missing precise rejection evidence: " + ", ".join(missing),
            )

    fallback_reason = record["fallback_reason"]
    if record["selected_source"] == "bundled":
        if not isinstance(fallback_reason, str) or not fallback_reason.strip():
            raise ContractError("$.fallback_reason", "invariant", "bundled selection requires a nonempty fallback reason")
    elif fallback_reason is not None:
        raise ContractError("$.fallback_reason", "invariant", "installed selection requires a null fallback reason")


def _validate_evidence(record: Mapping[str, Any]) -> None:
    unexpected_environment = sorted(set(record["environment"]) - ALLOWED_ENVIRONMENT_FIELDS)
    if unexpected_environment:
        raise ContractError(
            "$.environment",
            "environment_allowlist",
            "unapproved environment fields: " + ", ".join(unexpected_environment),
        )
    if record["outcome"] != "passed":
        return
    if not record["procedure"]:
        raise ContractError("$.procedure", "invariant", "passed evidence requires a non-empty procedure")
    manual = record.get("manual_observation")
    if not record["artifact_refs"] and not (record["type"] == "manual" and manual):
        raise ContractError("$.artifact_refs", "invariant", "passed evidence requires a result reference or manual observation")
    for index, artifact in enumerate(record["artifact_refs"]):
        if artifact["kind"] == "file":
            validate_relative_path(artifact["ref"], path=f"$.artifact_refs[{index}].ref")


def _validate_issue_ledger(record: Mapping[str, Any], previous: Mapping[str, Any] | None) -> None:
    ids = [issue["issue_id"] for issue in record["issues"]]
    if len(ids) != len(set(ids)):
        raise ContractError("$.issues", "invariant", "issue_id values must be unique")
    for index, issue in enumerate(record["issues"]):
        if issue["status"] == "closed" and not issue["resolution"]:
            raise ContractError(f"$.issues[{index}].resolution", "invariant", "closed issue requires a resolution")
        if issue["status"] == "closed" and not issue["regression_procedure"]:
            raise ContractError(
                f"$.issues[{index}].regression_procedure",
                "invariant",
                "closed issue requires a regression procedure",
            )
        if issue["status"] in {"resolving", "verification_pending"} and issue["owner"] is None:
            raise ContractError(f"$.issues[{index}].owner", "owner", f"{issue['status']} issue requires an owner")
    if previous is None:
        return
    if record["run_id"] != previous.get("run_id"):
        raise ContractError("$.run_id", "invariant", "run_id is immutable")
    old_by_id = {item["issue_id"]: item for item in previous.get("issues", [])}
    missing_ids = sorted(set(old_by_id) - set(ids))
    if missing_ids:
        raise ContractError("$.issues", "invariant", "issues cannot be removed from the ledger: " + ", ".join(missing_ids))
    for index, issue in enumerate(record["issues"]):
        old = old_by_id.get(issue["issue_id"])
        if old is None:
            if issue["status"] != "open":
                raise ContractError(f"$.issues[{index}].status", "transition", "a new issue must start open")
            continue
        validate_transition(old["status"], issue["status"], kind="issue")
        if issue["created_at"] != old["created_at"]:
            raise ContractError(f"$.issues[{index}].created_at", "invariant", "created_at is immutable")
        if issue["attempt_count"] < old["attempt_count"]:
            raise ContractError(f"$.issues[{index}].attempt_count", "invariant", "attempt_count cannot decrease")
        if issue["status"] == "reopened" and old["status"] != "reopened" and issue["attempt_count"] <= old["attempt_count"]:
            raise ContractError(
                f"$.issues[{index}].attempt_count",
                "invariant",
                "reopening an issue must increment attempt_count",
            )


def _validate_audit_projection(record: Mapping[str, Any]) -> None:
    event_type = record["type"]
    actor = record["actor"]
    run = record["projection"]["run"]
    lease = record["projection"]["lease"]
    pending = record["projection"]["pending_operation"]
    validate_record("run", run)
    if run["run_id"] != record["run_id"]:
        raise ContractError("$.projection.run.run_id", "invariant", "must match the audit envelope run_id")
    if run["updated_at"] != record["at"]:
        raise ContractError("$.projection.run.updated_at", "invariant", "must match the audit event timestamp")

    if lease is not None:
        validate_record("lease", lease)
        if lease["run_id"] != record["run_id"]:
            raise ContractError("$.projection.lease.run_id", "invariant", "must match the audit envelope run_id")
    if record["lease_id"] is not None:
        if lease is None:
            raise ContractError("$.projection.lease", "invariant", "lease-context event requires a resulting lease")
        if lease["lease_id"] != record["lease_id"]:
            raise ContractError("$.projection.lease.lease_id", "invariant", "must match the audit envelope lease_id")
        if lease["generation"] != record["lease_generation"]:
            raise ContractError("$.projection.lease.generation", "invariant", "must match the audit envelope generation")
        validate_owner(lease["owner"], actor, path="$.projection.lease.owner")
    if run["status"] == "active":
        if lease is None:
            raise ContractError("$.projection.lease", "invariant", "active run projection requires a lease")
        validate_owner(run["owner"], lease["owner"], path="$.projection.run.owner")

    if event_type == "run_created":
        if run["objective"] != record["data"]["objective"]:
            raise ContractError("$.projection.run.objective", "invariant", "must match run_created objective")
        if run["created_at"] != record["at"]:
            raise ContractError("$.projection.run.created_at", "invariant", "must match the run_created timestamp")
    if event_type == "operation_intended":
        if pending != record["data"]:
            raise ContractError(
                "$.projection.pending_operation",
                "invariant",
                "operation intent must project its complete pending operation",
            )
        if run["status"] != "active":
            raise ContractError("$.projection.run.status", "invariant", "operation intent requires an active run")
    elif pending is not None:
        raise ContractError(
            "$.projection.pending_operation",
            "invariant",
            "only operation_intended may leave an operation pending",
        )
    if event_type == "operation_reconciled":
        effect = record["data"]["effect"]
        if record["data"]["outcome"] == "known_not_started":
            if run["status"] != "active" or run["terminal_reason"] is not None:
                raise ContractError(
                    "$.projection.run.status",
                    "invariant",
                    "known-not-started reconciliation must restore the active run",
                )
        else:
            expected_status = "failed" if effect == "local" else "waiting_external"
            expected_code = "operation_outcome_unknown" if effect == "local" else "external_operation_outcome_unknown"
            if run["status"] != expected_status:
                raise ContractError(
                    "$.projection.run.status",
                    "invariant",
                    f"reconciled {effect} operation must project {expected_status}",
                )
            if run["terminal_reason"]["code"] != expected_code:
                raise ContractError(
                    "$.projection.run.terminal_reason.code",
                    "invariant",
                    f"reconciled {effect} operation must use {expected_code!r}",
                )
    if event_type in {"lease_acquired", "lease_renewed"}:
        if lease["expires_at"] != record["data"]["expires_at"]:
            raise ContractError("$.projection.lease.expires_at", "invariant", "must match lease event expiry")
        if lease["renewed_at"] != record["at"]:
            raise ContractError("$.projection.lease.renewed_at", "invariant", "must match the lease event timestamp")
        if event_type == "lease_acquired" and lease["acquired_at"] != record["at"]:
            raise ContractError("$.projection.lease.acquired_at", "invariant", "must match lease acquisition time")
    if event_type == "recovery_started":
        if lease is None or lease["generation"] != record["data"]["new_generation"]:
            raise ContractError("$.projection.lease.generation", "invariant", "must match the recovered generation")
        if run["status"] != "active":
            raise ContractError("$.projection.run.status", "invariant", "recovery projection must be active")
    if event_type == "stage_started" and run["stage"] != record["data"]["stage"]:
        raise ContractError("$.projection.run.stage", "invariant", "must match the started stage")
    if event_type == "heartbeat":
        if run["stage"] != record["data"]["stage"] or run["status"] != record["data"]["status"]:
            raise ContractError("$.projection.run", "invariant", "must match heartbeat stage and status")
        if run["last_heartbeat_at"] != record["at"]:
            raise ContractError("$.projection.run.last_heartbeat_at", "invariant", "must match heartbeat timestamp")
        if lease is None or lease["renewed_at"] != record["at"]:
            raise ContractError("$.projection.lease.renewed_at", "invariant", "heartbeat must carry its renewed lease")
    if event_type == "budget_reached":
        budget = record["data"]["budget"]
        projected_code = run["terminal_reason"]["code"]
        unknown_projection = any(
            run["status"] == status and projected_code == code
            for status, code in UNKNOWN_OUTCOME_PROJECTIONS.values()
        )
        if not unknown_projection:
            if run["status"] != "failed":
                raise ContractError("$.projection.run.status", "invariant", "budget exhaustion must leave the run failed")
            if not projected_code.startswith("budget_reached:"):
                raise ContractError(
                    "$.projection.run.terminal_reason.code",
                    "invariant",
                    "must identify the primary exhausted budget",
                )
        if run["budgets"][budget] != record["data"]["limit"]:
            raise ContractError("$.data.limit", "invariant", "must match the frozen run budget")
        stage = record["data"]["stage"]
        if budget == "max_stage_attempts":
            if stage is None:
                raise ContractError("$.data.stage", "invariant", "stage-attempt exhaustion requires a stage")
            observed = run["usage"]["stage_attempts"][stage]
        else:
            if stage is not None:
                raise ContractError("$.data.stage", "invariant", "stage is allowed only for stage-attempt exhaustion")
            usage_field = budget.removeprefix("max_")
            observed = run["usage"][usage_field]
        if observed is not None and observed != record["data"]["observed"]:
            raise ContractError("$.data.observed", "invariant", "must match the resulting run usage")
    terminal_status = {
        "kill_switch_detected": ("halted_kill_switch", "kill_switch_detected"),
        "run_completed": ("complete", None),
        "run_failed": ("failed", "run_failed"),
        "run_cancelled": ("cancelled", "run_cancelled"),
    }.get(event_type)
    if terminal_status is not None:
        expected_status, expected_code = terminal_status
        if run["status"] != expected_status:
            raise ContractError("$.projection.run.status", "invariant", f"{event_type} must project {expected_status}")
        if expected_code is not None and run["terminal_reason"]["code"] != expected_code:
            raise ContractError("$.projection.run.terminal_reason.code", "invariant", f"must equal {expected_code!r}")


def _validate_audit_projection_transition(record: Mapping[str, Any], previous: Mapping[str, Any]) -> None:
    run = record["projection"]["run"]
    previous_run = previous["projection"]["run"]
    for field in ("run_id", "asset", "mode", "objective", "done_gate", "budgets", "created_at"):
        if run[field] != previous_run[field]:
            raise ContractError(f"$.projection.run.{field}", "invariant", f"{field} changed in the audit projection chain")
    if run["authority_grant_id"] != previous_run["authority_grant_id"] and record["type"] != "recovery_started":
        raise ContractError(
            "$.projection.run.authority_grant_id",
            "invariant",
            "authority may change only in an explicit recovery projection",
        )
    previous_pending = previous["projection"]["pending_operation"]
    current_pending = record["projection"]["pending_operation"]
    known_not_started = (
        record["type"] == "operation_reconciled"
        and record["data"]["outcome"] == "known_not_started"
        and previous_pending is not None
    )
    if known_not_started:
        _validate_known_reservation_rollback(run, previous_run, previous_pending)
    else:
        _validate_usage_growth(run, previous_run)
    if previous_pending is None:
        if record["type"] == "operation_reconciled":
            raise ContractError("$.type", "transition", "operation reconciliation requires a pending intent")
        if record["type"] == "operation_intended" and current_pending != record["data"]:
            raise ContractError("$.projection.pending_operation", "invariant", "must match the new operation intent")
    else:
        if record["type"] == "operation_reconciled":
            if record["data"]["operation_id"] != previous_pending["operation_id"]:
                raise ContractError("$.data.operation_id", "invariant", "must match the pending operation")
            if record["data"]["effect"] != previous_pending["effect"]:
                raise ContractError("$.data.effect", "invariant", "must match the pending operation effect")
        elif record["type"] == previous_pending["completion_event_type"]:
            if record["data"] != previous_pending["completion_data"]:
                raise ContractError("$.data", "invariant", "must exactly match the pending completion data")
        else:
            raise ContractError(
                "$.type",
                "transition",
                "a pending operation must be completed or reconciled before any other event",
            )
        if current_pending is not None:
            raise ContractError("$.projection.pending_operation", "invariant", "completion must clear pending state")

    required_marker = _next_budget_marker(previous)
    if required_marker is not None:
        if record["type"] != "budget_reached":
            raise ContractError("$.type", "transition", "required budget marker cannot be skipped or interleaved")
        if record["data"] != required_marker:
            raise ContractError("$.data", "invariant", "budget markers must be complete, unique, and in stable order")
        if record["projection"] != previous["projection"]:
            raise ContractError("$.projection", "invariant", "deterministic budget marker must preserve its source projection")
    elif previous["type"] == "budget_reached" and record["type"] == "budget_reached":
        raise ContractError("$.data", "invariant", "duplicate or unexpected budget marker")
    elif record["type"] == "budget_reached":
        expected_markers = _exhausted_budget_markers(run)
        if expected_markers and record["data"] != expected_markers[0]:
            raise ContractError("$.data", "invariant", "primary budget marker violates stable order")

    previous_lease_for_expiry = previous["projection"]["lease"]
    if previous_lease_for_expiry is not None and parse_timestamp(record["at"], "$.at") >= parse_timestamp(
        previous_lease_for_expiry["expires_at"], "$.previous.projection.lease.expires_at"
    ):
        closes_pending = previous_pending is not None and (
            record["type"] == "operation_reconciled"
            or record["type"] == previous_pending["completion_event_type"]
        )
        safety_or_recovery = record["type"] in {
            "authority_revoked",
            "budget_reached",
            "kill_switch_detected",
            "recovery_started",
            "run_cancelled",
            "run_failed",
        }
        if not closes_pending and not safety_or_recovery:
            raise ContractError("$.at", "lease_expired", "event requires a lease that was valid at event time")
        if closes_pending and run["status"] == "active":
            raise ContractError(
                "$.projection.run.status",
                "lease_expired",
                "post-expiry completion or reconciliation must leave work non-active",
            )

    usage_changed = any(
        run["usage"][field] != previous_run["usage"][field]
        for field in ("mutations", "external_actions", "cost_usd")
    )
    if usage_changed and record["type"] != "operation_intended" and not known_not_started:
        raise ContractError(
            "$.projection.run.usage",
            "invariant",
            "mutation, external-action and cost usage may change only in a durable operation intent",
        )
    if record["type"] == "operation_intended":
        external_growth = run["usage"]["external_actions"] - previous_run["usage"]["external_actions"]
        expected_effect = "external" if external_growth else "local"
        if record["data"]["effect"] != expected_effect:
            raise ContractError(
                "$.data.effect",
                "invariant",
                "effect must be external exactly when external-action usage is reserved",
            )
    if parse_timestamp(run["updated_at"], "$.projection.run.updated_at") < parse_timestamp(
        previous_run["updated_at"], "$.previous.projection.run.updated_at"
    ):
        raise ContractError("$.projection.run.updated_at", "invariant", "projection time cannot move backwards")

    if record["type"] == "recovery_started":
        if previous_run["status"] not in {
            "waiting_approval",
            "waiting_external",
            "blocked",
            "failed",
            "halted_kill_switch",
        }:
            raise ContractError("$.projection.run.status", "transition", "recovery requires a recoverable prior state")
    elif record["type"] == "lease_acquired":
        if previous_run["status"] != "ready" or run["status"] != "active":
            raise ContractError("$.projection.run.status", "transition", "lease acquisition must activate a ready run")
    elif record["type"] == "authority_revoked" and previous_run["status"] == "active":
        if run["status"] != "waiting_approval":
            raise ContractError(
                "$.projection.run.status",
                "transition",
                "revoking active authority must project waiting_approval",
            )
        if run["terminal_reason"] is None or run["terminal_reason"]["code"] != "authority_revoked":
            raise ContractError(
                "$.projection.run.terminal_reason.code",
                "invariant",
                "revoking active authority must record authority_revoked",
            )
    elif record["type"] == "kill_switch_detected":
        if previous_run["status"] not in {
            "ready",
            "active",
            "waiting_approval",
            "waiting_external",
            "blocked",
            "failed",
        }:
            raise ContractError(
                "$.projection.run.status",
                "transition",
                "kill switch can halt only a nonterminal recoverable run",
            )
    elif record["type"] == "budget_reached":
        secondary_marker = previous["type"] == "budget_reached" and required_marker is not None
        previous_unknown = (
            previous["type"] == "operation_reconciled"
            and previous["data"].get("outcome") == "unknown"
        )
        current_reason = run.get("terminal_reason")
        current_code = current_reason.get("code") if isinstance(current_reason, Mapping) else None
        preserves_unknown = current_code in {code for _, code in UNKNOWN_OUTCOME_PROJECTIONS.values()}
        if secondary_marker:
            pass
        elif previous_unknown or preserves_unknown:
            if not previous_unknown:
                raise ContractError(
                    "$.projection.run.terminal_reason.code",
                    "invariant",
                    "unknown-outcome budget marker must immediately follow unknown reconciliation",
                )
            effect = previous["data"].get("effect")
            expected_projection = UNKNOWN_OUTCOME_PROJECTIONS.get(effect)
            if expected_projection is None:
                raise ContractError("$.previous.data.effect", "invariant", "unknown reconciliation has invalid effect")
            expected_status, expected_code = expected_projection
            if run["status"] != expected_status or current_code != expected_code:
                raise ContractError(
                    "$.projection.run",
                    "invariant",
                    "budget marker must preserve the prior unknown-outcome status and reason",
                )
            if run != previous_run:
                raise ContractError(
                    "$.projection.run",
                    "invariant",
                    "unknown-outcome budget marker must preserve the complete prior run projection",
                )
        elif previous_run["status"] not in {
            "active",
            "waiting_approval",
            "waiting_external",
            "blocked",
            "failed",
        }:
            raise ContractError(
                "$.projection.run.status",
                "transition",
                "budget exhaustion can fail only a nonterminal recoverable run",
            )
        elif current_code != f"budget_reached:{record['data']['budget']}":
            raise ContractError(
                "$.projection.run.terminal_reason.code",
                "invariant",
                "primary budget marker must identify its exhausted budget",
            )
    else:
        validate_transition(previous_run["status"], run["status"], kind="run")

    previous_attempts = previous_run["usage"]["stage_attempts"]
    current_attempts = run["usage"]["stage_attempts"]
    changed_attempts = [stage for stage in current_attempts if current_attempts[stage] != previous_attempts[stage]]
    if changed_attempts and not known_not_started:
        intended_stage = None
        if record["type"] == "operation_intended" and record["data"]["completion_event_type"] == "stage_started":
            intended_stage = record["data"]["completion_data"]["stage"]
        if intended_stage is None or changed_attempts != [intended_stage]:
            raise ContractError(
                "$.projection.run.usage.stage_attempts",
                "invariant",
                "only a stage-start intent may reserve its matching stage attempt counter",
            )
        stage = changed_attempts[0]
        if current_attempts[stage] != previous_attempts[stage] + 1:
            raise ContractError(
                f"$.projection.run.usage.stage_attempts.{stage}",
                "invariant",
                "stage-start intent must increment its stage counter by exactly one",
            )

    duration_growth = round(
        run["usage"]["duration_seconds"] - previous_run["usage"]["duration_seconds"],
        6,
    )
    previous_lease = previous["projection"]["lease"]
    expected_growth = 0.0
    if previous_run["status"] == "active":
        if previous_lease is None:
            raise ContractError(
                "$.previous.projection.lease",
                "invariant",
                "active duration requires a previously validated lease interval",
            )
        interval_start = parse_timestamp(previous["at"], "$.previous.at")
        interval_end = min(
            parse_timestamp(record["at"], "$.at"),
            parse_timestamp(previous_lease["expires_at"], "$.previous.projection.lease.expires_at"),
        )
        expected_growth = round(max(0.0, (interval_end - interval_start).total_seconds()), 6)
    if duration_growth != expected_growth:
        raise ContractError(
            "$.projection.run.usage.duration_seconds",
            "invariant",
            "duration must equal the complete validated active-lease interval",
        )

    previous_lease = previous["projection"]["lease"]
    current_lease = record["projection"]["lease"]
    if record["type"] == "lease_acquired":
        if previous_lease is not None:
            raise ContractError("$.projection.lease", "invariant", "initial acquisition requires no prior lease")
    elif record["type"] in {"lease_renewed", "heartbeat"}:
        if previous_lease is None or current_lease is None:
            raise ContractError("$.projection.lease", "invariant", "lease renewal requires both lease projections")
        for field in ("lease_id", "run_id", "lane_id", "owner", "acquired_at", "generation"):
            if current_lease[field] != previous_lease[field]:
                raise ContractError(f"$.projection.lease.{field}", "invariant", f"{field} cannot change on renewal")
        if parse_timestamp(current_lease["expires_at"], "$.projection.lease.expires_at") < parse_timestamp(
            previous_lease["expires_at"], "$.previous.projection.lease.expires_at"
        ):
            raise ContractError("$.projection.lease.expires_at", "invariant", "renewal cannot shorten a lease")
    elif record["type"] == "recovery_started":
        if current_lease is None:
            raise ContractError("$.projection.lease", "invariant", "recovery requires a resulting lease projection")
        previous_generation = record["data"]["previous_generation"]
        if previous_lease is None:
            if previous_run["status"] != "halted_kill_switch" or previous_generation is not None:
                raise ContractError(
                    "$.projection.lease",
                    "invariant",
                    "only a pre-lease kill-switch halt may recover without a previous lease",
                )
            if current_lease["generation"] != 0:
                raise ContractError(
                    "$.projection.lease.generation",
                    "invariant",
                    "pre-lease recovery must establish generation zero",
                )
        else:
            if previous_generation != previous_lease["generation"]:
                raise ContractError(
                    "$.data.previous_generation",
                    "invariant",
                    "must match the previous lease generation",
                )
            if current_lease["generation"] != previous_lease["generation"] + 1:
                raise ContractError("$.projection.lease.generation", "invariant", "recovery must increment generation by one")
            if current_lease["lease_id"] == previous_lease["lease_id"]:
                raise ContractError("$.projection.lease.lease_id", "invariant", "recovery requires a fresh lease_id")
    elif record["type"] not in {"kill_switch_detected", "run_completed", "run_failed", "run_cancelled"}:
        if current_lease != previous_lease:
            raise ContractError("$.projection.lease", "invariant", "this event cannot change the lease projection")


def _validate_audit_event(
    record: Mapping[str, Any],
    expected_owner: Mapping[str, Any] | None,
    previous: Mapping[str, Any] | None,
) -> None:
    lease_id = record["lease_id"]
    generation = record["lease_generation"]
    if (lease_id is None) != (generation is None):
        raise ContractError("$.lease_generation", "invariant", "lease_id and lease_generation must both be set or both be null")
    if record["type"] not in LEASE_OPTIONAL_EVENT_TYPES and lease_id is None:
        raise ContractError("$.lease_id", "invariant", f"{record['type']} requires lease context")
    if record["type"] in LEASE_FORBIDDEN_EVENT_TYPES and lease_id is not None:
        raise ContractError("$.lease_id", "invariant", f"{record['type']} must be recorded outside a lease")
    if record["type"] in {"lease_acquired", "lease_renewed"}:
        if record["data"]["lease_id"] != lease_id:
            raise ContractError("$.data.lease_id", "invariant", "must match the audit envelope lease_id")
        if record["data"]["generation"] != generation:
            raise ContractError("$.data.generation", "invariant", "must match the audit envelope lease_generation")
    if record["type"] == "recovery_started":
        previous_generation = record["data"]["previous_generation"]
        new_generation = record["data"]["new_generation"]
        if previous_generation is None:
            if new_generation != 0:
                raise ContractError(
                    "$.data.new_generation",
                    "invariant",
                    "pre-lease recovery must establish generation zero",
                )
        elif new_generation != previous_generation + 1:
            raise ContractError("$.data.new_generation", "invariant", "recovery must increment lease generation by exactly one")
        if new_generation != generation:
            raise ContractError("$.data.new_generation", "invariant", "must match the audit envelope lease_generation")
    if record["type"] == "issue_transitioned":
        validate_transition(record["data"]["from_status"], record["data"]["to_status"], kind="issue")
    if record["type"] == "authority_revoked":
        if parse_timestamp(record["data"]["revoked_at"], "$.data.revoked_at") > parse_timestamp(record["at"], "$.at"):
            raise ContractError("$.data.revoked_at", "invariant", "revocation truth cannot be later than its audit event")
    if record["type"] == "budget_reached":
        budget = record["data"]["budget"]
        limit = record["data"]["limit"]
        observed = record["data"]["observed"]
        if budget == "max_cost_usd":
            if not isinstance(observed, str) or (limit is not None and not isinstance(limit, str)):
                raise ContractError(
                    "$.data.observed",
                    "type",
                    "cost budget values must use canonical fixed-point decimal strings",
                )
            if limit is not None and Decimal(observed) < Decimal(limit):
                raise ContractError("$.data.observed", "invariant", "must meet or exceed the reached budget limit")
        else:
            if isinstance(observed, str) or isinstance(limit, str):
                raise ContractError("$.data.observed", "type", "non-cost budget values must be numeric")
            if limit is not None and observed < limit:
                raise ContractError("$.data.observed", "invariant", "must meet or exceed the reached budget limit")
    _validate_audit_projection(record)
    if record["type"] == "budget_reached" and previous is None:
        reason = record["projection"]["run"].get("terminal_reason")
        code = reason.get("code") if isinstance(reason, Mapping) else None
        if code in {unknown_code for _, unknown_code in UNKNOWN_OUTCOME_PROJECTIONS.values()}:
            raise ContractError(
                "$.projection.run.terminal_reason.code",
                "invariant",
                "unknown-outcome budget marker requires the immediately prior reconciliation event",
            )
        if code != f"budget_reached:{record['data']['budget']}":
            raise ContractError(
                "$.projection.run.terminal_reason.code",
                "invariant",
                "primary budget marker must identify its exhausted budget",
            )
    if previous is not None:
        _validate_audit_projection_transition(record, previous)
    if expected_owner is not None:
        validate_owner(record["actor"], expected_owner, path="$.actor")


def validate_record(
    record_type: str,
    record: Mapping[str, Any],
    *,
    previous: Mapping[str, Any] | None = None,
    expected_owner: Mapping[str, Any] | None = None,
    expected_authority_grant: Mapping[str, Any] | None = None,
) -> Mapping[str, Any]:
    """Validate one record against its JSON Schema and semantic invariants."""

    normalized_type = record_type.replace("-", "_")
    try:
        filename = SCHEMA_FILES[normalized_type]
    except KeyError as exc:
        raise ContractError("$", "record_type", f"unknown record type {record_type!r}") from exc
    if not isinstance(record, Mapping):
        raise ContractError("$", "type", "record must be an object")
    _validate_schema(record, _load_schema(filename), filename, "$")

    if normalized_type == "config":
        _validate_config(record)
    elif normalized_type == "install_receipt":
        _validate_install_receipt(record)
    elif normalized_type == "run":
        _validate_run(record, previous, expected_owner, expected_authority_grant)
    elif normalized_type == "lease":
        _validate_lease(record, expected_owner)
    elif normalized_type == "grant":
        _validate_grant(record)
    elif normalized_type == "route":
        _validate_route(record)
    elif normalized_type == "evidence":
        _validate_evidence(record)
    elif normalized_type == "issue_ledger":
        _validate_issue_ledger(record, previous)
    elif normalized_type == "audit_event":
        _validate_audit_event(record, expected_owner, previous)
    return record
