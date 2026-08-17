# Backend and state schema

## Scope

v0.1 has no remote backend, user account or hosted database. This document defines the local state store that makes bounded agent work resumable, inspectable and safe.

The schemas are normative even when a harness performs the workflow through instructions rather than a shared executable.

## Storage layout

```text
<project>/.the-loop/
  config.json
  STOP                         external kill switch, present means stop
  runs/
    <run-id>/
      run.json                 current projected state
      lease.json               current writer lease
      events.ndjson            append-only audit events
      issues.json              current issue ledger projection
      evidence/
        <evidence-id>.json
      artifacts/               ignored local outputs and command logs
  grants/
    <grant-id>.json             authority grants and revocations
  installs/
    <receipt-id>.json           setup operations and uninstall ownership
```

`.the-loop/` is ignored by Git except optional example fixtures under `tests/`. Runtime directories use owner-only permissions where the platform supports them.

## Common rules

- All records include `schema_version`.
- IDs are UUIDv4 strings generated locally.
- Timestamps use UTC RFC 3339 with a `Z` suffix.
- Enum values use lowercase snake case.
- Missing required data is an error. It is never inferred from prose.
- Writes use a temporary sibling file followed by atomic replacement.
- Ordinary worker and domain events are append-only under a valid lease. Run creation, authority control and the lease-independent kill-switch reducer follow their exact event-specific rules. Separately, an intent committed under a then-valid matching lease may be closed after expiry only by its exact declared semantic completion or reconciliation and the required deterministic, callback-free `budget_reached` marker sequence for that source event, as specified below.
- Unknown schema versions are read-only until migrated.
- Public examples use synthetic paths and actors.

## Config record

Path: `.the-loop/config.json`

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `schema_version` | string | yes | Initial value `1.0`. |
| `project_id` | UUID | yes | Stable local project identity. |
| `default_mode` | enum | yes | `loop` or `auto` in v0.1. |
| `state_root` | relative path | yes | Default `.the-loop`. Must remain inside project unless explicitly approved. |
| `kill_switches` | string array | yes | Default `['.the-loop/STOP']`. External paths require explicit config. |
| `heartbeat_seconds` | integer | yes | Default 120, range 15 to 600. |
| `lease_seconds` | integer | yes | Default 300, greater than heartbeat interval. |
| `routing` | object | yes | Capability pins and disabled providers. |
| `budgets` | object | yes | Safe defaults for bounded missions. |
| `telemetry` | boolean | yes | Must be `false` in v0.1. |
| `harnesses` | object | yes | Last discovery and behavior status per harness. |

### Budget object

| Field | Type | Default | Meaning |
| --- | --- | --- | --- |
| `max_duration_seconds` | integer | 7200 | Accumulated validated active-lease time for one mission. |
| `max_stage_attempts` | integer | 3 | Maximum attempts for each lifecycle stage before stuck-loop halt. |
| `max_mutations` | integer | 100 | State-changing action ceiling. |
| `max_external_actions` | integer | 0 | No outward action without an explicit grant. |
| `max_cost_usd` | fixed-point decimal string or null | null | Up to six fractional digits; null means no spending authority, not unlimited spend. |

## Install receipt

Path: `.the-loop/installs/<receipt-id>.json`

| Field | Type | Required |
| --- | --- | --- |
| `schema_version` | string | yes |
| `receipt_id` | UUID | yes |
| `created_at` | timestamp | yes |
| `actor` | string | yes |
| `source_version` | string | yes |
| `target_root` | path | yes |
| `harnesses` | enum array | yes |
| `operations` | operation array | yes |
| `result` | enum | yes: `complete`, `partial`, `rolled_back`, `failed` |

Each operation records action (`copy`, `link`, `mkdir`, `skip`), source digest, destination, pre-existing destination digest or null, resulting digest and rollback action. Uninstall may remove only an unchanged path created by that receipt.

## Harness status

