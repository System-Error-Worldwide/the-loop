---
name: the-loop-cloud
description: Provider-neutral remote planning envelope for restricted non-local execution context.
license: MIT
compatibility: Codex, Claude Code, Kimi Code, OpenCode and DeepSeek Harness
metadata:
  the-loop-capability: orchestration.cloud
  the-loop-version: "0.1"
---

# The Loop Cloud

Provider-neutral remote planning envelope for restricted non-local execution context.

## Use when

- Use when a run needs to offload coordination to a remote planner under no private infrastructure assumptions.

## Inputs

- Active run, objective, track, and authority context.
- Declared track boundaries and budget controls.
- Typed evidence references and required file paths.

## Procedure

1. Normalize remote capability, timeout, and trust assumptions into a bounded contract envelope.
2. Strip private topology details and convert local-only references to portable equivalents.
3. Verify signed context, destination, permissions, and evidence before queueing any remote task.
4. Refuse execution if remote replay, transport, or namespace proof is missing.
5. Persist proof of accepted plans and map remote results back through normal state contracts.

## Output contract

- Deterministic status, evidence hash list, and explicit status transitions.
- Typed halt reason with exact next-step obligations when blocked.

## Halt conditions

Stop with a precise error for missing authority, expired lease, namespace mismatch, unsafe proof, private data exposure, unknown capability, or unverified behavior claim.

## Notes

Core execution does not require network access or the source checkout. Use the bundled fallback behavior when live capabilities are blocked.
