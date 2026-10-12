---
name: spec-pack
description: Produce mutually consistent implementation-ready specifications and map every requirement to a build slice and verification gate. Use for a new app, website or major feature that needs PRD, technical design, flow, design brief, backend schema and engineering plan before code.
license: MIT
compatibility: Codex, Claude Code, Kimi Code, OpenCode and DeepSeek Harness
metadata:
  the-loop-capability: lifecycle.spec_pack
  the-loop-version: "0.1"
---

# Spec pack

## Purpose

Provide the complete bundled fallback for `lifecycle.spec_pack`. Establish the contract an implementer and independent tester will follow before gated implementation.

## Use when

Classify by risk before size:

- S0: bug, copy/config, single-file, mechanical, disposable POC or non-code deliverable inside existing boundaries. Record an exemption and reason; no pack is needed.
- S1: contained feature inside existing data/access/subsystem boundaries. One brief; UI on existing APIs also needs concrete visual direction and a rendered acceptance check.
- S2: new app/site, data-model, access or security boundary change, new surface plus backend, or multi-subsystem feature. Capability ledger first, then six documents. S2 risk overrides a size exemption; UI alone does not force S2.

Unresolved material or strategic decisions halt; they do not become safe defaults.

## Required inputs

- Validated run ID, declared asset, track, approved strategy and current stage.
- Problem, users, scope, constraints, risks, success measures and done gate.
- Known architecture, data, workflow, design and release context.
- Frozen budgets, current authority, owner and matching lease for any writes.
- Current evidence, issue state and recorded human decisions.

Reject missing or contradictory inputs rather than choosing an architecture by implication.

## Procedure

1. Record spec depth S0, S1 or S2 and the classification reason.
2. For S0, persist the recorded exemption and complete Spec pack with no pack documents unless Strategize is incomplete; do not halt authorized benign Build.
3. For S1, produce one implementation brief with requirements, touched surfaces, checks, risks, rollback, assumptions, slices and a small capability disposition table; include concrete visual direction and a rendered acceptance check when UI is in scope.
4. For S2, produce a capability ledger dispositioning every in-scope capability as in, out, later or blocked with owner and gate for blocked and no silent omissions, then the six documents: PRD, TDD, app flow, design brief, backend schema and engineering plan.
5. Give every functional and non-functional requirement a stable identifier and testable outcome.
6. Specify happy paths, failure paths, denial, interruption, recovery, unsupported and terminal states.
7. Define data shape, authority, privacy, security, migration and rollback behavior.
8. Separate structure and operational behavior from surface treatment where a user-facing output exists.
9. Map every requirement-to-slice relationship and name the exact done gate and evidence method for each slice.
10. Cross-check terminology, enums, scope, dependencies and deferred work across all documents.
11. Record unresolved decisions that materially alter the product as human gates; do not replace them with assumptions.

## Output contract

Return:

- run ID, stage `spec_pack`, track and declared asset;
- required document inventory and paths;
- requirements, assumptions and decision ledger;
- architecture, state, workflow, design and release contracts;
- implementation slices with dependencies, owners, done gates and rollback;
- requirement-to-slice and requirement-to-verification mapping;
- evidence references, issues, gate state and next stage or halt.

## Evidence gate

For S0, pass when the persisted exemption is recorded and Strategize is complete; no pack documents are required. For S1 and S2, pass only when the required documents exist, are mutually consistent and implementation-ready; every requirement maps to a slice and verification method; local references resolve; and no unresolved decision can change architecture, data, public behavior, authority or release risk. Evidence must be persisted before Build.

## Track requirements

For the code track, specify repository boundaries, executable behavior, security checks, migrations and technical rollback. For the non-code track, specify sources, factuality, format, calculation or render checks, review method and outward publication gate.

## Safety and authority

Specification is not authority to implement, publish, deploy or contact an external system. Writes stay inside the declared specification paths and use the active lease. Private data, credential-shaped values and unsupported compatibility claims stay out of public artifacts.

## Self-refutation

Ask whether two competent implementers could build materially different but specification-compliant products. If yes, identify and close the ambiguous requirement or halt for the missing decision.

## Halt conditions

Halt for a material unresolved decision, missing source of truth, conflicting requirement, unbounded scope, absent verification method, lost ownership, namespace change, expired authority, exhausted budget or detected stop. Name incomplete documents and the exact input needed.

Core execution does not require network access or the source checkout. The links below are optional public documentation.

## References

- [Stage contracts](https://github.com/System-Error-Worldwide/the-loop/blob/main/protocols/stage-contracts.md)
- [Skill routing](https://github.com/System-Error-Worldwide/the-loop/blob/main/protocols/skill-routing.md)
- [Code and non-code tracks](https://github.com/System-Error-Worldwide/the-loop/blob/main/protocols/code-non-code-tracks.md)
- [Autonomy policy](https://github.com/System-Error-Worldwide/the-loop/blob/main/protocols/autonomy-policy.md)
- [Run state and leases](https://github.com/System-Error-Worldwide/the-loop/blob/main/protocols/run-state-leases.md)
- [Issue ledger](https://github.com/System-Error-Worldwide/the-loop/blob/main/protocols/issue-ledger.md)
- [Evidence contract](https://github.com/System-Error-Worldwide/the-loop/blob/main/protocols/evidence-contract.md)
