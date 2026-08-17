---
name: decision-log
description: Persist high-value architecture and scope decisions with rationale.
license: MIT
compatibility: Codex, Claude Code, Kimi Code, OpenCode and DeepSeek Harness
metadata:
  the-loop-capability: quality.decision-log
  the-loop-version: "0.1"
---

# Decision Log

Persist high-value architecture and scope decisions with rationale.

## Use when

- Use when choosing between alternatives or accepting risky assumptions.

## Inputs

- Active run, objective, track, and authority context.
- Declared track boundaries and budget controls.
- Typed evidence references and required file paths.

## Procedure

1. Record decision statement, alternatives, rationale, owner, and timestamp.
2. Link each decision to affected skills, gates, and files.
3. Treat evidence links as required fields.
4. Preserve decisions as immutable records with explicit supersession path.
5. Include reversal conditions and review cadence.

## Output contract

- Deterministic status, evidence hash list, and explicit status transitions.
- Typed halt reason with exact next-step obligations when blocked.

## Halt conditions

Stop with a precise error for missing authority, expired lease, namespace mismatch, unsafe proof, private data exposure, unknown capability, or unverified behavior claim.

## Notes

Core execution does not require network access or the source checkout. Use the bundled fallback behavior when live capabilities are blocked.
