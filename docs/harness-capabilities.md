# Harness capabilities (Codex and Claude Code)

This document describes capability adapter rules for the `codex` and `claude_code` harness identifiers. Status remains unverified without current environment-scoped probes; nothing here replaces adapter JSON or doctor output.

## Lookup scope

Capability lookup is host-scoped for the active harness profile. Do not preload or inventory every adapter on every stage invocation.

## Shared adapter rules

- Routing uses an injected capability catalog when present, otherwise scoped discovery and qualified fallback. Requested skills and domain prerequisites require full `SKILL.md` reads and current route qualification and authority.
- Cache supplemental discovery per profile and environment until installation, profile or environment changes.
- Test MUST record distinct builder and evaluator invocation identities regardless of provider; evaluator context stays independent of builder conclusions.

External-first route records and guard caps stay authoritative. Native collaboration topology does not replace a recorded route.

## Codex

The live desktop or CLI session runtime is authoritative over stale configuration.

Optional native collaboration or Workflow transport MAY be used only when the capability is observed, the brief scope is explicit and transport is verified. An unreadable or empty payload is failure, not success. Do not switch providers or repin to bypass denied transport; use a qualified guarded process or serial fallback.

## Claude Code

Optional scoped subagents MAY be used only when observed, each with disjoint owned paths and an isolated mutating worktree.

External-first routes are unchanged. Native subagent topology does not replace a recorded route decision.

## Offline references

Normative stage, lease, issue and routing contracts live in the installed toolkit protocols, including [harness capability map](../protocols/harness-capability-map.md), [run state and leases](../protocols/run-state-leases.md) and [issue ledger](../protocols/issue-ledger.md).
