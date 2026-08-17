---
name: portfolio-review
description: Run generic portfolio snapshot checks without private portfolio intelligence or external sources.
license: MIT
compatibility: Codex, Claude Code, Kimi Code, OpenCode and DeepSeek Harness
metadata:
  the-loop-capability: memory.review
  the-loop-version: "0.1"
---

# Portfolio Review

Run generic portfolio snapshot checks without private portfolio intelligence or external sources.

## Use when

- Use when a cross-project view is needed for context framing, and no private identity data is present.

## Inputs

- Active run, objective, track, and authority context.
- Declared track boundaries and budget controls.
- Typed evidence references and required file paths.

## Procedure

1. Read only generic project indicators from local allowed sources.
2. Compute non-sensitive summary metrics with bounded scope and explicit caveats.
3. Do not pull private financial, identity, or account-level sources.
4. Require explicit consent for any external fetch or storage write.
5. Output a dry report that is safe to attach to a handoff record.

## Output contract

- Deterministic status, evidence hash list, and explicit status transitions.
- Typed halt reason with exact next-step obligations when blocked.

## Halt conditions

Stop with a precise error for missing authority, expired lease, namespace mismatch, unsafe proof, private data exposure, unknown capability, or unverified behavior claim.

## Notes

Core execution does not require network access or the source checkout. Use the bundled fallback behavior when live capabilities are blocked.
