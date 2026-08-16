---
name: the-loop-skill-creator
description: Construct or compose portable run-specific skill tasks and maintain explicit self-modification boundaries.
license: MIT
compatibility: Codex, Claude Code, Kimi Code and OpenCode
metadata:
  the-loop-capability: skill-planning.creator
  the-loop-version: "0.1"
---

# The Loop Skill Creator

Construct or compose portable run-specific skill tasks and maintain explicit self-modification boundaries.

## Use when

- Use when a workflow requires generating new internal skill invocation plans from existing primitives.

## Inputs

- Active run, objective, track, and authority context.
- Declared track boundaries and budget controls.
- Typed evidence references and required file paths.

## Procedure

1. Generate candidate task objects from proven routing, evidence, and capability constraints.
2. Never modify existing pack code directly; output manifests and approvals only.
3. Attach provenance, source, and safety metadata to each generated item.
4. Preserve a refusal path for unsupported capabilities and conflicting evidence.
5. Return exact created artifact hashes and execution boundaries.

## Output contract

- Deterministic status, evidence hash list, and explicit status transitions.
- Typed halt reason with exact next-step obligations when blocked.

## Halt conditions

Stop with a precise error for missing authority, expired lease, namespace mismatch, unsafe proof, private data exposure, unknown capability, or unverified behavior claim.

## Notes

Core execution does not require network access or the source checkout. Use the bundled fallback behavior when live capabilities are blocked.
