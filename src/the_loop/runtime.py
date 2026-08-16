"""Serialized event-authoritative runtime for bounded THE LOOP missions."""

from __future__ import annotations

import copy
import os
import stat
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, localcontext
from pathlib import Path
from typing import Any, Callable, Generic, Mapping, TypeVar

from .state import (
    PathPresence,
    StateLockHandle,
    append_event,
    atomic_write_json,
    create_json_exclusive,
    probe_kill_switch,
    read_events,
    read_json,
    remove_state_file,
    state_lock,
)
from .validation import ContractError, parse_timestamp, validate_owner, validate_record, validate_relative_path


T = TypeVar("T")
_FILESYSTEM_FAILURES = frozenset({"unsafe_path", "owner", "permissions", "platform", "lock", "rollback"})
_CONTROL_EVENT_TYPES = frozenset(
    {
        "run_created",
        "authority_granted",
        "authority_revoked",
        "lease_acquired",
        "lease_renewed",
        "operation_intended",
        "operation_reconciled",
        "budget_reached",
        "kill_switch_detected",
        "recovery_started",
        "run_completed",
        "run_failed",
        "run_cancelled",
    }
)
_STAGE_ORDER = ("strategize", "spec_pack", "build", "test", "resolve", "close")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _timestamp(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ContractError("$.clock", "clock", "runtime clock must return a timezone-aware datetime")
    normalized = value.astimezone(timezone.utc)
    rendered = normalized.isoformat(timespec="microseconds" if normalized.microsecond else "seconds")
    return rendered.replace("+00:00", "Z")


def _uuid4(factory: Callable[[], Any], path: str) -> str:
    try:
        value = uuid.UUID(str(factory()))
    except (ValueError, TypeError, AttributeError) as exc:
        raise ContractError(path, "id", "ID factory must return a UUIDv4 value") from exc
    if value.version != 4:
        raise ContractError(path, "id", "ID factory must return a UUIDv4 value")
    return str(value)


def _decimal(value: Any, path: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ContractError(path, "cost", "cost reservation must be a finite decimal number") from exc
    if not result.is_finite() or result < 0:
        raise ContractError(path, "cost", "cost reservation must be a finite non-negative decimal number")
    return result


def _request_cost(value: Any, path: str) -> Decimal:
    rendered = str(value)
    if "e" in rendered.lower():
        raise ContractError(path, "cost", "cost reservation must use fixed-point notation")
    fraction = rendered.partition(".")[2]
    if len(fraction) > 6:
        raise ContractError(path, "cost", "cost reservation supports at most six fractional places")
    return _decimal(value, path)


def _decimal_string(value: Decimal) -> str:
    rendered = format(value, "f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return "0" if rendered in {"", "-0"} else rendered


def _add_decimal(left: Decimal, right: Decimal) -> Decimal:
    scale = max(0, -left.as_tuple().exponent, -right.as_tuple().exponent)
    integer_digits = max(1, left.adjusted() + 1, right.adjusted() + 1)
    with localcontext() as context:
        context.prec = integer_digits + scale + 2
        return left + right


@dataclass(frozen=True)
class LeaseToken:
    lease_id: str
    generation: int
    owner: Mapping[str, Any]

    @classmethod
    def from_lease(cls, lease: Mapping[str, Any]) -> "LeaseToken":
        return cls(str(lease["lease_id"]), int(lease["generation"]), copy.deepcopy(lease["owner"]))


@dataclass(frozen=True)
class RuntimeSnapshot:
    run: dict[str, Any]
    lease: dict[str, Any] | None
    pending_operation: dict[str, Any] | None
    liveness: str

    @property
    def token(self) -> LeaseToken | None:
        return None if self.lease is None else LeaseToken.from_lease(self.lease)


@dataclass(frozen=True)
class MutationRequest:
    event_type: str
    data: Mapping[str, Any]
    action: str = "local_write"
    destination: str = "repository"
    mutations: int = 1
    external_actions: int = 0
    cost_usd: Any = Decimal("0")
    stage_attempt: str | None = None
    effect: str = "local"


@dataclass(frozen=True)
class MutationResult(Generic[T]):
    snapshot: RuntimeSnapshot
    value: T


class RunRuntime:
    """One event-authoritative, serialized runtime for one run."""

    def __init__(
        self,
        project_root: Path | str,
        run_id: str,
        *,
        clock: Callable[[], datetime] = _utc_now,
        id_factory: Callable[[], Any] = uuid.uuid4,
    ) -> None:
        self.project_root = Path(project_root).resolve(strict=True)
        try:
            parsed_run_id = uuid.UUID(str(run_id))
        except (ValueError, TypeError, AttributeError) as exc:
            raise ContractError("$.run_id", "id", "run_id must be a UUIDv4 value") from exc
        if parsed_run_id.version != 4:
            raise ContractError("$.run_id", "id", "run_id must be a UUIDv4 value")
        self.run_id = str(parsed_run_id)
        self._clock = clock
        self._id_factory = id_factory
        self._state_root, self._namespace_snapshot = self._bind_state_root()

    def _capture_namespace(self, state_root: str) -> tuple[tuple[Path, int, int], ...]:
        paths = [self.project_root, self.project_root / ".the-loop"]
        current = self.project_root
        for component in Path(state_root).parts:
            if component == ".":
                continue
            current /= component
            paths.append(current)
        observed: list[tuple[Path, int, int]] = []
        seen: set[Path] = set()
        for path in paths:
            if path in seen:
                continue
            seen.add(path)
            try:
                info = os.stat(path, follow_symlinks=False)
            except OSError as exc:
                raise ContractError(str(path), "unsafe_path", "runtime namespace component is unavailable") from exc
            if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
                raise ContractError(str(path), "unsafe_path", "runtime namespace component must be a real directory")
            observed.append((path, int(info.st_dev), int(info.st_ino)))
        return tuple(observed)

    @staticmethod
    def _serialized_namespace(snapshot: tuple[tuple[Path, int, int], ...], project_root: Path) -> list[dict[str, Any]]:
        return [
            {
                "path": "." if path == project_root else path.relative_to(project_root).as_posix(),
                "device": device,
                "inode": inode,
            }
            for path, device, inode in snapshot
        ]

    def _bind_state_root(self) -> tuple[str, tuple[tuple[Path, int, int], ...]]:
        config = read_json(".the-loop/config.json", project_root=self.project_root, record_type="config")
        if config is None:
            raise ContractError(".the-loop/config.json", "missing", "runtime config is missing")
        state_root = str(config["state_root"])
        validate_relative_path(state_root, path="$.state_root")
        namespace = self._capture_namespace(state_root)
        binding_path = Path(".the-loop") / f"state-root-{self.run_id}.json"
        lock_path = binding_path.with_suffix(".lock")
        desired = {
            "run_id": self.run_id,
            "state_root": state_root,
            "namespace": self._serialized_namespace(namespace, self.project_root),
        }
        with state_lock(lock_path, project_root=self.project_root) as lock:
            lock.assert_current()
            self._assert_namespace_snapshot(namespace)
            binding = read_json(binding_path, project_root=self.project_root)
            if binding is None:
                create_json_exclusive(binding_path, desired, project_root=self.project_root)
                binding = desired
            self._assert_namespace_snapshot(namespace)
            if binding != desired:
                raise ContractError(
                    "$.state_root",
                    "invariant",
                    "state_root is durably bound for this run and cannot change",
                )
        return state_root, namespace

    @staticmethod
    def _assert_namespace_snapshot(snapshot: tuple[tuple[Path, int, int], ...]) -> None:
        for path, device, inode in snapshot:
            try:
                info = os.stat(path, follow_symlinks=False)
            except OSError as exc:
                raise ContractError(str(path), "unsafe_path", "runtime namespace component is unavailable") from exc
            if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
                raise ContractError(str(path), "unsafe_path", "runtime namespace component must remain a real directory")
            if (int(info.st_dev), int(info.st_ino)) != (device, inode):
                raise ContractError(str(path), "unsafe_path", "runtime namespace identity changed")

    def _assert_namespace(self) -> None:
        self._assert_namespace_snapshot(self._namespace_snapshot)

    def _config(self) -> dict[str, Any]:
        self._assert_namespace()
        config = read_json(".the-loop/config.json", project_root=self.project_root, record_type="config")
        if config is None:
            raise ContractError(".the-loop/config.json", "missing", "runtime config is missing")
        validate_relative_path(config["state_root"], path="$.state_root")
        if str(config["state_root"]) != self._state_root:
            raise ContractError(
                "$.state_root",
                "invariant",
                "state_root is durably bound for this run and cannot change",
            )
        return config

    def _paths(self, config: Mapping[str, Any]) -> dict[str, Path]:
        root = Path(self._state_root)
        run_root = root / "runs" / self.run_id
        return {
            "run": run_root / "run.json",
            "lease": run_root / "lease.json",
            "events": run_root / "events.ndjson",
            "lock": run_root / "runtime.lock",
        }

    def _now(self, events: list[dict[str, Any]]) -> tuple[datetime, str]:
        value = self._clock()
        rendered = _timestamp(value)
        normalized = parse_timestamp(rendered, "$.clock")
        if events and normalized < parse_timestamp(events[-1]["at"], "$[-1].at"):
            raise ContractError("$.clock", "clock", "runtime clock cannot move behind the event-log head")
        return normalized, rendered

    def _events(self, paths: Mapping[str, Path]) -> list[dict[str, Any]]:
        events = read_events(paths["events"], project_root=self.project_root)
        if not events:
            raise ContractError(str(paths["events"]), "missing", "run event log is missing or empty")
        if events[-1]["run_id"] != self.run_id:
            raise ContractError("$[-1].run_id", "invariant", "event log does not belong to this runtime")
        return events

    @staticmethod
    def _from_events(
        events: list[dict[str, Any]],
    ) -> tuple[dict[str, Any], dict[str, Any] | None, dict[str, Any] | None]:
        projection = events[-1]["projection"]
        return (
            copy.deepcopy(projection["run"]),
            copy.deepcopy(projection["lease"]),
            copy.deepcopy(projection["pending_operation"]),
        )

    def _install_one(self, path: Path, record_type: str, desired: Mapping[str, Any]) -> None:
        try:
            current = read_json(path, project_root=self.project_root, record_type=record_type)
        except ContractError as exc:
            if exc.code in _FILESYSTEM_FAILURES:
                raise
            atomic_write_json(
                path,
                desired,
                project_root=self.project_root,
                record_type=record_type,
                expected_owner=desired.get("owner") if record_type == "lease" else None,
            )
            return
        if current == desired:
            return
        if current is None:
            create_json_exclusive(
                path,
                desired,
                project_root=self.project_root,
                record_type=record_type,
                expected_owner=desired.get("owner") if record_type == "lease" else None,
            )
            return
        atomic_write_json(
            path,
            desired,
            project_root=self.project_root,
            record_type=record_type,
            expected_owner=desired.get("owner") if record_type == "lease" else None,
        )

    def _install_projection(
        self,
        paths: Mapping[str, Path],
        run: Mapping[str, Any],
        lease: Mapping[str, Any] | None,
        lock: StateLockHandle,
    ) -> None:
        lock.assert_current()
        self._install_one(paths["run"], "run", run)
        lock.assert_current()
        if lease is None:
            remove_state_file(paths["lease"], project_root=self.project_root)
        else:
            self._install_one(paths["lease"], "lease", lease)
        lock.assert_current()

    def _reconcile(
        self,
        paths: Mapping[str, Path],
        lock: StateLockHandle,
    ) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any] | None, dict[str, Any] | None]:
        lock.assert_current()
        events = self._events(paths)
        run, lease, pending_operation = self._from_events(events)
        validate_record("run", run)
        if lease is not None:
            validate_record("lease", lease, expected_owner=lease["owner"])
        self._install_projection(paths, run, lease, lock)
        events, run, lease = self._repair_missing_budget_marker(paths, lock, events, run, lease)
        return events, run, lease, pending_operation

    def _grant(
        self,
        config: Mapping[str, Any],
        grant_id: str,
        run: Mapping[str, Any],
        now: datetime,
        *,
        action: str,
        destination: str,
    ) -> dict[str, Any]:
        grant_path = Path(str(config["state_root"])) / "grants" / f"{grant_id}.json"
        grant = read_json(grant_path, project_root=self.project_root, record_type="grant")
        if grant is None:
            raise ContractError(str(grant_path), "authority", "current authority grant is missing")
        if grant["revoked_at"] is not None:
            raise ContractError("$.authority_grant_id", "authority", "current authority grant is revoked")
        if parse_timestamp(grant["confirmed_at"], "$.grant.confirmed_at") > now:
            raise ContractError("$.authority_grant_id", "authority", "authority grant is not yet valid")
        if parse_timestamp(grant["expires_at"], "$.grant.expires_at") <= now:
            raise ContractError("$.authority_grant_id", "authority", "current authority grant is expired")
        scope = grant["scope"]
        exclusions = set(scope["exclusions"])
        asset = str(run["asset"]["name"])
        for value, label in ((asset, "asset"), (action, "action"), (destination, "destination")):
            if value in exclusions or "*" in exclusions:
                raise ContractError("$.authority_grant_id", "authority", f"authority grant explicitly excludes this {label}")
        for value, field, label in (
            (asset, "assets", "asset"),
            (action, "actions", "action"),
            (destination, "destinations", "destination"),
        ):
            allowed = set(scope[field])
            if value not in allowed and "*" not in allowed:
                raise ContractError("$.authority_grant_id", "authority", f"authority grant does not cover this {label}")
        return grant

    @staticmethod
    def _grant_lock_path(grant_id: str) -> Path:
        return Path(".the-loop") / f"grant-{grant_id}.lock"

    @staticmethod
    def _revocation_data(grant: Mapping[str, Any]) -> dict[str, str]:
        revoked_at = grant.get("revoked_at")
        revoked_by = grant.get("revoked_by")
        if not isinstance(revoked_at, str) or not isinstance(revoked_by, str) or not revoked_by:
            raise ContractError("$.grant.revoked_at", "invariant", "revoked grant must retain actor and timestamp truth")
        return {
            "grant_id": str(grant["grant_id"]),
            "revoked_at": revoked_at,
            "revoked_by": revoked_by,
        }

    @staticmethod
    def _matching_revocation_marker(
        events: list[dict[str, Any]],
        data: Mapping[str, Any],
    ) -> dict[str, Any] | None:
        grant_markers = [
            event
            for event in events
            if event["type"] == "authority_revoked" and event["data"].get("grant_id") == data["grant_id"]
        ]
        if any(marker["data"] != data for marker in grant_markers):
            raise ContractError(
                "$.authority_grant_id",
                "invariant",
                "revocation audit marker conflicts with persisted grant truth",
            )
        if len(grant_markers) > 1:
            raise ContractError(
                "$.authority_grant_id",
                "invariant",
                "revocation audit marker must appear exactly once per run and grant",
            )
        return None if not grant_markers else grant_markers[0]

    def _repair_revocation_marker_locked(
        self,
        paths: Mapping[str, Path],
        lock: StateLockHandle,
        events: list[dict[str, Any]],
        run: Mapping[str, Any],
        lease: Mapping[str, Any] | None,
        actor: Mapping[str, Any],
        now: datetime,
        grant: Mapping[str, Any],
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        data = self._revocation_data(grant)
        marker = self._matching_revocation_marker(events, data)
        if marker is not None:
            return events, copy.deepcopy(run)

        marker_now = max(now, parse_timestamp(data["revoked_at"], "$.grant.revoked_at"))
        marker_at = _timestamp(marker_now)

        projected = self._advance_duration(
            run,
            lease,
            parse_timestamp(events[-1]["at"], "$[-1].at"),
            marker_now,
        )
        projected["updated_at"] = marker_at
        if projected["status"] == "active":
            projected["status"] = "waiting_approval"
            projected["terminal_reason"] = {
                "code": "authority_revoked",
                "explanation": f"Authority grant was revoked by {data['revoked_by']}.",
            }
        try:
            completed = self._append(
                paths,
                lock,
                "authority_revoked",
                actor,
                marker_at,
                data,
                projected,
                lease,
                lease_context=False,
            )
        except BaseException as append_error:
            try:
                authoritative = self._events(paths)
                committed = self._matching_revocation_marker(authoritative, data)
            except BaseException as verification_error:
                raise ContractError(
                    "$.authority_grant_id",
                    "committed_state_unknown",
                    "revocation is durable but its audit head cannot be verified; do not restore the grant",
                ) from verification_error
            if committed is not None:
                if not self._same_event(committed, authoritative[-1]):
                    raise ContractError(
                        "$.authority_grant_id",
                        "committed_state_unknown",
                        "revocation marker committed but is not the canonical authoritative head",
                    ) from append_error
                repaired_run, repaired_lease, _ = self._from_events(authoritative)
                self._install_projection(paths, repaired_run, repaired_lease, lock)
                return authoritative, repaired_run
            raise ContractError(
                "$.authority_grant_id",
                "audit_pending",
                "revocation is durable but its per-run audit marker is pending; retry revocation or another mutating entry",
            ) from append_error
        return [*events, completed], projected

    def _repair_current_revocation(
        self,
        paths: Mapping[str, Path],
        lock: StateLockHandle,
        events: list[dict[str, Any]],
        run: Mapping[str, Any],
        lease: Mapping[str, Any] | None,
        actor: Mapping[str, Any],
        now: datetime,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        grant_id = str(run["authority_grant_id"])
        with state_lock(
            self._grant_lock_path(grant_id),
            project_root=self.project_root,
            exclusive=False,
            _root_already_locked=True,
        ) as grant_lock:
            grant_lock.assert_current()
            grant_path = Path(self._state_root) / "grants" / f"{grant_id}.json"
            grant = read_json(grant_path, project_root=self.project_root, record_type="grant")
            if grant is None:
                raise ContractError(str(grant_path), "authority", "current authority grant is missing")
            if grant["revoked_at"] is None:
                return events, copy.deepcopy(run)
            return self._repair_revocation_marker_locked(
                paths,
                lock,
                events,
                run,
                lease,
                actor,
                now,
                grant,
            )

    @staticmethod
    def _require_token(token: LeaseToken, run: Mapping[str, Any], lease: Mapping[str, Any] | None, now: datetime) -> None:
        if lease is None:
            raise ContractError("$.lease", "lease", "run has no active lease")
        if lease["lease_id"] != token.lease_id or lease["generation"] != token.generation:
            raise ContractError("$.lease", "lease", "lease token does not match the current lease")
        validate_owner(lease["owner"], token.owner, path="$.lease.owner")
        if run["owner"] is None:
            raise ContractError("$.owner", "owner", "leased run has no owner")
        validate_owner(run["owner"], token.owner)
        if now >= parse_timestamp(lease["expires_at"], "$.lease.expires_at"):
            raise ContractError("$.lease.expires_at", "lease_expired", "lease has expired and requires explicit recovery")

    @staticmethod
    def _advance_duration(
        run: Mapping[str, Any],
        lease: Mapping[str, Any] | None,
        head_at: datetime,
        now: datetime,
    ) -> dict[str, Any]:
        updated = copy.deepcopy(run)
        if run["status"] != "active":
            return updated
        end = now
        if lease is not None:
            end = min(end, parse_timestamp(lease["expires_at"], "$.lease.expires_at"))
        seconds = max(0.0, (end - head_at).total_seconds())
        updated["usage"]["duration_seconds"] = round(
            float(updated["usage"]["duration_seconds"]) + seconds,
            6,
        )
        return updated

    def _append(
        self,
        paths: Mapping[str, Path],
        lock: StateLockHandle,
        event_type: str,
        actor: Mapping[str, Any],
        at: str,
        data: Mapping[str, Any],
        run: Mapping[str, Any],
        lease: Mapping[str, Any] | None,
        *,
        lease_context: bool,
        pending_operation: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        self._assert_namespace()
        lock.assert_current()
        event = {
            "schema_version": "1.0",
            "event_id": _uuid4(self._id_factory, "$.event_id"),
            "run_id": self.run_id,
            "lease_id": lease["lease_id"] if lease_context and lease is not None else None,
            "lease_generation": lease["generation"] if lease_context and lease is not None else None,
            "type": event_type,
            "actor": copy.deepcopy(actor),
            "at": at,
            "data": copy.deepcopy(data),
            "projection": {
                "run": copy.deepcopy(run),
                "lease": copy.deepcopy(lease),
                "pending_operation": copy.deepcopy(pending_operation),
            },
        }
        self._assert_namespace()
        completed = append_event(
            paths["events"],
            event,
            project_root=self.project_root,
            expected_owner=actor if lease_context else None,
            expected_lease_id=lease["lease_id"] if lease_context and lease is not None else None,
            expected_generation=lease["generation"] if lease_context and lease is not None else None,
        )
        try:
            lock.assert_current()
            self._install_projection(paths, run, lease, lock)
        except Exception as projection_error:
            try:
                authoritative = self._events(paths)
            except Exception as verification_error:
                raise ContractError(
                    "$.projection",
                    "committed_state_unknown",
                    "event append may have committed but the authoritative head cannot be verified; do not retry",
                ) from verification_error
            head = authoritative[-1]
            if (
                head["event_id"] != completed["event_id"]
                or head["event_digest"] != completed["event_digest"]
                or head["sequence"] != completed["sequence"]
            ):
                raise ContractError(
                    "$.projection",
                    "committed_state_unknown",
                    "event append may have committed but is not the canonical authoritative head; do not retry",
                ) from projection_error
        return completed

    @staticmethod
    def _budget_marker_data(run: Mapping[str, Any]) -> list[dict[str, Any]]:
        return [
            {"budget": field, "stage": stage, "limit": limit, "observed": observed}
            for field, limit, observed, stage in RunRuntime._exhausted_usage_budgets(run)
        ]

    def _append_budget_marker(
        self,
        paths: Mapping[str, Path],
        lock: StateLockHandle,
        source_event: Mapping[str, Any],
        run: Mapping[str, Any],
        lease: Mapping[str, Any],
        data: Mapping[str, Any],
    ) -> None:
        self._append(
            paths,
            lock,
            "budget_reached",
            source_event["actor"],
            source_event["at"],
            data,
            run,
            lease,
            lease_context=True,
        )

    @staticmethod
    def _same_event(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
        return all(left[key] == right[key] for key in ("event_id", "event_digest", "sequence"))

    def _finish_budget_marker(
        self,
        paths: Mapping[str, Path],
        lock: StateLockHandle,
        source_event: Mapping[str, Any],
        run: Mapping[str, Any],
        lease: Mapping[str, Any],
        data: Mapping[str, Any],
    ) -> None:
        try:
            self._append_budget_marker(paths, lock, source_event, run, lease, data)
            return
        except ContractError:
            raise
        except Exception as marker_error:
            try:
                authoritative = self._events(paths)
            except Exception as verification_error:
                raise ContractError(
                    "$.budget_marker",
                    "committed_state_unknown",
                    "semantic completion committed but the authoritative budget-marker head cannot be verified; do not retry",
                ) from verification_error
            head = authoritative[-1]
            if self._same_event(head, source_event):
                return
            marker_projection = {
                "run": copy.deepcopy(run),
                "lease": copy.deepcopy(lease),
                "pending_operation": None,
            }
            if (
                head["type"] == "budget_reached"
                and head["run_id"] == source_event["run_id"]
                and head["previous_event_digest"] == source_event["event_digest"]
                and head["sequence"] == source_event["sequence"] + 1
                and head["actor"] == source_event["actor"]
                and head["data"] == data
                and head["projection"] == marker_projection
            ):
                return
            raise ContractError(
                "$.budget_marker",
                "committed_state_unknown",
                "semantic completion committed but the canonical budget-marker state is unknown; do not retry",
            ) from marker_error

    def _finish_budget_markers(
        self,
        paths: Mapping[str, Path],
        lock: StateLockHandle,
        source_event: Mapping[str, Any],
        run: Mapping[str, Any],
        lease: Mapping[str, Any],
        markers: list[dict[str, Any]],
    ) -> None:
        current_source = source_event
        for marker in markers:
            self._finish_budget_marker(paths, lock, current_source, run, lease, marker)
            authoritative = self._events(paths)
            head = authoritative[-1]
            if self._same_event(head, current_source):
                return
            current_source = head

    def _repair_missing_budget_marker(
        self,
        paths: Mapping[str, Path],
        lock: StateLockHandle,
        events: list[dict[str, Any]],
        run: Mapping[str, Any],
        lease: Mapping[str, Any] | None,
    ) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any] | None]:
        marker_start = len(events)
        while marker_start > 0 and events[marker_start - 1]["type"] == "budget_reached":
            marker_start -= 1
        source = events[marker_start - 1] if marker_start > 0 else None
        trailing = events[marker_start:]
        reason = run.get("terminal_reason")
        code = reason.get("code") if isinstance(reason, Mapping) else None
        marker_source = bool(trailing) or (
            source is not None
            and isinstance(code, str)
            and (
                code.startswith("budget_reached:")
                or (
                    source["type"] == "operation_reconciled"
                    and source["data"].get("outcome") == "unknown"
                    and code in {"operation_outcome_unknown", "external_operation_outcome_unknown"}
                )
            )
        )
        if not marker_source:
            return events, copy.deepcopy(run), copy.deepcopy(lease)
        markers = self._budget_marker_data(run)
        consumed = [event["data"] for event in trailing]
        if consumed != markers[: len(consumed)]:
            raise ContractError("$.budget_marker", "invariant", "budget marker sequence is duplicate, reordered, or mismatched")
        remaining = markers[len(consumed) :]
        if not remaining:
            return events, copy.deepcopy(run), copy.deepcopy(lease)
        if lease is None:
            raise ContractError("$.projection.lease", "invariant", "budget terminality requires lease context")
        self._finish_budget_markers(paths, lock, events[-1], run, lease, remaining)
        repaired_events = self._events(paths)
        repaired_run, repaired_lease, _ = self._from_events(repaired_events)
        return repaired_events, repaired_run, repaired_lease

    def _liveness(
        self,
        config: Mapping[str, Any],
        run: Mapping[str, Any],
        lease: Mapping[str, Any] | None,
        now: datetime,
    ) -> str:
        if run["status"] != "active":
            return "inactive"
        if lease is None:
            return "unleased"
        if now >= parse_timestamp(lease["expires_at"], "$.lease.expires_at"):
            return "expired"
        heartbeat_at = run["last_heartbeat_at"]
        if heartbeat_at is None:
            return "stale"
        stale_at = parse_timestamp(heartbeat_at, "$.last_heartbeat_at") + timedelta(
            seconds=int(config["heartbeat_seconds"])
        )
        return "stale" if now >= stale_at else "fresh"

    def _snapshot(
        self,
        config: Mapping[str, Any],
        run: Mapping[str, Any],
        lease: Mapping[str, Any] | None,
        pending_operation: Mapping[str, Any] | None,
        now: datetime,
    ) -> RuntimeSnapshot:
        liveness = self._liveness(config, run, lease, now)
        if pending_operation is not None:
            liveness = f"pending_{pending_operation['effect']}"
        return RuntimeSnapshot(
            copy.deepcopy(run),
            copy.deepcopy(lease),
            copy.deepcopy(pending_operation),
            liveness,
        )

    def _kill_hit(self, config: Mapping[str, Any]) -> tuple[str, str | None] | None:
        for configured_path in config["kill_switches"]:
            probe = probe_kill_switch(configured_path, project_root=self.project_root)
            if probe.presence is not PathPresence.ABSENT:
                return probe.configured_path, probe.detail
        return None

    def _stop_for_kill(
        self,
        config: Mapping[str, Any],
        paths: Mapping[str, Path],
        lock: StateLockHandle,
        events: list[dict[str, Any]],
        run: Mapping[str, Any],
        lease: Mapping[str, Any] | None,
        actor: Mapping[str, Any],
        now: datetime,
        at: str,
        *,
        detected_hit: tuple[str, str | None] | None = None,
        raise_on_stop: bool = True,
    ) -> dict[str, Any] | None:
        hit = detected_hit if detected_hit is not None else self._kill_hit(config)
        if hit is None:
            return
        configured_path, detail = hit
        if run["status"] in {"complete", "cancelled"}:
            raise ContractError("$.status", "terminal", "terminal run cannot be changed by a kill switch")
        stopped = copy.deepcopy(run)
        if run["status"] != "halted_kill_switch":
            halted = self._advance_duration(run, lease, parse_timestamp(events[-1]["at"], "$[-1].at"), now)
            halted["status"] = "halted_kill_switch"
            halted["updated_at"] = at
            explanation = f"Kill switch detected at {configured_path}."
            if detail:
                explanation += f" Presence was indeterminate: {detail}."
            halted["terminal_reason"] = {"code": "kill_switch_detected", "explanation": explanation}
            self._append(
                paths,
                lock,
                "kill_switch_detected",
                run["owner"] or actor,
                at,
                {"path": configured_path},
                halted,
                lease,
                lease_context=False,
            )
            stopped = halted
        if raise_on_stop:
            raise ContractError("$.kill_switch", "kill_switch", f"mutation stopped by configured path {configured_path}")
        return stopped

    def _reconcile_unstarted_operation(
        self,
        paths: Mapping[str, Path],
        lock: StateLockHandle,
        actor: Mapping[str, Any],
        at: str,
        run: Mapping[str, Any],
        lease: Mapping[str, Any],
        pending_operation: Mapping[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        effect = str(pending_operation["effect"])
        reconciled = copy.deepcopy(run)
        reservation = pending_operation["reservation"]
        reconciled["usage"]["mutations"] -= int(reservation["mutations"])
        reconciled["usage"]["external_actions"] -= int(reservation["external_actions"])
        reconciled["usage"]["cost_usd"] = reservation["prior_cost_usd"]
        stage_attempt = reservation["stage_attempt"]
        if stage_attempt is not None:
            reconciled["usage"]["stage_attempts"][stage_attempt] -= 1
        reconciled["stage"] = reservation["prior_stage"]
        reconciled["status"] = "active"
        reconciled["terminal_reason"] = None
        event = self._append(
            paths,
            lock,
            "operation_reconciled",
            actor,
            at,
            {
                "operation_id": pending_operation["operation_id"],
                "effect": effect,
                "outcome": "known_not_started",
            },
            reconciled,
            lease,
            lease_context=True,
            pending_operation=None,
        )
        return event, reconciled

    def _resolve_pending(
        self,
        config: Mapping[str, Any],
        paths: Mapping[str, Path],
        lock: StateLockHandle,
        events: list[dict[str, Any]],
        run: Mapping[str, Any],
        lease: Mapping[str, Any] | None,
        pending_operation: Mapping[str, Any] | None,
        now: datetime,
        at: str,
    ) -> None:
        if pending_operation is None:
            return
        effect = str(pending_operation["effect"])
        reconciled = self._advance_duration(
            run,
            lease,
            parse_timestamp(events[-1]["at"], "$[-1].at"),
            now,
        )
        reconciled["status"] = "failed" if effect == "local" else "waiting_external"
        code = "operation_outcome_unknown" if effect == "local" else "external_operation_outcome_unknown"
        reconciled["terminal_reason"] = {
            "code": code,
            "explanation": "Callback outcome is unknown after an interrupted pending operation.",
        }
        reconciled["updated_at"] = at
        actor = events[-1]["actor"]
        reconciled_event = self._append(
            paths,
            lock,
            "operation_reconciled",
            actor,
            at,
            {"operation_id": pending_operation["operation_id"], "effect": effect, "outcome": "unknown"},
            reconciled,
            lease,
            lease_context=lease is not None,
            pending_operation=None,
        )
        markers = self._budget_marker_data(reconciled)
        if markers:
            if lease is None:
                raise ContractError("$.projection.lease", "invariant", "unknown-operation budget markers require lease context")
            self._finish_budget_markers(paths, lock, reconciled_event, reconciled, lease, markers)
        raise ContractError(
            "$.pending_operation",
            "operation_outcome_unknown",
            f"interrupted {effect} operation was reconciled without replay",
        )

    def status(self) -> RuntimeSnapshot:
        config = self._config()
        paths = self._paths(config)
        with state_lock(paths["lock"], project_root=self.project_root, exclusive=False) as lock:
            lock.assert_current()
            events = self._events(paths)
            run, lease, pending_operation = self._from_events(events)
            now, _ = self._now(events)
            return self._snapshot(config, run, lease, pending_operation, now)

    def acquire(self, owner: Mapping[str, Any]) -> RuntimeSnapshot:
        config = self._config()
        paths = self._paths(config)
        with state_lock(paths["lock"], project_root=self.project_root) as lock:
            events, run, lease, pending_operation = self._reconcile(paths, lock)
            now, at = self._now(events)
            self._resolve_pending(config, paths, lock, events, run, lease, pending_operation, now, at)
            self._stop_for_kill(config, paths, lock, events, run, lease, owner, now, at)
            if lease is not None:
                raise ContractError(
                    "$.lease",
                    "lease_conflict",
                    f"lease is held by {lease['owner']} until {lease['expires_at']}; use renewal or explicit recovery",
                )
            if run["status"] != "ready":
                raise ContractError("$.status", "transition", "lease acquisition requires a ready run")
            events, run = self._repair_current_revocation(
                paths, lock, events, run, lease, owner, now
            )
            self._grant(config, run["authority_grant_id"], run, now, action="local_write", destination="repository")
            expires_at = _timestamp(now + timedelta(seconds=int(config["lease_seconds"])))
            acquired = {
                "schema_version": "1.0",
                "lease_id": _uuid4(self._id_factory, "$.lease_id"),
                "run_id": self.run_id,
                "lane_id": None,
                "owner": copy.deepcopy(owner),
                "acquired_at": at,
                "renewed_at": at,
                "expires_at": expires_at,
                "generation": 0,
            }
            validate_record("lease", acquired, expected_owner=owner)
            active = copy.deepcopy(run)
            active["status"] = "active"
            active["owner"] = copy.deepcopy(owner)
            active["last_heartbeat_at"] = at
            active["updated_at"] = at
            active["terminal_reason"] = None
            self._append(
                paths,
                lock,
                "lease_acquired",
                owner,
                at,
                {"lease_id": acquired["lease_id"], "generation": 0, "expires_at": expires_at},
                active,
                acquired,
                lease_context=True,
            )
            return self._snapshot(config, active, acquired, None, now)

    def _renew(
        self,
        token: LeaseToken,
        *,
        heartbeat: bool,
    ) -> RuntimeSnapshot:
        config = self._config()
        paths = self._paths(config)
        with state_lock(paths["lock"], project_root=self.project_root) as lock:
            events, run, lease, pending_operation = self._reconcile(paths, lock)
            now, at = self._now(events)
            self._resolve_pending(config, paths, lock, events, run, lease, pending_operation, now, at)
            self._stop_for_kill(config, paths, lock, events, run, lease, token.owner, now, at)
            self._require_token(token, run, lease, now)
            events, run = self._repair_current_revocation(
                paths, lock, events, run, lease, token.owner, now
            )
            self._grant(config, run["authority_grant_id"], run, now, action="local_write", destination="repository")
            if run["status"] != "active":
                raise ContractError("$.status", "transition", "lease renewal requires an active run")
            assert lease is not None
            if now <= parse_timestamp(lease["renewed_at"], "$.lease.renewed_at"):
                raise ContractError("$.clock", "clock", "lease renewal must advance renewed_at")
            active = self._advance_duration(run, lease, parse_timestamp(events[-1]["at"], "$[-1].at"), now)
            budget = self._duration_budget(active)
            if budget is not None:
                return self._fail_budget(config, paths, lock, token.owner, at, now, active, lease, budget)
            renewed = copy.deepcopy(lease)
            renewed["renewed_at"] = at
            renewed["expires_at"] = _timestamp(now + timedelta(seconds=int(config["lease_seconds"])))
            active["updated_at"] = at
            if heartbeat:
                active["last_heartbeat_at"] = at
            event_type = "heartbeat" if heartbeat else "lease_renewed"
            data = (
                {"stage": active["stage"], "status": active["status"]}
                if heartbeat
                else {
                    "lease_id": renewed["lease_id"],
                    "generation": renewed["generation"],
                    "expires_at": renewed["expires_at"],
                }
            )
            self._append(paths, lock, event_type, token.owner, at, data, active, renewed, lease_context=True)
            return self._snapshot(config, active, renewed, None, now)

    def renew(self, token: LeaseToken) -> RuntimeSnapshot:
        return self._renew(token, heartbeat=False)

    def heartbeat(self, token: LeaseToken) -> RuntimeSnapshot:
        return self._renew(token, heartbeat=True)

    def recover(
        self,
        owner: Mapping[str, Any],
        *,
        reason: str,
        authority_grant_id: str | None = None,
    ) -> RuntimeSnapshot:
        if not reason.strip():
            raise ContractError("$.reason", "required", "recovery reason must not be empty")
        config = self._config()
        paths = self._paths(config)
        with state_lock(paths["lock"], project_root=self.project_root) as lock:
            events, run, lease, pending_operation = self._reconcile(paths, lock)
            now, at = self._now(events)
            self._resolve_pending(config, paths, lock, events, run, lease, pending_operation, now, at)
            self._stop_for_kill(config, paths, lock, events, run, lease, owner, now, at)
            prelease_recovery = lease is None
            if prelease_recovery and run["status"] != "halted_kill_switch":
                raise ContractError(
                    "$.lease",
                    "lease",
                    "a missing previous lease is recoverable only after a pre-acquisition kill switch halt",
                )
            exhausted_budget = self._exhausted_usage_budget(run)
            if exhausted_budget is not None:
                field = exhausted_budget[0]
                if events[-1]["type"] != "budget_reached":
                    if lease is None:
                        raise ContractError("$.projection.lease", "invariant", "budget exhaustion requires lease context")
                    self._fail_budget(
                        config,
                        paths,
                        lock,
                        lease["owner"],
                        at,
                        now,
                        run,
                        lease,
                        exhausted_budget,
                    )
                raise ContractError(
                    f"$.budgets.{field}",
                    "budget",
                    f"budget_reached:{field} prevents recovery",
                )
            if lease is not None and now < parse_timestamp(lease["expires_at"], "$.lease.expires_at"):
                raise ContractError("$.lease.expires_at", "lease_conflict", "non-expired lease cannot be replaced")
            if run["status"] not in {
                "active",
                "waiting_approval",
                "waiting_external",
                "blocked",
                "failed",
                "halted_kill_switch",
            }:
                raise ContractError("$.status", "transition", "run status does not permit explicit recovery")
            events, run = self._repair_current_revocation(
                paths, lock, events, run, lease, owner, now
            )
            grant_id = authority_grant_id or run["authority_grant_id"]
            self._grant(config, grant_id, run, now, action="local_write", destination="repository")
            if run["status"] == "active" and lease is not None:
                failed = self._advance_duration(
                    run,
                    lease,
                    parse_timestamp(events[-1]["at"], "$[-1].at"),
                    now,
                )
                failed["status"] = "failed"
                failed["updated_at"] = at
                failed["terminal_reason"] = {
                    "code": "run_failed",
                    "explanation": "The previous active lease expired before explicit recovery.",
                }
                self._append(
                    paths,
                    lock,
                    "run_failed",
                    lease["owner"],
                    at,
                    {"reason": failed["terminal_reason"]["explanation"]},
                    failed,
                    lease,
                    lease_context=True,
                )
                run = failed
                exhausted_budget = self._exhausted_usage_budget(run)
                if exhausted_budget is not None:
                    field = exhausted_budget[0]
                    self._fail_budget(
                        config,
                        paths,
                        lock,
                        lease["owner"],
                        at,
                        now,
                        run,
                        lease,
                        exhausted_budget,
                    )
                    raise ContractError(
                        f"$.budgets.{field}",
                        "budget",
                        f"budget_reached:{field} prevents recovery",
                    )
            previous_generation = None if lease is None else int(lease["generation"])
            generation = 0 if previous_generation is None else previous_generation + 1
            replacement = {
                "schema_version": "1.0",
                "lease_id": _uuid4(self._id_factory, "$.lease_id"),
                "run_id": self.run_id,
                "lane_id": None if lease is None else lease["lane_id"],
                "owner": copy.deepcopy(owner),
                "acquired_at": at,
                "renewed_at": at,
                "expires_at": _timestamp(now + timedelta(seconds=int(config["lease_seconds"]))),
                "generation": generation,
            }
            recovered = self._advance_duration(run, lease, parse_timestamp(events[-1]["at"], "$[-1].at"), now)
            recovered["status"] = "active"
            recovered["owner"] = copy.deepcopy(owner)
            recovered["authority_grant_id"] = grant_id
            recovered["last_heartbeat_at"] = at
            recovered["updated_at"] = at
            recovered["terminal_reason"] = None
            self._append(
                paths,
                lock,
                "recovery_started",
                owner,
                at,
                {
                    "previous_generation": previous_generation,
                    "new_generation": generation,
                    "reason": reason,
                },
                recovered,
                replacement,
                lease_context=True,
            )
            return self._snapshot(config, recovered, replacement, None, now)

    def revoke_authority(self, actor: Mapping[str, Any], *, revoked_by: str) -> RuntimeSnapshot:
        if not revoked_by.strip():
            raise ContractError("$.revoked_by", "required", "revocation actor must not be empty")
        config = self._config()
        paths = self._paths(config)
        with state_lock(paths["lock"], project_root=self.project_root) as lock:
            events, run, lease, pending_operation = self._reconcile(paths, lock)
            now, at = self._now(events)
            self._resolve_pending(config, paths, lock, events, run, lease, pending_operation, now, at)
            grant_id = str(run["authority_grant_id"])
            with state_lock(
                self._grant_lock_path(grant_id),
                project_root=self.project_root,
                _root_already_locked=True,
            ) as grant_lock:
                grant_lock.assert_current()
                grant_path = Path(self._state_root) / "grants" / f"{grant_id}.json"
                grant = read_json(grant_path, project_root=self.project_root, record_type="grant")
                if grant is None:
                    raise ContractError(str(grant_path), "authority", "current authority grant is missing")
                if grant["revoked_at"] is None:
                    revoked = copy.deepcopy(grant)
                    revoked["revoked_at"] = at
                    revoked["revoked_by"] = revoked_by
                    self._assert_namespace()
                    atomic_write_json(
                        grant_path,
                        revoked,
                        project_root=self.project_root,
                        record_type="grant",
                    )
                    self._assert_namespace()
                else:
                    revoked = grant
                repaired_events, repaired_run = self._repair_revocation_marker_locked(
                    paths,
                    lock,
                    events,
                    run,
                    lease,
                    actor,
                    now,
                    revoked,
                )
                repaired_lease = repaired_events[-1]["projection"]["lease"]
                stopped = self._stop_for_kill(
                    config,
                    paths,
                    lock,
                    repaired_events,
                    repaired_run,
                    repaired_lease,
                    actor,
                    now,
                    at,
                    raise_on_stop=False,
                )
                final_run = repaired_run if stopped is None else stopped
                return self._snapshot(config, final_run, repaired_lease, None, now)

    @staticmethod
    def _duration_budget(run: Mapping[str, Any]) -> tuple[str, int, int | float, str | None] | None:
        observed = run["usage"]["duration_seconds"]
        limit = int(run["budgets"]["max_duration_seconds"])
        if _decimal(observed, "$.usage.duration_seconds") >= Decimal(limit):
            return "max_duration_seconds", limit, observed, None
        return None

    @staticmethod
    def _exhausted_usage_budgets(run: Mapping[str, Any]) -> list[tuple[str, Any, Any, str | None]]:
        exhausted: list[tuple[str, Any, Any, str | None]] = []
        reason = run.get("terminal_reason")
        reason_code = reason.get("code") if isinstance(reason, Mapping) else None
        primary_budget = (
            reason_code.removeprefix("budget_reached:")
            if isinstance(reason_code, str) and reason_code.startswith("budget_reached:")
            else None
        )
        duration = _decimal(run["usage"]["duration_seconds"], "$.usage.duration_seconds")
        if duration > 0 and duration >= Decimal(run["budgets"]["max_duration_seconds"]):
            exhausted.append(
                (
                    "max_duration_seconds",
                    run["budgets"]["max_duration_seconds"],
                    run["usage"]["duration_seconds"],
                    None,
                )
            )
        attempts = run["usage"]["stage_attempts"]
        attempt_limit = int(run["budgets"]["max_stage_attempts"])
        for stage in _STAGE_ORDER:
            value = attempts[stage]
            if int(value) > 0 and int(value) >= attempt_limit:
                exhausted.append(("max_stage_attempts", attempt_limit, value, stage))
        for field in ("mutations", "external_actions"):
            observed = int(run["usage"][field])
            budget_field = f"max_{field}"
            if (observed > 0 or primary_budget == budget_field) and observed >= int(run["budgets"][budget_field]):
                exhausted.append((budget_field, run["budgets"][budget_field], observed, None))
        cost_limit = run["budgets"]["max_cost_usd"]
        observed_cost = run["usage"]["cost_usd"]
        if observed_cost is None and primary_budget == "max_cost_usd" and cost_limit is not None:
            observed_cost = "0"
        if cost_limit is not None and observed_cost is not None:
            cost = _decimal(observed_cost, "$.usage.cost_usd")
            if (cost > 0 or primary_budget == "max_cost_usd") and cost >= _decimal(
                cost_limit, "$.budgets.max_cost_usd"
            ):
                exhausted.append(("max_cost_usd", cost_limit, observed_cost, None))
        return exhausted

    @staticmethod
    def _exhausted_usage_budget(run: Mapping[str, Any]) -> tuple[str, Any, Any, str | None] | None:
        exhausted = RunRuntime._exhausted_usage_budgets(run)
        return exhausted[0] if exhausted else None

    def _fail_budget(
        self,
        config: Mapping[str, Any],
        paths: Mapping[str, Path],
        lock: StateLockHandle,
        actor: Mapping[str, Any],
        at: str,
        now: datetime,
        run: Mapping[str, Any],
        lease: Mapping[str, Any],
        budget: tuple[str, Any, Any, str | None],
    ) -> RuntimeSnapshot:
        field, limit, observed, stage = budget
        failed = copy.deepcopy(run)
        failed["status"] = "failed"
        failed["updated_at"] = at
        failed["terminal_reason"] = {
            "code": f"budget_reached:{field}",
            "explanation": f"Budget {field} reached its configured limit.",
        }
        validate_record("run", failed)
        data = {"budget": field, "stage": stage, "limit": limit, "observed": observed}
        marker_event = self._append(
            paths,
            lock,
            "budget_reached",
            actor,
            at,
            data,
            failed,
            lease,
            lease_context=True,
        )
        markers = self._budget_marker_data(failed)
        if data in markers:
            if markers[0] != data:
                raise ContractError("$.budget_marker", "invariant", "primary budget marker violates stable order")
            markers = markers[1:]
        if markers:
            self._finish_budget_markers(paths, lock, marker_event, failed, lease, markers)
        return self._snapshot(config, failed, lease, None, now)

    @staticmethod
    def _validate_request_usage(request: MutationRequest) -> None:
        if request.effect not in {"local", "external"}:
            raise ContractError("$.effect", "enum", "operation effect must be local or external")
        derived_effect = (
            "local"
            if request.action == "local_write" and request.destination == "repository"
            else "external"
        )
        if request.effect != derived_effect:
            raise ContractError(
                "$.effect",
                "invariant",
                f"action {request.action!r} at destination {request.destination!r} must be declared {derived_effect}",
            )
        if request.mutations != 1:
            raise ContractError("$.mutations", "invariant", "each mutation callback must reserve exactly one mutation")
        expected_external_actions = 1 if derived_effect == "external" else 0
        if request.external_actions != expected_external_actions:
            raise ContractError(
                "$.external_actions",
                "invariant",
                f"{derived_effect} mutation must reserve exactly {expected_external_actions} external actions",
            )

    def _budget_projection(
        self,
        run: Mapping[str, Any],
        request: MutationRequest,
    ) -> tuple[dict[str, Any], tuple[str, Any, Any, str | None] | None, bool]:
        if request.event_type in _CONTROL_EVENT_TYPES:
            raise ContractError("$.event_type", "event_type", "perform_mutation cannot emit runtime control events")
        self._validate_request_usage(request)
        cost = _request_cost(request.cost_usd, "$.cost_usd")
        projected = copy.deepcopy(run)
        usage = projected["usage"]
        budgets = projected["budgets"]
        candidates: list[tuple[str, int | float | None, int | float, str | None, bool]] = []
        cost_reached_budget: tuple[str, Any, Any, str | None] | None = None

        if request.stage_attempt is not None:
            if request.stage_attempt not in usage["stage_attempts"]:
                raise ContractError("$.stage_attempt", "enum", "unknown lifecycle stage")
            usage["stage_attempts"][request.stage_attempt] += 1
            observed_attempts = usage["stage_attempts"][request.stage_attempt]
            candidates.append(
                (
                    "max_stage_attempts",
                    budgets["max_stage_attempts"],
                    observed_attempts,
                    request.stage_attempt,
                    True,
                )
            )
        if request.event_type == "stage_started":
            stage = request.data.get("stage")
            if request.stage_attempt != stage:
                raise ContractError(
                    "$.stage_attempt",
                    "invariant",
                    "stage_started must reserve exactly its declared stage attempt",
                )
            projected["stage"] = stage
        elif request.stage_attempt is not None:
            raise ContractError("$.stage_attempt", "invariant", "only stage_started may reserve a stage attempt")
        usage["mutations"] += request.mutations
        if request.mutations:
            candidates.append(("max_mutations", budgets["max_mutations"], usage["mutations"], None, True))
        usage["external_actions"] += request.external_actions
        if request.external_actions:
            candidates.append(
                ("max_external_actions", budgets["max_external_actions"], usage["external_actions"], None, True)
            )
        if cost > 0:
            prior_cost = _decimal(usage["cost_usd"] or 0, "$.usage.cost_usd")
            observed_cost = _add_decimal(prior_cost, cost)
            usage["cost_usd"] = _decimal_string(observed_cost)
            limit_value = budgets["max_cost_usd"]
            limit_decimal = None if limit_value is None else _decimal(limit_value, "$.budgets.max_cost_usd")
            over = limit_decimal is None or observed_cost > limit_decimal
            reached = limit_decimal is not None and observed_cost == limit_decimal
            if over:
                return (
                    copy.deepcopy(run),
                    ("max_cost_usd", limit_value, _decimal_string(prior_cost), None),
                    False,
                )
            if reached:
                cost_reached_budget = (
                    "max_cost_usd",
                    limit_value,
                    _decimal_string(observed_cost),
                    None,
                )

        for field, limit, observed, stage, relevant in candidates:
            if relevant and observed > limit:
                if field == "max_stage_attempts":
                    prior_observed = run["usage"]["stage_attempts"][stage]
                else:
                    prior_observed = run["usage"][field.removeprefix("max_")]
                return copy.deepcopy(run), (field, limit, prior_observed, stage), False
        for field, limit, observed, stage, relevant in candidates:
            if relevant and observed == limit:
                return projected, (field, limit, observed, stage), True
        if cost_reached_budget is not None:
            return projected, cost_reached_budget, True
        return projected, None, False

    def perform_mutation(
        self,
        token: LeaseToken,
        request: MutationRequest,
        callback: Callable[[], T],
    ) -> MutationResult[T]:
        config = self._config()
        paths = self._paths(config)
        with state_lock(paths["lock"], project_root=self.project_root) as lock:
            events, run, lease, pending_operation = self._reconcile(paths, lock)
            now, at = self._now(events)
            self._resolve_pending(config, paths, lock, events, run, lease, pending_operation, now, at)
            self._stop_for_kill(config, paths, lock, events, run, lease, token.owner, now, at)
            self._require_token(token, run, lease, now)
            self._validate_request_usage(request)
            events, run = self._repair_current_revocation(
                paths, lock, events, run, lease, token.owner, now
            )
            self._grant(
                config,
                run["authority_grant_id"],
                run,
                now,
                action=request.action,
                destination=request.destination,
            )
            if run["status"] != "active":
                raise ContractError("$.status", "transition", "mutation requires an active run")
            assert lease is not None
            advanced = self._advance_duration(run, lease, parse_timestamp(events[-1]["at"], "$[-1].at"), now)
            duration_budget = self._duration_budget(advanced)
            if duration_budget is not None:
                failed = self._fail_budget(
                    config, paths, lock, token.owner, at, now, advanced, lease, duration_budget
                )
                raise ContractError("$.budgets.max_duration_seconds", "budget", failed.run["terminal_reason"]["code"])
            projected, budget, reached_after = self._budget_projection(advanced, request)
            if budget is not None and not reached_after:
                has_remaining = False
                if budget[1] is not None:
                    if budget[0] == "max_cost_usd":
                        has_remaining = _decimal(budget[2], "$.usage.cost_usd") < _decimal(
                            budget[1],
                            "$.budgets.max_cost_usd",
                        )
                    else:
                        has_remaining = budget[2] < budget[1]
                if has_remaining:
                    raise ContractError(
                        f"$.budgets.{budget[0]}",
                        "budget_reservation",
                        "requested reservation exceeds the remaining budget",
                    )
                failed = self._fail_budget(config, paths, lock, token.owner, at, now, projected, lease, budget)
                raise ContractError(f"$.budgets.{budget[0]}", "budget", failed.run["terminal_reason"]["code"])
            projected["updated_at"] = at
            pending_operation = {
                "operation_id": _uuid4(self._id_factory, "$.operation_id"),
                "completion_event_type": request.event_type,
                "completion_data": copy.deepcopy(request.data),
                "effect": request.effect,
                "reservation": {
                    "mutations": request.mutations,
                    "external_actions": request.external_actions,
                    "cost_usd": _decimal_string(_request_cost(request.cost_usd, "$.cost_usd")),
                    "stage_attempt": request.stage_attempt,
                    "prior_cost_usd": run["usage"]["cost_usd"],
                    "prior_stage": run["stage"],
                },
            }
            with state_lock(
                self._grant_lock_path(str(run["authority_grant_id"])),
                project_root=self.project_root,
                exclusive=False,
                _root_already_locked=True,
            ) as grant_lock:
                grant_lock.assert_current()
                lock.assert_current()
                self._stop_for_kill(config, paths, lock, events, run, lease, token.owner, now, at)
                self._grant(
                    config,
                    run["authority_grant_id"],
                    run,
                    now,
                    action=request.action,
                    destination=request.destination,
                )
                lock.assert_current()
                intent_event = self._append(
                    paths,
                    lock,
                    "operation_intended",
                    token.owner,
                    at,
                    pending_operation,
                    projected,
                    lease,
                    lease_context=True,
                    pending_operation=pending_operation,
                )
            lock.assert_current()
            hit = self._kill_hit(config)
            if hit is not None:
                reconciled_event, reconciled = self._reconcile_unstarted_operation(
                    paths,
                    lock,
                    token.owner,
                    at,
                    projected,
                    lease,
                    pending_operation,
                )
                self._stop_for_kill(
                    config,
                    paths,
                    lock,
                    [*events, intent_event, reconciled_event],
                    reconciled,
                    lease,
                    token.owner,
                    now,
                    at,
                    detected_hit=hit,
                )
            lock.assert_current()
            self._assert_namespace()
            try:
                value = callback()
            except BaseException as callback_error:
                completion_now, completion_at = self._now([*events, intent_event])
                reconciled = self._advance_duration(
                    projected,
                    lease,
                    parse_timestamp(intent_event["at"], "$.intent.at"),
                    completion_now,
                )
                reconciled["status"] = "failed" if request.effect == "local" else "waiting_external"
                reconciled["updated_at"] = completion_at
                reconciled["terminal_reason"] = {
                    "code": (
                        "operation_outcome_unknown"
                        if request.effect == "local"
                        else "external_operation_outcome_unknown"
                    ),
                    "explanation": f"Mutation callback ended with {callback_error.__class__.__name__}; outcome is unknown.",
                }
                reconciled_event = self._append(
                    paths,
                    lock,
                    "operation_reconciled",
                    token.owner,
                    completion_at,
                    {
                        "operation_id": pending_operation["operation_id"],
                        "effect": request.effect,
                        "outcome": "unknown",
                    },
                    reconciled,
                    lease,
                    lease_context=True,
                    pending_operation=None,
                )
                markers = self._budget_marker_data(reconciled)
                if markers:
                    self._finish_budget_markers(paths, lock, reconciled_event, reconciled, lease, markers)
                raise
            lock.assert_current()
            completion_now, completion_at = self._now([*events, intent_event])
            completion = self._advance_duration(
                projected,
                lease,
                parse_timestamp(intent_event["at"], "$.intent.at"),
                completion_now,
            )
            completion["updated_at"] = completion_at
            completion_budget = self._duration_budget(completion)
            if completion_budget is None and budget is not None and reached_after:
                completion_budget = budget
            if completion_budget is not None:
                field = completion_budget[0]
                completion["status"] = "failed"
                completion["terminal_reason"] = {
                    "code": f"budget_reached:{field}",
                    "explanation": f"Budget {field} reached its configured limit.",
                }
            elif completion_now >= parse_timestamp(lease["expires_at"], "$.lease.expires_at"):
                completion["status"] = "failed"
                completion["terminal_reason"] = {
                    "code": "run_failed",
                    "explanation": "The lease expired while the mutation callback was running.",
                }
            validate_record("run", completion)
            completed_event = self._append(
                paths,
                lock,
                request.event_type,
                token.owner,
                completion_at,
                request.data,
                completion,
                lease,
                lease_context=True,
                pending_operation=None,
            )
            if completion_budget is not None:
                markers = self._budget_marker_data(completion)
                self._finish_budget_markers(paths, lock, completed_event, completion, lease, markers)
            snapshot = self._snapshot(config, completion, lease, None, completion_now)
            return MutationResult(snapshot, value)
