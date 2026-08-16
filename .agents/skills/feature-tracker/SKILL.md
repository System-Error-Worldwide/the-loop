---
name: feature-tracker
description: Track feature ownership, blockers, and done criteria as discrete records.
license: MIT
compatibility: Codex, Claude Code, Kimi Code and OpenCode
metadata:
  the-loop-capability: quality.feature-tracker
  the-loop-version: "0.1"
---

# Feature Tracker

Track feature ownership, blockers, and done criteria as discrete records.

## Use when

- Use when multiple tracks are running in parallel and evidence ownership must be visible.

## Inputs

- Active run, objective, track, and authority context.
- Declared track boundaries and budget controls.
- Typed evidence references and required file paths.

## Procedure

1. Create deterministic feature entries with owner, scope, and exit criteria.
2. Update each entry only through verified transitions.
3. Surface blockers and recovery obligations at every transition.
4. Provide machine-readable status for handoff and audit.
5. Avoid speculative claims without evidence references.

## Output contract

- Deterministic status, evidence hash list, and explicit status transitions.
- Typed halt reason with exact next-step obligations when blocked.

## Halt conditions

Stop with a precise error for missing authority, expired lease, namespace mismatch, unsafe proof, private data exposure, unknown capability, or unverified behavior claim.

## Notes

Core execution does not require network access or the source checkout. Use the bundled fallback behavior when live capabilities are blocked.
