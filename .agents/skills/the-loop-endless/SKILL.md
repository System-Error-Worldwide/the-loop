---
name: the-loop-endless
description: Supervisor mode that can pick safe bounded missions continuously without inventing new authority.
license: MIT
compatibility: Codex, Claude Code, Kimi Code and OpenCode
metadata:
  the-loop-capability: runtime.endless
  the-loop-version: "0.1"
---

# The Loop Endless

Supervisor mode that can pick safe bounded missions continuously without inventing new authority.

## Use when

- Use only when bounded kill boundaries, lease/authority recovery, and queue-empty halting are proven.

## Inputs

- Active run, objective, track, and authority context.
- Declared track boundaries and budget controls.
- Typed evidence references and required file paths.

## Procedure

1. Initialize supervisor config with explicit empty-queue stop semantics and kill-safety gates.
2. Observe queue and state signals; start one bounded mission only when safety gates are closed and fresh.
3. After each mission, verify state, budgets, and recovery boundaries before selecting next mission.
4. If mission selection fails or authority is revoked, pause and surface explicit repair path.
5. Emit periodic heartbeat evidence and never continue without explicit recovery permissions.

## Output contract

- Deterministic status, evidence hash list, and explicit status transitions.
- Typed halt reason with exact next-step obligations when blocked.

## Halt conditions

Stop with a precise error for missing authority, expired lease, namespace mismatch, unsafe proof, private data exposure, unknown capability, or unverified behavior claim.

## Notes

Core execution does not require network access or the source checkout. Use the bundled fallback behavior when live capabilities are blocked.
