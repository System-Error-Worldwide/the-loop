---
name: stack-summary
description: Produce a compact digest of active run, architecture, and support stack state.
license: MIT
compatibility: Codex, Claude Code, Kimi Code and OpenCode
metadata:
  the-loop-capability: memory.summary
  the-loop-version: "0.1"
---

# Stack Summary

Produce a compact digest of active run, architecture, and support stack state.

## Use when

- Use for handoff and periodic reflection when state complexity is increasing.

## Inputs

- Active run, objective, track, and authority context.
- Declared track boundaries and budget controls.
- Typed evidence references and required file paths.

## Procedure

1. Collect stack-level status, gates, blockers, and recent decisions.
2. Generate a compact summary with links to evidence artifacts and next action.
3. Avoid sensitive file paths, credentials, and private identifiers.
4. Emit one snapshot suitable for memory handoff and triage.
5. Keep summaries deterministic and stable by ordering inputs.

## Output contract

- Deterministic status, evidence hash list, and explicit status transitions.
- Typed halt reason with exact next-step obligations when blocked.

## Halt conditions

Stop with a precise error for missing authority, expired lease, namespace mismatch, unsafe proof, private data exposure, unknown capability, or unverified behavior claim.

## Notes

Core execution does not require network access or the source checkout. Use the bundled fallback behavior when live capabilities are blocked.