The harness enum covers the five first-class adapters: `codex`, `claude_code`,
`kimi_code`, `opencode` and `deepseek_harness`.

| Field | Type | Meaning |
| --- | --- | --- |
| `installed` | boolean | Executable or host integration found. |
| `version` | string or null | Reported version. |
| `discovery` | enum | `verified`, `failed`, `denied`, `unverified`. |
| `behavior` | enum | `verified`, `failed`, `denied`, `unverified`. |
| `skill_roots` | path array | Roots inspected by Doctor. |
| `collisions` | object array | Name, sources and winning precedence where knowable. |
| `pack_status` | enum | `complete`, `incomplete`, `integrity_unverified`, or `unverified`; ready requires `complete`. |
| `missing_skills` | string array | Required 31-package candidate names not verified in the inspected roots. |
| `pack_receipt_id` | UUID or null | Complete Setup receipt whose package and toolkit digests still match. |
| `pack_digest` | digest or null | Path-free digest of the verified receipt-owned pack identity. |
| `environment_digest` | digest or null | Doctor-derived harness, adapter, pack and runtime fingerprint supplied to an approved probe. |
| `checked_at` | timestamp | Freshness of result. |
| `evidence_id` | UUID or null | Behavior probe evidence. |
| `behavior_evidence` | object or null | Typed matching harness, version, project scope, `portable-skill-invocation` capability, allowed permission result, Doctor-derived environment digest and observation time. |

## Run record

Path: `.the-loop/runs/<run-id>/run.json`

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `schema_version` | string | yes | Initial value `1.0`. |
| `run_id` | UUID | yes | Matches directory. |
| `asset` | object | yes | Name, root, track and declared boundaries. |
| `mode` | enum | yes | `loop` or `auto` in v0.1. |
| `status` | enum | yes | Defined below. |
| `stage` | enum or null | Current lifecycle stage. |
| `objective` | string | yes | One bounded outcome. |
| `done_gate` | string array | yes | Testable conditions. |
| `authority_grant_id` | UUID | yes | Active grant, including default authority. |
| `budgets` | object | yes | Frozen mission budgets. |
| `usage` | object | yes | Duration, attempts, mutations, external actions and recorded cost. |
| `owner` | object or null | yes | Harness, actor and session identifier. |
| `selected_routes` | object | yes | Capability to provider decision. |
| `open_blocking_issues` | integer | yes | Derived but stored for fast status. |
| `last_heartbeat_at` | timestamp or null | yes | Liveness, not proof of progress. |
| `created_at` | timestamp | yes |  |
| `updated_at` | timestamp | yes |  |
| `terminal_reason` | object or null | yes | Code and explanation for terminal or waiting state. |

### Run status enum

`draft`, `ready`, `active`, `waiting_approval`, `waiting_external`, `blocked`, `failed`, `halted_kill_switch`, `complete`, `cancelled`.

### Stage enum

`strategize`, `spec_pack`, `build`, `test`, `resolve`, `close`.

### State transitions

| From | Allowed next states |
| --- | --- |
| `draft` | `ready`, `cancelled` |
| `ready` | `active`, `cancelled` |
| `active` | `waiting_approval`, `waiting_external`, `blocked`, `failed`, `halted_kill_switch`, `complete`, `cancelled` |
| `waiting_approval` | `ready`, `cancelled` |
| `waiting_external` | `ready`, `cancelled` |
| `blocked` | `ready`, `cancelled` |
| `failed` | `ready`, `cancelled` |
| `halted_kill_switch` | `ready`, `cancelled` |
| `complete` | none |
| `cancelled` | none |

Returning to `ready` is an explicit recovery event. It requires revalidation, a current authority grant and a new lease before `active`.

