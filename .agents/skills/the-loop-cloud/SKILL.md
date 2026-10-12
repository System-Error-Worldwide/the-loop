---
name: the-loop-cloud
description: Restricted or remote lifecycle work with real Build and Test execution when authorized shell and filesystem capabilities are observed; otherwise bounded planning, drafting and handoff without private infrastructure assumptions.
license: MIT
compatibility: Codex, Claude Code, Kimi Code, OpenCode and DeepSeek Harness
metadata:
  the-loop-capability: orchestration.cloud
  the-loop-version: "0.1"
---

# The Loop Cloud

## Purpose

Provide the complete bundled fallback for restricted or remote execution context. Route and qualify providers first; choose topology from observed capabilities. Execute real Build and Test commands when the active environment authorizes filesystem and shell work; use planning-only mode only when execution is unavailable.

## Use when

Use when the run must continue in a sandboxed, remote or network-separated environment and the user has declared asset, track, authority and done gate.

## Required inputs

- Validated run ID, declared asset, immutable track, objective and done gate.
- Active authority, owner, lease expectations, frozen budgets and stop controls; when stop controls, budgets or caps are missing, defer to the common stage envelope in [stage contracts](https://github.com/System-Error-Worldwide/the-loop/blob/main/protocols/stage-contracts.md) and halt with a named gap rather than inventing limits.
- When present, the active injected capability catalog; otherwise scoped discovery in documented harness roots and the qualified bundled fallback. Route records for required lifecycle stages. Absence of catalog injection alone MUST NOT halt portable core execution.
- Material authorized in the remote environment and explicit gaps when protected state is missing.

Reject missing authority, undeclared write boundaries or requests that require private topology disclosure.

## Procedure

1. Resolve each stage capability through routing before choosing native collaboration, guarded process or serial execution.
2. When filesystem and shell capabilities are observed and authorized, run the same Build and Test commands as local execution: record command, working directory, exit status and output artifact references.
3. When execution is unavailable, produce planning and drafting outputs only, name capability gaps and hand off with explicit next obligations.
4. Do not require invented transport or signature proof for local restricted work that stays inside authorized boundaries; genuine remote dispatch keeps dispatch proof and trusted-destination restrictions from [workflow dispatch](https://github.com/System-Error-Worldwide/the-loop/blob/main/protocols/workflow-dispatch.md).
5. Persist evidence through normal state contracts; missing required checks never promote green.

## Output contract

Return run ID, mode `cloud`, track, stage, authority and lease state; route and fallback reason; commands executed or planning-only gap list; artifacts and evidence references; issue summary; gate state; and next stage or halt.

## Evidence gate

Passed gates require persisted evidence. Unexecuted required checks remain unverified and block green. Planning output alone does not satisfy executable done-gate conditions.

## Track requirements

For the code track, preserve repository boundaries, command reproducibility and outward Git or deploy gates. For the non-code track, preserve factuality, format and publication gates.

## Safety and authority

Cloud mode does not broaden authority, bypass host denial or replay unknown effects. Unrelated user work and namespace invariants MUST be preserved. Optional completion signals validate envelopes and durable state; detached work needs supervisor recovery per dispatch contract. A watcher stays read-only.

## Self-refutation

Ask whether each claimed execution actually ran in the authorized environment and whether planning-only output is being treated as tested work.

## Halt conditions

Halt on missing authority, stop signal, budget exhaustion, unresolved unknown effect, expired lease, namespace mismatch, unsafe remote destination proof when dispatch is claimed, private data exposure, unknown capability, unverified behavior claim or blocked required checks.

Core execution does not require network access or the source checkout. The links below are optional public documentation.

## References

- [Workflow dispatch](https://github.com/System-Error-Worldwide/the-loop/blob/main/protocols/workflow-dispatch.md)
- [Stage contracts](https://github.com/System-Error-Worldwide/the-loop/blob/main/protocols/stage-contracts.md)
- [Skill routing](https://github.com/System-Error-Worldwide/the-loop/blob/main/protocols/skill-routing.md)
- [Code and non-code tracks](https://github.com/System-Error-Worldwide/the-loop/blob/main/protocols/code-non-code-tracks.md)
- [Autonomy policy](https://github.com/System-Error-Worldwide/the-loop/blob/main/protocols/autonomy-policy.md)
- [Evidence contract](https://github.com/System-Error-Worldwide/the-loop/blob/main/protocols/evidence-contract.md)
- [Run state and leases](https://github.com/System-Error-Worldwide/the-loop/blob/main/protocols/run-state-leases.md)
- [Issue ledger](https://github.com/System-Error-Worldwide/the-loop/blob/main/protocols/issue-ledger.md)
- [Harness capability map](https://github.com/System-Error-Worldwide/the-loop/blob/main/protocols/harness-capability-map.md)
