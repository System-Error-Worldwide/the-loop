---
name: health-check
description: Diagnose an observed symptom with reproducible evidence and return a bounded lifecycle entry packet without silently fixing it.
license: MIT
compatibility: Codex, Claude Code, Kimi Code and OpenCode
metadata:
  the-loop-capability: feeder.health_check
  the-loop-version: "0.1"
---

# Health check

## Purpose

Provide the complete bundled fallback for `feeder.health_check`. React to an observed symptom, establish what is actually failing and feed bounded evidence into the lifecycle without silently fixing the asset.

## Use when

Use when a user reports breakage, an expected surface is unavailable, a check begins failing or current health must be established for a named surface.

## Required inputs

- Validated run ID or a new-run request, declared asset, code or non-code track and observed symptom.
- Requested surface, expected behavior and available environment or source state.
- Read authority plus any exact authority and lease required to persist evidence or issues.
- Current done gate, known issues, budgets and stop controls.
- Requested diagnostic capability and route decision.

Reject an unbounded “check everything” request unless it is narrowed to an enumerated surface and coverage limit.

## Procedure

1. Restate the observed symptom and the exact surface under review.
2. Establish live or supplied state using read-only checks first; name inaccessible coverage.
3. Derive the smallest reproductions that distinguish the symptom from nearby causes.
4. Record command, file, source, visual or manual evidence with truthful outcomes.
5. Attempt to reproduce and refute each candidate defect.
6. Open an issue for every surviving implementation defect; do not change the asset.
7. Route the bounded entry packet to Strategize, Test or the issue ledger as appropriate.
8. Report the bundled fallback source and the precise reason any installed provider did not qualify.

## Output contract

Return:

- run ID, feeder `health-check`, track and declared asset;
- observed symptom, inspected surface and coverage classification;
- reproductions, evidence references and surviving issue references;
- ruled-out causes and unverified areas;
- bounded entry packet with target stage, done gate and required authority;
- gate state, next safe action or halt reason.

## Evidence gate

A diagnosis needs reproducible evidence tying the symptom to the claimed cause. File existence or process presence alone is not health proof. Sampled checks remain labeled sampled, and inaccessible checks remain `UNVERIFIED`.

## Track requirements

For the code track, preserve repository identity, worktree state, relevant runtime behavior and executable reproductions. For the non-code track, preserve source access, factuality, format or render observations and review gaps. Neither track converts observation into mutation.

## Safety and authority

Health-check is diagnostic. It does not own lifecycle advancement and proceeds without silently fixing a defect. Read-only checks must not mutate local or external state. Evidence or issue writes still require runtime preflight and a valid lease.

## Self-refutation

Ask whether the symptom reproduces, whether the proposed cause predicts the observation and whether a narrower competing cause fits the same evidence. Remove findings that do not survive.

## Halt conditions

Halt when the requested surface cannot be identified, state is inaccessible, a check would exceed authority, the namespace changes, a stop is detected, evidence cannot distinguish causes, or the request expands beyond the declared boundary. Return an entry packet rather than green.

## References

- [Stage contracts](../../../protocols/stage-contracts.md)
- [Skill routing](../../../protocols/skill-routing.md)
- [Code and non-code tracks](../../../protocols/code-non-code-tracks.md)
- [Autonomy policy](../../../protocols/autonomy-policy.md)
- [Run state and leases](../../../protocols/run-state-leases.md)
- [Issue ledger](../../../protocols/issue-ledger.md)
- [Evidence contract](../../../protocols/evidence-contract.md)