The runtime records that recovery atomically: `recovery_started` may collapse the recoverable-to-`ready` transition plus fresh lease acquisition into one event whose resulting projection is directly `active`. This is the sole event-scoped recovery exception to the table. Separately, `kill_switch_detected` may reduce `ready`, `active`, `waiting_approval`, `waiting_external`, `blocked` or `failed` directly to `halted_kill_switch`; it cannot authorize work. The status enum in `run.schema.json` defines permitted values, not the transition graph.

The ordinary graph is necessary but not sufficient. `lease_acquired` alone activates `ready`; `recovery_started` alone establishes a fresh generation and may project a recoverable waiting, blocked, failed or halted run directly to `active`; `authority_revoked` reduces active work to `waiting_approval` unless kill-switch truth requires the chain to preserve or finish in `halted_kill_switch`; unknown local and external `operation_reconciled` project `failed` and `waiting_external` respectively; ordinary budget exhaustion projects `failed`; `kill_switch_detected` alone uses the lease-independent halt reducer; and the three terminal run events project their matching complete, failed or cancelled state. A pending semantic completion must exactly match its intent. Budget equality or callback completion at lease expiry may cause that semantic event to project `failed` atomically. No graph edge authorizes an event whose type-specific payload, lease envelope, pending adjacency, authority, budget or reason is invalid.

`usage.stage_attempts` is a complete map keyed by `strategize`, `spec_pack`, `build`, `test`, `resolve` and `close`. Each counter is monotonic and `stage_started` increments exactly its matching stage. `usage.duration_seconds` is a non-negative number with microsecond precision and increases by the complete time proven inside each validated lease interval: the interval begins or resumes at an authoritative lease event and is closed or extended by the next validated event or heartbeat, never beyond the prior expiry. Sub-second intervals are retained instead of rounded away. Process downtime without a valid lease does not count. A callback that returns at or after exact lease expiry records its semantic result but atomically leaves the run failed; it cannot return an active projection or continue without fresh-generation recovery.

Ordinary frozen-budget exhaustion makes an active run `failed` with one primary terminal reason code `budget_reached:<field>`. If a successful callback reaches one or more limits exactly, its semantic completion event atomically carries that failed projection before the contiguous `budget_reached` marker sequence is appended. Every simultaneously exhausted budget receives exactly one marker per unique `(budget, stage)` key. The stable priority and marker order is `max_duration_seconds`; `max_stage_attempts` in canonical stage order (`strategize`, `spec_pack`, `build`, `test`, `resolve`, `close`); `max_mutations`; `max_external_actions`; `max_cost_usd`; the first exhausted key supplies the ordinary primary reason. A crash between or within those records therefore cannot leave the run active; the next exclusive command repairs the missing suffix from the authoritative source event and verified marker prefix before doing any work. Each marker records the frozen limit, observed usage and, for `max_stage_attempts`, the affected stage. A deterministic marker schema or invariant `ContractError` propagates and is never reclassified as a transient missing marker; only a non-contract append error may use canonical-head verification to distinguish a repairable pre-append miss, a verified committed marker, or `committed_state_unknown`.

Unknown-operation truth has precedence over every budget reason. When `operation_reconciled` with `outcome: unknown` retains usage that exhausts one or more budgets, its projection remains `failed` with `operation_outcome_unknown` for local work or `waiting_external` with `external_operation_outcome_unknown` for outward work. A contiguous marker sequence in the stable order above records every unique exhausted `(budget, stage)` key without changing the run or lease projection. Exhausted usage still blocks recovery and new work. A missing marker suffix is repaired deterministically only from that reconciliation and the verified marker prefix and never replays the callback.

Cost limits and usage are canonical fixed-point decimal strings with up to six fractional digits, never binary floating-point values. Each callback reserves exactly one mutation; only the exact `local_write` plus `repository` pair is local in v0.1, while every other action or destination is fail-closed as external and must reserve exactly one external action. Internal audit, repair and halt writes do not consume the asset-mutation budget.

## Lease record

Path: `.the-loop/runs/<run-id>/lease.json`

