---
name: the-loop-skill-planner
description: Propose safe, capability-scoped candidate sets and rank them for the next approved skill action.
license: MIT
compatibility: Codex, Claude Code, Kimi Code, OpenCode and DeepSeek Harness
metadata:
  the-loop-capability: skill-planning.router
  the-loop-version: "0.1"
---

# The Loop Skill Planner

Propose safe, capability-scoped candidate sets and rank them for the next approved skill action.

## Use when

- Use when a run requires selection decisions without immediate mutation.

## Inputs

- Active run, objective, track, and authority context.
- Declared track boundaries and budget controls.
- Typed evidence references and required file paths.

## Procedure

1. Collect candidate set and constraints: capability, track, environment, budget, and required evidence.
2. Score candidates using deterministic, documented policy plus deterministic tie-break rules.
3. Reject candidates with stale evidence, policy mismatch, or missing provenance.
4. Emit ranked, typed decision records and a deterministic fallback route.
5. Expose full ranking context for transparent review and audit.

## Output contract

- Deterministic status, evidence hash list, and explicit status transitions.
- Typed halt reason with exact next-step obligations when blocked.

## Halt conditions

Stop with a precise error for missing authority, expired lease, namespace mismatch, unsafe proof, private data exposure, unknown capability, or unverified behavior claim.

## Notes

Core execution does not require network access or the source checkout. Use the bundled fallback behavior when live capabilities are blocked.
