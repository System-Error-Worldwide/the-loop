from __future__ import annotations

import copy
import json
import multiprocessing
import os
import re
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows remains explicitly unverified.
    fcntl = None  # type: ignore[assignment]


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from the_loop import (  # noqa: E402
    ContractError,
    append_event,
    atomic_write_json,
    check_private_permissions,
    read_events,
    resolve_safe_path,
    validate_configured_path,
    validate_record,
    validate_relative_path,
)
import the_loop.state as state_module  # noqa: E402


FIXTURES = ROOT / "tests" / "fixtures" / "state"
VALID_FIXTURES = {
    "config": "config.json",
    "install_receipt": "install_receipt.json",
    "run": "run.json",
    "lease": "lease.json",
    "grant": "grant.json",
    "route": "route.json",
    "evidence": "evidence.json",
    "issue_ledger": "issue_ledger.json",
    "audit_event": "audit_event.json",
}


def fixture(name: str) -> dict:
    return json.loads((FIXTURES / "valid" / name).read_text(encoding="utf-8"))


def operation_reservation(*, mutations: int = 0, external_actions: int = 0) -> dict:
    return {
        "mutations": mutations,
        "external_actions": external_actions,
        "cost_usd": "0",
        "stage_attempt": None,
        "prior_cost_usd": None,
        "prior_stage": "strategize",
    }


def audit_projection(
    event_type: str,
    data: dict,
    owner: dict,
    *,
    lease_id: str | None,
    generation: int | None,
    at: str = "2026-08-16T08:00:00Z",
) -> dict:
    """Build one complete synthetic after-state for an audit event."""

    run = fixture("run.json")
    run["updated_at"] = at
    run["objective"] = data["objective"] if event_type == "run_created" else "Synthetic fixture"

    lease = None
    if lease_id is not None:
        lease = fixture("lease.json")
        lease.update(
            {
                "lease_id": lease_id,
                "owner": copy.deepcopy(owner),
                "acquired_at": at,
                "renewed_at": at,
                "expires_at": data.get("expires_at", "2026-08-16T08:05:00Z"),
                "generation": generation,
            }
        )
        run["status"] = "active"
        run["owner"] = copy.deepcopy(owner)

    pending_operation = None
    if event_type == "operation_intended":
        pending_operation = copy.deepcopy(data)
    elif event_type == "operation_reconciled":
        effect = data["effect"]
        if data["outcome"] == "unknown":
            run["status"] = "failed" if effect == "local" else "waiting_external"
            run["terminal_reason"] = {
                "code": "operation_outcome_unknown" if effect == "local" else "external_operation_outcome_unknown",
                "explanation": "Synthetic interrupted operation.",
            }
    elif event_type == "stage_started":
        run["stage"] = data["stage"]
        run["usage"]["stage_attempts"][data["stage"]] = 1
    elif event_type == "heartbeat":
        run["stage"] = data["stage"]
        run["status"] = data["status"]
        run["last_heartbeat_at"] = at
    elif event_type == "budget_reached":
        budget = data["budget"]
        run["status"] = "failed"
        run["terminal_reason"] = {
            "code": f"budget_reached:{budget}",
            "explanation": "Synthetic budget exhaustion.",
        }
        if budget == "max_stage_attempts":
            run["usage"]["stage_attempts"][data["stage"]] = data["observed"]
        else:
            run["usage"][budget.removeprefix("max_")] = data["observed"]
    elif event_type == "kill_switch_detected":
        run["status"] = "halted_kill_switch"
        run["terminal_reason"] = {"code": "kill_switch_detected", "explanation": data["path"]}
    elif event_type in {"run_completed", "run_failed", "run_cancelled"}:
        status = {"run_completed": "complete", "run_failed": "failed", "run_cancelled": "cancelled"}[event_type]
        run["status"] = status
        run["terminal_reason"] = None if event_type == "run_completed" else {
            "code": event_type,
            "explanation": data["reason"],
        }

    return {"run": run, "lease": lease, "pending_operation": pending_operation}


def append_concurrent_heartbeat(path_name: str, root_name: str, index: int) -> None:
    owner = {"harness": "codex", "actor": "synthetic-agent", "session_id": "session-1"}
    lease_id = "33333333-3333-4333-8333-333333333333"
    event = {
        "schema_version": "1.0",
        "event_id": f"{index:08x}-0000-4000-8000-000000000000",
        "run_id": "11111111-1111-4111-8111-111111111111",
        "lease_id": lease_id,
        "lease_generation": 0,
        "type": "heartbeat",
        "actor": owner,
        "at": "2026-08-16T08:00:00Z",
        "data": {"stage": "test", "status": "active"},
    }
    event["projection"] = audit_projection(
        event["type"],
        event["data"],
        owner,
        lease_id=lease_id,
        generation=0,
    )
    append_event(
        Path(path_name),
        event,
        project_root=Path(root_name),
        expected_owner=owner,
        expected_lease_id=lease_id,
        expected_generation=0,
    )


