---
name: audit
description: Compare declared contracts with observed artifacts or behavior, preserve coverage limits and feed evidence-backed drift into the lifecycle. Use for proactive drift, compliance, provenance, release-readiness or contract audits where findings must survive refutation.
license: MIT
compatibility: Codex, Claude Code, Kimi Code, OpenCode and DeepSeek Harness
metadata:
  the-loop-capability: feeder.audit
  the-loop-version: "0.1"
---

# Audit

## Purpose

Provide the complete bundled fallback for `feeder.audit`. Proactively find drift between declared contracts and observed artifacts or behavior without silently fixing the asset or claiming complete coverage from a sample.

## Use when

Use for a bounded compliance, consistency, provenance, security, quality or implementation-drift review with an enumerated population and acceptance contract.

## Required inputs

- Validated run ID or new-run request, declared asset, code or non-code track and audit objective.
- Declared contracts, requirement IDs, population boundary and coverage method.
- Observed artifact or environment access and known exclusions.
- Read authority plus any lease required for evidence and issue writes.
- Current issues, done gate, budgets and stop controls.

Reject a review that cannot define its population, sample or evidence standard.

## Procedure

1. Enumerate the class of items under review and partition included, excluded and unavailable members.
2. Map each declared contract to one or more observable checks.
3. Inspect the declared contracts and actual artifacts independently.
4. Label coverage complete, bounded, sampled or unverified before drawing conclusions.
5. Attempt to refute each discrepancy through reproduction and a second reading of its contract.
6. Record surviving drift with precise evidence, affected requirements, severity and reproduction.
7. Open or update issues without silently fixing them.
8. Return a bounded entry packet for Strategize, Test or Resolve; Audit does not advance the lifecycle or claim green.

## Output contract

Return:

- run ID, feeder `audit`, track and declared asset;
- audit objective, enumerated population and coverage classification;
- contract-to-check mapping;
- passed observations, surviving drift and evidence references;
- issue references, exclusions and unverified members;
- bounded entry packet, required authority, next safe action or halt.

## Evidence gate

Every finding must cite the exact contract and observed evidence. Exact counts require a complete enumeration and partition. A sampled audit cannot claim population-wide absence. Findings that fail self-refutation are removed from the report.

## Track requirements

For the code track, inspect repository state, executable behavior, security and relevant test evidence without modifying it. For the non-code track, inspect source support, calculations, factuality, format, rendered output and review evidence. Both tracks preserve unavailable checks as `UNVERIFIED`.

## Safety and authority

Audit is read-first and non-owning. It does not repair, publish, send or change an external system. Persisting evidence or issues requires runtime preflight and lease authority; any separate repair goes through Build or Resolve.

## Self-refutation

Try to reproduce every discrepancy, reread the exact contract and search for legitimate exceptions. Ask whether the coverage supports the claimed scope and discard findings that do not survive.

## Halt conditions

Halt on an unbounded population, missing contract, inaccessible required evidence, authority denial, namespace change, stop signal, privacy or security gate, or a conclusion that cannot be distinguished from sampling uncertainty. Report members skipped and why.

Core execution does not require network access or the source checkout. The links below are optional public documentation.

## References

- [Stage contracts](https://github.com/System-Error-Worldwide/the-loop/blob/main/protocols/stage-contracts.md)
- [Skill routing](https://github.com/System-Error-Worldwide/the-loop/blob/main/protocols/skill-routing.md)
- [Code and non-code tracks](https://github.com/System-Error-Worldwide/the-loop/blob/main/protocols/code-non-code-tracks.md)
- [Autonomy policy](https://github.com/System-Error-Worldwide/the-loop/blob/main/protocols/autonomy-policy.md)
- [Run state and leases](https://github.com/System-Error-Worldwide/the-loop/blob/main/protocols/run-state-leases.md)
- [Issue ledger](https://github.com/System-Error-Worldwide/the-loop/blob/main/protocols/issue-ledger.md)
- [Evidence contract](https://github.com/System-Error-Worldwide/the-loop/blob/main/protocols/evidence-contract.md)
