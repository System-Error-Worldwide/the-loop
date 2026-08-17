---
name: pre-commit-review
description: Static check gate before risky write operations.
license: MIT
compatibility: Codex, Claude Code, Kimi Code, OpenCode and DeepSeek Harness
metadata:
  the-loop-capability: quality.pre-commit-review
  the-loop-version: "0.1"
---

# Pre-Commit Review

Static check gate before risky write operations.

## Use when

- Use before committing or applying multi-file write batches.

## Inputs

- Active run, objective, track, and authority context.
- Declared track boundaries and budget controls.
- Typed evidence references and required file paths.

## Procedure

1. Validate changed files against project-owned schema and boundary checks.
2. Fail closed on missing allowlist, drift, private secret, or unverified dependency changes.
3. Emit explicit required fixes before write acceptance.
4. Allow no write when evidence is incomplete.
5. Return audit-style report with precise remediation paths.

## Output contract

- Deterministic status, evidence hash list, and explicit status transitions.
- Typed halt reason with exact next-step obligations when blocked.

## Halt conditions

Stop with a precise error for missing authority, expired lease, namespace mismatch, unsafe proof, private data exposure, unknown capability, or unverified behavior claim.

## Notes

Core execution does not require network access or the source checkout. Use the bundled fallback behavior when live capabilities are blocked.
