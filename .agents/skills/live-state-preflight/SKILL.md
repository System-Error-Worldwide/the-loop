---
name: live-state-preflight
description: Validate run-ready namespace, namespace ownership, and namespace-safe defaults before execution.
license: MIT
compatibility: Codex, Claude Code, Kimi Code and OpenCode
metadata:
  the-loop-capability: state.preflight
  the-loop-version: "0.1"
---

# Live State Preflight

Validate run-ready namespace, namespace ownership, and namespace-safe defaults before execution.

## Use when

- Use at session start or before critical state mutation.

## Inputs

- Active run, objective, track, and authority context.
- Declared track boundaries and budget controls.
- Typed evidence references and required file paths.

## Procedure

1. Collect provider namespace, roots, and state ownership with identity checks.
2. Reject private-path, symlink, or unknown namespace states before run entry.
3. Seed minimal safe defaults and report exact preflight state diff.
4. Refuse to continue when preflight invariants fail; return precise next action.
5. Persist preflight report to support deterministic replay and diagnosis.

## Output contract

- Deterministic status, evidence hash list, and explicit status transitions.
- Typed halt reason with exact next-step obligations when blocked.

## Halt conditions

Stop with a precise error for missing authority, expired lease, namespace mismatch, unsafe proof, private data exposure, unknown capability, or unverified behavior claim.

## Notes

Core execution does not require network access or the source checkout. Use the bundled fallback behavior when live capabilities are blocked.
