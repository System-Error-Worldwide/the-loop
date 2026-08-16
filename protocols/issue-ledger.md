# Issue ledger protocol

## Purpose

The issue ledger is the durable record of defects that survive self-refutation. It prevents failures from disappearing between Test, Resolve and Close. The record shape is [`issue-ledger.schema.json`](../schemas/issue-ledger.schema.json); state-changing issue actions are also represented by authoritative audit events.

## Normative requirements

### Record requirements

- **[ISS-001]** One run MUST have one ledger whose `run_id` matches the run and whose issue IDs are unique UUIDv4 values.
- **[ISS-002]** Every surviving defect MUST record a concise title, severity, blocking decision, affected requirement IDs, evidence IDs and reproducible steps.
- **[ISS-003]** Severity MUST be one of `critical`, `high`, `medium` or `low`; status MUST be one of `open`, `acknowledged`, `resolving`, `verification_pending`, `closed`, `reopened` or `deferred`.
- **[ISS-004]** A report that cannot yet be reproduced MUST remain represented with truthful evidence and MUST NOT be silently discarded as resolved.
- **[ISS-005]** Issue creation MUST append `issue_opened` with the same issue ID and severity through the durable operation-intent boundary.
- **[ISS-006]** Every status change MUST append `issue_transitioned` with the exact issue ID, prior status and resulting status through the durable operation-intent boundary.
- **[ISS-007]** Ledger replacement and its semantic audit event MUST preserve one authoritative outcome under interruption; an unmatched intent MUST follow the run-state non-replay rules.

### Lifecycle

```text
open -> acknowledged -> resolving -> verification_pending -> closed
  |          |              |                  |
  +-------> deferred <-------+                  +-> reopened
               |                                   |
               +-> acknowledged <------------------+
closed ------------------------------------------> reopened
```

The exact permitted transitions are:

| From | To |
| --- | --- |
| `open` | `acknowledged`, `deferred` |
| `acknowledged` | `resolving`, `deferred` |
| `resolving` | `verification_pending`, `deferred` |
| `verification_pending` | `closed`, `reopened`, `deferred` |
| `reopened` | `resolving`, `deferred` |
| `deferred` | `acknowledged` |
| `closed` | `reopened` |

- **[ISS-010]** An issue transition MUST follow the exact table above and MUST name the current stored status as `from_status`.
- **[ISS-011]** Test MUST open every defect that survives attempted refutation and MUST link the evidence that demonstrates it.
- **[ISS-012]** Resolve MUST move only an issue with an explicit owner to `resolving`, and that owner MUST match the actor performing the resolution work.
- **[ISS-013]** A proposed fix MUST move to `verification_pending` before it can close.
- **[ISS-014]** Test MUST close an issue only after its recorded regression procedure passes and the passing evidence ID is linked.
- **[ISS-015]** A failed regression MUST move the issue to `reopened`, preserve prior evidence and resolution history, and trigger the stuck-loop halt rule.
- **[ISS-016]** Deferral MUST include a truthful reason in `resolution`; `deferred` MUST NOT be treated as closed.
- **[ISS-017]** `attempt_count` MUST increase when a new resolution attempt begins and MUST NOT decrease.

### Blocking and completion

- **[ISS-020]** Any blocking issue whose status is not `closed` MUST prevent stage green and run completion.
- **[ISS-021]** `run.open_blocking_issues` MUST equal the number of blocking ledger issues whose status is not `closed`.
- **[ISS-022]** Critical and high findings MUST default to blocking unless the ledger records an explicit, evidence-backed reason for a different decision.
- **[ISS-023]** Close MUST validate the ledger and blocking count against the authoritative run state rather than trusting a summary.
- **[ISS-024]** A reopened issue or three consecutive red Test-to-Resolve passes MUST halt autonomous retries and surface the stuck-loop condition for human direction.

### Evidence and fidelity

- **[ISS-030]** Reproduction and regression procedures MUST be executable or explicitly marked manual, bounded and specific to the affected requirement.
- **[ISS-031]** Evidence links MUST resolve to evidence records for the same run; missing or invalid links MUST block closure.
- **[ISS-032]** A resolution description MUST state what changed or why no change was made and MUST NOT claim verification by itself.
- **[ISS-033]** Closing an issue MUST preserve its reproduction, regression procedure, evidence links, timestamps and attempt count.
- **[ISS-034]** A later contradiction MUST reopen the existing issue when it describes the same failure, rather than creating a duplicate that hides history.
- **[ISS-035]** Ledger output MUST report unresolved, deferred and unverified issues faithfully, without reducing severity or blocking status to make a gate pass.

## Failure and halt behavior

Unresolved blocking issues halt green and completion under ISS-020. Reopening or exhausting the retry gate halts autonomous resolution under ISS-024. Invalid transitions, missing evidence and ledger-to-run count drift fail closed under ISS-010, ISS-021 and ISS-031.

## Evidence

Conformance covers every valid and invalid transition, duplicate IDs, wrong `from_status`, missing owner, closure without passing regression evidence, reopened and deferred blockers, blocking-count drift, interrupted issue mutations and stuck-loop termination.

## Cross-references

| Protocol range | Source contract |
| --- | --- |
| ISS-001–017 | [`issue-ledger.schema.json`](../schemas/issue-ledger.schema.json), [`audit-event.schema.json`](../schemas/audit-event.schema.json), [App flow issue lifecycle](../docs/specs/app-flow.md#issue-lifecycle) |
| ISS-020–024 | [PRD FR-023–025](../docs/specs/prd.md#lifecycle), [Engineering retry gate](../docs/specs/engineering-plan.md#test-and-resolve-loop) |
| ISS-030–035 | [Evidence contract](evidence-contract.md), [Stage contracts](stage-contracts.md) |