| Field | Type | Required |
| --- | --- | --- |
| `schema_version` | string | yes |
| `lease_id` | UUID | yes |
| `run_id` | UUID | yes |
| `lane_id` | UUID or null | yes |
| `owner` | object | yes: harness, actor, session ID |
| `acquired_at` | timestamp | yes |
| `renewed_at` | timestamp | yes |
| `expires_at` | timestamp | yes |
| `generation` | integer | yes, increments on recovery |

### Lease invariants

- Acquisition uses exclusive file creation when no lease exists and is recorded once for the initial generation; subsequent activity uses `lease_renewed` or `recovery_started`, never another `lease_acquired` for an established generation.
- A non-expired lease cannot be replaced.
- An expired lease can be replaced only through explicit recovery, which increments generation and writes an event. A ready run halted before its first lease resumes through `recovery_started` with `previous_generation: null` and a fresh generation-zero lease; this is the only recovery form without a prior lease.
- `recovery_started` is the generation-establishing audit event for the replacement lease; a duplicate `lease_acquired` event is not required for that generation.
- Every mutation supplies lease ID and generation.
- A heartbeat may renew only its own matching lease.
- Clock reversal or an unparsable timestamp halts mutation.
- Each command uses one injected aware-UTC timestamp; `now == expires_at` is expired and is never renewed in place.
- At or after lease expiry, every ordinary worker and domain event is rejected. If `operation_intended` committed under that lease while it was valid, only its exact declared semantic completion or `operation_reconciled` and the required contiguous deterministic `budget_reached` marker sequence for that source may close it. Completion or reconciliation clears pending state and leaves the run non-active. Each marker is callback-free, cannot interleave, uses the source event's timestamp and unchanged lease identity and projection, and may be repaired later under the run lock from that canonical source and an already verified marker prefix. Outside that closure, only necessary callback-free safety or recovery reducers may append: lease-independent kill or revocation truth, truthful expired-run or budget reduction, cancellation, and fresh-generation recovery. None authorizes callback replay, a replacement callback, renewal under the expired generation or any new ordinary action, so the one-writer valid-lease invariant remains intact.

## Authority grant

Path: `.the-loop/grants/<grant-id>.json`

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `schema_version` | string | yes |  |
| `grant_id` | UUID | yes |  |
| `level` | enum | yes | `attended`, `bounded`, `scoped`, `operational`, `full`. |
| `actor` | string | yes | User-confirmed identity label. |
| `scope` | object | yes | Assets, actions, destinations and explicit exclusions. |
| `risks_shown` | string array | yes | Realistic risks displayed before confirmation. |
| `confirmation_text` | string | yes | Exact typed confirmation, excluding secrets. |
| `confirmed_at` | timestamp | yes |  |
| `expires_at` | timestamp | yes | No non-expiring elevated grant in v0.1. |
| `revoked_at` | timestamp or null | yes |  |
| `revoked_by` | string or null | yes |  |
| `permanent_invariants` | string array | yes | Fixed set validated by schema. |

### Permanent invariants

The exact set is `visible_authority`, `audit_log`, `evidence_required`, `run_ownership`, `leases`, `external_kill_switch`, `faithful_failure`, `no_silent_elevation`.

The validator rejects any elevated grant that omits one.
Explicit scope exclusions take precedence over positive assets, actions and destinations, including wildcard grants.

If a ready run has no lease and its bound grant expires or is revoked, acquisition is denied. A revoked grant still receives the required per-run audit marker, but v0.1 does not rewrite the ready run's authority binding before its first lease. Continuation uses a new run created under a current grant; explicit recovery with authority replacement remains available only to a leased or otherwise recoverable run.

## Route decision

Stored in `run.json` and written as an event.

