# Run state and lease protocol

## Purpose

This protocol defines the harness-neutral control plane for one bounded THE LOOP run. It applies equally to code and non-code tracks. Uppercase terms are normative only inside the numbered requirements below.

The [JSON Schemas](../schemas/README.md) define record shape. The digest-chained event log defines authoritative history. `run.json` and `lease.json` are replaceable projections of that history.

## Normative requirements

### Records and ownership

- **[RUN-001]** A run manager MUST identify a run by one UUIDv4 `run_id` and preserve its asset, objective, done gate, frozen budgets and creation time across every projection.
- **[RUN-002]** A run manager MUST serialize every state-changing command for one run under one stable run lock.
- **[RUN-003]** A writing worker MUST hold the current unexpired lease for the run or declared lane, with an exact match on lease ID, generation and owner.
- **[RUN-004]** A status reader MAY use a shared lock, but it MUST NOT take ownership or mutate state.
- **[RUN-005]** Every public runtime command MUST use an explicit project root and MUST reject a changed, aliased, replaced or indeterminate project/control/state-root namespace.

### Authoritative state

- **[RUN-010]** The append-only `events.ndjson` chain MUST be the authoritative run-control record.
- **[RUN-011]** Every event MUST carry the complete resulting `run`, nullable `lease` and nullable `pending_operation` projection required by `audit-event.schema.json`.
- **[RUN-012]** Before mutation, the manager MUST validate the full event chain, event order, digests, timestamps and projection continuity.
- **[RUN-013]** Before mutation, the manager MUST reconstruct state from the validated event chain and atomically repair stale or missing mutable projections.
- **[RUN-014]** A corrupt, incomplete or noncanonical event chain MUST be preserved and MUST block mutation; a mutable projection MUST NOT override it.
- **[RUN-015]** Event sequence numbers MUST begin at one and increase globally by exactly one, and event time MUST NOT move backwards.
- **[RUN-016]** A committed event whose canonical head can be verified MAY be reported as successful when projection repair fails; an unverifiable or noncanonical committed head MUST return `committed_state_unknown` with a do-not-retry warning.

### Status transitions

The ordinary projection status graph is:

```text
draft                    -> ready | cancelled
ready                    -> active | cancelled
active                   -> waiting_approval | waiting_external | blocked
                         -> failed | halted_kill_switch | complete | cancelled
waiting_approval         -> ready | cancelled
waiting_external         -> ready | cancelled
blocked | failed         -> ready | cancelled
halted_kill_switch       -> ready | cancelled
complete | cancelled     -> terminal
```

Two authoritative audit events have narrower atomic exceptions: `recovery_started` may collapse the recoverable-to-`ready` transition plus fresh lease acquisition into one projection that is directly `active`; `kill_switch_detected` may reduce `ready`, `active`, `waiting_approval`, `waiting_external`, `blocked` or `failed` directly to `halted_kill_switch`.

Event semantics further narrow the graph:

| Event scope | Required status effect |
| --- | --- |
| `lease_acquired` | `ready` to `active` with generation zero |
| `recovery_started` | recoverable waiting, blocked, failed or halted state directly to `active` with the required fresh lease generation |
| `authority_revoked` | active work to `waiting_approval`; if kill-switch truth is also present, preserve or finish in `halted_kill_switch`; no projection gains authority |
| unknown local `operation_reconciled` | `failed` with `operation_outcome_unknown` |
| unknown external `operation_reconciled` | `waiting_external` with `external_operation_outcome_unknown` |
| ordinary `budget_reached` | a permitted nonterminal state to `failed` with `budget_reached:<field>` |
| `kill_switch_detected` | a permitted recoverable nonterminal state to `halted_kill_switch` without lease context |
| `run_completed`, `run_failed`, `run_cancelled` | `complete`, `failed`, `cancelled` respectively |
| exact pending semantic completion | its declared stage/domain effect; budget equality or post-callback lease expiry may atomically leave the run `failed` |

- **[RUN-020]** A manager MUST accept only the ordinary graph above or the exact `recovery_started` and `kill_switch_detected` event-scoped exceptions stated above. The status enum in `run.schema.json` defines values, not transition authority.
- **[RUN-021]** Returning a waiting, blocked, failed or halted run to work MUST use explicit recovery; deleting a control file or changing a projection MUST NOT resume it.
- **[RUN-022]** `complete` and `cancelled` MUST be terminal, and no later event may follow their terminal event.
- **[RUN-023]** Run completion MUST require every declared done-gate condition to have passed evidence and `open_blocking_issues` to equal zero.
- **[RUN-024]** A graph edge MUST be treated as necessary but not sufficient: the event type, pending-operation adjacency, lease envelope, authority, budget and resulting reason MUST also satisfy its event-scoped contract.

