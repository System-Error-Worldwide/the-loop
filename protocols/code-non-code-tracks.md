# Code and non-code tracks

## Purpose

This protocol defines track-specific work controls while preserving one lifecycle, state, authority, evidence, and issue model. It implements [PRD FR-050 through FR-053](../docs/specs/prd.md#code-and-non-code-work) and the [TDD track contracts](../docs/specs/tdd.md#track-contracts).

RFC 2119 terms are normative only in numbered requirements. Each normative requirement has one stable `TRK` identifier.

## Normative requirements

## Track selection

- **[TRK-001]** A run MUST declare `code` or `noncode` before stage dispatch and MUST retain that immutable asset track for the bounded mission. A corrected track requires a new run; recovery MUST NOT rewrite the existing run's asset declaration.
- **[TRK-002]** Track selection MUST follow the primary artifact and verification method: executable repository behavior is code; research, prose, plans, operating documents, and designed deliverables without executable product behavior are non-code.
- **[TRK-003]** A mixed asset MUST declare one primary track and list secondary obligations from the other track in its done gate.
- **[TRK-004]** Both tracks MUST use the common stage envelope, authority grant, run ownership, lease, route, evidence, issue, halt, and close contracts.
- **[TRK-005]** A track MUST NOT be changed to evade a stronger evidence, isolation, factuality, or authority requirement.

## Shared work contract

- **[TRK-010]** Every track MUST define the output format, acceptance conditions, source inputs, mutation boundary, review method, and outward-action boundary before Build.
- **[TRK-011]** Every track MUST preserve unrelated work and MUST identify pre-existing changes that overlap the declared boundary.
- **[TRK-012]** Every track MUST record evidence conforming to [`evidence.schema.json`](../schemas/evidence.schema.json) and defects conforming to [`issue-ledger.schema.json`](../schemas/issue-ledger.schema.json).
- **[TRK-013]** Every track MUST label unsupported, inaccessible, uncertain, and untested claims truthfully.
- **[TRK-014]** Sending, publishing, deploying, purchasing, changing an external system, or communicating as the user MUST be treated as an outward action under [AUT-031](autonomy-policy.md#action-boundary).
- **[TRK-015]** If no installed provider satisfies the track contract, the stage MUST use the track-capable bundled fallback under [RTE-050](skill-routing.md#fallback).

## Code track

- **[TRK-100]** Before unattended code mutation, the worker MUST establish repository identity, branch or equivalent isolation, declared write paths, current worktree state, and relevant live-state coverage or explicitly record what could not be observed.
- **[TRK-101]** The code worker MUST preserve unrelated changes and MUST NOT reset, overwrite, stage, or include them in its claimed result.
- **[TRK-102]** Build MUST map each code change to an approved slice and requirement ID and MUST avoid unrelated refactors.
- **[TRK-103]** Test MUST execute the smallest complete set of build, static, unit, integration, security, and behavior checks justified by the changed surface; omitted applicable checks MUST be unverified.
- **[TRK-104]** A code pass MUST include reproducible commands, exit status, relevant environment facts, and artifact or output references.
- **[TRK-105]** A code failure MUST include a minimal reproduction, expected and observed behavior, affected requirement IDs, severity, and regression procedure.
- **[TRK-106]** Merge, push, release, deployment, dependency publication, and external configuration mutation MUST remain behind explicit outward authority.
- **[TRK-107]** Destructive repository operations MUST halt unless the exact target and recovery path are confirmed by authority.
- **[TRK-108]** Code-track fallback MUST be able to inspect, edit, test, resolve, and hand off locally without an optional third-party provider.

## Non-code track

- **[TRK-200]** Before drafting, the worker MUST define audience, purpose, format, factuality standard, source quality threshold, review method, and completion evidence.
- **[TRK-201]** Factual claims MUST be supported by supplied material, authoritative sources, reproducible calculations, or an explicit uncertainty marker.
- **[TRK-202]** The worker MUST NOT invent names, roles, dates, measurements, quotations, credentials, approvals, or outcomes to fill a source gap.
- **[TRK-203]** Research evidence MUST identify source, access date when relevant, and the claim it supports; inaccessible sources MUST NOT be cited as verified.
- **[TRK-204]** Calculation evidence MUST include inputs, method, units, assumptions, and a reproducible result.
- **[TRK-205]** Visual or formatted deliverables MUST be verified in the rendered output at relevant sizes; source markup or a static screenshot alone MUST NOT prove interaction or accessibility.
- **[TRK-206]** Review MUST test factuality, completeness, internal consistency, requested format, audience fit, and any domain-specific legal, privacy, accessibility, or brand gate.
- **[TRK-207]** A non-code pass MUST reference the final artifact, requirement coverage, review evidence, and unresolved verification gaps.
- **[TRK-208]** Publishing, submitting, sending, sharing, or editing an external record MUST remain behind explicit outward authority.
- **[TRK-209]** Non-code fallback MUST be able to draft, self-review, record evidence, open issues, and hand off without an optional third-party provider.

## Track handoff

- **[TRK-300]** A handoff MUST state the selected track, completed artifacts, source or repository state, evidence outcomes, open issues, unexecuted checks, and the next safe action.
- **[TRK-301]** A handoff between tracks MUST preserve common requirement, evidence, issue, authority, and run identifiers.
- **[TRK-302]** A downstream worker MUST revalidate track-specific assumptions when its environment or artifact representation differs from the producer's.

## Failure and halt behavior

- **[TRK-310]** A track MUST halt when required source or repository state, output format, authority, isolation, or verification method cannot be established.
- **[TRK-311]** A code-track halt MUST identify repository state, last safe change, test state, and recovery command or decision.
- **[TRK-312]** A non-code halt MUST identify unsupported claims, unavailable sources, incomplete sections, review gaps, and the input or decision needed to continue.
- **[TRK-313]** A mixed-track conflict MUST choose the stricter applicable authority and evidence rule or halt for clarification.

## Evidence

- **[TRK-320]** Track evidence MUST map each acceptance requirement to a procedure, outcome, actor, observation time, environment, and artifact reference.
- **[TRK-321]** Code evidence MUST preserve command and behavior reproducibility; non-code evidence MUST preserve source, factuality, calculation, render, or review reproducibility as applicable.
- **[TRK-322]** Evidence coverage MUST state whether it is complete, bounded, sampled, or unverified.

## Cross-references

| Protocol range | Source contract |
| --- | --- |
| TRK-001–015 | [PRD FR-050–053](../docs/specs/prd.md#code-and-non-code-work), [Run asset track](../docs/specs/backend-schema.md#run-record) |
| TRK-100–108 | [TDD: Code track](../docs/specs/tdd.md#code) |
| TRK-200–209 | [TDD: Non-code track](../docs/specs/tdd.md#non-code) |
| TRK-300–302 | [PRD FR-026](../docs/specs/prd.md#lifecycle), [App flow: Resume](../docs/specs/app-flow.md#resume) |
