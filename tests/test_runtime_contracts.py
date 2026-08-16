from __future__ import annotations

import copy
import json
import multiprocessing
import os
import shutil
import sys
import tempfile
import threading
import unittest
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from the_loop import (  # noqa: E402
    ContractError,
    LeaseToken,
    MutationRequest,
    PathPresence,
    PathProbe,
    RunRuntime,
    append_event,
    atomic_write_json,
    create_json_exclusive,
    probe_kill_switch,
    read_events,
    read_json,
    remove_state_file,
    state_lock,
    validate_record,
)
import the_loop.state as state_module  # noqa: E402


FIXTURES = ROOT / "tests" / "fixtures" / "state" / "valid"
RUN_ID = "11111111-1111-4111-8111-111111111111"
OWNER = {"harness": "codex", "actor": "synthetic-agent", "session_id": "session-1"}


def fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class Clock:
    def __init__(self, value: str) -> None:
        self.set(value)

    def set(self, value: str) -> None:
        self.value = datetime.fromisoformat(value.replace("Z", "+00:00"))

    def __call__(self) -> datetime:
        return self.value


class IdFactory:
    def __init__(self, start: int = 1) -> None:
        self.next = start

    def __call__(self) -> uuid.UUID:
        value = uuid.UUID(f"00000000-0000-4000-8000-{self.next:012x}")
        self.next += 1
        return value


def bootstrap(root: Path, *, budgets: dict | None = None) -> tuple[dict, dict, dict]:
    config = fixture("config.json")
    run = fixture("run.json")
    grant = fixture("grant.json")
    if budgets is not None:
        config["budgets"] = copy.deepcopy(budgets)
        run["budgets"] = copy.deepcopy(budgets)
    atomic_write_json(".the-loop/config.json", config, project_root=root, record_type="config")
    atomic_write_json(
        f".the-loop/grants/{grant['grant_id']}.json",
        grant,
        project_root=root,
        record_type="grant",
    )
    atomic_write_json(
        f".the-loop/runs/{RUN_ID}/run.json",
        run,
        project_root=root,
        record_type="run",
    )
    append_event(
        f".the-loop/runs/{RUN_ID}/events.ndjson",
        {
            "schema_version": "1.0",
            "event_id": "44444444-4444-4444-8444-444444444444",
            "run_id": RUN_ID,
            "lease_id": None,
            "lease_generation": None,
            "type": "run_created",
            "actor": {"harness": "manual", "actor": "synthetic-user", "session_id": "bootstrap"},
            "at": run["created_at"],
            "data": {"objective": run["objective"]},
            "projection": {"run": copy.deepcopy(run), "lease": None, "pending_operation": None},
        },
        project_root=root,
    )
    return config, run, grant


def bootstrap_additional_run(root: Path, run_id: str) -> dict:
    run = fixture("run.json")
    run["run_id"] = run_id
    atomic_write_json(
        f".the-loop/runs/{run_id}/run.json",
        run,
        project_root=root,
        record_type="run",
    )
    append_event(
        f".the-loop/runs/{run_id}/events.ndjson",
        {
            "schema_version": "1.0",
            "event_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
            "run_id": run_id,
            "lease_id": None,
            "lease_generation": None,
            "type": "run_created",
            "actor": {"harness": "manual", "actor": "synthetic-user", "session_id": "bootstrap-2"},
            "at": run["created_at"],
            "data": {"objective": run["objective"]},
            "projection": {"run": copy.deepcopy(run), "lease": None, "pending_operation": None},
        },
        project_root=root,
    )
    return run


def concurrent_acquire(root_name: str, actor_name: str, seed: int, queue) -> None:
    owner = {"harness": "codex", "actor": actor_name, "session_id": f"session-{seed}"}
    runtime = RunRuntime(
        Path(root_name),
        RUN_ID,
        clock=Clock("2026-08-16T08:01:00Z"),
        id_factory=IdFactory(seed),
    )
    try:
        snapshot = runtime.acquire(owner)
    except ContractError as exc:
        queue.put(("error", exc.code))
    else:
        queue.put(("acquired", snapshot.lease["owner"]["actor"]))


def crash_during_mutation(root_name: str, lease: dict, effect: str) -> None:
    runtime = RunRuntime(
        Path(root_name),
        RUN_ID,
        clock=Clock("2026-08-16T08:02:00Z"),
        id_factory=IdFactory(800),
    )
    request = MutationRequest(
        event_type="evidence_recorded",
        data={"evidence_id": "99999999-9999-4999-8999-999999999999", "outcome": "passed"},
        action="send" if effect == "external" else "local_write",
        destination="network" if effect == "external" else "repository",
        mutations=1,
        external_actions=1 if effect == "external" else 0,
        effect=effect,
    )

    def irreversible_boundary() -> None:
        marker = Path(root_name) / f"{effect}-callback-marker"
        marker.write_text("called-once\n", encoding="utf-8")
        os._exit(23)

    runtime.perform_mutation(LeaseToken.from_lease(lease), request, irreversible_boundary)