### Lease lifecycle

- **[RUN-030]** Initial acquisition MUST create one generation-zero lease exclusively and record exactly one `lease_acquired` event.
- **[RUN-031]** A non-expired lease MUST NOT be replaced, and a mismatched owner, lease ID or generation MUST be rejected.
- **[RUN-032]** Renewal and heartbeat MUST preserve lease ID, generation and owner, advance time, and set an expiry later than the event time.
- **[RUN-033]** Exact expiry (`now == expires_at`) MUST be treated as expired and MUST NOT be renewed in place.
- **[RUN-034]** Replacing an expired lease MUST use `recovery_started`, increment generation by exactly one and record the previous generation.
- **[RUN-035]** A ready run halted before its first lease MAY recover with `previous_generation: null` and a new generation-zero lease; no other recovery may omit a prior generation.
- **[RUN-036]** Recovery MUST revalidate current authority, namespace, budget and kill-switch state before establishing the replacement lease.
- **[RUN-037]** Recovery MUST reject a non-expired lease, an exhausted budget or a state outside the recoverable set.
- **[RUN-038]** A callback returning at or after lease expiry MUST preserve its semantic completion exactly once but MUST project the run as failed and require fresh-generation recovery.
- **[RUN-039]** At or after lease expiry, every ordinary worker or domain event MUST be rejected. An `operation_intended` committed under that lease while it was valid MAY be closed only by its exact declared semantic completion or `operation_reconciled`, followed only by the required contiguous deterministic `budget_reached` markers for that source event; completion or reconciliation MUST clear pending state and leave the run non-active, and each callback-free marker MUST use the source timestamp and unchanged lease identity and projection. Outside that closure, only the contract's necessary callback-free safety or recovery reducers for kill, revocation, truthful expired-run or budget reduction, cancellation, and fresh-generation recovery MAY append. These exceptions MUST NOT authorize callback replay, another callback or new ordinary work, and no unrelated event may interleave.

### Heartbeat and liveness

- **[RUN-040]** A heartbeat MUST be an owner-authenticated lease renewal, not evidence of useful progress.
- **[RUN-041]** Active liveness MUST be `unleased` without a lease, `expired` at or after expiry, `stale` when the last heartbeat is absent or at least one configured heartbeat interval old, and `fresh` otherwise.
- **[RUN-042]** Non-active liveness MUST be `inactive`, except that a durable pending operation MUST be surfaced as `pending_local` or `pending_external`.
- **[RUN-043]** Active duration MUST accumulate with subsecond precision only across validated lease intervals, stop at lease expiry and exclude unleased downtime.

### Authority linearization

- **[RUN-050]** Every action MUST remain within a visible, current, unexpired grant whose exclusions take precedence over positive scope and wildcards.
- **[RUN-051]** Mutation intent and official revocation for one grant MUST share one stable per-grant cooperative lock across all runs using that grant.
- **[RUN-052]** Mutation MUST hold the shared grant lock through final grant validation and durable `operation_intended`; official revocation MUST hold the exclusive grant lock through the irreversible grant update and its audit attempt.
- **[RUN-053]** A revocation completed before intent MUST prevent that intent; an intent already committed before revocation MAY complete exactly once under the authority recorded by the intent.
- **[RUN-054]** A revoked grant MUST never be restored automatically. Its persisted `revoked_at` and `revoked_by` are the source for every per-run `authority_revoked` marker.
- **[RUN-055]** A missing revocation marker MUST be repaired idempotently at most once per run before a supported mutating entry denies the revoked grant.
- **[RUN-056]** A pending revocation audit MUST return `audit_pending`; an unverifiable or noncanonical committed revocation state MUST return `committed_state_unknown`; neither condition may restore the grant.
- **[RUN-057]** The permanent invariants `visible_authority`, `audit_log`, `evidence_required`, `run_ownership`, `leases`, `external_kill_switch`, `faithful_failure` and `no_silent_elevation` MUST remain active at every authority level.
- **[RUN-058]** Revocation MUST remain a permitted safety-reducing control while a kill-switch probe is present or indeterminate, or the run is already `halted_kill_switch`; the chain MUST preserve exactly one revocation marker followed by the kill-switch event when it is not already recorded, and its final projection MUST be `halted_kill_switch` without authorizing work.

### Side-effect boundary

