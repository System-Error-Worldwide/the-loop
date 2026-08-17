---
name: test
description: Independently attempt to falsify the done gate, persist reproducible evidence and open every defect that survives refutation. Use when an approved implementation or non-code asset must be verified independently before it can be called green.
license: MIT
compatibility: Codex, Claude Code, Kimi Code, OpenCode and DeepSeek Harness
metadata:
  the-loop-capability: lifecycle.test
  the-loop-version: "0.1"
---

# Test

## Purpose

Provide the complete bundled fallback for `lifecycle.test`. Judge the artifact against declared requirements and observed evidence, not the implementer's success claim.

## Use when

Use after Build, after Resolve returns an issue to independent verification, or whenever a done-gate claim needs falsification.

## Required inputs

- Validated run ID, declared asset, track, current stage and exact done gate.
- Requirement IDs, changed artifacts, environment and relevant prior evidence.
- Current issue ledger, regression procedures and provider route records.
- Read authority for checks and exact authority plus matching lease for evidence or issue writes.
- Frozen budgets, stop controls and known unavailable capabilities.

Reject a test request whose acceptance conditions or observable environment cannot be identified.

## Procedure

1. Derive checks from the done gate, requirements, changed behavior, failure paths and track contract.
2. Attempt to falsify every acceptance claim before accepting it.
3. Exercise the normal path plus relevant boundaries, invalid inputs, permission denial, interruption, recovery and truthful unsupported behavior.
4. Capture reproducible evidence with procedure, actor, time, environment, outcome and result artifact.
5. Reproduce each candidate defect and try to refute it. Drop candidates that do not survive.
6. For every surviving defect, open or update one issue with severity, blocking state, minimal reproduction, expected and observed behavior and regression procedure.
7. Close an issue only when new passing regression evidence exists; preserve the original failure evidence.
8. Report green only when all required evidence passes and no blocking issue remains open.

## Output contract

Return:

- run ID, stage `test`, track and declared asset;
- checks attempted, coverage classification and exact environment;
- reproducible evidence references for each requirement;
- surviving defect and issue references;
- unexecuted, denied, blocked and unverified checks;
- gate state and next stage: `resolve`, `close` or a truthful halt.

## Evidence gate

Every passed condition needs current persisted evidence with a non-empty procedure and result reference. Any missing, stale, failed, blocked, denied or unverified required check blocks green. A screenshot proves only its captured visual state.

## Track requirements

For the code track, select justified build, static, unit, integration, security and behavior checks and preserve commands plus exit status. For the non-code track, test source quality, factuality, calculations, completeness, requested format, render output, audience fit and domain-specific review. Both code track and non-code track label bounded or sampled coverage explicitly.

## Safety and authority

Evidence collection stays within current authority. A read-only test cannot mutate production or contact an external system. Issue and evidence writes use the runtime intent boundary. Provider failure is recorded before rerouting and unknown operations are never replayed.

## Self-refutation

Attempt to reproduce each claimed defect and break each claimed pass. Check that a passing command actually exercises the requirement and that the observed artifact matches the inputs under review.

## Halt conditions

Halt green promotion when a required check cannot run, evidence is stale or invalid, a blocking issue remains, authority is denied, the lease is lost, a stop is detected, the namespace changes, or the retry gate is exhausted. A reopened issue or three red Test/Resolve passes requires a human gate.

Core execution does not require network access or the source checkout. The links below are optional public documentation.

## References

- [Stage contracts](https://github.com/System-Error-Worldwide/the-loop/blob/main/protocols/stage-contracts.md)
- [Skill routing](https://github.com/System-Error-Worldwide/the-loop/blob/main/protocols/skill-routing.md)
- [Code and non-code tracks](https://github.com/System-Error-Worldwide/the-loop/blob/main/protocols/code-non-code-tracks.md)
- [Autonomy policy](https://github.com/System-Error-Worldwide/the-loop/blob/main/protocols/autonomy-policy.md)
- [Run state and leases](https://github.com/System-Error-Worldwide/the-loop/blob/main/protocols/run-state-leases.md)
- [Issue ledger](https://github.com/System-Error-Worldwide/the-loop/blob/main/protocols/issue-ledger.md)
- [Evidence contract](https://github.com/System-Error-Worldwide/the-loop/blob/main/protocols/evidence-contract.md)
