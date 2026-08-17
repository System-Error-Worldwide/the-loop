---
name: retrospective
description: Review what worked, what blocked progress, and what must change next.
license: MIT
compatibility: Codex, Claude Code, Kimi Code, OpenCode and DeepSeek Harness
metadata:
  the-loop-capability: quality.retrospective
  the-loop-version: "0.1"
---

# Retrospective

Review what worked, what blocked progress, and what must change next.

## Use when

- Use after bounded slices complete or when recurrent failures recur.

## Inputs

- Active run, objective, track, and authority context.
- Declared track boundaries and budget controls.
- Typed evidence references and required file paths.

## Procedure

1. Collect completed evidence, failures, and recurring anti-patterns.
2. Assign likely root causes and confidence levels.
3. Create concise follow-up actions with owners and evidence requirements.
4. Persist learnings in approved non-sensitive format.
5. Avoid inventing conclusions not supported by logs.

## Output contract

- Deterministic status, evidence hash list, and explicit status transitions.
- Typed halt reason with exact next-step obligations when blocked.

## Halt conditions

Stop with a precise error for missing authority, expired lease, namespace mismatch, unsafe proof, private data exposure, unknown capability, or unverified behavior claim.

## Notes

Core execution does not require network access or the source checkout. Use the bundled fallback behavior when live capabilities are blocked.
