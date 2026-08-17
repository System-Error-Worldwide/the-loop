---
name: the-loop-doctor
description: Inspect THE LOOP harness installation, skill discovery, collisions, permissions, configuration, and optional behavior evidence without changing local state. Use when a user asks whether the pack is installed, discoverable, compatible, shadowed, safe to run, or why a harness cannot find it.
license: MIT
compatibility: Codex, Claude Code, Kimi Code, OpenCode and DeepSeek Harness
metadata:
  the-loop-capability: setup.doctor
  the-loop-version: "0.1"
---

# THE LOOP Doctor

Produce a read-only compatibility report for Codex, Claude Code, Kimi Code, and OpenCode. Discovery and behavior are separate claims.

## Inputs

- Repository root containing `adapters/<harness>/adapter.json`: the installed `.the-loop/toolkit` or the public checkout.
- Project root to inspect.
- Optional user home plus explicit `CODEX_HOME` and `KIMI_CODE_HOME` overrides for user-level roots.
- Optional behavior-probe callback explicitly permitted by the caller. A verified result requires typed, matching harness/version/scope/capability/permission/environment evidence.

## Procedure

1. Validate every generic adapter manifest.
2. Check each harness executable and available version string independently.
3. Inspect adapter-declared project roots and, when supplied, user roots without following symlinked roots.
4. Validate portable `SKILL.md` frontmatter, the complete 12-package identity, every source, duplicate name, and winning precedence. Call the pack complete only when the winning package digests and complete offline-toolkit digest match one unchanged Setup receipt.
5. Report discovery as `verified`, `failed`, `denied`, or `unverified`. Keep `installed: false` separate.
6. Run no behavior probe unless a library caller supplied an approved probe. Accept `verified` only for the exact `portable-skill-invocation` capability with the complete typed contract and the Doctor-derived harness, adapter, pack, and runtime environment digest; keep missing or mismatched proof non-ready.
7. Inspect runtime version, config validity and permissions, state namespace safety, and kill-switch visibility without writing.

Core execution does not require network access or the source checkout. The CLI intentionally performs discovery only; live behavior probes belong to the separately approved conformance run.

From an installed project, use `.the-loop/toolkit/scripts/the_loop_doctor.py`. The canonical public source is [`scripts/the_loop_doctor.py`](https://github.com/System-Error-Worldwide/the-loop/blob/main/scripts/the_loop_doctor.py), and the [harness capability map](https://github.com/System-Error-Worldwide/the-loop/blob/main/protocols/harness-capability-map.md) defines status semantics.

## Evidence

- Overall status plus one report for each of the four harnesses.
- Roots inspected, receipt-bound complete-pack status and digest, missing skills, collisions, issues, discovery status, typed behavior evidence, environment digest, and check time.
- Read-only filesystem snapshot and deterministic performance tests.

## Halt conditions

Label missing and invalid adapters, absent harnesses, denied roots, invalid packages, collisions, failed probes, and unverified probes precisely. Do not repair, overwrite, install, elevate permissions, invoke an undocumented command, or treat discovery as behavior proof.

Doctor does not collect prompts, send telemetry, or change the inspected project.
