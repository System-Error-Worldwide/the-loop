---
name: the-loop-endless
description: Supervisor that selects only approved queue items and runs bounded Auto missions with empty-queue stop, unchanged caps and safe-boundary cold epochs.
license: MIT
compatibility: Codex, Claude Code, Kimi Code, OpenCode and DeepSeek Harness
metadata:
  the-loop-capability: runtime.endless
  the-loop-version: "0.1"
---

# The Loop Endless

## Purpose

Provide the complete bundled fallback for continuous supervision. Select work only from an approved queue, run each item as a bounded Auto mission, and stop when the queue is empty. Never invent missions or broaden authority.

## Use when

Use when an approved queue, kill boundaries, lease recovery and empty-queue halting are configured and the user wants repeated bounded missions under the same safety contracts as Auto.

## Required inputs

- Supervisor configuration with approved queue reference and empty-queue stop semantics.
- Per-mission asset, track, done gate, frozen budgets, authority, kill switch and retry limits.
- Active injected capability catalog and current run-state projections.
- Evidence that queue selection is authorized and bounded.

Reject an undeclared queue, missing kill switch or open-ended mission scope.

## Procedure

1. Observe queue and authoritative state; start one bounded Auto mission only when safety gates pass and a fresh lease is available.
2. After each mission, verify budgets, issues and recovery boundaries before selecting the next approved item.
3. When the queue is empty, stop mission dispatch and return a truthful handoff. Read-only observation MAY occur only when explicitly configured as bounded monitoring; it MUST NOT become indefinite monitoring or invent new work.
4. Rotate context only at a safe boundary with no active mutations and no unresolved operations; carry compact goal, state, next action and evidence references; acquire a fresh lease through authorized recovery while preserving usage and caps. Do not stop solely because of an arbitrary context-size threshold.
5. Use optional completion signals only when observed; validate result envelopes and durable state. Detached work requires supervisor recovery; watchers remain read-only.
6. If selection fails or authority is revoked, pause and surface an explicit repair path.

## Output contract

Return supervisor run ID, queue state, active mission summary, heartbeat evidence, budget usage, halt reason and next safe action.

## Evidence gate

Each mission must satisfy Auto evidence gates before the supervisor advances the queue. Missing fresh evaluation or open blockers prevent claiming queue progress.

## Track requirements

Inherit track rules from each bounded mission. Outward actions remain gated per mission authority.

## Safety and authority

Endless cannot create queue items, elevate permissions, reset budgets on recovery or bypass Auto halt rules. Recovery uses a fresh lease and does not replay unknown effects.

## Self-refutation

Ask whether the next mission is still on the approved queue, within caps and covered by current authority.

## Halt conditions

Halt on empty queue when stop is required, mission failure without recovery, revoked authority, kill signal, budget exhaustion, expired or lost lease, namespace mismatch, unsafe proof, private data exposure, unknown required capability, reopened issue or three red Test/Resolve passes on the active mission.

Core execution does not require network access or the source checkout. The links below are optional public documentation.

## References

- [Workflow dispatch](https://github.com/System-Error-Worldwide/the-loop/blob/main/protocols/workflow-dispatch.md)
- [Stage contracts](https://github.com/System-Error-Worldwide/the-loop/blob/main/protocols/stage-contracts.md)
- [Autonomy policy](https://github.com/System-Error-Worldwide/the-loop/blob/main/protocols/autonomy-policy.md)
- [Run state and leases](https://github.com/System-Error-Worldwide/the-loop/blob/main/protocols/run-state-leases.md)
- [Skill routing](https://github.com/System-Error-Worldwide/the-loop/blob/main/protocols/skill-routing.md)
