---
name: the-loop-doctor
description: Inspect THE LOOP harness installation, skill discovery, collisions, permissions, configuration, and optional behavior evidence without changing local state.
license: MIT
compatibility: Codex, Claude Code, Kimi Code and OpenCode
metadata:
  the-loop-capability: setup.doctor
  the-loop-version: "0.1"
---

# THE LOOP Doctor

Produce a read-only compatibility report for Codex, Claude Code, Kimi Code, and OpenCode. Discovery and behavior are separate claims.

## Inputs

- Public repository root containing `adapters/<harness>/adapter.json`.
- Project root to inspect.
- Optional user home for user-level roots.
- Optional behavior-probe callback explicitly permitted by the caller.

## Procedure

1. Validate every generic adapter manifest.
2. Check each harness executable and available version string independently.
3. Inspect adapter-declared project roots and, when supplied, user roots without following symlinked roots.
4. Validate portable `SKILL.md` frontmatter and report every source, duplicate name, and winning precedence.
5. Report discovery as `verified`, `failed`, `denied`, or `unverified`. Keep `installed: false` separate.
6. Run no behavior probe unless the caller supplied an approved probe. Preserve `verified`, `failed`, `denied`, and `unverified` exactly.
7. Inspect runtime version, config validity and permissions, state namespace safety, and kill-switch visibility without writing.

Use [`scripts/the_loop_doctor.py`](../../../scripts/the_loop_doctor.py) for the CLI and the [harness capability map](../../../protocols/harness-capability-map.md) for status semantics.

## Evidence

- Overall status plus one report for each of the four harnesses.
- Roots inspected, skills, collisions, issues, discovery status, behavior status, and check time.
- Read-only filesystem snapshot and deterministic performance tests.

## Halt conditions

Label missing and invalid adapters, absent harnesses, denied roots, invalid packages, collisions, failed probes, and unverified probes precisely. Do not repair, overwrite, install, elevate permissions, invoke an undocumented command, or treat discovery as behavior proof.

Doctor does not collect prompts, send telemetry, or change the inspected project.
