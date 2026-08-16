---
name: strategize
description: Turn a stated intent into the smallest bounded problem, outcome, scope and testable success gate before implementation begins.
license: MIT
compatibility: Codex, Claude Code, Kimi Code and OpenCode
metadata:
  the-loop-capability: lifecycle.strategize
  the-loop-version: "0.1"
---

# Strategize

## Purpose

Provide the complete bundled fallback for `lifecycle.strategize`. Convert intent into a decision brief that is bounded enough to specify and verify. Do not draft implementation or hide a strategic fork.

## Use when

Use for the first lifecycle stage, or when scope, objective or the definition of success has materially changed. An installed specialist may replace this fallback only through a recorded qualified route.

## Required inputs

- Validated run ID, declared asset, immutable `code` or `noncode` track and current stage.
- User intent, known constraints, supplied sources and relevant prior decisions.
- Frozen mission budget, active authority reference and exact mutation boundary.
- Current issues and evidence references, if this is a revised strategy.
- A requested capability and fallback route decision.

Reject the invocation when owner, lease, authority, asset, track or state cannot be established. Read-only analysis may continue only if the result is explicitly an unverified halt packet rather than a stage pass.

## Procedure

1. Restate the observed problem without adding unconfirmed facts.
2. Define the desired outcome and the user or operator who benefits.
3. Draw explicit in-scope, out-of-scope and later boundaries around one declared asset.
4. List assumptions as confirmed, safely defaulted with a reversal condition, or unresolved human gates.
5. Identify dependencies, authority needs, external effects, cost, privacy, legal and security risks.
6. State success measures and turn each into a falsifiable done gate.
7. Choose the smallest sufficient next unit: specification, one build slice, a non-code drafting unit, or a truthful halt.
8. Record the bundled fallback as provider source and preserve every installed-candidate rejection reason.

## Output contract

Return:

- run ID, stage `strategize`, track and declared asset;
- bounded problem statement and desired outcome;
- in-scope, out-of-scope and later lists;
- assumptions, constraints, risks and unresolved decisions;
- success measures and exact done gate;
- produced artifacts plus evidence and issue references;
- resulting gate state and recommended next stage or halt reason.

## Evidence gate

Pass only when each material assumption has a confirmation, safe default with reversal condition, or named human gate, and each success measure has a verification method. Persist passing evidence before advancing. Missing or stale required evidence is `UNVERIFIED`, never passed.

## Track requirements

For the code track, include repository identity, worktree state, intended isolation, live-state coverage and executable acceptance behavior. For the non-code track, include audience, format, factuality standard, source threshold, review method and publication boundary.

## Safety and authority

Strategy may recommend outward work but cannot perform it. Expansion to another asset, audience, integration or materially broader success condition requires a new authority decision. Every side effect remains behind runtime preflight, durable intent and an unexpired matching lease.

## Self-refutation

Ask: does this solve the stated problem with the smallest sufficient scope, and could a different implementer satisfy the wording while producing the wrong outcome? Tighten any ambiguous gate before passing.

## Halt conditions

Halt on a strategic fork that changes the asset, authority, cost, legal exposure, privacy exposure or success definition; missing required source state; conflicting constraints; exhausted budget; detected stop; lost ownership; or an unavailable verification method. Include the last completed action, evidence gap and exact decision needed to continue.

## References

- [Stage contracts](../../../protocols/stage-contracts.md)
- [Skill routing](../../../protocols/skill-routing.md)
- [Code and non-code tracks](../../../protocols/code-non-code-tracks.md)
- [Autonomy policy](../../../protocols/autonomy-policy.md)
- [Run state and leases](../../../protocols/run-state-leases.md)
- [Issue ledger](../../../protocols/issue-ledger.md)
- [Evidence contract](../../../protocols/evidence-contract.md)