| Field | Type | Required |
| --- | --- | --- |
| `capability` | string | yes, namespaced such as `lifecycle.test` |
| `harness` | enum | yes: `codex`, `claude_code`, `kimi_code`, `opencode` |
| `track` | enum | yes: `code`, `noncode` |
| `environment_digest` | digest | yes, relevant environment fingerprint without raw private values |
| `requirements` | string array | yes |
| `candidates` | object array | yes |
| `selected_provider` | string | yes |
| `selected_source` | enum | `installed`, `bundled` |
| `reason` | string | yes |
| `verified_at` | timestamp or null | yes |
| `fallback_reason` | string or null | yes |

Each candidate records source, compatibility, explicit capability evidence, description score, behavior status, typed behavior observations, rejection reasons and provenance type. Every typed observation records capability, harness, track, environment digest, outcome, `observed_at`, and an evidence ID. Raw prompt content and raw private environment values are not stored.

A current capability-scoped `behavior_status: failed` disqualifies that candidate. A selected `verified` candidate requires exactly one latest typed observation matching the route capability, harness, track, and environment digest; it must be `passed`, its evidence ID identifies the probe, and route `verified_at` must equal its `observed_at`. A newer matching pass may supersede an older failure, but the older observation remains visible. Route-record validation rejects a selected failed candidate, missing or mismatched observations, multiple observations tied at the latest matching time, a latest matching denied, failed, or unverified outcome, a verification-time mismatch, and description-only or untyped evidence presented as behavior proof.

## Evidence record

Path: `.the-loop/runs/<run-id>/evidence/<evidence-id>.json`

| Field | Type | Required |
| --- | --- | --- |
| `schema_version` | string | yes |
| `evidence_id` | UUID | yes |
| `run_id` | UUID | yes |
| `stage` | enum | yes |
| `requirement_ids` | string array | yes |
| `type` | enum | `command`, `file`, `visual`, `source`, `manual`, `harness_probe` |
| `description` | string | yes |
| `procedure` | string array | yes |
| `outcome` | enum | `passed`, `failed`, `blocked`, `denied`, `unverified` |
| `artifact_refs` | object array | yes |
| `digest` | string or null | yes |
| `actor` | object | yes |
| `observed_at` | timestamp | yes |
| `environment` | object | yes, redacted and allowlisted |

An evidence record cannot use `passed` without a non-empty procedure and at least one result reference or explicit manual observation.

## Issue ledger

Path: `.the-loop/runs/<run-id>/issues.json`

| Field | Type | Required |
| --- | --- | --- |
| `schema_version` | string | yes |
| `run_id` | UUID | yes |
| `issues` | issue array | yes |
| `updated_at` | timestamp | yes |

### Issue

| Field | Type | Required |
| --- | --- | --- |
| `issue_id` | UUID | yes |
| `title` | string | yes |
| `severity` | enum | `critical`, `high`, `medium`, `low` |
| `blocking` | boolean | yes |
| `status` | enum | `open`, `acknowledged`, `resolving`, `verification_pending`, `closed`, `reopened`, `deferred` |
| `requirement_ids` | string array | yes |
| `evidence_ids` | UUID array | yes |
| `reproduction` | string array | yes |
| `owner` | object or null | yes |
| `attempt_count` | integer | yes |
| `resolution` | string or null | yes |
| `regression_procedure` | string array | yes |
| `created_at` | timestamp | yes |
| `updated_at` | timestamp | yes |

A blocking issue in any status other than `closed` prevents run completion. `deferred` is not equivalent to closed.

## Audit event

Path: `.the-loop/runs/<run-id>/events.ndjson`

| Field | Type | Required |
| --- | --- | --- |
| `schema_version` | string | yes |
| `event_id` | UUID | yes |
| `sequence` | integer | yes, starts at 1 and increments by exactly one across the event log |
| `run_id` | UUID | yes |
| `lease_id` | UUID or null | yes |
| `lease_generation` | integer or null | yes |
| `type` | string enum | yes |
| `actor` | object | yes |
| `at` | timestamp | yes |
| `data` | object | yes, type-specific and schema-validated |
| `projection` | object | yes, complete resulting `run`, nullable `lease` and nullable `pending_operation` |
| `previous_event_digest` | string or null | yes |
| `event_digest` | string | yes |

