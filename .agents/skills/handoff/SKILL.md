---
name: handoff
description: Produce a safe session boundary with current state, evidence, and next actions.
license: MIT
compatibility: Codex, Claude Code, Kimi Code, OpenCode and DeepSeek Harness
metadata:
  the-loop-capability: quality.handoff
  the-loop-version: "0.1"
---

# Handoff

Produce a safe session boundary with current state, evidence, and next actions.

## Use when

- Use at natural stage transitions and when switching owners.

## Inputs

- Active run, objective, track, and authority context.
- Declared track boundaries and budget controls.
- Typed evidence references and required file paths.

## Procedure

1. Capture active run, open risks, completed evidence, and unresolved risks.
2. Serialize required context for deterministic continuation.
3. Validate references and omit sensitive paths or secrets.
4. Mark stale assumptions and owner questions explicitly.
5. Seal with exact completion timestamp and outcome status.

## Output contract

- Deterministic status, evidence hash list, and explicit status transitions.
- Typed halt reason with exact next-step obligations when blocked.

## Halt conditions

Stop with a precise error for missing authority, expired lease, namespace mismatch, unsafe proof, private data exposure, unknown capability, or unverified behavior claim.

## Notes

Core execution does not require network access or the source checkout. Use the bundled fallback behavior when live capabilities are blocked.