class StatePrimitiveTests(unittest.TestCase):
    def test_exclusive_create_read_and_identity_safe_remove(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = Path(".the-loop/runtime/value.json")
            create_json_exclusive(path, {"value": 1}, project_root=root)
            self.assertEqual({"value": 1}, read_json(path, project_root=root))
            with self.assertRaisesRegex(ContractError, r"\[exists\]"):
                create_json_exclusive(path, {"value": 2}, project_root=root)
            self.assertTrue(remove_state_file(path, project_root=root))
            self.assertIsNone(read_json(path, project_root=root))
            self.assertFalse(remove_state_file(path, project_root=root))

    def test_remove_rolls_quarantine_back_on_unlink_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = Path(".the-loop/runtime/value.json")
            create_json_exclusive(path, {"value": 1}, project_root=root)
            real_unlink = os.unlink

            def fail_quarantine(name, *args, **kwargs):
                if str(name).endswith(".remove"):
                    raise OSError("injected unlink failure")
                return real_unlink(name, *args, **kwargs)

            with mock.patch.object(state_module.os, "unlink", side_effect=fail_quarantine):
                with self.assertRaisesRegex(OSError, "injected unlink failure"):
                    remove_state_file(path, project_root=root)
            self.assertEqual({"value": 1}, read_json(path, project_root=root))
            self.assertEqual([], list((root / ".the-loop" / "runtime").glob("*.remove")))

    def test_lock_handle_detects_canonical_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = Path(".the-loop/runs/run/runtime.lock")
            with self.assertRaisesRegex(ContractError, r"\[lock\]"):
                with state_lock(path, project_root=root) as handle:
                    lock_path = root / path
                    displaced = lock_path.with_name("displaced.lock")
                    lock_path.rename(displaced)
                    lock_path.write_bytes(b"")
                    os.chmod(lock_path, 0o600)
                    handle.assert_current()

    def test_kill_probe_counts_broken_symlink_and_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            stop = root / "STOP"
            self.assertEqual(PathPresence.ABSENT, probe_kill_switch("STOP", project_root=root).presence)
            stop.symlink_to(root / "missing-target")
            self.assertEqual(PathPresence.PRESENT, probe_kill_switch("STOP", project_root=root).presence)
            self.assertEqual(
                PathPresence.INDETERMINATE,
                probe_kill_switch("../STOP", project_root=root).presence,
            )


class RuntimeContractTests(unittest.TestCase):
    def test_exhausted_stage_attempt_markers_use_canonical_stage_order(self) -> None:
        run = fixture("run.json")
        run["budgets"]["max_stage_attempts"] = 1
        run["usage"]["stage_attempts"]["build"] = 1
        run["usage"]["stage_attempts"]["strategize"] = 1
        exhausted = RunRuntime._exhausted_usage_budgets(run)
        self.assertEqual(
            [("max_stage_attempts", "strategize"), ("max_stage_attempts", "build")],
            [(budget, stage) for budget, _limit, _observed, stage in exhausted],
        )

    def test_state_root_is_durably_bound_per_run(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config, _, _ = bootstrap(root)
            shutil.copytree(root / ".the-loop", root / ".alternate")
            clock = Clock("2026-08-16T08:01:00Z")
            runtime = RunRuntime(root, RUN_ID, clock=clock, id_factory=IdFactory(80))
            runtime.acquire(OWNER)

            config["state_root"] = ".alternate"
            atomic_write_json(
                ".the-loop/config.json",
                config,
                project_root=root,
                record_type="config",
            )
            with self.assertRaisesRegex(ContractError, r"\[invariant\].*durably bound"):
                RunRuntime(root, RUN_ID, clock=clock, id_factory=IdFactory(85))
            alternate_events = read_events(
                f".alternate/runs/{RUN_ID}/events.ndjson",
                project_root=root,
            )
            self.assertEqual(["run_created"], [event["type"] for event in alternate_events])

    def test_same_path_namespace_replacement_is_rejected_by_existing_and_fresh_runtime(self) -> None:
        for component in ("project", "state_root"):
            with self.subTest(component=component), tempfile.TemporaryDirectory() as temporary:
                parent = Path(temporary)
                root = parent / "project"
                root.mkdir()
                bootstrap(root)
                runtime = RunRuntime(root, RUN_ID, clock=Clock("2026-08-16T08:01:00Z"), id_factory=IdFactory(81))
                runtime.acquire(OWNER)

                if component == "project":
                    displaced = parent / "displaced-project"
                    root.rename(displaced)
                    shutil.copytree(displaced, root)
                else:
                    displaced = root / ".displaced-the-loop"
                    (root / ".the-loop").rename(displaced)
                    shutil.copytree(displaced, root / ".the-loop")

                with self.assertRaisesRegex(ContractError, r"\[unsafe_path\].*identity changed"):
                    runtime.status()
                with self.assertRaisesRegex(ContractError, r"\[invariant\].*durably bound"):
                    RunRuntime(root, RUN_ID, clock=Clock("2026-08-16T08:02:00Z"), id_factory=IdFactory(82))
                original_events = read_events(
                    f".the-loop/runs/{RUN_ID}/events.ndjson",
                    project_root=displaced if component == "project" else root,
                ) if component == "project" else read_events(
                    f".displaced-the-loop/runs/{RUN_ID}/events.ndjson",
                    project_root=root,
                )
                self.assertEqual(["run_created", "lease_acquired"], [event["type"] for event in original_events])

    def test_namespace_replacement_during_callback_prevents_completion_commit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bootstrap(root)
            clock = Clock("2026-08-16T08:01:00Z")
            runtime = RunRuntime(root, RUN_ID, clock=clock, id_factory=IdFactory(83))
            acquired = runtime.acquire(OWNER)
            clock.set("2026-08-16T08:02:00Z")
            displaced = root / ".displaced-the-loop"

            def replace_namespace() -> str:
                (root / ".the-loop").rename(displaced)
                shutil.copytree(displaced, root / ".the-loop")
                return "side-effect-happened"

            with self.assertRaisesRegex(ContractError, r"\[(?:unsafe_path|lock)\]"):
                runtime.perform_mutation(
                    acquired.token,
                    MutationRequest(
                        event_type="stage_completed",
                        data={"stage": "strategize", "outcome": "passed"},
                    ),
                    replace_namespace,
                )
            for event_root in (".the-loop", ".displaced-the-loop"):
                events = read_events(f"{event_root}/runs/{RUN_ID}/events.ndjson", project_root=root)
                self.assertEqual("operation_intended", events[-1]["type"])
                self.assertIsNotNone(events[-1]["projection"]["pending_operation"])

    def test_ready_run_with_present_switch_is_durably_halted_before_acquisition(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bootstrap(root)
            (root / ".the-loop" / "STOP").write_text("stop\n", encoding="utf-8")
            clock = Clock("2026-08-16T08:01:00Z")
            runtime = RunRuntime(
                root,
                RUN_ID,
                clock=clock,
                id_factory=IdFactory(90),
            )
            with self.assertRaisesRegex(ContractError, r"\[kill_switch\]"):
                runtime.acquire(OWNER)
            event = read_events(f".the-loop/runs/{RUN_ID}/events.ndjson", project_root=root)[-1]
            self.assertEqual("kill_switch_detected", event["type"])
            self.assertEqual("halted_kill_switch", event["projection"]["run"]["status"])
            self.assertIsNone(event["projection"]["lease"])
            self.assertIsNone(event["lease_id"])
            (root / ".the-loop" / "STOP").unlink()
            clock.set("2026-08-16T08:02:00Z")
            recovered = runtime.recover(OWNER, reason="Explicit recovery after removing the stop file")
            self.assertEqual("active", recovered.run["status"])
            self.assertEqual(0, recovered.lease["generation"])
            event = read_events(f".the-loop/runs/{RUN_ID}/events.ndjson", project_root=root)[-1]
            self.assertEqual("recovery_started", event["type"])
            self.assertIsNone(event["data"]["previous_generation"])
            self.assertEqual(0, event["data"]["new_generation"])

    def test_concurrent_acquisition_has_one_winner_and_one_precise_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bootstrap(root)
            context = multiprocessing.get_context("fork")
            queue = context.Queue()
            workers = [
                context.Process(target=concurrent_acquire, args=(str(root), f"agent-{index}", 100 + index * 10, queue))
                for index in range(2)
            ]
            for worker in workers:
                worker.start()
            for worker in workers:
                worker.join(10)
                self.assertEqual(0, worker.exitcode)
            results = sorted(queue.get(timeout=2) for _ in workers)
            self.assertEqual(["acquired", "error"], sorted(item[0] for item in results))
            self.assertIn(("error", "lease_conflict"), results)
            events = read_events(f".the-loop/runs/{RUN_ID}/events.ndjson", project_root=root)
            self.assertEqual(1, sum(item["type"] == "lease_acquired" for item in events))

    def test_acquire_heartbeat_and_projection_reconciliation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bootstrap(root)
            clock = Clock("2026-08-16T08:01:00Z")
            runtime = RunRuntime(root, RUN_ID, clock=clock, id_factory=IdFactory())
            acquired = runtime.acquire(OWNER)
            self.assertEqual("active", acquired.run["status"])
            self.assertEqual(0, acquired.lease["generation"])

            stale = fixture("run.json")
            atomic_write_json(
                f".the-loop/runs/{RUN_ID}/run.json",
                stale,
                project_root=root,
                record_type="run",
            )
            clock.set("2026-08-16T08:02:00Z")
            heartbeat = runtime.heartbeat(acquired.token)
            self.assertEqual("2026-08-16T08:02:00Z", heartbeat.run["last_heartbeat_at"])
            projected = read_json(
                f".the-loop/runs/{RUN_ID}/run.json",
                project_root=root,
                record_type="run",
            )
            self.assertEqual(heartbeat.run, projected)

    def test_expired_active_run_fails_before_fresh_generation_recovery(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bootstrap(root)
            clock = Clock("2026-08-16T08:01:00Z")
            runtime = RunRuntime(root, RUN_ID, clock=clock, id_factory=IdFactory(20))
            acquired = runtime.acquire(OWNER)
            clock.set("2026-08-16T08:07:00Z")
            recovered = runtime.recover(OWNER, reason="Expired lease recovery")
            self.assertEqual(1, recovered.lease["generation"])
            self.assertNotEqual(acquired.lease["lease_id"], recovered.lease["lease_id"])
            events = read_events(f".the-loop/runs/{RUN_ID}/events.ndjson", project_root=root)
            self.assertEqual(["run_failed", "recovery_started"], [item["type"] for item in events[-2:]])

    def test_expired_active_run_records_duration_budget_before_blocking_recovery(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            budgets = fixture("run.json")["budgets"]
            budgets["max_duration_seconds"] = 300
            bootstrap(root, budgets=budgets)
            clock = Clock("2026-08-16T08:01:00Z")
            runtime = RunRuntime(root, RUN_ID, clock=clock, id_factory=IdFactory(35))
            runtime.acquire(OWNER)
            clock.set("2026-08-16T08:07:00Z")
            with self.assertRaisesRegex(ContractError, r"budget_reached:max_duration_seconds prevents recovery"):
                runtime.recover(OWNER, reason="Expired lease cannot reset duration")
            events = read_events(f".the-loop/runs/{RUN_ID}/events.ndjson", project_root=root)
            self.assertEqual(["run_failed", "budget_reached"], [item["type"] for item in events[-2:]])
            self.assertEqual(300, events[-1]["projection"]["run"]["usage"]["duration_seconds"])
            self.assertEqual(
                "budget_reached:max_duration_seconds",
                events[-1]["projection"]["run"]["terminal_reason"]["code"],
            )

    def test_renewal_preserves_generation_and_rejects_wrong_or_expired_token(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bootstrap(root)
            clock = Clock("2026-08-16T08:01:00Z")
            runtime = RunRuntime(root, RUN_ID, clock=clock, id_factory=IdFactory(60))
            acquired = runtime.acquire(OWNER)
            wrong = copy.deepcopy(acquired.lease)
            wrong["generation"] = 1
            clock.set("2026-08-16T08:02:00Z")
            with self.assertRaisesRegex(ContractError, r"\[lease\].*does not match"):
                runtime.renew(type(acquired.token).from_lease(wrong))
            renewed = runtime.renew(acquired.token)
            self.assertEqual(acquired.lease["lease_id"], renewed.lease["lease_id"])
            self.assertEqual(0, renewed.lease["generation"])
            self.assertGreater(renewed.lease["expires_at"], acquired.lease["expires_at"])
            clock.set("2026-08-16T08:08:00Z")
            with self.assertRaisesRegex(ContractError, r"\[lease_expired\]"):
                runtime.renew(renewed.token)

    def test_detected_switch_halts_without_matching_lease_envelope(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bootstrap(root)
            clock = Clock("2026-08-16T08:01:00Z")
            runtime = RunRuntime(root, RUN_ID, clock=clock, id_factory=IdFactory(40))
            acquired = runtime.acquire(OWNER)
            stop = root / ".the-loop" / "STOP"
            stop.write_text("stop\n", encoding="utf-8")
            clock.set("2026-08-16T08:02:00Z")
            with self.assertRaisesRegex(ContractError, r"\[kill_switch\]"):
                runtime.heartbeat(acquired.token)
            event = read_events(f".the-loop/runs/{RUN_ID}/events.ndjson", project_root=root)[-1]
            self.assertEqual("kill_switch_detected", event["type"])
            self.assertIsNone(event["lease_id"])
            self.assertEqual("halted_kill_switch", event["projection"]["run"]["status"])

    def test_successful_mutation_is_intended_before_semantic_completion(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bootstrap(root)
            clock = Clock("2026-08-16T08:01:00Z")
            runtime = RunRuntime(root, RUN_ID, clock=clock, id_factory=IdFactory(200))
            acquired = runtime.acquire(OWNER)
            clock.set("2026-08-16T08:02:00Z")
            calls: list[str] = []
            result = runtime.perform_mutation(
                acquired.token,
                MutationRequest(
                    event_type="stage_completed",
                    data={"stage": "strategize", "outcome": "passed"},
                ),
                lambda: calls.append("called"),
            )
            self.assertEqual(["called"], calls)
            self.assertIsNone(result.snapshot.pending_operation)
            self.assertEqual(1, result.snapshot.run["usage"]["mutations"])
            events = read_events(f".the-loop/runs/{RUN_ID}/events.ndjson", project_root=root)
            self.assertEqual(["operation_intended", "stage_completed"], [item["type"] for item in events[-2:]])
            self.assertIsNotNone(events[-2]["projection"]["pending_operation"])
            self.assertIsNone(events[-1]["projection"]["pending_operation"])

    def test_grant_revocation_wins_before_intent_across_runs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bootstrap(root)
            second_run_id = "22222222-2222-4222-8222-222222222222"
            bootstrap_additional_run(root, second_run_id)
            clock = Clock("2026-08-16T08:01:00Z")
            mutation_runtime = RunRuntime(root, RUN_ID, clock=clock, id_factory=IdFactory(210))
            revocation_runtime = RunRuntime(root, second_run_id, clock=clock, id_factory=IdFactory(230))
            acquired = mutation_runtime.acquire(OWNER)
            revocation_runtime.acquire({**OWNER, "session_id": "session-2"})
            clock.set("2026-08-16T08:02:00Z")
            grant_written = threading.Event()
            allow_revoke_audit = threading.Event()
            real_atomic_write = atomic_write_json
            revocation_errors: list[BaseException] = []
            mutation_errors: list[BaseException] = []
            callbacks: list[str] = []

            def pause_after_grant_write(*args, **kwargs):
                result = real_atomic_write(*args, **kwargs)
                if kwargs.get("record_type") == "grant" and args[1]["revoked_at"] is not None:
                    grant_written.set()
                    self.assertTrue(allow_revoke_audit.wait(5))
                return result

            def revoke() -> None:
                try:
                    revocation_runtime.revoke_authority(OWNER, revoked_by="synthetic-user")
                except BaseException as exc:  # pragma: no cover - asserted below.
                    revocation_errors.append(exc)

            def mutate() -> None:
                try:
                    mutation_runtime.perform_mutation(
                        acquired.token,
                        MutationRequest(
                            event_type="stage_completed",
                            data={"stage": "strategize", "outcome": "passed"},
                        ),
                        lambda: callbacks.append("called"),
                    )
                except BaseException as exc:
                    mutation_errors.append(exc)

            with mock.patch("the_loop.runtime.atomic_write_json", side_effect=pause_after_grant_write):
                revoker = threading.Thread(target=revoke)
                revoker.start()
                self.assertTrue(grant_written.wait(5))
                mutator = threading.Thread(target=mutate)
                mutator.start()
                self.assertTrue(mutator.is_alive())
                self.assertEqual([], callbacks)
                allow_revoke_audit.set()
                revoker.join(5)
                mutator.join(5)
            self.assertFalse(revoker.is_alive())
            self.assertFalse(mutator.is_alive())
            self.assertEqual([], revocation_errors)
            self.assertEqual([], callbacks)
            self.assertEqual(1, len(mutation_errors))
            self.assertRegex(str(mutation_errors[0]), r"\[authority\].*revoked")
            self.assertEqual([], callbacks)
            events = read_events(f".the-loop/runs/{RUN_ID}/events.ndjson", project_root=root)
            self.assertEqual("authority_revoked", events[-1]["type"])
            self.assertEqual("waiting_approval", events[-1]["projection"]["run"]["status"])
            revocation_events = read_events(
                f".the-loop/runs/{second_run_id}/events.ndjson",
                project_root=root,
            )
            self.assertEqual(1, sum(event["type"] == "authority_revoked" for event in events))
            self.assertEqual(1, sum(event["type"] == "authority_revoked" for event in revocation_events))
            self.assertEqual(events[-1]["data"], revocation_events[-1]["data"])

    def test_grant_intent_wins_before_revocation_across_runs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bootstrap(root)
            second_run_id = "22222222-2222-4222-8222-222222222222"
            bootstrap_additional_run(root, second_run_id)
            clock = Clock("2026-08-16T08:01:00Z")
            mutation_runtime = RunRuntime(root, RUN_ID, clock=clock, id_factory=IdFactory(240))
            revocation_runtime = RunRuntime(root, second_run_id, clock=clock, id_factory=IdFactory(260))
            acquired = mutation_runtime.acquire(OWNER)
            revocation_runtime.acquire({**OWNER, "session_id": "session-2"})
            clock.set("2026-08-16T08:02:00Z")
            intent_committed = threading.Event()
            allow_intent_return = threading.Event()
            callbacks: list[str] = []
            mutation_errors: list[BaseException] = []
            revocation_errors: list[BaseException] = []
            real_append = mutation_runtime._append

            def pause_after_intent(*args, **kwargs):
                event = real_append(*args, **kwargs)
                if args[2] == "operation_intended":
                    intent_committed.set()
                    self.assertTrue(allow_intent_return.wait(5))
                return event

            def mutate() -> None:
                try:
                    mutation_runtime.perform_mutation(
                        acquired.token,
                        MutationRequest(
                            event_type="stage_completed",
                            data={"stage": "strategize", "outcome": "passed"},
                        ),
                        lambda: callbacks.append("called"),
                    )
                except BaseException as exc:  # pragma: no cover - asserted below.
                    mutation_errors.append(exc)

            def revoke() -> None:
                try:
                    revocation_runtime.revoke_authority(OWNER, revoked_by="synthetic-user")
                except BaseException as exc:  # pragma: no cover - asserted below.
                    revocation_errors.append(exc)

            with mock.patch.object(mutation_runtime, "_append", side_effect=pause_after_intent):
                mutator = threading.Thread(target=mutate)
                mutator.start()
                self.assertTrue(intent_committed.wait(5))
                revoker = threading.Thread(target=revoke)
                revoker.start()
                self.assertTrue(revoker.is_alive())
                allow_intent_return.set()
                mutator.join(5)
                revoker.join(5)
            self.assertFalse(mutator.is_alive())
            self.assertFalse(revoker.is_alive())
            self.assertEqual([], mutation_errors)
            self.assertEqual([], revocation_errors)
            self.assertEqual(["called"], callbacks)
            mutation_events = read_events(f".the-loop/runs/{RUN_ID}/events.ndjson", project_root=root)
            self.assertEqual(["operation_intended", "stage_completed"], [event["type"] for event in mutation_events[-2:]])
            revocation_events = read_events(
                f".the-loop/runs/{second_run_id}/events.ndjson",
                project_root=root,
            )
            self.assertEqual("authority_revoked", revocation_events[-1]["type"])

    def test_revoke_retry_with_committed_marker_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bootstrap(root)
            clock = Clock("2026-08-16T08:01:00Z")
            runtime = RunRuntime(root, RUN_ID, clock=clock, id_factory=IdFactory(270))
            runtime.acquire(OWNER)
            clock.set("2026-08-16T08:02:00Z")
            first = runtime.revoke_authority(OWNER, revoked_by="synthetic-user")
            before = read_events(f".the-loop/runs/{RUN_ID}/events.ndjson", project_root=root)
            second = runtime.revoke_authority(OWNER, revoked_by="different-retry-actor")
            after = read_events(f".the-loop/runs/{RUN_ID}/events.ndjson", project_root=root)
            self.assertEqual(len(before), len(after))
            self.assertEqual(1, sum(event["type"] == "authority_revoked" for event in after))
            self.assertEqual("synthetic-user", after[-1]["data"]["revoked_by"])
            self.assertEqual("2026-08-16T08:02:00Z", after[-1]["data"]["revoked_at"])
            self.assertEqual("waiting_approval", first.run["status"])
            self.assertEqual(first.run, second.run)

    def test_revocation_remains_available_under_present_or_indeterminate_kill(self) -> None:
        for switch_mode in ("present", "indeterminate"):
            with self.subTest(switch_mode=switch_mode), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                _, _, grant = bootstrap(root)
                clock = Clock("2026-08-16T08:01:00Z")
                runtime = RunRuntime(root, RUN_ID, clock=clock, id_factory=IdFactory(275))
                runtime.acquire(OWNER)
                clock.set("2026-08-16T08:02:00Z")
                if switch_mode == "present":
                    (root / ".the-loop" / "STOP").write_text("stop\n", encoding="utf-8")

                probe_patch = (
                    mock.patch(
                        "the_loop.runtime.probe_kill_switch",
                        return_value=PathProbe(
                            ".the-loop/STOP",
                            PathPresence.INDETERMINATE,
                            "injected probe failure",
                        ),
                    )
                    if switch_mode == "indeterminate"
                    else mock.patch("the_loop.runtime.probe_kill_switch", wraps=probe_kill_switch)
                )
                with probe_patch:
                    result = runtime.revoke_authority(OWNER, revoked_by="synthetic-user")

                persisted = read_json(
                    f".the-loop/grants/{grant['grant_id']}.json",
                    project_root=root,
                    record_type="grant",
                )
                self.assertEqual("synthetic-user", persisted["revoked_by"])
                self.assertEqual("2026-08-16T08:02:00Z", persisted["revoked_at"])
                self.assertEqual("halted_kill_switch", result.run["status"])
                self.assertEqual("kill_switch_detected", result.run["terminal_reason"]["code"])
                events = read_events(f".the-loop/runs/{RUN_ID}/events.ndjson", project_root=root)
                self.assertEqual(["authority_revoked", "kill_switch_detected"], [event["type"] for event in events[-2:]])
                self.assertEqual(1, sum(event["type"] == "authority_revoked" for event in events))
                self.assertEqual(1, sum(event["type"] == "kill_switch_detected" for event in events))

    def test_revoke_preappend_failure_is_repaired_on_retry(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bootstrap(root)
            clock = Clock("2026-08-16T08:01:00Z")
            runtime = RunRuntime(root, RUN_ID, clock=clock, id_factory=IdFactory(280))
            runtime.acquire(OWNER)
            clock.set("2026-08-16T08:02:00Z")
            real_append = runtime._append

            def fail_before_marker(*args, **kwargs):
                if args[2] == "authority_revoked":
                    raise OSError("injected pre-append failure")
                return real_append(*args, **kwargs)

            with mock.patch.object(runtime, "_append", side_effect=fail_before_marker):
                with self.assertRaisesRegex(ContractError, r"\[audit_pending\]"):
                    runtime.revoke_authority(OWNER, revoked_by="synthetic-user")
            grant = read_json(
                ".the-loop/grants/22222222-2222-4222-8222-222222222222.json",
                project_root=root,
                record_type="grant",
            )
            self.assertEqual("synthetic-user", grant["revoked_by"])
            self.assertNotIn(
                "authority_revoked",
                [event["type"] for event in read_events(f".the-loop/runs/{RUN_ID}/events.ndjson", project_root=root)],
            )

            repaired = runtime.revoke_authority(OWNER, revoked_by="ignored-on-retry")
            events = read_events(f".the-loop/runs/{RUN_ID}/events.ndjson", project_root=root)
            self.assertEqual("waiting_approval", repaired.run["status"])
            self.assertEqual(1, sum(event["type"] == "authority_revoked" for event in events))
            self.assertEqual("synthetic-user", events[-1]["data"]["revoked_by"])

    def test_revoke_postcommit_error_accepts_only_canonical_marker(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bootstrap(root)
            clock = Clock("2026-08-16T08:01:00Z")
            runtime = RunRuntime(root, RUN_ID, clock=clock, id_factory=IdFactory(290))
            runtime.acquire(OWNER)
            clock.set("2026-08-16T08:02:00Z")
            real_append = runtime._append

            def append_then_raise(*args, **kwargs):
                event = real_append(*args, **kwargs)
                if args[2] == "authority_revoked":
                    raise OSError("injected post-commit failure")
                return event

            with mock.patch.object(runtime, "_append", side_effect=append_then_raise):
                result = runtime.revoke_authority(OWNER, revoked_by="synthetic-user")
            events = read_events(f".the-loop/runs/{RUN_ID}/events.ndjson", project_root=root)
            self.assertEqual("authority_revoked", events[-1]["type"])
            self.assertEqual(1, sum(event["type"] == "authority_revoked" for event in events))
            self.assertEqual(events[-1]["projection"]["run"], result.run)

    def test_revoke_persistent_and_unverifiable_failures_never_restore_grant(self) -> None:
        for failure_mode, expected_code in (
            ("persistent", "audit_pending"),
            ("unverifiable", "committed_state_unknown"),
        ):
            with self.subTest(failure_mode=failure_mode), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                bootstrap(root)
                clock = Clock("2026-08-16T08:01:00Z")
                runtime = RunRuntime(root, RUN_ID, clock=clock, id_factory=IdFactory(300))
                runtime.acquire(OWNER)
                clock.set("2026-08-16T08:02:00Z")
                real_events = runtime._events
                event_reads = 0

                def fail_verification(paths):
                    nonlocal event_reads
                    event_reads += 1
                    if event_reads == 1:
                        return real_events(paths)
                    raise OSError("injected verification failure")

                events_patch = (
                    mock.patch.object(runtime, "_events", side_effect=fail_verification)
                    if failure_mode == "unverifiable"
                    else mock.patch.object(runtime, "_events", wraps=real_events)
                )
                with events_patch, mock.patch.object(
                    runtime,
                    "_append",
                    side_effect=OSError("injected persistent append failure"),
                ):
                    with self.assertRaisesRegex(ContractError, rf"\[{expected_code}\]"):
                        runtime.revoke_authority(OWNER, revoked_by="synthetic-user")
                    if failure_mode == "persistent":
                        with self.assertRaisesRegex(ContractError, r"\[audit_pending\]"):
                            runtime.revoke_authority(OWNER, revoked_by="ignored-on-retry")
                grant = read_json(
                    ".the-loop/grants/22222222-2222-4222-8222-222222222222.json",
                    project_root=root,
                    record_type="grant",
                )
                self.assertEqual("synthetic-user", grant["revoked_by"])
                self.assertIsNotNone(grant["revoked_at"])

    def test_post_intent_stop_rolls_back_exact_reservation_and_remains_recoverable(self) -> None:
        for switch_mode in ("present", "indeterminate"):
            with self.subTest(switch_mode=switch_mode), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                budgets = fixture("run.json")["budgets"]
                budgets.update(
                    {
                        "max_stage_attempts": 1,
                        "max_mutations": 1,
                        "max_external_actions": 1,
                        "max_cost_usd": "1",
                    }
                )
                bootstrap(root, budgets=budgets)
                grant = fixture("grant.json")
                grant["scope"]["actions"].append("send")
                grant["scope"]["destinations"].append("network")
                grant["scope"]["exclusions"] = []
                atomic_write_json(
                    f".the-loop/grants/{grant['grant_id']}.json",
                    grant,
                    project_root=root,
                    record_type="grant",
                )
                clock = Clock("2026-08-16T08:01:00Z")
                runtime = RunRuntime(root, RUN_ID, clock=clock, id_factory=IdFactory(220))
                acquired = runtime.acquire(OWNER)
                clock.set("2026-08-16T08:02:00Z")
                callbacks: list[str] = []
                real_append = runtime._append
                probe_calls = 0

                def append_then_stop(*args, **kwargs):
                    event = real_append(*args, **kwargs)
                    if args[2] == "operation_intended":
                        (root / ".the-loop" / "STOP").write_text("stop\n", encoding="utf-8")
                    return event

                def become_indeterminate(configured_path, **_kwargs):
                    nonlocal probe_calls
                    probe_calls += 1
                    if probe_calls < 3:
                        return PathProbe(configured_path, PathPresence.ABSENT)
                    return PathProbe(configured_path, PathPresence.INDETERMINATE, "injected probe failure")

                patcher = (
                    mock.patch.object(runtime, "_append", side_effect=append_then_stop)
                    if switch_mode == "present"
                    else mock.patch("the_loop.runtime.probe_kill_switch", side_effect=become_indeterminate)
                )
                with patcher:
                    with self.assertRaisesRegex(ContractError, r"\[kill_switch\]"):
                        runtime.perform_mutation(
                            acquired.token,
                            MutationRequest(
                                event_type="stage_started",
                                data={"stage": "build"},
                                action="send",
                                destination="network",
                                external_actions=1,
                                cost_usd="1",
                                stage_attempt="build",
                                effect="external",
                            ),
                            lambda: callbacks.append("called"),
                        )
                self.assertEqual([], callbacks)
                events = read_events(f".the-loop/runs/{RUN_ID}/events.ndjson", project_root=root)
                self.assertEqual(
                    ["operation_intended", "operation_reconciled", "kill_switch_detected"],
                    [event["type"] for event in events[-3:]],
                )
                self.assertEqual("known_not_started", events[-2]["data"]["outcome"])
                halted = events[-1]["projection"]["run"]
                self.assertEqual("halted_kill_switch", halted["status"])
                self.assertEqual(0, halted["usage"]["mutations"])
                self.assertEqual(0, halted["usage"]["external_actions"])
                self.assertIsNone(halted["usage"]["cost_usd"])
                self.assertEqual(0, halted["usage"]["stage_attempts"]["build"])
                self.assertEqual("strategize", halted["stage"])

                if switch_mode == "present":
                    (root / ".the-loop" / "STOP").unlink()
                clock.set("2026-08-16T08:07:00Z")
                recovered = runtime.recover(OWNER, reason="Known-not-started operation was safely rolled back")
                self.assertEqual("active", recovered.run["status"])
                self.assertEqual(1, recovered.lease["generation"])

    def test_successful_callback_elapsed_time_is_charged_atomically(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            budgets = fixture("run.json")["budgets"]
            budgets["max_duration_seconds"] = 60
            bootstrap(root, budgets=budgets)
            clock = Clock("2026-08-16T08:01:00Z")
            runtime = RunRuntime(root, RUN_ID, clock=clock, id_factory=IdFactory(205))
            acquired = runtime.acquire(OWNER)
            clock.set("2026-08-16T08:01:10Z")

            def slow_callback() -> str:
                clock.set("2026-08-16T08:02:10Z")
                return "done"

            result = runtime.perform_mutation(
                acquired.token,
                MutationRequest(
                    event_type="stage_completed",
                    data={"stage": "strategize", "outcome": "passed"},
                ),
                slow_callback,
            )
            self.assertEqual("done", result.value)
            self.assertEqual(70, result.snapshot.run["usage"]["duration_seconds"])
            self.assertEqual("failed", result.snapshot.run["status"])
            self.assertEqual(
                "budget_reached:max_duration_seconds",
                result.snapshot.run["terminal_reason"]["code"],
            )
            events = read_events(f".the-loop/runs/{RUN_ID}/events.ndjson", project_root=root)
            self.assertEqual("stage_completed", events[-2]["type"])
            self.assertEqual("budget_reached", events[-1]["type"])

    def test_callback_completion_at_lease_expiry_closes_non_active(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bootstrap(root)
            clock = Clock("2026-08-16T08:01:00Z")
            runtime = RunRuntime(root, RUN_ID, clock=clock, id_factory=IdFactory(212))
            acquired = runtime.acquire(OWNER)
            clock.set("2026-08-16T08:01:10Z")

            def callback_at_expiry() -> None:
                clock.set(acquired.lease["expires_at"])

            result = runtime.perform_mutation(
                acquired.token,
                MutationRequest(
                    event_type="stage_completed",
                    data={"stage": "strategize", "outcome": "passed"},
                ),
                callback_at_expiry,
            )
            self.assertEqual("failed", result.snapshot.run["status"])
            self.assertEqual("run_failed", result.snapshot.run["terminal_reason"]["code"])
            events = read_events(f".the-loop/runs/{RUN_ID}/events.ndjson", project_root=root)
            intended, completed = events[-2:]
            self.assertEqual("stage_completed", completed["type"])
            invalid_active = copy.deepcopy(completed)
            invalid_active["projection"]["run"]["status"] = "active"
            invalid_active["projection"]["run"]["terminal_reason"] = None
            with self.assertRaisesRegex(ContractError, r"post-expiry completion.*non-active"):
                validate_record("audit_event", invalid_active, previous=intended)

    def test_simultaneous_budgets_emit_stable_complete_sequence_and_repair_suffix(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            budgets = fixture("run.json")["budgets"]
            budgets.update(
                {
                    "max_duration_seconds": 60,
                    "max_stage_attempts": 1,
                    "max_mutations": 1,
                    "max_external_actions": 1,
                    "max_cost_usd": "1",
                }
            )
            _, _, grant = bootstrap(root, budgets=budgets)
            grant["scope"]["actions"].append("send")
            grant["scope"]["destinations"].append("network")
            grant["scope"]["exclusions"] = []
            atomic_write_json(
                f".the-loop/grants/{grant['grant_id']}.json",
                grant,
                project_root=root,
                record_type="grant",
            )
            clock = Clock("2026-08-16T08:01:00Z")
            runtime = RunRuntime(root, RUN_ID, clock=clock, id_factory=IdFactory(213))
            acquired = runtime.acquire(OWNER)
            clock.set("2026-08-16T08:01:10Z")
            marker_calls = 0
            real_append_marker = runtime._append_budget_marker

            def fail_third_marker(*args, **kwargs):
                nonlocal marker_calls
                marker_calls += 1
                if marker_calls == 3:
                    raise OSError("injected marker interruption")
                return real_append_marker(*args, **kwargs)

            def exact_limit_callback() -> None:
                clock.set("2026-08-16T08:02:00Z")

            with mock.patch.object(runtime, "_append_budget_marker", side_effect=fail_third_marker):
                result = runtime.perform_mutation(
                    acquired.token,
                    MutationRequest(
                        event_type="stage_started",
                        data={"stage": "build"},
                        action="send",
                        destination="network",
                        effect="external",
                        external_actions=1,
                        cost_usd="1",
                        stage_attempt="build",
                    ),
                    exact_limit_callback,
                )
            self.assertEqual("budget_reached:max_duration_seconds", result.snapshot.run["terminal_reason"]["code"])
            events = read_events(f".the-loop/runs/{RUN_ID}/events.ndjson", project_root=root)
            self.assertEqual(2, sum(event["type"] == "budget_reached" for event in events))

            clock.set("2026-08-16T08:03:00Z")
            with self.assertRaisesRegex(ContractError, r"budget_reached:max_duration_seconds prevents recovery"):
                runtime.recover(OWNER, reason="All exhausted budgets remain terminal")
            events = read_events(f".the-loop/runs/{RUN_ID}/events.ndjson", project_root=root)
            markers = [event for event in events if event["type"] == "budget_reached"]
            self.assertEqual(
                [
                    ("max_duration_seconds", None),
                    ("max_stage_attempts", "build"),
                    ("max_mutations", None),
                    ("max_external_actions", None),
                    ("max_cost_usd", None),
                ],
                [(event["data"]["budget"], event["data"]["stage"]) for event in markers],
            )
            self.assertTrue(all(event["projection"] == markers[0]["projection"] for event in markers))

            completion = events[-6]
            reordered = copy.deepcopy(markers[0])
            reordered["data"] = copy.deepcopy(markers[1]["data"])
            with self.assertRaisesRegex(ContractError, r"stable order"):
                validate_record("audit_event", reordered, previous=completion)

            duplicate = copy.deepcopy(markers[-1])
            duplicate["event_id"] = "ffffffff-ffff-4fff-8fff-ffffffffffff"
            duplicate["sequence"] += 1
            duplicate["previous_event_digest"] = markers[-1]["event_digest"]
            duplicate["event_digest"] = "f" * 64
            with self.assertRaisesRegex(ContractError, r"duplicate or unexpected budget marker"):
                validate_record("audit_event", duplicate, previous=markers[-1])

            skipped = copy.deepcopy(completion)
            skipped["event_id"] = "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee"
            skipped["sequence"] += 1
            skipped["previous_event_digest"] = completion["event_digest"]
            skipped["event_digest"] = "e" * 64
            with self.assertRaisesRegex(ContractError, r"required budget marker cannot be skipped"):
                validate_record("audit_event", skipped, previous=completion)

    def test_wrong_five_way_primary_is_rejected_before_semantic_completion_append(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            budgets = fixture("run.json")["budgets"]
            budgets.update(
                {
                    "max_duration_seconds": 60,
                    "max_stage_attempts": 1,
                    "max_mutations": 1,
                    "max_external_actions": 1,
                    "max_cost_usd": "1",
                }
            )
            _, _, grant = bootstrap(root, budgets=budgets)
            grant["scope"]["actions"].append("send")
            grant["scope"]["destinations"].append("network")
            grant["scope"]["exclusions"] = []
            atomic_write_json(
                f".the-loop/grants/{grant['grant_id']}.json",
                grant,
                project_root=root,
                record_type="grant",
            )
            clock = Clock("2026-08-16T08:01:00Z")
            runtime = RunRuntime(root, RUN_ID, clock=clock, id_factory=IdFactory(2130))
            acquired = runtime.acquire(OWNER)
            clock.set("2026-08-16T08:01:10Z")
            callback_calls: list[str] = []

            def exact_limit_callback() -> None:
                callback_calls.append("called")
                clock.set("2026-08-16T08:02:00Z")

            wrong_primary = ("max_cost_usd", "1", "1", None)
            with mock.patch.object(runtime, "_duration_budget", side_effect=[None, wrong_primary]):
                with self.assertRaisesRegex(ContractError, r"stable primary priority"):
                    runtime.perform_mutation(
                        acquired.token,
                        MutationRequest(
                            event_type="stage_started",
                            data={"stage": "build"},
                            action="send",
                            destination="network",
                            effect="external",
                            external_actions=1,
                            cost_usd="1",
                            stage_attempt="build",
                        ),
                        exact_limit_callback,
                    )
            events = read_events(f".the-loop/runs/{RUN_ID}/events.ndjson", project_root=root)
            self.assertEqual("operation_intended", events[-1]["type"])
            self.assertEqual(["called"], callback_calls)

            clock.set("2026-08-16T08:03:00Z")
            with self.assertRaisesRegex(ContractError, r"operation_outcome_unknown"):
                runtime.recover(OWNER, reason="Rejected completion must reconcile without replay")
            events = read_events(f".the-loop/runs/{RUN_ID}/events.ndjson", project_root=root)
            markers = [event for event in events if event["type"] == "budget_reached"]
            self.assertEqual(5, len(markers))
            self.assertTrue(
                all(
                    marker["projection"]["run"]["terminal_reason"]["code"]
                    == "external_operation_outcome_unknown"
                    for marker in markers
                )
            )
            self.assertEqual(["called"], callback_calls)

    def test_deterministic_budget_marker_contract_error_is_not_reported_as_success(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            budgets = fixture("run.json")["budgets"]
            budgets.update(
                {
                    "max_duration_seconds": 60,
                    "max_stage_attempts": 1,
                    "max_mutations": 1,
                    "max_external_actions": 1,
                    "max_cost_usd": "1",
                }
            )
            _, _, grant = bootstrap(root, budgets=budgets)
            grant["scope"]["actions"].append("send")
            grant["scope"]["destinations"].append("network")
            grant["scope"]["exclusions"] = []
            atomic_write_json(
                f".the-loop/grants/{grant['grant_id']}.json",
                grant,
                project_root=root,
                record_type="grant",
            )
            clock = Clock("2026-08-16T08:01:00Z")
            runtime = RunRuntime(root, RUN_ID, clock=clock, id_factory=IdFactory(2140))
            acquired = runtime.acquire(OWNER)
            clock.set("2026-08-16T08:01:10Z")

            def exact_limit_callback() -> None:
                clock.set("2026-08-16T08:02:00Z")

            with mock.patch.object(
                runtime,
                "_append_budget_marker",
                side_effect=ContractError("$.data", "invariant", "injected deterministic marker defect"),
            ):
                with self.assertRaisesRegex(ContractError, r"injected deterministic marker defect"):
                    runtime.perform_mutation(
                        acquired.token,
                        MutationRequest(
                            event_type="stage_started",
                            data={"stage": "build"},
                            action="send",
                            destination="network",
                            effect="external",
                            external_actions=1,
                            cost_usd="1",
                            stage_attempt="build",
                        ),
                        exact_limit_callback,
                    )
            events = read_events(f".the-loop/runs/{RUN_ID}/events.ndjson", project_root=root)
            self.assertEqual("stage_started", events[-1]["type"])
            self.assertFalse(any(event["type"] == "budget_reached" for event in events))

            clock.set("2026-08-16T08:03:00Z")
            with self.assertRaisesRegex(ContractError, r"budget_reached:max_duration_seconds prevents recovery"):
                runtime.recover(OWNER, reason="Repair deterministic marker suffix before recovery")
            events = read_events(f".the-loop/runs/{RUN_ID}/events.ndjson", project_root=root)
            self.assertEqual(5, sum(event["type"] == "budget_reached" for event in events))

    def test_external_unknown_outcome_preserves_reason_across_all_budget_markers(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            budgets = fixture("run.json")["budgets"]
            budgets.update(
                {
                    "max_duration_seconds": 60,
                    "max_stage_attempts": 1,
                    "max_mutations": 1,
                    "max_external_actions": 1,
                    "max_cost_usd": "1",
                }
            )
            _, _, grant = bootstrap(root, budgets=budgets)
            grant["scope"]["actions"].append("send")
            grant["scope"]["destinations"].append("network")
            grant["scope"]["exclusions"] = []
            atomic_write_json(
                f".the-loop/grants/{grant['grant_id']}.json",
                grant,
                project_root=root,
                record_type="grant",
            )
            clock = Clock("2026-08-16T08:01:00Z")
            runtime = RunRuntime(root, RUN_ID, clock=clock, id_factory=IdFactory(214))
            acquired = runtime.acquire(OWNER)
            clock.set("2026-08-16T08:01:10Z")
            callback_calls: list[str] = []

            def uncertain_callback() -> None:
                callback_calls.append("called")
                clock.set("2026-08-16T08:02:00Z")
                raise RuntimeError("injected simultaneous uncertainty")

            with self.assertRaisesRegex(RuntimeError, "injected simultaneous uncertainty"):
                runtime.perform_mutation(
                    acquired.token,
                    MutationRequest(
                        event_type="stage_started",
                        data={"stage": "build"},
                        action="send",
                        destination="network",
                        effect="external",
                        external_actions=1,
                        cost_usd="1",
                        stage_attempt="build",
                    ),
                    uncertain_callback,
                )
            events = read_events(f".the-loop/runs/{RUN_ID}/events.ndjson", project_root=root)
            markers = [event for event in events if event["type"] == "budget_reached"]
            self.assertEqual(5, len(markers))
            self.assertEqual(
                ["max_duration_seconds", "max_stage_attempts", "max_mutations", "max_external_actions", "max_cost_usd"],
                [event["data"]["budget"] for event in markers],
            )
            self.assertTrue(all(event["projection"]["run"]["status"] == "waiting_external" for event in markers))
            self.assertTrue(
                all(
                    event["projection"]["run"]["terminal_reason"]["code"]
                    == "external_operation_outcome_unknown"
                    for event in markers
                )
            )
            with self.assertRaisesRegex(ContractError, r"budget_reached:max_duration_seconds prevents recovery"):
                runtime.recover(OWNER, reason="Unknown external outcome must not replay")
            self.assertEqual(["called"], callback_calls)

    def test_failed_callback_elapsed_time_preserves_unknown_outcome_and_blocks_recovery(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            budgets = fixture("run.json")["budgets"]
            budgets["max_duration_seconds"] = 60
            bootstrap(root, budgets=budgets)
            clock = Clock("2026-08-16T08:01:00Z")
            runtime = RunRuntime(root, RUN_ID, clock=clock, id_factory=IdFactory(215))
            acquired = runtime.acquire(OWNER)
            clock.set("2026-08-16T08:01:10Z")

            def slow_failure() -> None:
                clock.set("2026-08-16T08:02:10Z")
                raise RuntimeError("injected callback failure")

            with self.assertRaisesRegex(RuntimeError, "injected callback failure"):
                runtime.perform_mutation(
                    acquired.token,
                    MutationRequest(
                        event_type="stage_completed",
                        data={"stage": "strategize", "outcome": "passed"},
                    ),
                    slow_failure,
                )
            events = read_events(f".the-loop/runs/{RUN_ID}/events.ndjson", project_root=root)
            reconciled = events[-2]
            self.assertEqual("operation_reconciled", reconciled["type"])
            self.assertEqual(70, reconciled["projection"]["run"]["usage"]["duration_seconds"])
            self.assertEqual(
                "operation_outcome_unknown",
                reconciled["projection"]["run"]["terminal_reason"]["code"],
            )
            exhausted = events[-1]
            self.assertEqual("budget_reached", exhausted["type"])
            self.assertEqual(
                "operation_outcome_unknown",
                exhausted["projection"]["run"]["terminal_reason"]["code"],
            )
            self.assertEqual("failed", exhausted["projection"]["run"]["status"])
            self.assertEqual("max_duration_seconds", exhausted["data"]["budget"])
            self.assertEqual(70, exhausted["data"]["observed"])
            before_recovery = len(events)
            with self.assertRaisesRegex(ContractError, r"budget_reached:max_duration_seconds prevents recovery"):
                runtime.recover(OWNER, reason="Must not reset exhausted duration")
            self.assertEqual(
                before_recovery,
                len(read_events(f".the-loop/runs/{RUN_ID}/events.ndjson", project_root=root)),
            )

    def test_external_unknown_outcome_keeps_priority_at_exact_mutation_budget(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            budgets = fixture("run.json")["budgets"]
            budgets["max_mutations"] = 1
            budgets["max_external_actions"] = 2
            _, _, grant = bootstrap(root, budgets=budgets)
            grant["scope"]["actions"].append("send")
            grant["scope"]["destinations"].append("network")
            grant["scope"]["exclusions"] = []
            atomic_write_json(
                f".the-loop/grants/{grant['grant_id']}.json",
                grant,
                project_root=root,
                record_type="grant",
            )
            clock = Clock("2026-08-16T08:01:00Z")
            runtime = RunRuntime(root, RUN_ID, clock=clock, id_factory=IdFactory(218))
            acquired = runtime.acquire(OWNER)
            clock.set("2026-08-16T08:02:00Z")
            callback_calls: list[str] = []

            def uncertain_send() -> None:
                callback_calls.append("called")
                raise RuntimeError("injected external uncertainty")

            request = MutationRequest(
                event_type="stage_completed",
                data={"stage": "strategize", "outcome": "passed"},
                action="send",
                destination="network",
                effect="external",
                external_actions=1,
            )
            with self.assertRaisesRegex(RuntimeError, "injected external uncertainty"):
                runtime.perform_mutation(acquired.token, request, uncertain_send)

            events = read_events(f".the-loop/runs/{RUN_ID}/events.ndjson", project_root=root)
            self.assertEqual(["operation_reconciled", "budget_reached"], [event["type"] for event in events[-2:]])
            marker = events[-1]
            self.assertEqual("max_mutations", marker["data"]["budget"])
            self.assertEqual(1, marker["data"]["observed"])
            self.assertEqual("waiting_external", marker["projection"]["run"]["status"])
            self.assertEqual(
                "external_operation_outcome_unknown",
                marker["projection"]["run"]["terminal_reason"]["code"],
            )
            retry_calls: list[str] = []
            with self.assertRaises(ContractError):
                runtime.perform_mutation(acquired.token, request, lambda: retry_calls.append("replayed"))
            self.assertEqual(["called"], callback_calls)
            self.assertEqual([], retry_calls)

    def test_unknown_outcome_repairs_missing_exact_budget_marker_without_replay(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            budgets = fixture("run.json")["budgets"]
            budgets["max_mutations"] = 1
            bootstrap(root, budgets=budgets)
            clock = Clock("2026-08-16T08:01:00Z")
            runtime = RunRuntime(root, RUN_ID, clock=clock, id_factory=IdFactory(219))
            acquired = runtime.acquire(OWNER)
            clock.set("2026-08-16T08:02:00Z")
            callback_calls: list[str] = []

            def uncertain_write() -> None:
                callback_calls.append("called")
                raise RuntimeError("injected local uncertainty")

            with mock.patch.object(runtime, "_append_budget_marker", side_effect=OSError("marker unavailable")):
                with self.assertRaisesRegex(RuntimeError, "injected local uncertainty"):
                    runtime.perform_mutation(
                        acquired.token,
                        MutationRequest(
                            event_type="stage_completed",
                            data={"stage": "strategize", "outcome": "passed"},
                        ),
                        uncertain_write,
                    )

            events = read_events(f".the-loop/runs/{RUN_ID}/events.ndjson", project_root=root)
            self.assertEqual("operation_reconciled", events[-1]["type"])
            self.assertEqual("operation_outcome_unknown", events[-1]["projection"]["run"]["terminal_reason"]["code"])

            clock.set("2026-08-16T08:03:00Z")
            with self.assertRaisesRegex(ContractError, r"budget_reached:max_mutations prevents recovery"):
                runtime.recover(OWNER, reason="Exhausted usage cannot be reset")
            events = read_events(f".the-loop/runs/{RUN_ID}/events.ndjson", project_root=root)
            self.assertEqual("budget_reached", events[-1]["type"])
            self.assertEqual("operation_outcome_unknown", events[-1]["projection"]["run"]["terminal_reason"]["code"])
            self.assertEqual(1, events[-1]["data"]["observed"])
            self.assertEqual(["called"], callback_calls)

    def test_unknown_outcome_budget_marker_requires_exact_prior_projection(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            budgets = fixture("run.json")["budgets"]
            budgets["max_mutations"] = 1
            bootstrap(root, budgets=budgets)
            clock = Clock("2026-08-16T08:01:00Z")
            runtime = RunRuntime(root, RUN_ID, clock=clock, id_factory=IdFactory(220))
            acquired = runtime.acquire(OWNER)
            clock.set("2026-08-16T08:02:00Z")

            with self.assertRaisesRegex(RuntimeError, "injected uncertainty"):
                runtime.perform_mutation(
                    acquired.token,
                    MutationRequest(
                        event_type="stage_completed",
                        data={"stage": "strategize", "outcome": "passed"},
                    ),
                    lambda: (_ for _ in ()).throw(RuntimeError("injected uncertainty")),
                )

            events = read_events(f".the-loop/runs/{RUN_ID}/events.ndjson", project_root=root)
            reconciled, marker = events[-2:]
            validate_record("audit_event", marker, previous=reconciled, expected_owner=OWNER)

            overwritten = copy.deepcopy(marker)
            overwritten["projection"]["run"]["terminal_reason"] = {
                "code": "budget_reached:max_mutations",
                "explanation": "Budget max_mutations reached its configured limit.",
            }
            with self.assertRaisesRegex(ContractError, r"must preserve (?:its source projection|the prior unknown-outcome)"):
                validate_record("audit_event", overwritten, previous=reconciled, expected_owner=OWNER)

            with self.assertRaisesRegex(ContractError, r"requires the immediately prior reconciliation event"):
                validate_record("audit_event", marker, expected_owner=OWNER)

    def test_successful_callback_at_lease_boundary_never_returns_active(self) -> None:
        cases = (
            ("2026-08-16T08:05:59.999999Z", "active", 299.999999),
            ("2026-08-16T08:06:00Z", "failed", 300),
            ("2026-08-16T08:06:01Z", "failed", 300),
        )
        for finished_at, expected_status, expected_duration in cases:
            with self.subTest(finished_at=finished_at), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                bootstrap(root)
                clock = Clock("2026-08-16T08:01:00Z")
                runtime = RunRuntime(root, RUN_ID, clock=clock, id_factory=IdFactory(225))
                acquired = runtime.acquire(OWNER)
                clock.set("2026-08-16T08:01:00Z")

                def boundary_callback() -> str:
                    clock.set(finished_at)
                    return "committed"

                result = runtime.perform_mutation(
                    acquired.token,
                    MutationRequest(
                        event_type="stage_completed",
                        data={"stage": "strategize", "outcome": "passed"},
                    ),
                    boundary_callback,
                )
                self.assertEqual("committed", result.value)
                self.assertEqual(expected_status, result.snapshot.run["status"])
                self.assertEqual(expected_duration, result.snapshot.run["usage"]["duration_seconds"])
                if expected_status == "failed":
                    self.assertEqual("run_failed", result.snapshot.run["terminal_reason"]["code"])
                    recovered = runtime.recover(OWNER, reason="Lease expired during the completed callback")
                    self.assertEqual(1, recovered.lease["generation"])

    def test_mutation_budget_exhaustion_is_failed_and_truthful(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            budgets = fixture("run.json")["budgets"]
            budgets["max_mutations"] = 1
            bootstrap(root, budgets=budgets)
            clock = Clock("2026-08-16T08:01:00Z")
            runtime = RunRuntime(root, RUN_ID, clock=clock, id_factory=IdFactory(300))
            acquired = runtime.acquire(OWNER)
            clock.set("2026-08-16T08:02:00Z")
            result = runtime.perform_mutation(
                acquired.token,
                MutationRequest(
                    event_type="stage_completed",
                    data={"stage": "strategize", "outcome": "passed"},
                ),
                lambda: "complete",
            )
            self.assertEqual("failed", result.snapshot.run["status"])
            self.assertEqual(
                "budget_reached:max_mutations",
                result.snapshot.run["terminal_reason"]["code"],
            )
            event = read_events(f".the-loop/runs/{RUN_ID}/events.ndjson", project_root=root)[-1]
            self.assertEqual("budget_reached", event["type"])
            self.assertEqual(1, event["data"]["observed"])
            events = read_events(f".the-loop/runs/{RUN_ID}/events.ndjson", project_root=root)
            self.assertEqual("stage_completed", events[-2]["type"])
            self.assertEqual("failed", events[-2]["projection"]["run"]["status"])
            self.assertIsNone(events[-2]["projection"]["pending_operation"])

    def test_exact_budget_completion_repairs_a_missing_audit_marker(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            budgets = fixture("run.json")["budgets"]
            budgets["max_mutations"] = 1
            bootstrap(root, budgets=budgets)
            clock = Clock("2026-08-16T08:01:00Z")
            runtime = RunRuntime(root, RUN_ID, clock=clock, id_factory=IdFactory(307))
            acquired = runtime.acquire(OWNER)
            clock.set("2026-08-16T08:02:00Z")
            with mock.patch.object(runtime, "_append_budget_marker", side_effect=OSError("injected marker failure")):
                result = runtime.perform_mutation(
                    acquired.token,
                    MutationRequest(
                        event_type="stage_completed",
                        data={"stage": "strategize", "outcome": "passed"},
                    ),
                    lambda: None,
                )
            self.assertEqual("failed", result.snapshot.run["status"])
            events = read_events(f".the-loop/runs/{RUN_ID}/events.ndjson", project_root=root)
            self.assertEqual("stage_completed", events[-1]["type"])
            self.assertEqual("failed", events[-1]["projection"]["run"]["status"])
            clock.set("2026-08-16T08:03:00Z")
            with self.assertRaisesRegex(ContractError, r"\[transition\]"):
                runtime.heartbeat(acquired.token)
            events = read_events(f".the-loop/runs/{RUN_ID}/events.ndjson", project_root=root)
            self.assertEqual("budget_reached", events[-1]["type"])
            self.assertEqual("max_mutations", events[-1]["data"]["budget"])

    def test_committed_budget_marker_survives_post_append_error(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            budgets = fixture("run.json")["budgets"]
            budgets["max_mutations"] = 1
            bootstrap(root, budgets=budgets)
            clock = Clock("2026-08-16T08:01:00Z")
            runtime = RunRuntime(root, RUN_ID, clock=clock, id_factory=IdFactory(309))
            acquired = runtime.acquire(OWNER)
            clock.set("2026-08-16T08:02:00Z")
            real_append_marker = runtime._append_budget_marker

            def append_then_raise(*args, **kwargs):
                real_append_marker(*args, **kwargs)
                raise OSError("injected post-append failure")

            with mock.patch.object(runtime, "_append_budget_marker", side_effect=append_then_raise):
                result = runtime.perform_mutation(
                    acquired.token,
                    MutationRequest(
                        event_type="stage_completed",
                        data={"stage": "strategize", "outcome": "passed"},
                    ),
                    lambda: None,
                )
            self.assertEqual("failed", result.snapshot.run["status"])
            event = read_events(f".the-loop/runs/{RUN_ID}/events.ndjson", project_root=root)[-1]
            self.assertEqual("budget_reached", event["type"])

    def test_committed_event_survives_projection_install_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bootstrap(root)
            clock = Clock("2026-08-16T08:01:00Z")
            runtime = RunRuntime(root, RUN_ID, clock=clock, id_factory=IdFactory(311))
            acquired = runtime.acquire(OWNER)
            clock.set("2026-08-16T08:02:00Z")
            real_install = runtime._install_projection
            calls = 0

            def fail_completion_install(*args, **kwargs):
                nonlocal calls
                calls += 1
                if calls == 3:
                    raise OSError("injected projection failure")
                return real_install(*args, **kwargs)

            callbacks: list[str] = []
            with mock.patch.object(runtime, "_install_projection", side_effect=fail_completion_install):
                result = runtime.perform_mutation(
                    acquired.token,
                    MutationRequest(
                        event_type="stage_completed",
                        data={"stage": "strategize", "outcome": "passed"},
                    ),
                    lambda: callbacks.append("called"),
                )
            self.assertEqual(["called"], callbacks)
            self.assertEqual("active", result.snapshot.run["status"])
            events = read_events(f".the-loop/runs/{RUN_ID}/events.ndjson", project_root=root)
            self.assertEqual("stage_completed", events[-1]["type"])

    def test_unverifiable_head_after_projection_failure_forbids_retry(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bootstrap(root)
            clock = Clock("2026-08-16T08:01:00Z")
            runtime = RunRuntime(root, RUN_ID, clock=clock, id_factory=IdFactory(313))
            acquired = runtime.acquire(OWNER)
            clock.set("2026-08-16T08:02:00Z")
            real_install = runtime._install_projection
            real_events = runtime._events
            install_calls = 0
            event_calls = 0

            def fail_completion_install(*args, **kwargs):
                nonlocal install_calls
                install_calls += 1
                if install_calls == 3:
                    raise OSError("injected projection failure")
                return real_install(*args, **kwargs)

            def fail_commit_verification(*args, **kwargs):
                nonlocal event_calls
                event_calls += 1
                if event_calls == 2:
                    raise OSError("injected head read failure")
                return real_events(*args, **kwargs)

            callbacks: list[str] = []
            with mock.patch.object(runtime, "_install_projection", side_effect=fail_completion_install), mock.patch.object(
                runtime,
                "_events",
                side_effect=fail_commit_verification,
            ):
                with self.assertRaisesRegex(ContractError, r"\[committed_state_unknown\].*do not retry"):
                    runtime.perform_mutation(
                        acquired.token,
                        MutationRequest(
                            event_type="stage_completed",
                            data={"stage": "strategize", "outcome": "passed"},
                        ),
                        lambda: callbacks.append("called"),
                    )
            self.assertEqual(["called"], callbacks)
            events = read_events(f".the-loop/runs/{RUN_ID}/events.ndjson", project_root=root)
            self.assertEqual("stage_completed", events[-1]["type"])

    def test_zero_mutation_budget_denies_callback_without_counting_it(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            budgets = fixture("run.json")["budgets"]
            budgets["max_mutations"] = 0
            bootstrap(root, budgets=budgets)
            clock = Clock("2026-08-16T08:01:00Z")
            runtime = RunRuntime(root, RUN_ID, clock=clock, id_factory=IdFactory(315))
            acquired = runtime.acquire(OWNER)
            clock.set("2026-08-16T08:02:00Z")
            calls: list[str] = []
            with self.assertRaisesRegex(ContractError, r"budget_reached:max_mutations"):
                runtime.perform_mutation(
                    acquired.token,
                    MutationRequest(
                        event_type="stage_completed",
                        data={"stage": "strategize", "outcome": "passed"},
                    ),
                    lambda: calls.append("called"),
                )
            self.assertEqual([], calls)
            event = read_events(f".the-loop/runs/{RUN_ID}/events.ndjson", project_root=root)[-1]
            self.assertEqual("budget_reached", event["type"])
            self.assertEqual(0, event["projection"]["run"]["usage"]["mutations"])
            self.assertEqual(0, event["data"]["observed"])
            clock.set("2026-08-16T08:07:00Z")
            with self.assertRaisesRegex(ContractError, r"budget_reached:max_mutations prevents recovery"):
                runtime.recover(OWNER, reason="A zero-limit denial remains terminal")

    def test_callback_usage_units_cannot_be_declared_away_or_inflated(self) -> None:
        for request in (
            MutationRequest(
                event_type="stage_completed",
                data={"stage": "strategize", "outcome": "passed"},
                mutations=0,
            ),
            MutationRequest(
                event_type="stage_completed",
                data={"stage": "strategize", "outcome": "passed"},
                mutations=2,
            ),
            MutationRequest(
                event_type="evidence_recorded",
                data={"evidence_id": "99999999-9999-4999-8999-999999999999", "outcome": "passed"},
                action="send",
                destination="network",
                effect="external",
                external_actions=0,
            ),
            MutationRequest(
                event_type="evidence_recorded",
                data={"evidence_id": "99999999-9999-4999-8999-999999999999", "outcome": "passed"},
                action="send",
                destination="network",
                effect="external",
                external_actions=2,
            ),
        ):
            with self.subTest(request=request), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                budgets = fixture("run.json")["budgets"]
                budgets["max_external_actions"] = 2
                bootstrap(root, budgets=budgets)
                clock = Clock("2026-08-16T08:01:00Z")
                runtime = RunRuntime(root, RUN_ID, clock=clock, id_factory=IdFactory(325))
                acquired = runtime.acquire(OWNER)
                clock.set("2026-08-16T08:02:00Z")
                callbacks: list[str] = []
                before = len(read_events(f".the-loop/runs/{RUN_ID}/events.ndjson", project_root=root))
                with self.assertRaisesRegex(ContractError, r"\[invariant\]"):
                    runtime.perform_mutation(acquired.token, request, lambda: callbacks.append("called"))
                self.assertEqual([], callbacks)
                after = len(read_events(f".the-loop/runs/{RUN_ID}/events.ndjson", project_root=root))
                self.assertEqual(before, after)

    def test_outward_action_cannot_be_spoofed_as_local_or_bypass_external_budget(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bootstrap(root)
            grant = fixture("grant.json")
            grant["scope"]["actions"] = ["local_write", "send"]
            grant["scope"]["destinations"] = ["repository", "network"]
            grant["scope"]["exclusions"] = []
            atomic_write_json(
                f".the-loop/grants/{grant['grant_id']}.json",
                grant,
                project_root=root,
                record_type="grant",
            )
            clock = Clock("2026-08-16T08:01:00Z")
            runtime = RunRuntime(root, RUN_ID, clock=clock, id_factory=IdFactory(327))
            acquired = runtime.acquire(OWNER)
            clock.set("2026-08-16T08:02:00Z")
            callbacks: list[str] = []
            spoofed = MutationRequest(
                event_type="evidence_recorded",
                data={"evidence_id": "99999999-9999-4999-8999-999999999999", "outcome": "passed"},
                action="send",
                destination="network",
                effect="local",
            )
            with self.assertRaisesRegex(ContractError, r"\[invariant\].*must be declared external"):
                runtime.perform_mutation(acquired.token, spoofed, lambda: callbacks.append("spoofed"))
            outward = MutationRequest(
                event_type="evidence_recorded",
                data={"evidence_id": "99999999-9999-4999-8999-999999999999", "outcome": "passed"},
                action="send",
                destination="network",
                effect="external",
                external_actions=1,
            )
            with self.assertRaisesRegex(ContractError, r"budget_reached:max_external_actions"):
                runtime.perform_mutation(acquired.token, outward, lambda: callbacks.append("outward"))
            self.assertEqual([], callbacks)
            event = read_events(f".the-loop/runs/{RUN_ID}/events.ndjson", project_root=root)[-1]
            self.assertEqual("max_external_actions", event["data"]["budget"])

    def test_stage_attempt_budget_is_per_stage(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            budgets = fixture("run.json")["budgets"]
            budgets["max_stage_attempts"] = 1
            bootstrap(root, budgets=budgets)
            clock = Clock("2026-08-16T08:01:00Z")
            runtime = RunRuntime(root, RUN_ID, clock=clock, id_factory=IdFactory(330))
            acquired = runtime.acquire(OWNER)
            clock.set("2026-08-16T08:02:00Z")
            result = runtime.perform_mutation(
                acquired.token,
                MutationRequest(
                    event_type="stage_started",
                    data={"stage": "build"},
                    stage_attempt="build",
                ),
                lambda: None,
            )
            attempts = result.snapshot.run["usage"]["stage_attempts"]
            self.assertEqual(1, attempts["build"])
            self.assertEqual(0, attempts["test"])
            self.assertEqual("budget_reached:max_stage_attempts", result.snapshot.run["terminal_reason"]["code"])
            event = read_events(f".the-loop/runs/{RUN_ID}/events.ndjson", project_root=root)[-1]
            self.assertEqual("build", event["data"]["stage"])
            clock.set("2026-08-16T08:03:00Z")
            with self.assertRaisesRegex(ContractError, r"\[transition\]"):
                runtime.heartbeat(acquired.token)

    def test_active_duration_budget_counts_only_valid_lease_interval(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            budgets = fixture("run.json")["budgets"]
            budgets["max_duration_seconds"] = 60
            bootstrap(root, budgets=budgets)
            clock = Clock("2026-08-16T08:01:00Z")
            runtime = RunRuntime(root, RUN_ID, clock=clock, id_factory=IdFactory(350))
            acquired = runtime.acquire(OWNER)
            clock.set("2026-08-16T08:02:00Z")
            exhausted = runtime.heartbeat(acquired.token)
            self.assertEqual(60, exhausted.run["usage"]["duration_seconds"])
            self.assertEqual("failed", exhausted.run["status"])
            self.assertEqual("budget_reached:max_duration_seconds", exhausted.run["terminal_reason"]["code"])

    def test_subsecond_heartbeats_cannot_bypass_duration_budget(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            budgets = fixture("run.json")["budgets"]
            budgets["max_duration_seconds"] = 1
            bootstrap(root, budgets=budgets)
            clock = Clock("2026-08-16T08:01:00Z")
            runtime = RunRuntime(root, RUN_ID, clock=clock, id_factory=IdFactory(360))
            snapshot = runtime.acquire(OWNER)
            clock.set("2026-08-16T08:01:00.600000Z")
            snapshot = runtime.heartbeat(snapshot.token)
            self.assertEqual(0.6, snapshot.run["usage"]["duration_seconds"])
            clock.set("2026-08-16T08:01:01.200000Z")
            snapshot = runtime.heartbeat(snapshot.token)
            self.assertEqual(1.2, snapshot.run["usage"]["duration_seconds"])
            self.assertEqual("failed", snapshot.run["status"])
            self.assertEqual(
                "budget_reached:max_duration_seconds",
                snapshot.run["terminal_reason"]["code"],
            )

    def test_decimal_cost_reservation_is_exact_and_null_denies_spend(self) -> None:
        huge_whole = "1000000000000000000000000000000000000000000000000"
        cases = (
            (None, ("0.01",), None),
            ("0.3", ("0.1", "0.1", "0.1"), "0.3"),
            (f"{huge_whole}.3", (huge_whole, "0.1", "0.2"), f"{huge_whole}.3"),
        )
        for limit, costs, expected_cost in cases:
            with self.subTest(limit=limit), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                budgets = fixture("run.json")["budgets"]
                budgets["max_cost_usd"] = limit
                bootstrap(root, budgets=budgets)
                clock = Clock("2026-08-16T08:01:00Z")
                runtime = RunRuntime(root, RUN_ID, clock=clock, id_factory=IdFactory(370))
                snapshot = runtime.acquire(OWNER)
                callback_calls = 0
                for index, cost in enumerate(costs, start=1):
                    clock.set(f"2026-08-16T08:0{index + 1}:00Z")

                    def callback() -> None:
                        nonlocal callback_calls
                        callback_calls += 1

                    request = MutationRequest(
                        event_type="evidence_recorded",
                        data={
                            "evidence_id": f"{index:08x}-0000-4000-8000-000000000000",
                            "outcome": "passed",
                        },
                        cost_usd=cost,
                    )
                    if limit is None:
                        with self.assertRaisesRegex(ContractError, r"budget_reached:max_cost_usd"):
                            runtime.perform_mutation(snapshot.token, request, callback)
                    else:
                        result = runtime.perform_mutation(snapshot.token, request, callback)
                        snapshot = result.snapshot
                if expected_cost is not None:
                    self.assertEqual(len(costs), callback_calls)
                    self.assertEqual(expected_cost, snapshot.run["usage"]["cost_usd"])
                    self.assertEqual("budget_reached:max_cost_usd", snapshot.run["terminal_reason"]["code"])
                else:
                    self.assertEqual(0, callback_calls)
                    event = read_events(f".the-loop/runs/{RUN_ID}/events.ndjson", project_root=root)[-1]
                    self.assertEqual("budget_reached", event["type"])
                    self.assertIsNone(event["projection"]["run"]["usage"]["cost_usd"])
                    self.assertEqual("0", event["data"]["observed"])

    def test_cost_reservation_rejects_exponent_and_excess_precision(self) -> None:
        for cost in ("1e-3", "0.0000001", 0.30000000000000004):
            with self.subTest(cost=cost), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                budgets = fixture("run.json")["budgets"]
                budgets["max_cost_usd"] = "1"
                bootstrap(root, budgets=budgets)
                clock = Clock("2026-08-16T08:01:00Z")
                runtime = RunRuntime(root, RUN_ID, clock=clock, id_factory=IdFactory(390))
                acquired = runtime.acquire(OWNER)
                clock.set("2026-08-16T08:02:00Z")
                callbacks: list[str] = []
                with self.assertRaisesRegex(ContractError, r"\[cost\]"):
                    runtime.perform_mutation(
                        acquired.token,
                        MutationRequest(
                            event_type="evidence_recorded",
                            data={
                                "evidence_id": "99999999-9999-4999-8999-999999999999",
                                "outcome": "passed",
                            },
                            cost_usd=cost,
                        ),
                        lambda: callbacks.append("called"),
                    )
                self.assertEqual([], callbacks)

    def test_cost_overage_uses_decimal_not_lexicographic_comparison(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            budgets = fixture("run.json")["budgets"]
            budgets["max_cost_usd"] = "10"
            bootstrap(root, budgets=budgets)
            clock = Clock("2026-08-16T08:01:00Z")
            runtime = RunRuntime(root, RUN_ID, clock=clock, id_factory=IdFactory(395))
            snapshot = runtime.acquire(OWNER)
            clock.set("2026-08-16T08:02:00Z")
            first = runtime.perform_mutation(
                snapshot.token,
                MutationRequest(
                    event_type="evidence_recorded",
                    data={"evidence_id": "99999999-9999-4999-8999-999999999999", "outcome": "passed"},
                    cost_usd="9",
                ),
                lambda: "first",
            )
            self.assertEqual("9", first.snapshot.run["usage"]["cost_usd"])
            clock.set("2026-08-16T08:03:00Z")
            callbacks: list[str] = []
            with self.assertRaisesRegex(ContractError, r"\[budget_reservation\]"):
                runtime.perform_mutation(
                    first.snapshot.token,
                    MutationRequest(
                        event_type="evidence_recorded",
                        data={"evidence_id": "88888888-8888-4888-8888-888888888888", "outcome": "passed"},
                        cost_usd="2",
                    ),
                    lambda: callbacks.append("called"),
                )
            self.assertEqual([], callbacks)
            event = read_events(f".the-loop/runs/{RUN_ID}/events.ndjson", project_root=root)[-1]
            self.assertEqual("9", event["projection"]["run"]["usage"]["cost_usd"])

    def test_hard_crash_pending_operation_is_reconciled_without_replay(self) -> None:
        for effect, expected_status in (("local", "failed"), ("external", "waiting_external")):
            with self.subTest(effect=effect), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                budgets = fixture("run.json")["budgets"]
                budgets["max_external_actions"] = 2
                bootstrap(root, budgets=budgets)
                if effect == "external":
                    grant = fixture("grant.json")
                    grant["scope"]["actions"].append("send")
                    grant["scope"]["destinations"].append("network")
                    grant["scope"]["exclusions"] = []
                    atomic_write_json(
                        f".the-loop/grants/{grant['grant_id']}.json",
                        grant,
                        project_root=root,
                        record_type="grant",
                    )
                clock = Clock("2026-08-16T08:01:00Z")
                runtime = RunRuntime(root, RUN_ID, clock=clock, id_factory=IdFactory(400))
                acquired = runtime.acquire(OWNER)
                context = multiprocessing.get_context("fork")
                worker = context.Process(
                    target=crash_during_mutation,
                    args=(str(root), acquired.lease, effect),
                )
                worker.start()
                worker.join(10)
                self.assertEqual(23, worker.exitcode)
                events = read_events(f".the-loop/runs/{RUN_ID}/events.ndjson", project_root=root)
                self.assertEqual("operation_intended", events[-1]["type"])
                self.assertEqual(effect, events[-1]["projection"]["pending_operation"]["effect"])

                clock.set("2026-08-16T08:03:00Z")
                with self.assertRaisesRegex(ContractError, r"\[operation_outcome_unknown\]"):
                    runtime.heartbeat(acquired.token)
                events = read_events(f".the-loop/runs/{RUN_ID}/events.ndjson", project_root=root)
                self.assertEqual("operation_reconciled", events[-1]["type"])
                self.assertEqual("unknown", events[-1]["data"]["outcome"])
                self.assertEqual(expected_status, events[-1]["projection"]["run"]["status"])
                self.assertEqual(1, events[-1]["projection"]["run"]["usage"]["mutations"])
                self.assertEqual(
                    1 if effect == "external" else 0,
                    events[-1]["projection"]["run"]["usage"]["external_actions"],
                )
                self.assertIsNone(events[-1]["projection"]["pending_operation"])
                self.assertEqual("called-once\n", (root / f"{effect}-callback-marker").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