Required event types include `run_created`, `authority_granted`, `authority_revoked`, `lease_acquired`, `lease_renewed`, `route_selected`, `stage_started`, `heartbeat`, `evidence_recorded`, `issue_opened`, `issue_transitioned`, `stage_completed`, `operation_intended`, `operation_reconciled`, `budget_reached`, `kill_switch_detected`, `recovery_started`, `run_completed`, `run_failed` and `run_cancelled`.

`run_created` appears exactly once as the first event. It cannot be replayed later, including while recovery is pending.

The audit log is the authoritative run-control record. Every event carries the complete after-state `projection.run`, `projection.lease` and `projection.pending_operation`; `run_created` therefore contains the complete initial run, and lease, recovery, heartbeat and control events contain all acquired, renewed, expiry, lane, owner, status, reason and usage state required for repair. Before mutation, the manager validates the full chain and projection continuity, then deterministically repairs `run.json` and `lease.json` from the latest complete state when either mutable projection is missing or stale. A corrupt chain is preserved and blocks mutation. Mutable projections are never accepted as a trusted seed over a valid audit head.

Before invoking a side-effecting callback, the manager appends `operation_intended`. Its complete pending record contains a unique `operation_id`, the exact permitted semantic completion event type and payload, an explicit `local` or `external` effect classification, and the exact mutation, external-action, cost and optional stage-attempt reservation plus the prior stage/cost needed for deterministic rollback. A successful callback is followed immediately by that exact semantic event and payload, which clears pending state. If the reservation exactly exhausts one or more budgets, that same completion event atomically projects the failed state with the first stable-priority budget as its primary reason before the complete marker sequence. No unrelated event may interleave.

An unmatched pending intent after an uncontrolled interruption is an unknown outcome, never a retry instruction. Reconciliation appends `operation_reconciled` with `outcome: unknown`, retains the full reservation, clears pending state and moves local work to `failed` with code `operation_outcome_unknown`, or outward work to `waiting_external` with code `external_operation_outcome_unknown`. When the runtime itself proves the callback has not begun, such as a kill switch detected immediately after intent, it instead appends `outcome: known_not_started`, rolls back that exact reservation, restores the prior stage/cost and then records the halt. This narrow rollback does not require recovery before the following safety-control event and cannot be inferred after a process crash. When pending state exists, only its exact declared semantic completion or reconciliation may close it, including when the lease expires after the intent committed while valid; the contiguous required budget-marker sequence may then follow with the source timestamp and unchanged projection. Such post-expiry closure must leave work non-active, cannot interleave an unrelated event and cannot authorize any new action. Without a valid lease, ordinary domain and worker events are rejected even when no operation is pending; only the expressly defined callback-free safety and recovery reducers remain available. Prevention of callback replay is a runtime invariant backed by the durable reconciled state.

Projection continuity keeps mission identity and frozen budgets immutable, keeps usage monotonic, permits authority changes only during explicit recovery, requires lease ID/generation/owner alignment with the event envelope, requires an active run owner to match the resulting lease owner, and enforces the intent-to-completion or intent-to-reconciliation adjacency contract.

Authority revocation and mutation intent share a stable per-grant cooperative lock. Mutation holds the shared side through its final grant validation and durable intent append; the official revocation path holds the exclusive side through the grant update and revocation audit. The lock boundary is the authority linearization point: a completed revocation prevents intent, while an already durable intent may finish exactly once under the authority it recorded. Runs sharing a grant use the same lock path. The revoked grant is irreversible truth. Its per-run `authority_revoked` marker records the persisted `revoked_at` and `revoked_by`; retry repairs an absent marker exactly once, accepts an already verified marker without duplication, and never restores the grant when audit state is pending or unverifiable. Every supported mutating entry repairs its run's marker before denying use of a shared revoked grant. Revocation remains a safety-reducing control when a kill-switch probe is present or indeterminate, or the run is already halted: the grant is persisted revoked, exactly one `authority_revoked` marker is appended or repaired, `kill_switch_detected` follows when needed, and the returned final projection is `halted_kill_switch`. The audit chain preserves both truths and grants no work authority.

