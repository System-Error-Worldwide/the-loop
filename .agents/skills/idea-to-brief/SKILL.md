---
name: idea-to-brief
description: Convert raw requirement snippets into a compact, testable planning brief with falsifiable gates.
license: MIT
compatibility: Codex, Claude Code, Kimi Code and OpenCode
metadata:
  the-loop-capability: planning.brief
  the-loop-version: "0.1"
---

# Idea to Brief

Convert raw requirement snippets into a compact, testable planning brief with falsifiable gates.

## Use when

- Use for ambiguous requests or before build when success criteria are unclear.

## Inputs

- Active run, objective, track, and authority context.
- Declared track boundaries and budget controls.
- Typed evidence references and required file paths.

## Procedure

1. Normalize user intent into objective, scope, constraints, and acceptance criteria.
2. Extract assumptions and unknowns with explicit follow-up questions.
3. Produce a brief that is executable by spec-pack and test gates.
4. Attach falsifiable risks and explicit owner decisions.
5. Return one concise artifact with clear done conditions.

## Output contract

- Deterministic status, evidence hash list, and explicit status transitions.
- Typed halt reason with exact next-step obligations when blocked.

## Halt conditions

Stop with a precise error for missing authority, expired lease, namespace mismatch, unsafe proof, private data exposure, unknown capability, or unverified behavior claim.

## Notes

Core execution does not require network access or the source checkout. Use the bundled fallback behavior when live capabilities are blocked.
