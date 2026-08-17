---
name: the-loop-watch
description: Read-only visibility lane for shared signals, state, and issue visibility without taking locks or leases.
license: MIT
compatibility: Codex, Claude Code, Kimi Code, OpenCode and DeepSeek Harness
metadata:
  the-loop-capability: watch.runtime
  the-loop-version: "0.1"
---

# The Loop Watch

Read-only visibility lane for shared signals, state, and issue visibility without taking locks or leases.

## Use when

- Use when monitoring is needed without changing run state or writing artifacts.

## Inputs

- Active run, objective, track, and authority context.
- Declared track boundaries and budget controls.
- Typed evidence references and required file paths.

## Procedure

1. Open project/project-root and state paths in bounded read-only mode only.
2. Collect canonical signals (status, lease window, issue surface, external kill visibility).
3. Never repair, mutate, acquire, heartbeat, or authorize; report only evidence and limits.
4. Return explicit blocked reasons for missing namespace identity or unreadable state.
5. Emit a compact snapshot with timestamp and confidence.

## Output contract

- Deterministic status, evidence hash list, and explicit status transitions.
- Typed halt reason with exact next-step obligations when blocked.

## Halt conditions

Stop with a precise error for missing authority, expired lease, namespace mismatch, unsafe proof, private data exposure, unknown capability, or unverified behavior claim.

## Notes

Core execution does not require network access or the source checkout. Use the bundled fallback behavior when live capabilities are blocked.
