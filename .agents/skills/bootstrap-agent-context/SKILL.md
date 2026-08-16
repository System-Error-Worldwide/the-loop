---
name: bootstrap-agent-context
description: Initialize a bounded context for a run with evidence, scope, and recovery anchors.
license: MIT
compatibility: Codex, Claude Code, Kimi Code and OpenCode
metadata:
  the-loop-capability: context.bootstrap
  the-loop-version: "0.1"
---

# Bootstrap Agent Context

Initialize a bounded context for a run with evidence, scope, and recovery anchors.

## Use when

- Use before orchestration starts when track, owner, and expected boundaries are unknown.

## Inputs

- Active run, objective, track, and authority context.
- Declared track boundaries and budget controls.
- Typed evidence references and required file paths.

## Procedure

1. Read minimal project and user context required for safe run bootstrapping.
2. Collect canonical identifiers and freeze them into typed context.
3. Initialize run boundaries, expected outputs, and stop conditions.
4. Never infer hidden credentials or private infrastructure assumptions.
5. Return a stable context snapshot for later diagnostics and handoff.

## Output contract

- Deterministic status, evidence hash list, and explicit status transitions.
- Typed halt reason with exact next-step obligations when blocked.

## Halt conditions

Stop with a precise error for missing authority, expired lease, namespace mismatch, unsafe proof, private data exposure, unknown capability, or unverified behavior claim.

## Notes

Core execution does not require network access or the source checkout. Use the bundled fallback behavior when live capabilities are blocked.
