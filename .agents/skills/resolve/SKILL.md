---
name: resolve
description: Apply the minimum repair for owned reproducible issues and return them to independent verification without closing them yourself. Use when Test has recorded a reproducible owned defect with a bounded repair gate.
license: MIT
compatibility: Codex, Claude Code, Kimi Code, OpenCode and DeepSeek Harness
metadata:
  the-loop-capability: lifecycle.resolve
  the-loop-version: "0.1"
---

# Resolve

## Purpose

Provide the complete bundled fallback for `lifecycle.resolve`. Repair evidence-backed defects through the durable issue lifecycle while preserving failure history.

## Use when

Use only after Test records one or more reproducible issues and an explicit owner accepts the bounded resolution work.

## Required inputs

- Validated run ID, declared asset, track and stage `resolve`.
- Owned issue IDs, original failure evidence and minimal reproductions.
- Affected requirement IDs, approved write boundary and regression procedure.
- The issue-specific done gate for returning the repair to independent Test.
- Current artifact or repository state, including unrelated changes.
- Active authority, matching lease, frozen budgets and stop controls.

Reject unowned issues, invalid issue transitions and fixes without a reproducible failure.

## Procedure

1. Validate issue status and ownership, then move the issue to `resolving` through the durable event boundary.
2. Rerun the original reproduction and inspect for a narrower cause.
3. Make the minimum change that addresses that cause while preserving unrelated work.
4. Record what changed and link it to the same issue and requirement IDs.
5. Run only the smallest repair check needed before independent Test.
6. Move the issue to `verification_pending`; do not close it.
7. Return the original reproduction and regression procedure to Test.
8. If the issue reopens after one attempted closure, stop the autonomous loop and surface the stuck condition.

## Output contract

Return:

- run ID, stage `resolve`, track and declared asset;
- owned issue IDs and status transitions;
- root cause, changed artifacts and preserved unrelated state;
- repair evidence and exact regression procedure;
- issues moved to `verification_pending`;
- usage, gate state and recommended `test` or halt.

## Evidence gate

Resolve passes its own stage only when the original failure remains linked, the repair is documented, the issue is `verification_pending` and Test has a reproducible regression procedure. Repair evidence is not closure evidence.

## Track requirements

For the code track, preserve isolation, command output and executable regression steps. For the non-code track, preserve source and factuality evidence, changed sections, calculation or render checks and reviewer instructions. Both code track and non-code track retain the original defect record.

## Safety and authority

Mutate only the owned issue and declared artifact boundary under the current lease. Do not weaken tests, evidence gates, issue severity or authority to make a failure disappear. External correction, publication or notification needs explicit outward authority.

## Self-refutation

Rerun the original reproduction, ask whether the cause is narrower than the proposed fix and look for a regression hidden by the change. Do not alter the reproduction merely to make it pass.

## Halt conditions

Halt when the issue lacks evidence or ownership, the reproduction is no longer valid and cannot be explained, scope expands, unrelated changes overlap, authority or lease is invalid, a stop is detected, an unknown outcome exists, the issue reopens, or Test remains red after three passes.

Core execution does not require network access or the source checkout. The links below are optional public documentation.

## References

- [Stage contracts](https://github.com/System-Error-Worldwide/the-loop/blob/main/protocols/stage-contracts.md)
- [Skill routing](https://github.com/System-Error-Worldwide/the-loop/blob/main/protocols/skill-routing.md)
- [Code and non-code tracks](https://github.com/System-Error-Worldwide/the-loop/blob/main/protocols/code-non-code-tracks.md)
- [Autonomy policy](https://github.com/System-Error-Worldwide/the-loop/blob/main/protocols/autonomy-policy.md)
- [Run state and leases](https://github.com/System-Error-Worldwide/the-loop/blob/main/protocols/run-state-leases.md)
- [Issue ledger](https://github.com/System-Error-Worldwide/the-loop/blob/main/protocols/issue-ledger.md)
- [Evidence contract](https://github.com/System-Error-Worldwide/the-loop/blob/main/protocols/evidence-contract.md)