class RecordContractTests(unittest.TestCase):
    def test_all_schema_documents_are_json_objects(self) -> None:
        schemas = sorted((ROOT / "schemas").glob("*.schema.json"))
        self.assertEqual(10, len(schemas))
        for schema in schemas:
            self.assertIsInstance(json.loads(schema.read_text(encoding="utf-8")), dict, schema.name)

    def test_valid_fixture_passes_every_record_contract(self) -> None:
        for record_type, filename in VALID_FIXTURES.items():
            with self.subTest(record_type=record_type):
                validate_record(record_type, fixture(filename))

    def test_invalid_enum_is_precise(self) -> None:
        record = json.loads((FIXTURES / "invalid" / "enum-config.json").read_text(encoding="utf-8"))
        with self.assertRaisesRegex(ContractError, r"\$\.default_mode: \[enum\]"):
            validate_record("config", record)

    def test_invalid_transition_is_precise(self) -> None:
        previous = fixture("run.json")
        current = copy.deepcopy(previous)
        current["status"] = "complete"
        current["stage"] = "close"
        current["updated_at"] = "2026-08-16T08:01:00Z"
        with self.assertRaisesRegex(ContractError, r"\$\.status: \[transition\].*ready.*complete"):
            validate_record("run", current, previous=previous)

    def test_run_update_preserves_owner_mission_authority_budgets_and_usage(self) -> None:
        ready = fixture("run.json")
        owner = {"harness": "codex", "actor": "synthetic-agent", "session_id": "session-1"}
        active = copy.deepcopy(ready)
        active["status"] = "active"
        active["owner"] = owner
        active["usage"]["mutations"] = 2
        active["updated_at"] = "2026-08-16T08:01:00Z"
        validate_record("run", active, previous=ready, expected_owner=owner)

        mutations = {
            "owner": lambda record: record.__setitem__("owner", {**owner, "actor": "other-agent"}),
            "objective": lambda record: record.__setitem__("objective", "Expanded mission"),
            "authority_grant_id": lambda record: record.__setitem__("authority_grant_id", "99999999-9999-4999-8999-999999999999"),
            "budgets": lambda record: record["budgets"].__setitem__("max_mutations", 999),
            "usage": lambda record: record["usage"].__setitem__("mutations", 1),
        }
        for field, mutate in mutations.items():
            with self.subTest(field=field):
                changed = copy.deepcopy(active)
                changed["updated_at"] = "2026-08-16T08:02:00Z"
                mutate(changed)
                with self.assertRaises(ContractError):
                    validate_record("run", changed, previous=active, expected_owner=owner)

        owner_changed = copy.deepcopy(active)
        owner_changed["owner"] = {**owner, "actor": "other-agent"}
        owner_changed["updated_at"] = "2026-08-16T08:02:00Z"
        with self.assertRaisesRegex(ContractError, r"\$\.owner: \[owner_context\]"):
            validate_record("run", owner_changed, previous=active)

    def test_stage_attempt_usage_is_per_stage_and_monotonic(self) -> None:
        previous = fixture("run.json")
        previous["usage"]["stage_attempts"]["test"] = 2
        current = copy.deepcopy(previous)
        current["updated_at"] = "2026-08-16T08:01:00Z"
        current["usage"]["stage_attempts"]["resolve"] = 1
        validate_record("run", current, previous=previous)

        current["usage"]["stage_attempts"]["test"] = 1
        with self.assertRaisesRegex(ContractError, r"\$\.usage\.stage_attempts\.test: \[invariant\]"):
            validate_record("run", current, previous=previous)

    def test_cost_usage_uses_canonical_exact_decimal_strings(self) -> None:
        previous = fixture("run.json")
        previous["budgets"]["max_cost_usd"] = "10000000000000002"
        previous["usage"]["cost_usd"] = "10000000000000000.1"
        current = copy.deepcopy(previous)
        current["updated_at"] = "2026-08-16T08:01:00Z"
        current["usage"]["cost_usd"] = "10000000000000000.2"
        validate_record("run", current, previous=previous)

        decreased = copy.deepcopy(current)
        decreased["usage"]["cost_usd"] = "9999999999999999.9"
        with self.assertRaisesRegex(ContractError, r"\$\.usage\.cost_usd: \[invariant\]"):
            validate_record("run", decreased, previous=current)

        for invalid in (0.1, "01.00", "1e3", "0.1234567"):
            with self.subTest(invalid=invalid):
                record = copy.deepcopy(current)
                record["usage"]["cost_usd"] = invalid
                with self.assertRaises(ContractError):
                    validate_record("run", record)

    def test_selected_route_requires_verified_compatible_behavior(self) -> None:
        for status in ("failed", "denied", "unverified"):
            with self.subTest(status=status):
                route = fixture("route.json")
                route["candidates"][0]["behavior_status"] = status
                with self.assertRaisesRegex(ContractError, r"selected candidate must have verified behavior"):
                    validate_record("route", route)

        incompatible = fixture("route.json")
        incompatible["candidates"][0]["compatibility"] = ["claude_code"]
        with self.assertRaisesRegex(ContractError, r"selected candidate must include the active harness"):
            validate_record("route", incompatible)

    def test_route_candidate_identity_is_unique(self) -> None:
        route = fixture("route.json")
        duplicate = copy.deepcopy(route["candidates"][0])
        duplicate["description_score"] = 0.5
        route["candidates"].append(duplicate)
        with self.assertRaisesRegex(ContractError, r"candidate provider and source identity must be unique"):
            validate_record("route", route)

        different_source = fixture("route.json")
        installed = copy.deepcopy(different_source["candidates"][0])
        installed.update(
            {
                "source": "installed",
                "behavior_status": "unverified",
                "behavior_observations": [],
                "provenance_type": "upstream-dependency",
            }
        )
        different_source["candidates"].append(installed)
        validate_record("route", different_source)

    def test_verified_route_requires_latest_matching_typed_behavior_proof(self) -> None:
        base = fixture("route.json")

        null_proof = copy.deepcopy(base)
        null_proof["candidates"][0]["behavior_observations"] = None
        with self.assertRaisesRegex(ContractError, r"behavior_observations: \[type\]"):
            validate_record("route", null_proof)

        description_only = copy.deepcopy(base)
        description_only["candidates"][0]["capability_evidence"] = ["description:looks-compatible"]
        description_only["candidates"][0]["behavior_observations"] = []
        with self.assertRaisesRegex(ContractError, r"matching typed behavior observation"):
            validate_record("route", description_only)

        no_verification_time = copy.deepcopy(base)
        no_verification_time["verified_at"] = None
        with self.assertRaisesRegex(ContractError, r"verified selection requires a typed passing observation"):
            validate_record("route", no_verification_time)

        ancient = copy.deepcopy(base)
        ancient["verified_at"] = "2026-08-16T08:01:00Z"
        with self.assertRaisesRegex(ContractError, r"verified_at must equal the latest"):
            validate_record("route", ancient)

        for field, value in (
            ("capability", "lifecycle.build"),
            ("harness", "claude_code"),
            ("track", "noncode"),
            ("environment_digest", "b" * 64),
        ):
            with self.subTest(mismatch=field):
                mismatched = copy.deepcopy(base)
                mismatched["candidates"][0]["behavior_observations"][0][field] = value
                with self.assertRaisesRegex(ContractError, r"matching typed behavior observation"):
                    validate_record("route", mismatched)

        newer_failure = copy.deepcopy(base)
        failure = copy.deepcopy(newer_failure["candidates"][0]["behavior_observations"][0])
        failure.update(
            {
                "outcome": "failed",
                "observed_at": "2026-08-16T08:01:00Z",
                "evidence_id": "88888888-8888-4888-8888-888888888888",
            }
        )
        newer_failure["candidates"][0]["behavior_observations"].append(failure)
        newer_failure["verified_at"] = failure["observed_at"]
        with self.assertRaisesRegex(ContractError, r"latest matching passing observation"):
            validate_record("route", newer_failure)

        superseded_failure = fixture("route.json")
        older_failure = copy.deepcopy(superseded_failure["candidates"][0]["behavior_observations"][0])
        older_failure.update(
            {
                "outcome": "failed",
                "observed_at": "2026-08-16T07:59:00Z",
                "evidence_id": "77777777-7777-4777-8777-777777777777",
            }
        )
        superseded_failure["candidates"][0]["behavior_observations"].insert(0, older_failure)
        validate_record("route", superseded_failure)

    def test_route_behavior_proof_is_fresh_and_same_time_conflicts_fail(self) -> None:
        exact_boundary = fixture("route.json")
        exact_boundary["decided_at"] = "2026-08-17T08:00:00Z"
        validate_record("route", exact_boundary)

        stale = fixture("route.json")
        stale["decided_at"] = "2026-08-17T08:00:01Z"
        with self.assertRaisesRegex(ContractError, r"stale_behavior.*86400-second maximum age"):
            validate_record("route", stale)

        future_proof = fixture("route.json")
        future_proof["decided_at"] = "2026-08-16T07:59:59Z"
        with self.assertRaisesRegex(ContractError, r"decision cannot precede its behavior proof"):
            validate_record("route", future_proof)

        wrong_bound = fixture("route.json")
        wrong_bound["behavior_max_age_seconds"] = 172800
        with self.assertRaisesRegex(ContractError, r"behavior_max_age_seconds: \[const\]"):
            validate_record("route", wrong_bound)

        for outcome in ("passed", "failed"):
            with self.subTest(same_time_outcome=outcome):
                conflict = fixture("route.json")
                observation = copy.deepcopy(conflict["candidates"][0]["behavior_observations"][0])
                observation.update(
                    {
                        "outcome": outcome,
                        "evidence_id": "88888888-8888-4888-8888-888888888888",
                    }
                )
                conflict["candidates"][0]["behavior_observations"].append(observation)
                with self.assertRaisesRegex(ContractError, r"one unique latest matching passing observation"):
                    validate_record("route", conflict)

    def test_unselected_installed_disqualifications_need_precise_reasons(self) -> None:
        cases = (
            ("failed", ["codex"], ["behavior_failed"]),
            ("denied", ["codex"], ["behavior_denied"]),
            ("verified", ["claude_code"], ["harness_incompatible:codex"]),
            ("failed", ["claude_code"], ["behavior_failed", "harness_incompatible:codex"]),
        )
        for status, compatibility, required_reasons in cases:
            with self.subTest(status=status, compatibility=compatibility):
                route = fixture("route.json")
                candidate = copy.deepcopy(route["candidates"][0])
                candidate.update(
                    {
                        "provider": f"installed-{status}-{len(compatibility)}",
                        "source": "installed",
                        "compatibility": compatibility,
                        "behavior_status": status,
                        "behavior_observations": [],
                        "rejection_reasons": [],
                        "provenance_type": "upstream-dependency",
                    }
                )
                route["candidates"].append(candidate)
                with self.assertRaisesRegex(ContractError, r"missing precise rejection evidence"):
                    validate_record("route", route)
                candidate["rejection_reasons"] = required_reasons[:-1]
                if len(required_reasons) > 1:
                    with self.assertRaisesRegex(ContractError, re.escape(required_reasons[-1])):
                        validate_record("route", route)
                candidate["rejection_reasons"] = required_reasons
                validate_record("route", route)

    def test_route_fallback_reason_matches_selected_source(self) -> None:
        for invalid in (None, "", "   "):
            with self.subTest(bundled_fallback_reason=invalid):
                route = fixture("route.json")
                route["fallback_reason"] = invalid
                with self.assertRaisesRegex(ContractError, r"bundled selection requires a nonempty fallback reason"):
                    validate_record("route", route)

        installed = fixture("route.json")
        installed["candidates"][0].update(
            {"source": "installed", "provenance_type": "upstream-dependency"}
        )
        installed["selected_source"] = "installed"
        for invalid in ("not needed", ""):
            with self.subTest(installed_fallback_reason=invalid):
                installed["fallback_reason"] = invalid
                with self.assertRaisesRegex(ContractError, r"installed selection requires a null fallback reason"):
                    validate_record("route", installed)
        installed["fallback_reason"] = None
        validate_record("route", installed)

        bundled_upstream = fixture("route.json")
        bundled_upstream["candidates"][0]["provenance_type"] = "upstream-dependency"
        with self.assertRaisesRegex(ContractError, r"upstream dependency must be selected from the installed source"):
            validate_record("route", bundled_upstream)

    def test_budget_terminal_reason_uses_stable_primary_priority(self) -> None:
        run = fixture("run.json")
        run["budgets"].update(
            {
                "max_duration_seconds": 60,
                "max_stage_attempts": 1,
                "max_mutations": 1,
                "max_external_actions": 1,
                "max_cost_usd": "1",
            }
        )
        run["usage"]["duration_seconds"] = 60
        run["usage"]["stage_attempts"]["build"] = 1
        run["usage"]["mutations"] = 1
        run["usage"]["external_actions"] = 1
        run["usage"]["cost_usd"] = "1"
        run["status"] = "failed"
        run["terminal_reason"] = {
            "code": "budget_reached:max_cost_usd",
            "explanation": "Injected wrong primary.",
        }
        with self.assertRaisesRegex(ContractError, r"stable primary priority"):
            validate_record("run", run)

        run["terminal_reason"] = {
            "code": "budget_reached:max_duration_seconds",
            "explanation": "Correct stable primary.",
        }
        validate_record("run", run)

    def test_budget_terminal_reason_requires_failed_state(self) -> None:
        record = fixture("run.json")
        record["status"] = "blocked"
        record["terminal_reason"] = {
            "code": "budget_reached:max_mutations",
            "explanation": "Synthetic exhaustion.",
        }
        with self.assertRaisesRegex(ContractError, r"\$\.status: \[invariant\].*failed"):
            validate_record("run", record)

        under_limit = fixture("run.json")
        under_limit["status"] = "failed"
        under_limit["terminal_reason"] = {
            "code": "budget_reached:max_mutations",
            "explanation": "Synthetic exhaustion.",
        }
        with self.assertRaisesRegex(ContractError, r"usage at its configured limit"):
            validate_record("run", under_limit)

    def test_timestamp_requires_rfc3339_t_separator(self) -> None:
        record = fixture("run.json")
        record["created_at"] = "2026-08-16 08:00:00Z"
        record["updated_at"] = "2026-08-16 08:00:00Z"
        with self.assertRaisesRegex(ContractError, r"\$\.created_at: \[pattern\]"):
            validate_record("run", record)

    def test_authority_change_requires_explicit_validated_grant_during_recovery(self) -> None:
        previous = fixture("run.json")
        previous["status"] = "waiting_approval"
        previous["terminal_reason"] = {"code": "approval", "explanation": "Awaiting authority elevation."}
        current = copy.deepcopy(previous)
        current["status"] = "ready"
        current["terminal_reason"] = None
        current["authority_grant_id"] = "99999999-9999-4999-8999-999999999999"
        current["updated_at"] = "2026-08-16T08:01:00Z"
        with self.assertRaisesRegex(ContractError, r"\$\.authority_grant_id: \[authority\]"):
            validate_record("run", current, previous=previous)
        grant = fixture("grant.json")
        grant["grant_id"] = current["authority_grant_id"]
        validate_record("run", current, previous=previous, expected_authority_grant=grant)

        same_grant = copy.deepcopy(previous)
        same_grant["status"] = "ready"
        same_grant["terminal_reason"] = None
        same_grant["updated_at"] = "2026-08-16T08:01:00Z"
        with self.assertRaisesRegex(ContractError, r"\[authority\].*validated current grant"):
            validate_record("run", same_grant, previous=previous)
        revoked = fixture("grant.json")
        revoked["revoked_at"] = "2026-08-16T08:00:30Z"
        revoked["revoked_by"] = "Moses"
        with self.assertRaisesRegex(ContractError, r"\[authority\].*revoked"):
            validate_record("run", same_grant, previous=previous, expected_authority_grant=revoked)

        future = fixture("grant.json")
        future["confirmed_at"] = "2026-08-16T09:00:00Z"
        with self.assertRaisesRegex(ContractError, r"\[authority\].*confirmed after"):
            validate_record("run", same_grant, previous=previous, expected_authority_grant=future)

        no_destination = fixture("grant.json")
        no_destination["scope"]["destinations"] = []
        with self.assertRaisesRegex(ContractError, r"\[authority\].*repository writes"):
            validate_record("run", same_grant, previous=previous, expected_authority_grant=no_destination)

        for exclusion in ("synthetic-asset", "local_write", "repository", "*"):
            with self.subTest(exclusion=exclusion):
                excluded = fixture("grant.json")
                excluded["scope"]["exclusions"] = [exclusion]
                with self.assertRaisesRegex(ContractError, r"\[authority\].*explicitly excludes"):
                    validate_record("run", same_grant, previous=previous, expected_authority_grant=excluded)

        unrelated_exclusion = fixture("grant.json")
        unrelated_exclusion["scope"]["exclusions"] = ["network"]
        validate_record("run", same_grant, previous=previous, expected_authority_grant=unrelated_exclusion)

    def test_active_run_requires_owner(self) -> None:
        record = fixture("run.json")
        record["status"] = "active"
        with self.assertRaisesRegex(ContractError, r"\$\.owner: \[owner\]"):
            validate_record("run", record)

    def test_wrong_lease_owner_is_precise(self) -> None:
        record = fixture("lease.json")
        expected = {"harness": "codex", "actor": "other-agent", "session_id": "session-1"}
        with self.assertRaisesRegex(ContractError, r"\$\.owner: \[owner\].*actor"):
            validate_record("lease", record, expected_owner=expected)

    def test_missing_permanent_invariant_fails(self) -> None:
        record = fixture("grant.json")
        record["permanent_invariants"] = record["permanent_invariants"][1:]
        with self.assertRaisesRegex(ContractError, r"\$\.permanent_invariants: \[min_items\]"):
            validate_record("grant", record)

    def test_cross_field_invariant_is_precise(self) -> None:
        record = fixture("config.json")
        record["lease_seconds"] = record["heartbeat_seconds"]
        with self.assertRaisesRegex(ContractError, r"\$\.lease_seconds: \[invariant\]"):
            validate_record("config", record)

    def test_invalid_relative_path_is_precise(self) -> None:
        record = json.loads((FIXTURES / "invalid" / "path-config.json").read_text(encoding="utf-8"))
        with self.assertRaisesRegex(ContractError, r"\$\.state_root"):
            validate_record("config", record)
        with self.assertRaisesRegex(ContractError, r"\$\.state_root: \[unsafe_path\]"):
            validate_relative_path("../escape", path="$.state_root")

    def test_config_accepts_explicit_absolute_kill_switch(self) -> None:
        record = fixture("config.json")
        record["kill_switches"].append("/tmp/the-loop-stop")
        validate_record("config", record)
        self.assertEqual("/tmp/the-loop-stop", validate_configured_path("/tmp/the-loop-stop"))

    def test_config_rejects_traversing_absolute_kill_switch(self) -> None:
        record = fixture("config.json")
        record["kill_switches"].append("/tmp/../private-stop")
        with self.assertRaisesRegex(ContractError, r"\$\.kill_switches\[1\]: \[pattern\]"):
            validate_record("config", record)
        with self.assertRaisesRegex(ContractError, r"\[unsafe_path\].*traversal"):
            validate_configured_path("/tmp/../private-stop")

    def test_user_level_install_and_discovered_roots_accept_absolute_paths(self) -> None:
        receipt = fixture("install_receipt.json")
        receipt["target_root"] = "/tmp/the-loop-user-install"
        validate_record("install_receipt", receipt)

        config = fixture("config.json")
        config["harnesses"]["codex"] = {
            "installed": True,
            "version": "1.0",
            "discovery": "verified",
            "behavior": "unverified",
            "skill_roots": ["/tmp/codex-skills"],
            "collisions": [],
            "checked_at": "2026-08-16T08:00:00Z",
            "evidence_id": None,
        }
        validate_record("config", config)

    def test_symlink_escape_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as project_name, tempfile.TemporaryDirectory() as outside_name:
            project = Path(project_name)
            (project / "escape").symlink_to(Path(outside_name), target_is_directory=True)
            with self.assertRaisesRegex(ContractError, r"\[unsafe_path\].*escapes"):
                resolve_safe_path(project, "escape/state.json")

    @unittest.skipUnless(hasattr(os, "chmod"), "POSIX-like permissions required")
    def test_insecure_permissions_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_name:
            path = Path(temporary_name) / "state.json"
            path.write_text("{}", encoding="utf-8")
            path.chmod(0o644)
            with self.assertRaisesRegex(ContractError, r"\[permissions\]"):
                check_private_permissions(path)


