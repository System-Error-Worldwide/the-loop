---
name: the-loop-parallel
description: Plan and run bounded parallel-lane work only when lanes are independent, integration ownership is explicit and every merged result is independently verified before parent mutation.
license: MIT
compatibility: Codex, Claude Code, Kimi Code and OpenCode
metadata:
  the-loop-capability: orchestration.parallel
  the-loop-version: "0.1"
---

# The Loop Parallel

## Purpose

Enable one bounded run to advance with parallel worker lanes when the work can be proven independent. It is the extension mode that schedules multiple bounded workers and merges their outputs only through the parent run's integration owner.

## Use when

Use when all of the following are true:

- Work can be split into disjoint lanes with non-overlapping write boundaries.
- Each lane can be proven independently against the same track, run scope and authority.
- Integration ownership is explicit and cannot be delegated through side effects.
- The parent run can verify merged output before advancing stage/state.

## Required inputs

- One active run with current owner, lease, authority and budgets.
- Declared objective, track, bounded done gate and explicit output boundary per lane.
- A dispatch packet per lane that includes run/parent IDs, assets, boundaries, budgets, authority reference, stop controls and evidence obligations.
- Capability ranking for each lane and a bounded fallback path for any worker denial/failure.
- Proof that lanes are disjoint and that no lane can overwrite a shared state file, issue ledger row or destination.

Do not start when write boundaries are unclear or when the run state is stale, stopped, denied, expired or under recovery.

## Procedure

1. Build or load the parent run context and verify lease, owner, authority and kill-switch status.
2. Validate every lane packet for track-specific authority, budgets, namespace, and output obligations.
3. Rank required capability requests and route each lane with the same safety checks used by single-worker execution.
4. Start lanes only when each lane has a provable isolation claim and disjoint write map.
5. Require a worker to emit route, status, usage and artifact evidence in a normal result envelope.
6. Reject unknown outcomes; do not replay unknown callbacks.
7. Run the integration owner once after every worker result to verify merged outputs, update issues, and preserve parent state continuity.
8. If lanes disagree on the same objective, halt and open a recovery path rather than picking one winner silently.
9. Record one coherent handoff summary for any partial completion, including what was merged and what remains.

## Output contract

At each boundary report run ID, parent run ID, active lease, owner, authority expiry, lane map, worker identities, worker envelopes, merged artifacts, issue list, usage totals, halt reason and next stage. Parent advancement is only allowed by the integration owner after a verified merge check.

## Evidence gate

Every lane must persist proof for: dispatch packet, route result, worker envelope, result verification, integration merge decision and issue impact. Unknown outcome and partial merge states are closed as blocked and must require explicit recovery.

## Track requirements

For code track, lane separation must include path- or resource-level ownership and conflict checks before any mutable action. For non-code track, lane separation must include recipient and audience separation, format safety and publication authority checks.

## Safety and authority

Parallel execution never broadens authority, budgets, output scope, namespace or stop conditions. A stop signal, lost lease, stop state, missing permission, open issue or terminal parent state blocks new lane starts and merge decisions.

## Self-refutation

Before merge, re-check that every lane output is bounded to its packet, that no two lanes touched the same output boundary, and that every claim is backed by current evidence.

## Halt conditions

Halt on stale state, missing or expired authority, namespace change, stop signal, lane failure without verified result, merge conflict, unresolved conflict evidence, budget exhaustion, or explicit integration owner request.

## References

- [Workflow dispatch](https://github.com/System-Error-Worldwide/the-loop/blob/main/protocols/workflow-dispatch.md)
- [Run state and leases](https://github.com/System-Error-Worldwide/the-loop/blob/main/protocols/run-state-leases.md)
- [Evidence contract](https://github.com/System-Error-Worldwide/the-loop/blob/main/protocols/evidence-contract.md)
- [Issue ledger](https://github.com/System-Error-Worldwide/the-loop/blob/main/protocols/issue-ledger.md)
- [Autonomy policy](https://github.com/System-Error-Worldwide/the-loop/blob/main/protocols/autonomy-policy.md)
- [Stage contracts](https://github.com/System-Error-Worldwide/the-loop/blob/main/protocols/stage-contracts.md)
- [Skill routing](https://github.com/System-Error-Worldwide/the-loop/blob/main/protocols/skill-routing.md)
