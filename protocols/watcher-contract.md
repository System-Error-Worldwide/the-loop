# Watcher contract

## Purpose

The watcher is a read-only observer. It reports durable run state and liveness without acquiring ownership, advancing work, repairing projections or making control decisions. It is not the run manager, supervisor, recovery agent or kill switch.

## Normative requirements

### Read-only boundary

- **[WAT-001]** A watcher MUST operate without a writer lease and MUST NOT present itself as the run owner.
- **[WAT-002]** A watcher MUST use read-only operations and shared locks for state, event, issue, evidence, grant and configuration inspection.
- **[WAT-003]** A watcher MUST NOT create, replace, delete or repair a run projection, lease, event log, issue ledger, evidence record, grant, lock, kill-switch file or asset file.
- **[WAT-004]** A watcher MUST NOT acquire, renew, heartbeat, recover, cancel, complete or revoke a run, and MUST NOT append any event or pending operation.
- **[WAT-005]** A watcher MUST NOT invoke a stage, provider, callback, external action or autonomous retry.
- **[WAT-006]** A watcher MAY recommend a manager action in output, but it MUST label the recommendation as unexecuted and MUST NOT claim that it changed state.

### Authoritative observation

- **[WAT-010]** A watcher MUST validate the event chain before treating it as authoritative.
- **[WAT-011]** A watcher MUST derive run, lease and pending-operation state from the last valid complete event projection and MUST NOT trust a conflicting mutable projection.
- **[WAT-012]** A watcher MUST report stale or missing mutable projections as drift without repairing them.
- **[WAT-013]** A corrupt, incomplete, changing or unreadable chain MUST produce `state_unverified` with the precise reason; the watcher MUST NOT infer progress beyond the last verified state.
- **[WAT-014]** A watcher MUST take a shared event-log lock so an in-progress valid append is not misreported as corruption.
- **[WAT-015]** A watcher MUST report the observation timestamp and the authoritative head sequence, event ID and digest used for the snapshot.

### Liveness classification

| Classification | Condition |
| --- | --- |
| `inactive` | Run status is not `active` and there is no pending operation. |
| `unleased` | Run is `active` and no lease is projected. |
| `expired` | Run is `active` and observation time is at or after lease expiry. |
| `stale` | Run is `active`, lease is unexpired, and heartbeat is absent or at least one configured heartbeat interval old. |
| `fresh` | Run is `active`, lease is unexpired, and heartbeat is newer than the stale boundary. |
| `pending_local` | A local pending operation exists. |
| `pending_external` | An external pending operation exists. |
| `state_unverified` | Authoritative state cannot be verified. |

- **[WAT-020]** A watcher MUST classify liveness using the table above and an aware UTC observation time.
- **[WAT-021]** Exact lease expiry and exact heartbeat staleness boundaries MUST classify as `expired` and `stale` respectively.
- **[WAT-022]** Pending-operation classification MUST take precedence over ordinary active/inactive liveness.
- **[WAT-023]** `fresh` MUST mean only that the recorded heartbeat is recent; it MUST NOT be presented as proof of progress, correctness or ownership beyond the lease record.
- **[WAT-024]** `stale`, `expired`, `unleased` and pending states MUST NOT trigger takeover or replay by the watcher.

### Safety signals

- **[WAT-030]** A watcher MAY probe configured kill-switch paths read-only and MUST distinguish absent, present and indeterminate results.
- **[WAT-031]** A present or indeterminate kill-switch probe MUST be reported as stop-signaled or stop-unverified respectively; the watcher MUST NOT append `kill_switch_detected`.
- **[WAT-032]** Removing or observing an absent switch MUST NOT be reported as resumed work.
- **[WAT-033]** Elevated authority MUST be visible in every watcher snapshot, including grant level, scope, expiry and revocation state, without exposing confirmation secrets.
- **[WAT-034]** A revoked grant lacking its per-run marker MUST be reported as audit drift and MUST be left for a supported mutating entry or explicit manager repair.
- **[WAT-035]** A pending external outcome MUST be reported as requiring human verification and MUST NOT be converted into success, failure or retry.

### Output and polling

- **[WAT-040]** Watcher output MUST include run ID, status, stage, liveness, owner, lease generation and expiry, last heartbeat, pending effect, authority warning, usage versus budgets, blocking-issue count and terminal reason when available.
- **[WAT-041]** Watcher output MUST distinguish observed facts, derived classifications, warnings and unexecuted recommendations.
- **[WAT-042]** A watcher MUST redact secrets, credentials, private payloads and unnecessary machine identifiers from logs and notifications.
- **[WAT-043]** Polling MUST be bounded and configurable, release all shared locks between observations and avoid holding a descriptor while sleeping.
- **[WAT-044]** Repeated identical observations SHOULD be coalesced, while status, liveness, lease, authority, pending-operation, budget, issue or kill-switch changes SHOULD be emitted promptly.
- **[WAT-045]** Watcher failure MUST be reported as watcher failure; it MUST NOT change the observed run to failed, halted or complete.

## Failure and halt behavior

Unverifiable authoritative state produces `state_unverified` under WAT-013. Watcher failure remains separate from run failure under WAT-045. Stop signals, expired ownership and pending outcomes are reported but never acted on by the watcher under WAT-024, WAT-031 and WAT-035.

## Evidence

Conformance proves zero filesystem mutations across fresh, stale, expired, unleased, pending local, pending external, kill-switch present, kill-switch indeterminate, elevated, revoked, corrupt-chain and concurrent-append observations. It also verifies shared-lock release between polls and confirms that no manager API is invoked.

## Cross-references

| Protocol range | Source contract |
| --- | --- |
| WAT-001–015 | [Run state and lease protocol](run-state-leases.md), [Backend audit contract](../docs/specs/backend-schema.md#audit-event) |
| WAT-020–024 | [Runtime liveness model](../docs/specs/backend-schema.md#run-record), [`run.schema.json`](../schemas/run.schema.json), [`lease.schema.json`](../schemas/lease.schema.json) |
| WAT-030–045 | [Kill-switch journey](../docs/specs/app-flow.md#kill-switch-journey), [Autonomy policy](autonomy-policy.md) |