- **[RUN-060]** Before invoking a side-effecting callback, the manager MUST append `operation_intended` with a unique operation ID, exact completion event and payload, derived effect and exact usage reservation.
- **[RUN-061]** In v0.1, only the exact pair `local_write` plus `repository` MUST classify as local; every other action or destination MUST classify as external.
- **[RUN-062]** One callback MUST reserve exactly one mutation; an external callback MUST also reserve exactly one external action, while a local callback MUST reserve zero external actions.
- **[RUN-063]** A successful callback MUST append its exact declared semantic completion next, clear pending state and MUST NOT permit an interleaving or mismatched completion.
- **[RUN-064]** An uncontrolled interruption with pending intent MUST append `operation_reconciled` with `outcome: unknown`, retain the reservation and MUST NOT replay the callback.
- **[RUN-065]** Unknown local work MUST become `failed` with `operation_outcome_unknown`; unknown external work MUST become `waiting_external` with `external_operation_outcome_unknown`.
- **[RUN-066]** Only the same live process proving callback entry never occurred MAY reconcile `known_not_started`, roll back that exact reservation and restore the recorded prior stage and cost.

### Budgets and stop control

- **[RUN-070]** Frozen duration, stage-attempt, mutation, external-action and optional cost budgets MUST be checked before work and after callback time is charged.
- **[RUN-071]** Cost values MUST use canonical non-negative fixed-point decimal strings with at most six fractional digits; a null cost limit MUST mean no spending authority.
- **[RUN-072]** Ordinary budget exhaustion outside the unknown-operation precedence in RUN-077 MUST leave the run `failed` with one primary `budget_reached:<field>` reason chosen by RUN-079 and MUST emit one matching marker for every simultaneously exhausted budget.
- **[RUN-073]** A successful callback reaching a budget exactly MUST atomically carry the failed projection in its semantic completion; a missing following marker MUST be repaired before later exclusive work.
- **[RUN-074]** Every configured kill-switch path MUST be probed before mutation, and present or indeterminate state MUST fail closed.
- **[RUN-075]** `kill_switch_detected` MUST be permitted without lease context only to reduce a recoverable nonterminal run to `halted_kill_switch`; it MUST NOT authorize ordinary work.
- **[RUN-076]** Kill-switch removal MUST NOT resume the run; explicit recovery with a current grant and the required generation change remains necessary.
- **[RUN-077]** When an unknown-operation reconciliation retains usage that exhausts one or more budgets, the reconciliation's local `failed` or external `waiting_external` status and unknown-outcome reason MUST remain the primary projection; the contiguous `budget_reached` marker sequence MUST record every exhausted limit and observation using the reconciliation timestamp without changing run or lease projection.
- **[RUN-078]** Exhausted usage after unknown-operation reconciliation MUST block recovery and new work even though the primary terminal reason is not `budget_reached:<field>`; every missing marker MUST be repaired deterministically from that reconciliation and the already verified marker prefix without replaying the callback.
- **[RUN-079]** Simultaneously exhausted budgets MUST emit exactly one marker per unique `(budget, stage)` key in this stable order: `max_duration_seconds`; `max_stage_attempts` in canonical stage order `strategize`, `spec_pack`, `build`, `test`, `resolve`, `close`; `max_mutations`; `max_external_actions`; `max_cost_usd`. Ordinary exhaustion MUST use the first key as its single primary budget reason, while unknown-outcome reconciliation MUST retain its unknown-outcome reason.

## Failure and halt behavior

- **[RUN-080]** A runtime MUST distinguish denied authority, lease conflict, lease expiry, budget exhaustion, kill-switch stop, unknown operation outcome, pending audit and unknown committed state.
- **[RUN-081]** A runtime MUST NOT claim success, completion, replay safety or green status when the corresponding authoritative evidence cannot be verified.
- **[RUN-082]** A runtime MUST preserve the last verified history and provide a recovery or human-verification condition instead of silently weakening an invariant.

## Evidence

Conformance includes two-writer exclusion, renewal and expiry boundaries, generation recovery, stale projection repair, corrupt-chain rejection, grant revoke-wins and intent-wins races, callback interruption, exact rollback, budget equality, kill-switch present and indeterminate probes, and namespace replacement at every side-effect boundary.

## Cross-references

| Protocol range | Source contract |
| --- | --- |
| RUN-001–043 | [Run, lease and audit-event contracts](../docs/specs/backend-schema.md#run-record), [`run.schema.json`](../schemas/run.schema.json), [`lease.schema.json`](../schemas/lease.schema.json) |
| RUN-050–058 | [Authority grant and revocation contract](../docs/specs/backend-schema.md#authority-grant), [`grant.schema.json`](../schemas/grant.schema.json), [Autonomy policy](autonomy-policy.md) |
| RUN-060–079 | [Pending-operation, budget and kill-switch contract](../docs/specs/backend-schema.md#audit-event), [`audit-event.schema.json`](../schemas/audit-event.schema.json) |
| RUN-080–082 | [PRD FR-030–038](../docs/specs/prd.md#state-ownership-and-recovery), [TDD run manager](../docs/specs/tdd.md#run-manager) |
