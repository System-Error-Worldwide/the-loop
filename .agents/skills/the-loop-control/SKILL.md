---
name: the-loop-control
description: Runtime control plane for stop/recover/halt transitions and explicit escalation boundaries.
license: MIT
compatibility: Codex, Claude Code, Kimi Code, OpenCode and DeepSeek Harness
metadata:
  the-loop-capability: control.runtime
  the-loop-version: "0.1"
---

# The Loop Control

Runtime control plane for stop/recover/halt transitions and explicit escalation boundaries.

## Use when

- Use when multiple agents or lifecycle owners need one explicit control path for run progression.

## Inputs

- Active run, objective, track, and authority context.
- Declared track boundaries and budget controls.
- Typed evidence references and required file paths.

## Procedure

1. Map every requested control command to a finite-state transition and verified preconditions.
2. Validate namespace, run identity, and lease before any control mutation.
3. Apply control atomically with failure rollback; if rollback fails, return precise state.
4. Do not continue any run advancement after control-level terminalization unless recovery evidence exists.
5. Record control provenance and emitted command/result for later audit.

## Output contract

- Deterministic status, evidence hash list, and explicit status transitions.
- Typed halt reason with exact next-step obligations when blocked.

## Halt conditions

Stop with a precise error for missing authority, expired lease, namespace mismatch, unsafe proof, private data exposure, unknown capability, or unverified behavior claim.

## Notes

Core execution does not require network access or the source checkout. Use the bundled fallback behavior when live capabilities are blocked.
