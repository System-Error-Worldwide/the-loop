---
name: the-loop-autonomy
description: Bounded authority lifecycle for grants, expiries, kill switch, and permission boundaries.
license: MIT
compatibility: Codex, Claude Code, Kimi Code and OpenCode
metadata:
  the-loop-capability: autonomy.control
  the-loop-version: "0.1"
---

# The Loop Autonomy

Bounded authority lifecycle for grants, expiries, kill switch, and permission boundaries.

## Use when

- Use when run authority must be explicitly checked before every action, authority windows need to be enforced, and recovery must remain faithful when grants are revoked or expired.

## Inputs

- Active run, objective, track, and authority context.
- Declared track boundaries and budget controls.
- Typed evidence references and required file paths.

## Procedure

1. Validate active lease, owner, grant, authority evidence, and stop conditions before mutation.
2. Classify authority states into active/expired/revoked and compute the permitted next action matrix.
3. Attach explicit rationale for every fallback to manual recovery, approval, or wait states.
4. Emit one recoverable/one blocked handoff artifact that prevents ambiguous privilege continuation.
5. Seal outcomes with deterministic evidence and status transitions, never inventing authority.

## Output contract

- Deterministic status, evidence hash list, and explicit status transitions.
- Typed halt reason with exact next-step obligations when blocked.

## Halt conditions

Stop with a precise error for missing authority, expired lease, namespace mismatch, unsafe proof, private data exposure, unknown capability, or unverified behavior claim.

## Notes

Core execution does not require network access or the source checkout. Use the bundled fallback behavior when live capabilities are blocked.