The complete chain is validated before every append, including the first. Event timestamps never move backwards, and each acquisition or renewal expiry is later than its event timestamp.

`kill_switch_detected` is a safety-control event and may be recorded without lease context. It may move any recoverable nonterminal run (`ready`, `active`, either waiting state, `blocked` or `failed`) directly to `halted_kill_switch`. This exception can only reduce authority; it cannot authorize ordinary mutation or recovery, and complete or cancelled runs remain terminal.

Digest chaining detects accidental edits. It is not presented as tamper-proof security because a local owner can rewrite the entire store.

Projection writes and event-log operations require an explicit project root. Path preparation captures one immutable namespace snapshot containing the project-root identity plus the observed presence and identity of every intermediate component and target. The runtime additionally binds the device/inode identity of the project root, `.the-loop` and every configured state-root component to the run; every public command and the pre-intent, pre-callback and pre-commit boundaries recheck it, so a same-string clone or replacement cannot create a second history. Descriptor walking consumes the snapshot without re-baselining replacements, rejects unexpected appearance, disappearance, replacement, symlink and hard-link aliases, and verifies that the canonical path still names the operated inode before reporting success. Readers take a shared lock and appenders take an exclusive lock so a valid in-progress append is never reported as corruption. Locks are released by closing the retained descriptor, keeping cleanup leak-free without a separate unlock step that could turn a durable append into a reported failure.

Projection replacement snapshots the prior canonical bytes before mutation. If any post-replacement namespace, identity, permission or link-count check fails, the retained parent descriptor restores those bytes through a fresh private inode (or removes the new target when the projection was initially absent) before the operation reports failure.

## Command and skill operations

The implementation exposes these logical operations. A harness may wrap them in a skill rather than a standalone CLI.

| Operation | Mutation | Authority |
| --- | --- | --- |
| `setup plan` | no | read access |
| `setup apply` | yes | exact install approval |
| `doctor` | no, except optional report file | read access; harness probes may prompt |
| `run create` | yes | default local authority |
| `run status` | no | read access |
| `run acquire` | yes | valid owner and authority |
| `run heartbeat` | yes | matching lease |
| `run transition` | yes | matching lease plus valid schema transition |
| `issue open/update` | yes | matching lease |
| `evidence add` | yes | matching lease |
| `authority grant/revoke` | yes | typed user confirmation or user revocation |
| `run stop` | yes | user-controlled kill switch or cancel authority |
| `run resume` | yes | explicit recovery, current grant and fresh lease |

## Migration policy

- Schema versions use `major.minor`.
- A minor migration may add optional fields or enum values that old readers can safely ignore.
- A major migration requires an explicit command, backup and migration evidence.
- Migration writes a new tree, validates it, then swaps atomically.
- Failed migration leaves the original tree untouched.
- Downgrade is read-only unless a tested reverse migration exists.

## Remote future

Cloud or Endless may later need a shared state adapter. Any adapter must preserve the same records, atomic ownership semantics and kill-switch behavior. A remote database cannot become a reason to remove local export, visible authority or faithful failure states.

## Assumption ledger

| Assumption | Class | Consequence if wrong |
| --- | --- | --- |
| One active writer per run or lane is sufficient. | safe default | Add compare-and-swap storage without changing lease semantics. |
| UUIDv4 is acceptable for local IDs. | safe default | Change ID generation only in a major schema migration. |
| Owner-only filesystem permissions are available on required platforms. | safe default | Doctor warns and the user decides whether the environment is acceptable. |
| Cost cannot be measured reliably across every harness. | safe default | Treat missing cost as unverified and never as zero. |
