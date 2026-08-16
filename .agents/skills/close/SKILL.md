---
name: close
description: Reconcile authoritative run evidence and issues into a truthful terminal status, limitations and portable handoff.
license: MIT
compatibility: Codex, Claude Code, Kimi Code and OpenCode
metadata:
  the-loop-capability: lifecycle.close
  the-loop-version: "0.1"
---

# Close

## Purpose

Provide the complete bundled fallback for `lifecycle.close`. End one bounded mission with a truthful status and portable handoff based on authoritative evidence rather than the worker narrative.

## Use when

Use after Test reports the done gate satisfied, or when a mission must stop as blocked, failed, cancelled, waiting or kill-halted with its current truth preserved.

## Required inputs

- Validated run ID, declared asset, track, objective, done gate and current stage.
- Authoritative event head, projected run and lease, pending-operation state and authority record.
- Complete route, evidence and issue references for the mission.
- Delivered artifacts, current source or repository state and usage against budgets.
- Required terminal decision and any explicit cancellation or recovery authority.

Reject summaries that conflict with the event chain or issue ledger.

## Procedure

1. Validate the authoritative chain and derive the current run, lease and pending-operation state.
2. Compare every done-gate condition with current persisted evidence.
3. Validate that `open_blocking_issues` equals the ledger count and inspect every open blocking issue.
4. Preserve all failed, blocked, denied, unverified and unknown outcomes in the digest.
5. Confirm delivered artifacts, route history, authority used, budgets and last completed action.
6. Emit `complete` only when every required evidence item passed and no open blocking issue remains.
7. Otherwise emit the exact valid status and terminal reason; never convert an incomplete mission to complete.
8. Produce a portable handoff with reproduction steps and the next safe action for every unresolved item.

## Output contract

Return:

- run ID, stage `close`, track, declared asset and objective;
- delivered artifacts and source or repository state;
- route, evidence and issue outcomes;
- authority used, lease and usage summary;
- last completed action, pending or unknown effects and unresolved gates;
- exact final status, terminal reason and portable handoff.

## Evidence gate

`COMPLETE` requires all done-gate evidence passed and zero blocking issues outside `closed`. Any missing, stale, failed, blocked, denied or unverified required evidence blocks completion. The final event must satisfy the run-state contract.

## Track requirements

For the code track, preserve revision or worktree state, reproducible checks and deployment or release status. For the non-code track, preserve final artifact, sources, factuality and review evidence plus publication status. Both code track and non-code track distinguish produced from externally published.

## Safety and authority

Close cannot repair state by assertion, replay an unknown effect or perform an unapproved outward action. Elevated authority remains visibly warned. Kill-halted, waiting, failed and cancelled states stay truthful and require their defined recovery path.

## Self-refutation

Compare the final claim with authoritative evidence and the issue ledger. Ask whether any missing check, unresolved effect, open blocker or stale input contradicts the proposed status.

## Halt conditions

Halt completion when the event chain is invalid, evidence cannot be resolved, the blocking count drifts, a pending outcome is unknown, authority is absent for the terminal event, the namespace changes or a stop signal requires `halted_kill_switch`. Still return the last verified state and next safe action.

## References

- [Stage contracts](../../../protocols/stage-contracts.md)
- [Skill routing](../../../protocols/skill-routing.md)
- [Code and non-code tracks](../../../protocols/code-non-code-tracks.md)
- [Autonomy policy](../../../protocols/autonomy-policy.md)
- [Run state and leases](../../../protocols/run-state-leases.md)
- [Issue ledger](../../../protocols/issue-ledger.md)
- [Evidence contract](../../../protocols/evidence-contract.md)
