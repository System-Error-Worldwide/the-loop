---
name: the-loop
description: Run one attended evidence-led lifecycle with visible stage gates, qualified routing, bundled fallbacks and truthful close. Use when a user asks to take one code or non-code asset through strategy, specification, build, independent test, resolution and close with confirmation at meaningful gates.
license: MIT
compatibility: Codex, Claude Code, Kimi Code and OpenCode
metadata:
  the-loop-capability: orchestration.attended
  the-loop-version: "0.1"
---

# The Loop

## Purpose

Provide the complete bundled fallback for one attended v0.1 mission. Coordinate the public lifecycle while keeping meaningful gates visible to the user.

The default sequence is `strategize -> spec_pack -> build -> test -> close`, with `test -> resolve -> test` only while issue and retry gates permit it.

## Use when

Use when the user wants one declared code or non-code asset driven through an attended lifecycle and expects confirmation at meaningful scope, specification, authority and outward-action gates.

## Required inputs

- Intent, one declared asset, immutable track and testable desired outcome.
- Validated run ID or authority to create one, owner and project root.
- Frozen budgets, authority grant, done gate and stop-control configuration.
- Current source or repository state, evidence and issue references.
- Harness capability catalog or a truthful statement that no installed provider is verified.

Do not infer missing scope, owner, authority, success criteria or track.

## Procedure

1. Create or load one run and display asset, track, authority, budgets and current gate.
2. Acquire or validate the matching lease before any writing action.
3. For each stage, validate authoritative state, stop controls, clock, ownership, lease, authority and budget.
4. Submit the smallest capability request and persist the route before execution.
5. Use a qualified installed provider when proven; otherwise run the complete bundled fallback and show the fallback reason.
6. Execute Strategize, then surface its meaningful decision gate.
7. Execute Spec pack when required and surface the implementation gate.
8. Execute one approved Build slice, then independent Test.
9. Route surviving issues through Resolve and back to Test until green or the retry gate halts.
10. Execute Close with authoritative evidence and issue state. Never translate blocked, denied, failed or unverified outcomes into success.

## Output contract

At each boundary show run ID, declared asset, mode, track, stage, owner and lease; authority and expiry; budgets and usage; selected provider and fallback reason; artifacts, evidence and issues; last completed action; current done gate; and next stage or halt.

Final output includes the exact run status and portable handoff.

## Evidence gate

Advance a stage only after its output contract is satisfied and required evidence is persisted. Close as complete only when every done-gate condition passes and no blocking issue remains open. Attended confirmation is recorded; conversational momentum is not approval.

## Track requirements

For the code track, require repository identity, isolation before unattended edits, executable checks and explicit push, merge, deploy or release authority. For the non-code track, require audience, format, factuality, source quality, review evidence and explicit publication authority.

## Safety and authority

The attended mode still enforces runtime state, durable operation intent, lease ownership, frozen budgets and the external kill switch. Installed providers inherit no broader authority. Unknown outcomes are reconciled without replay.

Optional delegation is capability-gated. If it is unavailable, run the same packet serially or inline. Any watcher remains read-only and cannot own, repair or advance the run.

## Self-refutation

At every stage ask whether the claimed gate is supported by authoritative evidence, whether scope has expanded and whether provider-specific success language hides a missing common-contract field.

## Halt conditions

Halt for missing specifications, unresolved strategic forks, absent or expired authority, lost lease, changed namespace, stop signal, exhausted budget, unknown external state, reopened issue, three red Test/Resolve passes or any security, legal, privacy, money or destructive judgment outside scope. Return the exact reason and continuation condition.

Core execution does not require network access or the source checkout. The links below are optional public documentation.

## References

- [Stage contracts](https://github.com/System-Error-Worldwide/the-loop/blob/main/protocols/stage-contracts.md)
- [Skill routing](https://github.com/System-Error-Worldwide/the-loop/blob/main/protocols/skill-routing.md)
- [Code and non-code tracks](https://github.com/System-Error-Worldwide/the-loop/blob/main/protocols/code-non-code-tracks.md)
- [Autonomy policy](https://github.com/System-Error-Worldwide/the-loop/blob/main/protocols/autonomy-policy.md)
- [Run state and leases](https://github.com/System-Error-Worldwide/the-loop/blob/main/protocols/run-state-leases.md)
- [Issue ledger](https://github.com/System-Error-Worldwide/the-loop/blob/main/protocols/issue-ledger.md)
- [Evidence contract](https://github.com/System-Error-Worldwide/the-loop/blob/main/protocols/evidence-contract.md)
- [Workflow dispatch](https://github.com/System-Error-Worldwide/the-loop/blob/main/protocols/workflow-dispatch.md)
- [Watcher contract](https://github.com/System-Error-Worldwide/the-loop/blob/main/protocols/watcher-contract.md)
- [Harness capability map](https://github.com/System-Error-Worldwide/the-loop/blob/main/protocols/harness-capability-map.md)
