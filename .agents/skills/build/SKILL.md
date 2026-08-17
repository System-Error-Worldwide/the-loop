---
name: build
description: Implement one approved code slice or non-code drafting unit while preserving unrelated work and recording the smallest relevant checks. Use after strategy and required specifications are green and one bounded implementation unit is approved.
license: MIT
compatibility: Codex, Claude Code, Kimi Code, OpenCode and DeepSeek Harness
metadata:
  the-loop-capability: lifecycle.build
  the-loop-version: "0.1"
---

# Build

## Purpose

Provide the complete bundled fallback for `lifecycle.build`. Produce only the artifacts required by one approved slice and leave acceptance to Test.

## Use when

Use after the applicable strategy and specification gate has passed and one code slice or non-code drafting unit has explicit boundaries, requirements and a done gate.

## Required inputs

- Validated run ID, declared asset, immutable track and stage `build`.
- One approved slice, requirement IDs, write paths and acceptance conditions.
- Current repository or source state, including overlapping user changes.
- Active authority, owner, lease generation, frozen budgets and kill-switch state.
- Selected route, evidence obligations and open issue summary.

Reject a slice that is unapproved, internally contradictory or missing its verification method.

## Procedure

1. Revalidate state, namespace, ownership, lease, authority, budget and stop controls.
2. Inspect only the context needed for one approved slice and identify unrelated changes before mutation.
3. For unattended code, establish branch or equivalent isolation before editing.
4. Route the requested capability; use this bundled fallback when no installed provider qualifies and record why.
5. Make the minimum necessary change. Do not refactor adjacent code or broaden a non-code deliverable for convenience.
6. Before every side-effecting callback, use the runtime durable-intent boundary. Never replay an unknown outcome.
7. Run the smallest relevant checks that catch malformed output before independent Test.
8. Record changed artifacts, requirement coverage, limitations and any observed defect without claiming green.

## Output contract

Return:

- run ID, stage `build`, track, declared asset and approved slice;
- changed or produced artifacts and preserved unrelated changes;
- implemented requirement IDs and deliberate non-changes;
- smallest relevant checks with evidence references;
- new or updated issue references;
- usage, last completed action, gate state and recommended `test` or halt.

## Evidence gate

Build evidence identifies each changed artifact, the requirement it implements and the smallest relevant check performed. A passing pre-check is not independent acceptance. Missing checks remain `UNVERIFIED` and are handed to Test.

## Track requirements

For the code track, preserve worktree state, isolation, executable commands, exit status and security-relevant behavior. For the non-code track, preserve source attribution, factuality, requested format, calculation or render evidence and review readiness. Both code track and non-code track keep publishing and external changes behind approval.

## Safety and authority

Mutate only declared paths under the current lease. Do not stage, reset, delete, send, push, merge, deploy, publish, purchase, change remote configuration or install providers without exact authority. An installed provider cannot widen the parent grant.

## Self-refutation

Ask whether every change is necessary for the declared slice, whether a smaller change meets the done gate and whether any unrelated behavior or user work was damaged.

## Halt conditions

Halt on missing gated specifications, lost ownership, namespace replacement, scope expansion, overlapping unowned changes, absent or expired authority, exhausted budget, stop signal, unknown callback outcome or a required verification method that cannot run. Report the last safe state and recovery condition.

Core execution does not require network access or the source checkout. The links below are optional public documentation.

## References

- [Stage contracts](https://github.com/System-Error-Worldwide/the-loop/blob/main/protocols/stage-contracts.md)
- [Skill routing](https://github.com/System-Error-Worldwide/the-loop/blob/main/protocols/skill-routing.md)
- [Code and non-code tracks](https://github.com/System-Error-Worldwide/the-loop/blob/main/protocols/code-non-code-tracks.md)
- [Autonomy policy](https://github.com/System-Error-Worldwide/the-loop/blob/main/protocols/autonomy-policy.md)
- [Run state and leases](https://github.com/System-Error-Worldwide/the-loop/blob/main/protocols/run-state-leases.md)
- [Issue ledger](https://github.com/System-Error-Worldwide/the-loop/blob/main/protocols/issue-ledger.md)
- [Evidence contract](https://github.com/System-Error-Worldwide/the-loop/blob/main/protocols/evidence-contract.md)
