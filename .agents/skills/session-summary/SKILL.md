---
name: session-summary
description: Capture concise outcomes from an execution window for the next continuation.
license: MIT
compatibility: Codex, Claude Code, Kimi Code and OpenCode
metadata:
  the-loop-capability: quality.session-summary
  the-loop-version: "0.1"
---

# Session Summary

Capture concise outcomes from an execution window for the next continuation.

## Use when

- Use when session scope ends or before asynchronous handoff.

## Inputs

- Active run, objective, track, and authority context.
- Declared track boundaries and budget controls.
- Typed evidence references and required file paths.

## Procedure

1. Summarize achieved gates, outstanding blockers, and exact artifacts produced.
2. Report assumptions and open risks that affect next slice.
3. Include exact tests run and next evidence obligations.
4. Keep scope bounded to the executed session only.
5. Produce one compact output compatible with handoff tooling.

## Output contract

- Deterministic status, evidence hash list, and explicit status transitions.
- Typed halt reason with exact next-step obligations when blocked.

## Halt conditions

Stop with a precise error for missing authority, expired lease, namespace mismatch, unsafe proof, private data exposure, unknown capability, or unverified behavior claim.

## Notes

Core execution does not require network access or the source checkout. Use the bundled fallback behavior when live capabilities are blocked.