class ProjectionTests(unittest.TestCase):
    def test_atomic_write_is_valid_and_private(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_name:
            root = Path(temporary_name)
            path = root / "run.json"
            record = fixture("run.json")
            atomic_write_json(path, record, record_type="run", project_root=root)
            self.assertEqual(record, json.loads(path.read_text(encoding="utf-8")))
            self.assertEqual(0, path.stat().st_mode & 0o077)

    def test_interrupted_replace_preserves_last_valid_projection(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_name:
            root = Path(temporary_name)
            path = root / "run.json"
            previous = fixture("run.json")
            atomic_write_json(path, previous, record_type="run", project_root=root)
            before = path.read_bytes()

            updated = copy.deepcopy(previous)
            updated["status"] = "active"
            updated["owner"] = {"harness": "codex", "actor": "synthetic-agent", "session_id": "session-1"}
            updated["updated_at"] = "2026-08-16T08:01:00Z"

            def interrupt() -> None:
                raise OSError("synthetic interruption before replace")

            with self.assertRaisesRegex(OSError, "synthetic interruption"):
                atomic_write_json(
                    path,
                    updated,
                    record_type="run",
                    previous=previous,
                    expected_owner=updated["owner"],
                    project_root=root,
                    _before_replace=interrupt,
                )
            self.assertEqual(before, path.read_bytes())
            self.assertEqual([], list(root.glob(".run.json.*.tmp")))

    def test_parent_swap_cannot_redirect_atomic_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as project_name, tempfile.TemporaryDirectory() as outside_name:
            root = Path(project_name)
            state_root = root / ".the-loop"
            path = state_root / "runs" / "run-1" / "run.json"
            previous = fixture("run.json")
            atomic_write_json(path, previous, record_type="run", project_root=root)
            before = path.read_bytes()

            outside = Path(outside_name)
            outside_target = outside / "runs" / "run-1" / "run.json"
            outside_target.parent.mkdir(parents=True)
            outside_target.write_text('{"outside":"preserved"}\n', encoding="utf-8")
            outside_target.chmod(0o600)
            outside_before = outside_target.read_bytes()
            held = root / ".the-loop-held"

            updated = copy.deepcopy(previous)
            updated["status"] = "active"
            updated["owner"] = {"harness": "codex", "actor": "synthetic-agent", "session_id": "session-1"}
            updated["updated_at"] = "2026-08-16T08:01:00Z"

            def swap_parent() -> None:
                state_root.rename(held)
                state_root.symlink_to(outside, target_is_directory=True)

            try:
                with self.assertRaisesRegex(ContractError, r"\[unsafe_path\].*parent changed"):
                    atomic_write_json(
                        path,
                        updated,
                        record_type="run",
                        previous=previous,
                        expected_owner=updated["owner"],
                        project_root=root,
                        _before_replace=swap_parent,
                    )
                self.assertEqual(outside_before, outside_target.read_bytes())
                self.assertEqual(before, (held / "runs" / "run-1" / "run.json").read_bytes())
                self.assertEqual([], list((held / "runs" / "run-1").glob(".run.json.*.tmp")))
            finally:
                if state_root.is_symlink():
                    state_root.unlink()

    def test_parent_swap_inside_replace_reports_failure(self) -> None:
        with tempfile.TemporaryDirectory() as project_name, tempfile.TemporaryDirectory() as outside_name:
            root = Path(project_name)
            state_root = root / ".the-loop"
            path = state_root / "runs" / "run-1" / "run.json"
            previous = fixture("run.json")
            atomic_write_json(path, previous, record_type="run", project_root=root)

            outside = Path(outside_name)
            outside_target = outside / "runs" / "run-1" / "run.json"
            outside_target.parent.mkdir(parents=True)
            outside_target.write_text('{"outside":"preserved"}\n', encoding="utf-8")
            outside_target.chmod(0o600)
            outside_before = outside_target.read_bytes()
            held = root / ".the-loop-held"

            updated = copy.deepcopy(previous)
            updated["status"] = "active"
            updated["owner"] = {"harness": "codex", "actor": "synthetic-agent", "session_id": "session-1"}
            updated["updated_at"] = "2026-08-16T08:01:00Z"
            real_replace = os.replace

            def swap_during_replace(source: object, destination: object, **kwargs: object) -> None:
                state_root.rename(held)
                state_root.symlink_to(outside, target_is_directory=True)
                real_replace(source, destination, **kwargs)

            try:
                with mock.patch("the_loop.state.os.replace", side_effect=swap_during_replace):
                    with self.assertRaisesRegex(ContractError, r"\[unsafe_path\].*canonical projection changed"):
                        atomic_write_json(
                            path,
                            updated,
                            record_type="run",
                            previous=previous,
                            expected_owner=updated["owner"],
                            project_root=root,
                        )
                self.assertEqual(outside_before, outside_target.read_bytes())
                self.assertEqual("ready", json.loads((held / "runs" / "run-1" / "run.json").read_text())["status"])
            finally:
                if state_root.is_symlink():
                    state_root.unlink()

    def test_late_projection_hard_link_prevents_success(self) -> None:
        with tempfile.TemporaryDirectory() as project_name, tempfile.TemporaryDirectory() as outside_name:
            root = Path(project_name)
            path = root / "run.json"
            alias = Path(outside_name) / "run-alias.json"
            atomic_write_json(path, {"old": True}, project_root=root)
            before = path.read_bytes()
            real_replace = os.replace

            def link_during_replace(source: object, destination: object, **kwargs: object) -> None:
                os.link(source, alias, src_dir_fd=kwargs.get("src_dir_fd"))
                real_replace(source, destination, **kwargs)

            with mock.patch("the_loop.state.os.replace", side_effect=link_during_replace):
                with self.assertRaisesRegex(ContractError, r"\[unsafe_path\].*hard-linked"):
                    atomic_write_json(path, {"new": True}, project_root=root)
            self.assertEqual(before, path.read_bytes())
            self.assertTrue(alias.exists())
            self.assertNotEqual(alias.stat().st_ino, path.stat().st_ino)
            self.assertEqual(1, path.stat().st_nlink)

    def test_unsafe_projection_snapshot_cannot_become_safe_before_open(self) -> None:
        with tempfile.TemporaryDirectory() as project_name, tempfile.TemporaryDirectory() as outside_name:
            root = Path(project_name)
            path = root / "run.json"
            alias = Path(outside_name) / "run-alias.json"
            atomic_write_json(path, {"old": True}, project_root=root)
            os.link(path, alias)
            before = path.read_bytes()
            real_open_parent = state_module._open_state_parent

            def remove_alias_after_snapshot(snapshot: object, **kwargs: object) -> object:
                alias.unlink()
                return real_open_parent(snapshot, **kwargs)

            with mock.patch("the_loop.state._open_state_parent", side_effect=remove_alias_after_snapshot):
                with self.assertRaisesRegex(ContractError, r"\[unsafe_path\].*hard-linked"):
                    atomic_write_json(path, {"new": True}, project_root=root)
            self.assertEqual(before, path.read_bytes())
            self.assertEqual(1, path.stat().st_nlink)

    def test_nested_runtime_directories_are_private(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_name:
            root = Path(temporary_name)
            path = root / ".the-loop" / "runs" / "run-1" / "run.json"
            atomic_write_json(path, fixture("run.json"), record_type="run", project_root=root)
            for directory in (root / ".the-loop", root / ".the-loop" / "runs", path.parent):
                with self.subTest(directory=directory):
                    self.assertEqual(0, directory.stat().st_mode & 0o077)

    def test_projection_target_symlink_is_rejected_before_resolution(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_name:
            root = Path(temporary_name)
            victim = root / "victim.json"
            victim.write_text('{"preserved":true}\n', encoding="utf-8")
            victim.chmod(0o600)
            target = root / "run.json"
            target.symlink_to(victim)
            before = victim.read_bytes()
            with self.assertRaisesRegex(ContractError, r"\[unsafe_path\].*symlink"):
                atomic_write_json(target, fixture("run.json"), record_type="run", project_root=root)
            self.assertEqual(before, victim.read_bytes())

    def test_existing_projection_hard_link_is_rejected_before_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as project_name, tempfile.TemporaryDirectory() as outside_name:
            root = Path(project_name)
            victim = Path(outside_name) / "victim.json"
            victim.write_text(json.dumps(fixture("run.json")) + "\n", encoding="utf-8")
            victim.chmod(0o600)
            target = root / "run.json"
            os.link(victim, target)
            before = victim.read_bytes()
            with self.assertRaisesRegex(ContractError, r"\[unsafe_path\].*hard-linked"):
                atomic_write_json(target, fixture("run.json"), record_type="run", project_root=root)
            self.assertEqual(before, victim.read_bytes())
            self.assertEqual(before, target.read_bytes())
            self.assertEqual(2, target.stat().st_nlink)

    @unittest.skipUnless(Path("/dev/fd").exists() or Path("/proc/self/fd").exists(), "fd accounting unavailable")
    def test_rejected_private_parent_does_not_leak_descriptors(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_name:
            root = Path(temporary_name)
            state_root = root / ".the-loop"
            state_root.mkdir(mode=0o755)
            state_root.chmod(0o755)
            path = state_root / "runs" / "run.json"
            fd_root = Path("/dev/fd") if Path("/dev/fd").exists() else Path("/proc/self/fd")
            before = len(list(fd_root.iterdir()))
            for _ in range(40):
                with self.assertRaisesRegex(ContractError, r"\[permissions\]"):
                    atomic_write_json(path, fixture("run.json"), record_type="run", project_root=root)
                with self.assertRaisesRegex(ContractError, r"\[permissions\]"):
                    read_events(state_root / "runs" / "events.ndjson", project_root=root)
            after = len(list(fd_root.iterdir()))
            self.assertEqual(before, after)


class EventLogTests(unittest.TestCase):
    OWNER = {"harness": "codex", "actor": "synthetic-agent", "session_id": "session-1"}
    LEASE_ID = "33333333-3333-4333-8333-333333333333"

    def event(
        self,
        event_id: str,
        event_type: str,
        *,
        lease: bool,
        generation: int = 0,
        lease_id: str = LEASE_ID,
        projection_lease: bool | None = None,
    ) -> dict:
        data = {
            "run_created": {"objective": "Synthetic fixture"},
            "authority_granted": {"grant_id": "22222222-2222-4222-8222-222222222222", "level": "bounded"},
            "authority_revoked": {
                "grant_id": "22222222-2222-4222-8222-222222222222",
                "revoked_at": "2026-08-16T08:00:00Z",
                "revoked_by": "Moses",
            },
            "lease_acquired": {"lease_id": lease_id, "generation": generation, "expires_at": "2026-08-16T08:05:00Z"},
            "lease_renewed": {"lease_id": lease_id, "generation": generation, "expires_at": "2026-08-16T08:05:00Z"},
            "kill_switch_detected": {"path": ".the-loop/STOP"},
            "stage_started": {"stage": "test"},
            "heartbeat": {"stage": "test", "status": "active"},
            "run_completed": {"reason": "Done gate passed"},
            "run_failed": {"reason": "Test gate failed"},
            "recovery_started": {
                "previous_generation": generation - 1,
                "new_generation": generation,
                "reason": "Expired lease",
            },
        }[event_type]
        event = {
            "schema_version": "1.0",
            "event_id": event_id,
            "run_id": "11111111-1111-4111-8111-111111111111",
            "lease_id": lease_id if lease else None,
            "lease_generation": generation if lease else None,
            "type": event_type,
            "actor": self.OWNER,
            "at": "2026-08-16T08:00:00Z",
            "data": data,
        }
        projected_lease = lease if projection_lease is None else projection_lease
        event["projection"] = audit_projection(
            event_type,
            data,
            self.OWNER,
            lease_id=lease_id if projected_lease else None,
            generation=generation if projected_lease else None,
        )
        return event

    def test_events_append_with_sequence_and_digest_chain(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_name:
            root = Path(temporary_name)
            path = root / "events.ndjson"
            first = append_event(path, self.event("44444444-4444-4444-8444-444444444444", "run_created", lease=False), project_root=root)
            second = append_event(
                path,
                self.event("99999999-9999-4999-8999-999999999999", "lease_acquired", lease=True),
                project_root=root,
                expected_owner=self.OWNER,
                expected_lease_id=self.LEASE_ID,
                expected_generation=0,
            )
            events = read_events(path, project_root=root)
            self.assertEqual([1, 2], [event["sequence"] for event in events])
            self.assertEqual(first["event_digest"], second["previous_event_digest"])
            self.assertEqual(0, path.stat().st_mode & 0o077)

    def test_caller_sequence_must_increment_across_lease_contexts(self) -> None:
        cases = (
            ("authority_revoked", False, {}),
            (
                "lease_acquired",
                True,
                {
                    "expected_owner": self.OWNER,
                    "expected_lease_id": self.LEASE_ID,
                    "expected_generation": 0,
                },
            ),
        )
        for event_type, lease, expectations in cases:
            with self.subTest(event_type=event_type), tempfile.TemporaryDirectory() as temporary_name:
                root = Path(temporary_name)
                path = root / "events.ndjson"
                append_event(
                    path,
                    self.event("44444444-4444-4444-8444-444444444444", "run_created", lease=False),
                    project_root=root,
                )
                before = path.read_bytes()
                duplicate = self.event("99999999-9999-4999-8999-999999999999", event_type, lease=lease)
                duplicate["sequence"] = 1
                with self.assertRaisesRegex(ContractError, r"\[event_chain\].*increment"):
                    append_event(path, duplicate, project_root=root, **expectations)
                self.assertEqual(before, path.read_bytes())
                self.assertEqual([1], [event["sequence"] for event in read_events(path, project_root=root)])

    def test_first_append_must_create_a_valid_chain(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_name:
            root = Path(temporary_name)
            path = root / "events.ndjson"
            with self.assertRaisesRegex(ContractError, r"\[event_chain\].*first audit event"):
                append_event(
                    path,
                    self.event("44444444-4444-4444-8444-444444444444", "authority_granted", lease=False),
                    project_root=root,
                )
            wrong_sequence = self.event("55555555-5555-4555-8555-555555555555", "run_created", lease=False)
            wrong_sequence["sequence"] = 2
            with self.assertRaisesRegex(ContractError, r"\[event_chain\].*sequence must be one"):
                append_event(path, wrong_sequence, project_root=root)
            self.assertEqual([], read_events(path, project_root=root))

    @unittest.skipIf(sys.platform == "win32", "fcntl concurrency contract requires POSIX")
    def test_concurrent_writers_preserve_one_digest_chain(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_name:
            root = Path(temporary_name)
            path = root / "events.ndjson"
            append_event(path, self.event("44444444-4444-4444-8444-444444444444", "run_created", lease=False), project_root=root)
            append_event(
                path,
                self.event("99999999-9999-4999-8999-999999999999", "lease_acquired", lease=True),
                project_root=root,
                expected_owner=self.OWNER,
                expected_lease_id=self.LEASE_ID,
                expected_generation=0,
            )
            context = multiprocessing.get_context("fork")
            processes = [
                context.Process(target=append_concurrent_heartbeat, args=(str(path), str(root), index))
                for index in range(1, 5)
            ]
            for process in processes:
                process.start()
            for process in processes:
                process.join(timeout=10)
                self.assertEqual(0, process.exitcode)
            events = read_events(path, project_root=root)
            self.assertEqual(6, len(events))
            self.assertEqual([1, 2, 3, 4, 5, 6], [event["sequence"] for event in events])

    def test_append_repairs_a_valid_unterminated_final_record(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_name:
            root = Path(temporary_name)
            path = root / "events.ndjson"
            append_event(path, self.event("44444444-4444-4444-8444-444444444444", "run_created", lease=False), project_root=root)
            path.write_bytes(path.read_bytes().rstrip(b"\n"))
            append_event(
                path,
                self.event("99999999-9999-4999-8999-999999999999", "lease_acquired", lease=True),
                project_root=root,
                expected_owner=self.OWNER,
                expected_lease_id=self.LEASE_ID,
                expected_generation=0,
            )
            self.assertEqual(2, len(read_events(path, project_root=root)))

    def test_null_lease_event_cannot_hide_same_generation_lease_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_name:
            root = Path(temporary_name)
            path = root / "events.ndjson"
            append_event(path, self.event("44444444-4444-4444-8444-444444444444", "run_created", lease=False), project_root=root)
            first_lease = self.LEASE_ID
            append_event(
                path,
                self.event("55555555-5555-4555-8555-555555555555", "lease_acquired", lease=True, generation=0, lease_id=first_lease),
                project_root=root,
                expected_owner=self.OWNER,
                expected_lease_id=first_lease,
                expected_generation=0,
            )
            append_event(
                path,
                self.event(
                    "66666666-6666-4666-8666-666666666666",
                    "authority_granted",
                    lease=False,
                    projection_lease=True,
                ),
                project_root=root,
            )
            replacement_lease = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
            with self.assertRaisesRegex(ContractError, r"\[event_chain\].*lease_id changed"):
                append_event(
                    path,
                    self.event(
                        "77777777-7777-4777-8777-777777777777",
                        "lease_renewed",
                        lease=True,
                        generation=0,
                        lease_id=replacement_lease,
                    ),
                    project_root=root,
                    expected_owner=self.OWNER,
                    expected_lease_id=replacement_lease,
                    expected_generation=0,
                )

    def test_new_generation_requires_exact_recovery_event(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_name:
            root = Path(temporary_name)
            path = root / "events.ndjson"
            append_event(path, self.event("44444444-4444-4444-8444-444444444444", "run_created", lease=False), project_root=root)
            append_event(
                path,
                self.event("55555555-5555-4555-8555-555555555555", "lease_acquired", lease=True),
                project_root=root,
                expected_owner=self.OWNER,
                expected_lease_id=self.LEASE_ID,
                expected_generation=0,
            )
            next_lease = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
            with self.assertRaisesRegex(ContractError, r"\[event_chain\].*recovery_started"):
                append_event(
                    path,
                    self.event(
                        "66666666-6666-4666-8666-666666666666",
                        "lease_acquired",
                        lease=True,
                        generation=1,
                        lease_id=next_lease,
                    ),
                    project_root=root,
                    expected_owner=self.OWNER,
                    expected_lease_id=next_lease,
                    expected_generation=1,
                )
            recovery = self.event(
                "77777777-7777-4777-8777-777777777777",
                "recovery_started",
                lease=True,
                generation=2,
                lease_id=next_lease,
            )
            recovery["data"]["previous_generation"] = 0
            recovery.update({"sequence": 3, "previous_event_digest": None, "event_digest": "d" * 64})
            with self.assertRaisesRegex(ContractError, r"\[invariant\].*exactly one"):
                validate_record("audit_event", recovery)

    def test_recovery_event_cannot_repeat_one_generation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_name:
            root = Path(temporary_name)
            path = root / "events.ndjson"
            append_event(path, self.event("44444444-4444-4444-8444-444444444444", "run_created", lease=False), project_root=root)
            append_event(
                path,
                self.event("55555555-5555-4555-8555-555555555555", "lease_acquired", lease=True),
                project_root=root,
                expected_owner=self.OWNER,
                expected_lease_id=self.LEASE_ID,
                expected_generation=0,
            )
            append_event(
                path,
                self.event("88888888-8888-4888-8888-888888888888", "run_failed", lease=True),
                project_root=root,
                expected_owner=self.OWNER,
                expected_lease_id=self.LEASE_ID,
                expected_generation=0,
            )
            next_lease = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
            append_event(
                path,
                self.event(
                    "66666666-6666-4666-8666-666666666666",
                    "recovery_started",
                    lease=True,
                    generation=1,
                    lease_id=next_lease,
                ),
                project_root=root,
                expected_owner=self.OWNER,
                expected_lease_id=next_lease,
                expected_generation=1,
            )
            with self.assertRaisesRegex(ContractError, r"\[event_chain\].*cannot repeat"):
                append_event(
                    path,
                    self.event(
                        "77777777-7777-4777-8777-777777777777",
                        "recovery_started",
                        lease=True,
                        generation=1,
                        lease_id=next_lease,
                    ),
                    project_root=root,
                    expected_owner=self.OWNER,
                    expected_lease_id=next_lease,
                    expected_generation=1,
                )

    def test_pre_lease_kill_recovery_establishes_only_generation_zero(self) -> None:
        def seeded_log(root: Path, *, halted: bool) -> tuple[Path, dict]:
            path = root / "events.ndjson"
            append_event(
                path,
                self.event("44444444-4444-4444-8444-444444444444", "run_created", lease=False),
                project_root=root,
            )
            previous = read_events(path, project_root=root)[-1]
            if halted:
                kill = self.event(
                    "55555555-5555-4555-8555-555555555555",
                    "kill_switch_detected",
                    lease=False,
                )
                kill["at"] = "2026-08-16T08:01:00Z"
                kill["projection"]["run"]["updated_at"] = kill["at"]
                previous = append_event(path, kill, project_root=root)
            return path, previous

        with tempfile.TemporaryDirectory() as temporary_name:
            root = Path(temporary_name)
            path, _ = seeded_log(root, halted=True)
            recovery = self.event(
                "66666666-6666-4666-8666-666666666666",
                "recovery_started",
                lease=True,
                generation=0,
            )
            recovery["at"] = "2026-08-16T08:02:00Z"
            recovery["data"]["previous_generation"] = None
            recovery["projection"]["run"]["updated_at"] = recovery["at"]
            recovery["projection"]["lease"]["acquired_at"] = recovery["at"]
            recovery["projection"]["lease"]["renewed_at"] = recovery["at"]
            accepted = append_event(
                path,
                recovery,
                project_root=root,
                expected_owner=self.OWNER,
                expected_lease_id=self.LEASE_ID,
                expected_generation=0,
            )
            self.assertEqual(0, accepted["data"]["new_generation"])

        invalid_cases = (
            (True, None, 1, r"initial lease generation must be zero"),
            (False, None, 0, r"the first lease event must be lease_acquired"),
            (True, 0, 1, r"initial lease generation must be zero"),
        )
        for halted, previous_generation, new_generation, message in invalid_cases:
            with self.subTest(
                halted=halted,
                previous_generation=previous_generation,
                new_generation=new_generation,
            ), tempfile.TemporaryDirectory() as temporary_name:
                root = Path(temporary_name)
                path, _ = seeded_log(root, halted=halted)
                recovery = self.event(
                    "77777777-7777-4777-8777-777777777777",
                    "recovery_started",
                    lease=True,
                    generation=new_generation,
                )
                recovery["at"] = "2026-08-16T08:02:00Z"
                recovery["data"]["previous_generation"] = previous_generation
                recovery["projection"]["run"]["updated_at"] = recovery["at"]
                recovery["projection"]["lease"]["acquired_at"] = recovery["at"]
                recovery["projection"]["lease"]["renewed_at"] = recovery["at"]
                with self.assertRaisesRegex(ContractError, message):
                    append_event(
                        path,
                        recovery,
                        project_root=root,
                        expected_owner=self.OWNER,
                        expected_lease_id=self.LEASE_ID,
                        expected_generation=new_generation,
                    )

    def test_lease_acquired_cannot_repeat_one_generation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_name:
            root = Path(temporary_name)
            path = root / "events.ndjson"
            append_event(path, self.event("44444444-4444-4444-8444-444444444444", "run_created", lease=False), project_root=root)
            append_event(
                path,
                self.event("55555555-5555-4555-8555-555555555555", "lease_acquired", lease=True),
                project_root=root,
                expected_owner=self.OWNER,
                expected_lease_id=self.LEASE_ID,
                expected_generation=0,
            )
            with self.assertRaisesRegex(ContractError, r"\[event_chain\].*use lease_renewed"):
                append_event(
                    path,
                    self.event("66666666-6666-4666-8666-666666666666", "lease_acquired", lease=True),
                    project_root=root,
                    expected_owner=self.OWNER,
                    expected_lease_id=self.LEASE_ID,
                    expected_generation=0,
                )
            self.assertEqual(2, len(read_events(path, project_root=root)))

    def test_lease_renewal_time_cannot_reverse_or_already_be_expired(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_name:
            root = Path(temporary_name)
            path = root / "events.ndjson"
            append_event(path, self.event("44444444-4444-4444-8444-444444444444", "run_created", lease=False), project_root=root)
            append_event(
                path,
                self.event("55555555-5555-4555-8555-555555555555", "lease_acquired", lease=True),
                project_root=root,
                expected_owner=self.OWNER,
                expected_lease_id=self.LEASE_ID,
                expected_generation=0,
            )
            reversed_renewal = self.event(
                "66666666-6666-4666-8666-666666666666",
                "lease_renewed",
                lease=True,
            )
            reversed_renewal["at"] = "2026-08-16T07:59:00Z"
            reversed_renewal["projection"]["run"]["updated_at"] = reversed_renewal["at"]
            reversed_renewal["projection"]["lease"]["renewed_at"] = reversed_renewal["at"]
            with self.assertRaisesRegex(ContractError, r"\[invariant\]"):
                append_event(
                    path,
                    reversed_renewal,
                    project_root=root,
                    expected_owner=self.OWNER,
                    expected_lease_id=self.LEASE_ID,
                    expected_generation=0,
                )
            expired_renewal = self.event(
                "77777777-7777-4777-8777-777777777777",
                "lease_renewed",
                lease=True,
            )
            expired_renewal["at"] = "2026-08-16T08:06:00Z"
            expired_renewal["projection"]["run"]["updated_at"] = expired_renewal["at"]
            expired_renewal["projection"]["lease"]["renewed_at"] = expired_renewal["at"]
            with self.assertRaisesRegex(ContractError, r"\[invariant\].*lease timestamps"):
                append_event(
                    path,
                    expired_renewal,
                    project_root=root,
                    expected_owner=self.OWNER,
                    expected_lease_id=self.LEASE_ID,
                    expected_generation=0,
                )
            self.assertEqual(2, len(read_events(path, project_root=root)))

    def test_failed_run_can_enter_audited_recovery(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_name:
            root = Path(temporary_name)
            path = root / "events.ndjson"
            append_event(path, self.event("44444444-4444-4444-8444-444444444444", "run_created", lease=False), project_root=root)
            append_event(
                path,
                self.event("55555555-5555-4555-8555-555555555555", "lease_acquired", lease=True),
                project_root=root,
                expected_owner=self.OWNER,
                expected_lease_id=self.LEASE_ID,
                expected_generation=0,
            )
            append_event(
                path,
                self.event("66666666-6666-4666-8666-666666666666", "run_failed", lease=True),
                project_root=root,
                expected_owner=self.OWNER,
                expected_lease_id=self.LEASE_ID,
                expected_generation=0,
            )
            with self.assertRaisesRegex(ContractError, r"\[event_chain\].*recovery_started"):
                append_event(
                    path,
                    self.event("88888888-8888-4888-8888-888888888888", "stage_started", lease=True),
                    project_root=root,
                    expected_owner=self.OWNER,
                    expected_lease_id=self.LEASE_ID,
                    expected_generation=0,
                )
            next_lease = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
            append_event(
                path,
                self.event(
                    "77777777-7777-4777-8777-777777777777",
                    "recovery_started",
                    lease=True,
                    generation=1,
                    lease_id=next_lease,
                ),
                project_root=root,
                expected_owner=self.OWNER,
                expected_lease_id=next_lease,
                expected_generation=1,
            )
            self.assertEqual(4, len(read_events(path, project_root=root)))

    def test_run_created_cannot_repeat_during_recovery(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_name:
            root = Path(temporary_name)
            path = root / "events.ndjson"
            append_event(path, self.event("44444444-4444-4444-8444-444444444444", "run_created", lease=False), project_root=root)
            append_event(
                path,
                self.event("55555555-5555-4555-8555-555555555555", "lease_acquired", lease=True),
                project_root=root,
                expected_owner=self.OWNER,
                expected_lease_id=self.LEASE_ID,
                expected_generation=0,
            )
            append_event(
                path,
                self.event("66666666-6666-4666-8666-666666666666", "run_failed", lease=True),
                project_root=root,
                expected_owner=self.OWNER,
                expected_lease_id=self.LEASE_ID,
                expected_generation=0,
            )
            with self.assertRaisesRegex(ContractError, r"\[event_chain\].*only as the first"):
                append_event(
                    path,
                    self.event("77777777-7777-4777-8777-777777777777", "run_created", lease=False),
                    project_root=root,
                )
            self.assertEqual(3, len(read_events(path, project_root=root)))

    def test_kill_switch_requires_fresh_generation_recovery(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_name:
            root = Path(temporary_name)
            path = root / "events.ndjson"
            append_event(path, self.event("44444444-4444-4444-8444-444444444444", "run_created", lease=False), project_root=root)
            append_event(
                path,
                self.event("55555555-5555-4555-8555-555555555555", "lease_acquired", lease=True),
                project_root=root,
                expected_owner=self.OWNER,
                expected_lease_id=self.LEASE_ID,
                expected_generation=0,
            )
            append_event(
                path,
                self.event("66666666-6666-4666-8666-666666666666", "kill_switch_detected", lease=True),
                project_root=root,
                expected_owner=self.OWNER,
                expected_lease_id=self.LEASE_ID,
                expected_generation=0,
            )
            with self.assertRaisesRegex(ContractError, r"\[event_chain\].*recovery_started"):
                append_event(
                    path,
                    self.event("77777777-7777-4777-8777-777777777777", "stage_started", lease=True),
                    project_root=root,
                    expected_owner=self.OWNER,
                    expected_lease_id=self.LEASE_ID,
                    expected_generation=0,
                )

    def test_completed_run_remains_terminal(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_name:
            root = Path(temporary_name)
            path = root / "events.ndjson"
            append_event(path, self.event("44444444-4444-4444-8444-444444444444", "run_created", lease=False), project_root=root)
            append_event(
                path,
                self.event("55555555-5555-4555-8555-555555555555", "lease_acquired", lease=True),
                project_root=root,
                expected_owner=self.OWNER,
                expected_lease_id=self.LEASE_ID,
                expected_generation=0,
            )
            append_event(
                path,
                self.event("66666666-6666-4666-8666-666666666666", "run_completed", lease=True),
                project_root=root,
                expected_owner=self.OWNER,
                expected_lease_id=self.LEASE_ID,
                expected_generation=0,
            )
            with self.assertRaisesRegex(ContractError, r"\[event_chain\].*terminal"):
                append_event(
                    path,
                    self.event(
                        "77777777-7777-4777-8777-777777777777",
                        "recovery_started",
                        lease=True,
                        generation=1,
                        lease_id="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
                    ),
                    project_root=root,
                    expected_owner=self.OWNER,
                    expected_lease_id="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
                    expected_generation=1,
                )

    def test_authority_revocation_is_lease_independent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_name:
            root = Path(temporary_name)
            path = root / "events.ndjson"
            append_event(path, self.event("44444444-4444-4444-8444-444444444444", "run_created", lease=False), project_root=root)
            append_event(path, self.event("88888888-8888-4888-8888-888888888888", "authority_revoked", lease=False), project_root=root)
            self.assertEqual("authority_revoked", read_events(path, project_root=root)[1]["type"])

    def test_lease_required_event_requires_caller_expectations(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_name:
            root = Path(temporary_name)
            path = root / "events.ndjson"
            append_event(path, self.event("44444444-4444-4444-8444-444444444444", "run_created", lease=False), project_root=root)
            with self.assertRaisesRegex(ContractError, r"\[lease_context\].*expected_owner"):
                append_event(
                    path,
                    self.event("99999999-9999-4999-8999-999999999999", "stage_started", lease=True),
                    project_root=root,
                )

    def test_kill_switch_control_event_can_be_lease_independent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_name:
            root = Path(temporary_name)
            path = root / "events.ndjson"
            append_event(path, self.event("44444444-4444-4444-8444-444444444444", "run_created", lease=False), project_root=root)
            append_event(
                path,
                self.event("99999999-9999-4999-8999-999999999999", "kill_switch_detected", lease=False),
                project_root=root,
            )
            events = read_events(path, project_root=root)
            self.assertEqual("halted_kill_switch", events[-1]["projection"]["run"]["status"])
            self.assertIsNone(events[-1]["lease_id"])

    def test_event_data_is_type_specific(self) -> None:
        event = self.event("99999999-9999-4999-8999-999999999999", "kill_switch_detected", lease=True)
        event.update({"sequence": 1, "previous_event_digest": None, "event_digest": "d" * 64, "data": {}})
        with self.assertRaisesRegex(ContractError, r"\[one_of\]"):
            validate_record("audit_event", event)

    def test_lease_payload_must_match_event_envelope(self) -> None:
        event = self.event("99999999-9999-4999-8999-999999999999", "lease_acquired", lease=True)
        event.update({"sequence": 1, "previous_event_digest": None, "event_digest": "d" * 64})
        event["data"]["lease_id"] = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
        with self.assertRaisesRegex(ContractError, r"\$\.data\.lease_id: \[invariant\]"):
            validate_record("audit_event", event)

    def test_audit_projection_aligns_with_envelope_and_owner(self) -> None:
        event = self.event("99999999-9999-4999-8999-999999999999", "lease_acquired", lease=True)
        event.update({"sequence": 2, "previous_event_digest": "a" * 64, "event_digest": "d" * 64})
        validate_record("audit_event", event, expected_owner=self.OWNER)

        missing = copy.deepcopy(event)
        del missing["projection"]
        with self.assertRaisesRegex(ContractError, r"\$: \[required\].*projection"):
            validate_record("audit_event", missing)

        wrong_run = copy.deepcopy(event)
        wrong_run["projection"]["run"]["run_id"] = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
        with self.assertRaisesRegex(ContractError, r"\$\.projection\.run\.run_id: \[invariant\]"):
            validate_record("audit_event", wrong_run)

        wrong_owner = copy.deepcopy(event)
        wrong_owner["projection"]["lease"]["owner"]["actor"] = "other-agent"
        with self.assertRaisesRegex(ContractError, r"\$\.projection\.lease\.owner: \[owner\]"):
            validate_record("audit_event", wrong_owner)

    def test_audit_projection_chain_is_immutable_and_interval_bounded(self) -> None:
        created = self.event("44444444-4444-4444-8444-444444444444", "run_created", lease=False)
        created.update({"sequence": 1, "previous_event_digest": None, "event_digest": "a" * 64})
        acquired = self.event("55555555-5555-4555-8555-555555555555", "lease_acquired", lease=True)
        acquired.update({"sequence": 2, "previous_event_digest": "a" * 64, "event_digest": "b" * 64})
        validate_record("audit_event", acquired, previous=created)

        changed = copy.deepcopy(acquired)
        changed["projection"]["run"]["asset"]["name"] = "different-asset"
        with self.assertRaisesRegex(ContractError, r"\$\.projection\.run\.asset: \[invariant\]"):
            validate_record("audit_event", changed, previous=created)

        heartbeat = self.event("66666666-6666-4666-8666-666666666666", "heartbeat", lease=True)
        heartbeat["at"] = "2026-08-16T08:01:00Z"
        heartbeat["projection"]["run"]["updated_at"] = heartbeat["at"]
        heartbeat["projection"]["run"]["last_heartbeat_at"] = heartbeat["at"]
        heartbeat["projection"]["run"]["usage"]["duration_seconds"] = 60
        heartbeat["projection"]["lease"]["renewed_at"] = heartbeat["at"]
        heartbeat.update({"sequence": 3, "previous_event_digest": "b" * 64, "event_digest": "c" * 64})
        validate_record("audit_event", heartbeat, previous=acquired)

        overcounted = copy.deepcopy(heartbeat)
        overcounted["projection"]["run"]["usage"]["duration_seconds"] = 61
        with self.assertRaisesRegex(ContractError, r"complete validated active-lease interval"):
            validate_record("audit_event", overcounted, previous=acquired)

    def test_pending_operation_must_complete_exactly_and_is_not_replayable(self) -> None:
        acquired = self.event("55555555-5555-4555-8555-555555555555", "lease_acquired", lease=True)
        acquired.update({"sequence": 2, "previous_event_digest": "a" * 64, "event_digest": "b" * 64})
        operation = {
            "operation_id": "77777777-7777-4777-8777-777777777777",
            "completion_event_type": "stage_completed",
            "completion_data": {"stage": "test", "outcome": "passed"},
            "effect": "local",
            "reservation": operation_reservation(mutations=1),
        }
        intended = {
            **copy.deepcopy(acquired),
            "event_id": "66666666-6666-4666-8666-666666666666",
            "sequence": 3,
            "type": "operation_intended",
            "data": copy.deepcopy(operation),
            "previous_event_digest": "b" * 64,
            "event_digest": "c" * 64,
        }
        intended["projection"]["pending_operation"] = copy.deepcopy(operation)
        intended["projection"]["run"]["usage"]["mutations"] += 1
        validate_record("audit_event", intended, previous=acquired)

        false_external = copy.deepcopy(intended)
        false_external["data"]["effect"] = "external"
        false_external["projection"]["pending_operation"]["effect"] = "external"
        with self.assertRaisesRegex(ContractError, r"external exactly when external-action usage is reserved"):
            validate_record("audit_event", false_external, previous=acquired)

        completed = {
            **copy.deepcopy(intended),
            "event_id": "88888888-8888-4888-8888-888888888888",
            "sequence": 4,
            "type": "stage_completed",
            "data": copy.deepcopy(operation["completion_data"]),
            "previous_event_digest": "c" * 64,
            "event_digest": "d" * 64,
        }
        completed["projection"]["pending_operation"] = None
        validate_record("audit_event", completed, previous=intended)

        wrong_result = copy.deepcopy(completed)
        wrong_result["data"]["outcome"] = "blocked"
        with self.assertRaisesRegex(ContractError, r"must exactly match the pending completion data"):
            validate_record("audit_event", wrong_result, previous=intended)

        ordinary = copy.deepcopy(completed)
        ordinary["event_id"] = "99999999-9999-4999-8999-999999999999"
        ordinary["sequence"] = 5
        ordinary["previous_event_digest"] = "d" * 64
        ordinary["event_digest"] = "e" * 64
        validate_record("audit_event", ordinary, previous=completed)

    def test_ordinary_lease_event_at_expiry_is_rejected(self) -> None:
        acquired = self.event("55555555-5555-4555-8555-555555555555", "lease_acquired", lease=True)
        acquired.update({"sequence": 2, "previous_event_digest": "a" * 64, "event_digest": "b" * 64})
        route = copy.deepcopy(acquired)
        route.update(
            {
                "event_id": "66666666-6666-4666-8666-666666666666",
                "sequence": 3,
                "type": "route_selected",
                "at": acquired["projection"]["lease"]["expires_at"],
                "data": {
                    "capability": "lifecycle.test",
                    "selected_provider": "bundled-test",
                    "selected_source": "bundled",
                },
                "previous_event_digest": "b" * 64,
                "event_digest": "c" * 64,
            }
        )
        route["projection"]["run"]["updated_at"] = route["at"]
        route["projection"]["run"]["usage"]["duration_seconds"] = 300
        with self.assertRaisesRegex(ContractError, r"event requires a lease that was valid"):
            validate_record("audit_event", route, previous=acquired)

    def test_pending_operation_reconciliation_is_fail_closed_by_effect(self) -> None:
        acquired = self.event("55555555-5555-4555-8555-555555555555", "lease_acquired", lease=True)
        acquired.update({"sequence": 2, "previous_event_digest": "a" * 64, "event_digest": "b" * 64})
        for effect, expected_status, expected_code in (
            ("local", "failed", "operation_outcome_unknown"),
            ("external", "waiting_external", "external_operation_outcome_unknown"),
        ):
            with self.subTest(effect=effect):
                operation = {
                    "operation_id": "77777777-7777-4777-8777-777777777777",
                    "completion_event_type": "evidence_recorded",
                    "completion_data": {
                        "evidence_id": "99999999-9999-4999-8999-999999999999",
                        "outcome": "passed",
                    },
                    "effect": effect,
                    "reservation": operation_reservation(
                        mutations=0 if effect == "external" else 1,
                        external_actions=1 if effect == "external" else 0,
                    ),
                }
                intended = copy.deepcopy(acquired)
                intended.update(
                    {
                        "event_id": "66666666-6666-4666-8666-666666666666",
                        "sequence": 3,
                        "type": "operation_intended",
                        "data": copy.deepcopy(operation),
                        "previous_event_digest": "b" * 64,
                        "event_digest": "c" * 64,
                    }
                )
                intended["projection"]["pending_operation"] = copy.deepcopy(operation)
                if effect == "external":
                    intended["projection"]["run"]["usage"]["external_actions"] += 1
                validate_record("audit_event", intended, previous=acquired)

                reconciled = copy.deepcopy(intended)
                reconciled.update(
                    {
                        "event_id": "88888888-8888-4888-8888-888888888888",
                        "sequence": 4,
                        "type": "operation_reconciled",
                        "data": {
                            "operation_id": operation["operation_id"],
                            "effect": effect,
                            "outcome": "unknown",
                        },
                        "previous_event_digest": "c" * 64,
                        "event_digest": "d" * 64,
                    }
                )
                reconciled["projection"]["pending_operation"] = None
                reconciled["projection"]["run"]["status"] = expected_status
                reconciled["projection"]["run"]["terminal_reason"] = {
                    "code": expected_code,
                    "explanation": "Callback outcome is unknown after interruption.",
                }
                validate_record("audit_event", reconciled, previous=intended)

                mismatched = copy.deepcopy(reconciled)
                mismatched_effect = "external" if effect == "local" else "local"
                mismatched["data"]["effect"] = mismatched_effect
                mismatched["projection"]["run"]["status"] = (
                    "waiting_external" if mismatched_effect == "external" else "failed"
                )
                mismatched["projection"]["run"]["terminal_reason"]["code"] = (
                    "external_operation_outcome_unknown"
                    if mismatched_effect == "external"
                    else "operation_outcome_unknown"
                )
                with self.assertRaisesRegex(ContractError, r"must match the pending operation effect"):
                    validate_record("audit_event", mismatched, previous=intended)

    def test_issue_transition_and_budget_reached_payloads_are_semantic(self) -> None:
        base = {
            "schema_version": "1.0",
            "event_id": "99999999-9999-4999-8999-999999999999",
            "sequence": 1,
            "run_id": "11111111-1111-4111-8111-111111111111",
            "lease_id": self.LEASE_ID,
            "lease_generation": 0,
            "actor": self.OWNER,
            "at": "2026-08-16T08:00:00Z",
            "previous_event_digest": None,
            "event_digest": "d" * 64,
        }
        base["projection"] = audit_projection(
            "issue_transitioned",
            {"issue_id": "88888888-8888-4888-8888-888888888888", "from_status": "open", "to_status": "closed"},
            self.OWNER,
            lease_id=self.LEASE_ID,
            generation=0,
        )
        issue = {**base, "type": "issue_transitioned", "data": {
            "issue_id": "88888888-8888-4888-8888-888888888888",
            "from_status": "open",
            "to_status": "closed",
        }}
        with self.assertRaisesRegex(ContractError, r"\[transition\].*open.*closed"):
            validate_record("audit_event", issue)

        budget = {**base, "type": "budget_reached", "data": {
            "budget": "max_mutations",
            "stage": None,
            "limit": 100,
            "observed": 1,
        }}
        budget["projection"] = audit_projection(
            "budget_reached",
            budget["data"],
            self.OWNER,
            lease_id=self.LEASE_ID,
            generation=0,
        )
        with self.assertRaisesRegex(ContractError, r"\$\.data\.observed: \[invariant\]"):
            validate_record("audit_event", budget)

        attempts = copy.deepcopy(budget)
        attempts["data"] = {"budget": "max_stage_attempts", "stage": "test", "limit": 3, "observed": 3}
        attempts["projection"] = audit_projection(
            "budget_reached",
            attempts["data"],
            self.OWNER,
            lease_id=self.LEASE_ID,
            generation=0,
        )
        validate_record("audit_event", attempts)
        attempts["data"]["stage"] = None
        with self.assertRaisesRegex(ContractError, r"\$\.data\.stage: \[invariant\]"):
            validate_record("audit_event", attempts)

    def test_event_target_symlink_is_rejected_before_resolution(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_name:
            root = Path(temporary_name)
            victim = root / "victim.ndjson"
            victim.write_bytes(b"")
            victim.chmod(0o600)
            target = root / "events.ndjson"
            target.symlink_to(victim)
            with self.assertRaisesRegex(ContractError, r"\[unsafe_path\].*symlink"):
                append_event(
                    target,
                    self.event("44444444-4444-4444-8444-444444444444", "run_created", lease=False),
                    project_root=root,
                )
            self.assertEqual(b"", victim.read_bytes())

    def test_event_target_hard_link_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as project_name, tempfile.TemporaryDirectory() as outside_name:
            root = Path(project_name)
            victim = Path(outside_name) / "victim.ndjson"
            victim.write_bytes(b"")
            victim.chmod(0o600)
            target = root / "events.ndjson"
            os.link(victim, target)
            with self.assertRaisesRegex(ContractError, r"\[unsafe_path\].*hard-linked"):
                append_event(
                    target,
                    self.event("44444444-4444-4444-8444-444444444444", "run_created", lease=False),
                    project_root=root,
                )
            self.assertEqual(b"", victim.read_bytes())

    def test_parent_swap_cannot_redirect_event_append(self) -> None:
        with tempfile.TemporaryDirectory() as project_name, tempfile.TemporaryDirectory() as outside_name:
            root = Path(project_name)
            state_root = root / ".the-loop"
            path = state_root / "runs" / "run-1" / "events.ndjson"
            append_event(
                path,
                self.event("44444444-4444-4444-8444-444444444444", "run_created", lease=False),
                project_root=root,
            )

            outside = Path(outside_name)
            outside_target = outside / "runs" / "run-1" / "events.ndjson"
            outside_target.parent.mkdir(parents=True)
            outside_target.write_bytes(b"")
            outside_target.chmod(0o600)
            outside_before = outside_target.read_bytes()
            held = root / ".the-loop-held"

            def swap_parent() -> None:
                state_root.rename(held)
                state_root.symlink_to(outside, target_is_directory=True)

            try:
                with self.assertRaisesRegex(ContractError, r"\[unsafe_path\].*parent changed"):
                    append_event(
                        path,
                        self.event("99999999-9999-4999-8999-999999999999", "lease_acquired", lease=True),
                        project_root=root,
                        expected_owner=self.OWNER,
                        expected_lease_id=self.LEASE_ID,
                        expected_generation=0,
                        _before_open=swap_parent,
                    )
                self.assertEqual(outside_before, outside_target.read_bytes())
                self.assertEqual(
                    1,
                    len(read_events(held / "runs" / "run-1" / "events.ndjson", project_root=root)),
                )
            finally:
                if state_root.is_symlink():
                    state_root.unlink()

    def test_parent_swap_inside_event_open_reports_failure(self) -> None:
        with tempfile.TemporaryDirectory() as project_name, tempfile.TemporaryDirectory() as outside_name:
            root = Path(project_name)
            state_root = root / ".the-loop"
            path = state_root / "runs" / "run-1" / "events.ndjson"
            append_event(
                path,
                self.event("44444444-4444-4444-8444-444444444444", "run_created", lease=False),
                project_root=root,
            )
            outside = Path(outside_name)
            outside_target = outside / "runs" / "run-1" / "events.ndjson"
            outside_target.parent.mkdir(parents=True)
            outside_target.write_bytes(b"")
            outside_target.chmod(0o600)
            held = root / ".the-loop-held"
            real_open = os.open
            swapped = False

            def swap_during_open(name: object, flags: int, mode: int = 0o777, *, dir_fd: int | None = None) -> int:
                nonlocal swapped
                if name == path.name and flags & os.O_APPEND and not swapped:
                    swapped = True
                    state_root.rename(held)
                    state_root.symlink_to(outside, target_is_directory=True)
                return real_open(name, flags, mode, dir_fd=dir_fd)

            try:
                with mock.patch("the_loop.state.os.open", side_effect=swap_during_open):
                    with self.assertRaisesRegex(ContractError, r"\[unsafe_path\].*canonical event log changed"):
                        append_event(
                            path,
                            self.event("99999999-9999-4999-8999-999999999999", "lease_acquired", lease=True),
                            project_root=root,
                            expected_owner=self.OWNER,
                            expected_lease_id=self.LEASE_ID,
                            expected_generation=0,
                        )
                self.assertEqual(b"", outside_target.read_bytes())
                self.assertEqual(
                    1,
                    len(read_events(held / "runs" / "run-1" / "events.ndjson", project_root=root)),
                )
            finally:
                if state_root.is_symlink():
                    state_root.unlink()

    def test_existing_event_log_disappearance_before_read_is_not_empty_history(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_name:
            root = Path(temporary_name)
            path = root / "events.ndjson"
            detached = root / "events-detached.ndjson"
            append_event(
                path,
                self.event("44444444-4444-4444-8444-444444444444", "run_created", lease=False),
                project_root=root,
            )
            before = path.read_bytes()
            real_open = os.open
            swapped = False

            def remove_before_read_open(name: object, flags: int, mode: int = 0o777, *, dir_fd: int | None = None) -> int:
                nonlocal swapped
                if name == path.name and not flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT) and not swapped:
                    swapped = True
                    path.rename(detached)
                return real_open(name, flags, mode, dir_fd=dir_fd)

            with mock.patch("the_loop.state.os.open", side_effect=remove_before_read_open):
                with self.assertRaisesRegex(ContractError, r"\[unsafe_path\].*disappeared before read"):
                    read_events(path, project_root=root)
            self.assertFalse(path.exists())
            self.assertEqual(before, detached.read_bytes())

    def test_intermediate_directory_disappearance_cannot_hide_or_split_history(self) -> None:
        for operation in ("read", "append"):
            with self.subTest(operation=operation), tempfile.TemporaryDirectory() as temporary_name:
                root = Path(temporary_name)
                state_root = root / ".the-loop"
                path = state_root / "runs" / "run-1" / "events.ndjson"
                detached = root / ".the-loop-detached"
                append_event(
                    path,
                    self.event("44444444-4444-4444-8444-444444444444", "run_created", lease=False),
                    project_root=root,
                )
                before = path.read_bytes()
                real_open = os.open
                swapped = False

                def remove_before_directory_open(
                    name: object,
                    flags: int,
                    mode: int = 0o777,
                    *,
                    dir_fd: int | None = None,
                ) -> int:
                    nonlocal swapped
                    if name == state_root.name and flags & getattr(os, "O_DIRECTORY", 0) and not swapped:
                        swapped = True
                        state_root.rename(detached)
                    return real_open(name, flags, mode, dir_fd=dir_fd)

                with mock.patch("the_loop.state.os.open", side_effect=remove_before_directory_open):
                    with self.assertRaisesRegex(ContractError, r"\[unsafe_path\].*directory disappeared before open"):
                        if operation == "read":
                            read_events(path, project_root=root)
                        else:
                            append_event(
                                path,
                                self.event("55555555-5555-4555-8555-555555555555", "run_created", lease=False),
                                project_root=root,
                            )
                self.assertFalse(state_root.exists())
                self.assertEqual(before, (detached / "runs" / "run-1" / "events.ndjson").read_bytes())

    def test_observed_project_root_disappearance_is_not_empty_history(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_name:
            base = Path(temporary_name)
            root = base / "project"
            root.mkdir()
            resolved_root = root.resolve()
            path = root / ".the-loop" / "events.ndjson"
            detached = base / "project-detached"
            append_event(
                path,
                self.event("44444444-4444-4444-8444-444444444444", "run_created", lease=False),
                project_root=root,
            )
            before = path.read_bytes()
            real_open = os.open
            swapped = False

            def remove_before_root_open(
                name: object,
                flags: int,
                mode: int = 0o777,
                *,
                dir_fd: int | None = None,
            ) -> int:
                nonlocal swapped
                if Path(name) == resolved_root and not swapped:
                    swapped = True
                    root.rename(detached)
                return real_open(name, flags, mode, dir_fd=dir_fd)

            with mock.patch("the_loop.state.os.open", side_effect=remove_before_root_open):
                with self.assertRaisesRegex(ContractError, r"\[unsafe_path\].*project root disappeared before open"):
                    read_events(path, project_root=root)
            self.assertFalse(root.exists())
            self.assertEqual(before, (detached / ".the-loop" / "events.ndjson").read_bytes())

    def test_path_snapshot_prevents_root_parent_and_target_rebaselining(self) -> None:
        for boundary in ("root", "intermediate", "target"):
            for operation in ("read", "append"):
                with self.subTest(boundary=boundary, operation=operation), tempfile.TemporaryDirectory() as temporary_name:
                    base = Path(temporary_name)
                    root = base / "project"
                    root.mkdir()
                    state_root = root / ".the-loop"
                    path = state_root / "events.ndjson"
                    append_event(
                        path,
                        self.event("44444444-4444-4444-8444-444444444444", "run_created", lease=False),
                        project_root=root,
                    )
                    before = path.read_bytes()
                    real_open_parent = state_module._open_state_parent
                    swapped = False
                    original_path: Path

                    def swap_after_snapshot(snapshot: object, **kwargs: object) -> object:
                        nonlocal swapped, original_path
                        if not swapped:
                            swapped = True
                            if boundary == "root":
                                detached = base / "project-detached"
                                root.rename(detached)
                                root.mkdir()
                                original_path = detached / ".the-loop" / "events.ndjson"
                            elif boundary == "intermediate":
                                detached = root / ".the-loop-detached"
                                state_root.rename(detached)
                                state_root.mkdir(mode=0o700)
                                original_path = detached / "events.ndjson"
                            else:
                                detached = state_root / "events-detached.ndjson"
                                path.rename(detached)
                                path.write_bytes(b"")
                                path.chmod(0o600)
                                original_path = detached
                        return real_open_parent(snapshot, **kwargs)

                    with mock.patch("the_loop.state._open_state_parent", side_effect=swap_after_snapshot):
                        with self.assertRaisesRegex(ContractError, r"\[unsafe_path\].*(changed|disappeared|appeared)"):
                            if operation == "read":
                                read_events(path, project_root=root)
                            else:
                                append_event(
                                    path,
                                    self.event("55555555-5555-4555-8555-555555555555", "run_created", lease=False),
                                    project_root=root,
                                )
                    self.assertTrue(swapped)
                    self.assertEqual(before, original_path.read_bytes())
                    if path.exists():
                        self.assertEqual(b"", path.read_bytes())

    def test_intermediate_directory_appearance_during_create_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_name:
            root = Path(temporary_name)
            path = root / ".the-loop" / "runs" / "run-1" / "events.ndjson"
            real_mkdir = os.mkdir
            appeared = False

            def appear_before_directory_create(
                name: object,
                mode: int = 0o777,
                *,
                dir_fd: int | None = None,
            ) -> None:
                nonlocal appeared
                if name == ".the-loop" and not appeared:
                    appeared = True
                    real_mkdir(name, mode, dir_fd=dir_fd)
                real_mkdir(name, mode, dir_fd=dir_fd)

            with mock.patch("the_loop.state.os.mkdir", side_effect=appear_before_directory_create):
                with self.assertRaisesRegex(ContractError, r"\[unsafe_path\].*directory appeared before creation"):
                    append_event(
                        path,
                        self.event("44444444-4444-4444-8444-444444444444", "run_created", lease=False),
                        project_root=root,
                    )
            self.assertFalse(path.exists())

    def test_existing_event_log_disappearance_before_append_cannot_split_history(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_name:
            root = Path(temporary_name)
            path = root / "events.ndjson"
            detached = root / "events-detached.ndjson"
            append_event(
                path,
                self.event("44444444-4444-4444-8444-444444444444", "run_created", lease=False),
                project_root=root,
            )
            before = path.read_bytes()
            real_open = os.open
            swapped = False

            def remove_before_append_open(name: object, flags: int, mode: int = 0o777, *, dir_fd: int | None = None) -> int:
                nonlocal swapped
                if name == path.name and flags & os.O_APPEND and not swapped:
                    swapped = True
                    path.rename(detached)
                return real_open(name, flags, mode, dir_fd=dir_fd)

            with mock.patch("the_loop.state.os.open", side_effect=remove_before_append_open):
                with self.assertRaisesRegex(ContractError, r"\[unsafe_path\].*disappeared before append"):
                    append_event(
                        path,
                        self.event("55555555-5555-4555-8555-555555555555", "run_created", lease=False),
                        project_root=root,
                    )
            self.assertFalse(path.exists())
            self.assertEqual(before, detached.read_bytes())

    def test_absent_event_log_appearance_before_read_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_name:
            root = Path(temporary_name)
            path = root / "events.ndjson"
            real_open = os.open
            appeared = False

            def appear_before_read_open(name: object, flags: int, mode: int = 0o777, *, dir_fd: int | None = None) -> int:
                nonlocal appeared
                if name == path.name and not flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT) and not appeared:
                    appeared = True
                    path.write_bytes(b"")
                    path.chmod(0o600)
                return real_open(name, flags, mode, dir_fd=dir_fd)

            with mock.patch("the_loop.state.os.open", side_effect=appear_before_read_open):
                with self.assertRaisesRegex(ContractError, r"\[unsafe_path\].*changed before read"):
                    read_events(path, project_root=root)

    def test_absent_event_log_appearance_before_create_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_name:
            root = Path(temporary_name)
            path = root / "events.ndjson"
            real_open = os.open
            appeared = False

            def appear_before_create(name: object, flags: int, mode: int = 0o777, *, dir_fd: int | None = None) -> int:
                nonlocal appeared
                if name == path.name and flags & os.O_CREAT and not appeared:
                    appeared = True
                    path.write_bytes(b"")
                    path.chmod(0o600)
                return real_open(name, flags, mode, dir_fd=dir_fd)

            with mock.patch("the_loop.state.os.open", side_effect=appear_before_create):
                with self.assertRaisesRegex(ContractError, r"\[unsafe_path\].*appeared before creation"):
                    append_event(
                        path,
                        self.event("44444444-4444-4444-8444-444444444444", "run_created", lease=False),
                        project_root=root,
                    )
            self.assertEqual(b"", path.read_bytes())

    @unittest.skipIf(fcntl is None, "fcntl locking contract requires POSIX")
    def test_target_replacement_after_lock_reports_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_name:
            root = Path(temporary_name)
            path = root / "events.ndjson"
            append_event(
                path,
                self.event("44444444-4444-4444-8444-444444444444", "run_created", lease=False),
                project_root=root,
            )
            detached = root / "events-detached.ndjson"
            real_flock = fcntl.flock
            replaced = False

            def replace_after_lock(descriptor: int, operation: int) -> object:
                nonlocal replaced
                result = real_flock(descriptor, operation)
                if operation == fcntl.LOCK_EX and not replaced:
                    replaced = True
                    path.rename(detached)
                    path.write_bytes(b"")
                    path.chmod(0o600)
                return result

            with mock.patch("the_loop.state.fcntl.flock", side_effect=replace_after_lock):
                with self.assertRaisesRegex(ContractError, r"\[unsafe_path\].*canonical event log changed"):
                    append_event(
                        path,
                        self.event("99999999-9999-4999-8999-999999999999", "lease_acquired", lease=True),
                        project_root=root,
                        expected_owner=self.OWNER,
                        expected_lease_id=self.LEASE_ID,
                        expected_generation=0,
                    )
            self.assertEqual(b"", path.read_bytes())
            self.assertEqual(1, len(read_events(detached, project_root=root)))

    def test_partial_append_failure_restores_exact_prior_log(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_name:
            root = Path(temporary_name)
            path = root / "events.ndjson"
            append_event(
                path,
                self.event("44444444-4444-4444-8444-444444444444", "run_created", lease=False),
                project_root=root,
            )
            before = path.read_bytes()
            real_write = os.write
            calls = 0

            def partial_then_fail(descriptor: int, data: bytes) -> int:
                nonlocal calls
                calls += 1
                if calls == 1:
                    return real_write(descriptor, data[: max(1, len(data) // 2)])
                raise OSError("synthetic append failure")

            with mock.patch("the_loop.state.os.write", side_effect=partial_then_fail):
                with self.assertRaisesRegex(OSError, "synthetic append failure"):
                    append_event(
                        path,
                        self.event("99999999-9999-4999-8999-999999999999", "authority_granted", lease=False),
                        project_root=root,
                    )
            self.assertEqual(before, path.read_bytes())
            self.assertEqual(1, len(read_events(path, project_root=root)))

    def test_late_hard_link_is_detected_and_append_is_rolled_back(self) -> None:
        with tempfile.TemporaryDirectory() as project_name, tempfile.TemporaryDirectory() as outside_name:
            root = Path(project_name)
            path = root / "events.ndjson"
            append_event(
                path,
                self.event("44444444-4444-4444-8444-444444444444", "run_created", lease=False),
                project_root=root,
            )
            before = path.read_bytes()
            alias = Path(outside_name) / "events-alias.ndjson"
            real_write = os.write
            linked = False

            def link_during_write(descriptor: int, data: bytes) -> int:
                nonlocal linked
                if not linked:
                    linked = True
                    os.link(path, alias)
                return real_write(descriptor, data)

            with mock.patch("the_loop.state.os.write", side_effect=link_during_write):
                with self.assertRaisesRegex(ContractError, r"\[unsafe_path\].*hard-linked"):
                    append_event(
                        path,
                        self.event("99999999-9999-4999-8999-999999999999", "authority_granted", lease=False),
                        project_root=root,
                    )
            self.assertEqual(before, path.read_bytes())
            self.assertEqual(before, alias.read_bytes())

    def test_read_revalidates_replacement_permissions_after_open(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_name:
            root = Path(temporary_name)
            path = root / "events.ndjson"
            append_event(
                path,
                self.event("44444444-4444-4444-8444-444444444444", "run_created", lease=False),
                project_root=root,
            )
            replacement_bytes = path.read_bytes()
            detached = root / "events-detached.ndjson"
            real_open = os.open
            swapped = False

            def swap_before_read_open(name: object, flags: int, mode: int = 0o777, *, dir_fd: int | None = None) -> int:
                nonlocal swapped
                if name == path.name and not flags & (os.O_WRONLY | os.O_RDWR) and not swapped:
                    swapped = True
                    path.rename(detached)
                    path.write_bytes(replacement_bytes)
                    path.chmod(0o644)
                return real_open(name, flags, mode, dir_fd=dir_fd)

            with mock.patch("the_loop.state.os.open", side_effect=swap_before_read_open):
                with self.assertRaisesRegex(ContractError, r"\[permissions\]"):
                    read_events(path, project_root=root)
            self.assertEqual(0o644, path.stat().st_mode & 0o777)

    @unittest.skipIf(fcntl is None, "fcntl locking contract requires POSIX")
    def test_reader_waits_for_exclusive_append_to_finish(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_name:
            root = Path(temporary_name)
            path = root / "events.ndjson"
            append_event(
                path,
                self.event("44444444-4444-4444-8444-444444444444", "run_created", lease=False),
                project_root=root,
            )
            partial_written = threading.Event()
            release_writer = threading.Event()
            reader_done = threading.Event()
            errors: list[BaseException] = []
            observed: list[dict] = []
            real_write = os.write
            split_once = False

            def split_write(descriptor: int, data: bytes) -> int:
                nonlocal split_once
                if not split_once and len(data) > 1:
                    split_once = True
                    count = real_write(descriptor, data[: len(data) // 2])
                    partial_written.set()
                    if not release_writer.wait(timeout=2):
                        raise TimeoutError("reader-lock test did not release writer")
                    return count
                return real_write(descriptor, data)

            def write_event() -> None:
                try:
                    with mock.patch("the_loop.state.os.write", side_effect=split_write):
                        append_event(
                            path,
                            self.event("99999999-9999-4999-8999-999999999999", "lease_acquired", lease=True),
                            project_root=root,
                            expected_owner=self.OWNER,
                            expected_lease_id=self.LEASE_ID,
                            expected_generation=0,
                        )
                except BaseException as exc:
                    errors.append(exc)

            def read_log() -> None:
                try:
                    observed.extend(read_events(path, project_root=root))
                except BaseException as exc:
                    errors.append(exc)
                finally:
                    reader_done.set()

            writer = threading.Thread(target=write_event)
            writer.start()
            self.assertTrue(partial_written.wait(timeout=2))
            reader = threading.Thread(target=read_log)
            reader.start()
            self.assertFalse(reader_done.wait(timeout=0.05))
            release_writer.set()
            writer.join(timeout=2)
            reader.join(timeout=2)
            self.assertFalse(writer.is_alive())
            self.assertFalse(reader.is_alive())
            self.assertEqual([], errors)
            self.assertEqual(2, len(observed))

    @unittest.skipIf(fcntl is None, "fcntl locking contract requires POSIX")
    @unittest.skipUnless(Path("/dev/fd").exists() or Path("/proc/self/fd").exists(), "fd accounting unavailable")
    def test_unlock_failure_hook_cannot_create_false_failure_or_fd_leak(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_name:
            root = Path(temporary_name)
            path = root / "events.ndjson"
            fd_root = Path("/dev/fd") if Path("/dev/fd").exists() else Path("/proc/self/fd")
            before = len(list(fd_root.iterdir()))
            real_flock = fcntl.flock

            def fail_explicit_unlock(descriptor: int, operation: int) -> object:
                if operation == fcntl.LOCK_UN:
                    raise OSError("synthetic unlock failure")
                return real_flock(descriptor, operation)

            with mock.patch("the_loop.state.fcntl.flock", side_effect=fail_explicit_unlock):
                appended = append_event(
                    path,
                    self.event("44444444-4444-4444-8444-444444444444", "run_created", lease=False),
                    project_root=root,
                )
                observed = read_events(path, project_root=root)
            after = len(list(fd_root.iterdir()))
            self.assertEqual(appended["event_id"], observed[0]["event_id"])
            self.assertEqual(before, after)

    def test_append_rejects_insecure_existing_event_log(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_name:
            root = Path(temporary_name)
            path = root / "events.ndjson"
            path.write_bytes(b"")
            path.chmod(0o644)
            with self.assertRaisesRegex(ContractError, r"\[permissions\]"):
                append_event(
                    path,
                    self.event("44444444-4444-4444-8444-444444444444", "run_created", lease=False),
                    project_root=root,
                )
            self.assertEqual(b"", path.read_bytes())

    def test_every_audit_event_type_has_a_valid_payload_contract(self) -> None:
        grant_id = "22222222-2222-4222-8222-222222222222"
        item_id = "99999999-9999-4999-8999-999999999999"
        payloads = {
            "run_created": {"objective": "Synthetic fixture"},
            "authority_granted": {"grant_id": grant_id, "level": "bounded"},
            "authority_revoked": {
                "grant_id": grant_id,
                "revoked_at": "2026-08-16T08:00:00Z",
                "revoked_by": "Moses",
            },
            "lease_acquired": {"lease_id": self.LEASE_ID, "generation": 0, "expires_at": "2026-08-16T08:05:00Z"},
            "lease_renewed": {"lease_id": self.LEASE_ID, "generation": 0, "expires_at": "2026-08-16T08:05:00Z"},
            "route_selected": {"capability": "lifecycle.test", "selected_provider": "bundled:test", "selected_source": "bundled"},
            "stage_started": {"stage": "test"},
            "heartbeat": {"stage": "test", "status": "active"},
            "evidence_recorded": {"evidence_id": item_id, "outcome": "passed"},
            "issue_opened": {"issue_id": item_id, "severity": "high"},
            "issue_transitioned": {"issue_id": item_id, "from_status": "open", "to_status": "acknowledged"},
            "stage_completed": {"stage": "test", "outcome": "passed"},
            "operation_intended": {
                "operation_id": "77777777-7777-4777-8777-777777777777",
                "completion_event_type": "stage_completed",
                "completion_data": {"stage": "test", "outcome": "passed"},
                "effect": "local",
                "reservation": operation_reservation(),
            },
            "operation_reconciled": {
                "operation_id": "77777777-7777-4777-8777-777777777777",
                "effect": "local",
                "outcome": "unknown",
            },
            "budget_reached": {"budget": "max_mutations", "stage": None, "limit": 100, "observed": 100},
            "kill_switch_detected": {"path": ".the-loop/STOP"},
            "recovery_started": {"previous_generation": 0, "new_generation": 1, "reason": "Expired lease"},
            "run_completed": {"reason": "Done gate passed"},
            "run_failed": {"reason": "Test gate failed"},
            "run_cancelled": {"reason": "User cancelled"},
        }
        for index, (event_type, data) in enumerate(payloads.items(), start=1):
            with self.subTest(event_type=event_type):
                lease_optional = event_type in {"run_created", "authority_granted", "authority_revoked"}
                event = {
                    "schema_version": "1.0",
                    "event_id": f"{index:08x}-0000-4000-8000-000000000000",
                    "sequence": index,
                    "run_id": "11111111-1111-4111-8111-111111111111",
                    "lease_id": None if lease_optional else self.LEASE_ID,
                    "lease_generation": None if lease_optional else 0,
                    "type": event_type,
                    "actor": self.OWNER,
                    "at": "2026-08-16T08:00:00Z",
                    "data": data,
                    "previous_event_digest": None,
                    "event_digest": "d" * 64,
                }
                if event_type == "recovery_started":
                    event["lease_generation"] = data["new_generation"]
                event["projection"] = audit_projection(
                    event_type,
                    data,
                    self.OWNER,
                    lease_id=event["lease_id"],
                    generation=event["lease_generation"],
                )
                validate_record("audit_event", event)

    def test_tampered_event_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_name:
            root = Path(temporary_name)
            path = root / "events.ndjson"
            append_event(path, self.event("44444444-4444-4444-8444-444444444444", "run_created", lease=False), project_root=root)
            raw = path.read_text(encoding="utf-8").replace(
                "44444444-4444-4444-8444-444444444444",
                "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
            )
            path.write_text(raw, encoding="utf-8")
            path.chmod(0o600)
            with self.assertRaisesRegex(ContractError, r"\[digest\]"):
                read_events(path, project_root=root)

    def test_insecure_event_log_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_name:
            path = Path(temporary_name) / "events.ndjson"
            path.write_text("", encoding="utf-8")
            path.chmod(0o644)
            with self.assertRaisesRegex(ContractError, r"\[permissions\]"):
                read_events(path, project_root=path.parent)


if __name__ == "__main__":
    unittest.main()
