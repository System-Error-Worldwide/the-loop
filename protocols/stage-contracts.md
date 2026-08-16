# Stage contracts

## Purpose

This protocol defines the harness-neutral contract for lifecycle stages and feeders. It implements [PRD FR-010 and FR-020 through FR-026](../docs/specs/prd.md#lifecycle), the [attended and bounded Auto journeys](../docs/specs/app-flow.md#attended-loop-journey), and the state model in the [backend schema](../docs/specs/backend-schema.md#run-record).

RFC 2119 terms are normative only in numbered requirements. Each normative requirement has one stable `STG` identifier.

## Normative requirements

## Common stage envelope

- **[STG-001]** A stage invocation MUST receive a run identifier, declared asset boundary, track, objective, current stage, done gate, active authority reference, frozen budgets, current issue summary, available evidence references, and requested capability.
- **[STG-002]** A stage MUST reject an invocation whose run, owner, lease, authority, stage, or asset boundary cannot be established from validated state; the rejection MUST name the missing or conflicting field.
- **[STG-003]** A stage MUST declare its required inputs, output shape, evidence gate, self-refutation question, halt conditions, and bundled fallback capability before work begins.
- **[STG-004]** A stage output MUST identify the run, stage, track, produced or changed artifacts, evidence references, issue references, resulting gate state, and recommended next stage or halt reason.
- **[STG-005]** A stage MUST preserve unrelated user work and MUST restrict mutations to its declared asset and slice boundary.
- **[STG-006]** A stage MUST obtain its provider through [skill routing](skill-routing.md#route-decision) and MUST validate the provider result against this protocol regardless of provider source.
- **[STG-007]** A stage MUST record failed, denied, blocked, inaccessible, and unverified checks as those exact outcomes; it MUST NOT convert any of them to passed.
- **[STG-008]** A stage MUST create or update issue-ledger entries for every surviving blocking defect and MUST link relevant evidence and requirement identifiers.
- **[STG-009]** A state-changing stage action MUST pass the runtime preflight defined by [AUT-030](autonomy-policy.md#action-boundary) and the authoritative state rules in the [backend schema](../docs/specs/backend-schema.md#audit-event).
- **[STG-010]** A side-effecting callback MUST use the durable intent and exact completion contract defined by `FR-037` and `FR-038` in the [PRD](../docs/specs/prd.md#state-ownership-and-recovery); an unknown pending operation MUST NOT be replayed.
- **[STG-011]** A stage MUST halt when its done gate requires evidence that the active environment cannot produce; it MAY hand off with an explicit unverified outcome and reproduction procedure.
- **[STG-012]** A stage MUST use its bundled fallback when no installed provider qualifies, as required by [RTE-031](skill-routing.md#fallback).
- **[STG-013]** A provider failure MUST be recorded before rerouting; a stage MUST NOT silently substitute another provider.
- **[STG-014]** A stage transition MUST be written only after the current stage output satisfies its contract or records a truthful halt.

## Lifecycle ordering

- **[STG-020]** The default lifecycle SHALL be `strategize -> spec_pack -> build -> test -> close`, with `test -> resolve -> test` repeated only while the issue and retry gates allow it.
- **[STG-021]** `spec_pack` MAY be skipped only when the asset is outside the spec gate or a recorded human override explicitly permits the skip.
- **[STG-022]** `build` MUST consume one approved slice; it MUST NOT expand the accepted scope without a new strategy or approval gate.
- **[STG-023]** `test` MUST be independent of the implementation claim and MUST attempt to falsify every required acceptance condition.
- **[STG-024]** `resolve` MUST operate from owned issue records and MUST return each addressed issue to independent verification.
- **[STG-025]** `close` MUST refuse a complete result while required evidence is not passed or any blocking issue has a status other than `closed`.
- **[STG-026]** Attended mode MUST surface meaningful stage gates to the user; bounded Auto MAY cross only gates already covered by visible authority and frozen mission scope.

## Stage definitions

### Strategize

- **[STG-100]** Strategize MUST take the stated intent and known constraints as primary inputs and MUST output a bounded problem statement, desired outcome, in-scope and out-of-scope boundaries, assumptions, risks, success measures, and a testable done gate.
- **[STG-101]** Strategize evidence MUST show that each material assumption is confirmed, safely defaulted with a reversal condition, or raised as a human gate.
- **[STG-102]** Strategize MUST halt on a strategic fork whose alternatives materially change the asset, authority, cost, legal exposure, or success definition.
- **[STG-103]** Strategize self-refutation MUST ask whether the proposed work solves the stated problem with the smallest sufficient scope.

### Spec pack

- **[STG-110]** Spec pack MUST determine the required document set from asset type and change scope and MUST output mutually consistent, implementation-ready specifications before gated implementation.
- **[STG-111]** For a new application, website, or major feature, Spec pack MUST produce the six documents named by [PRD FR-021](../docs/specs/prd.md#lifecycle) and the [engineering plan spec gate](../docs/specs/engineering-plan.md#phase-1-specification-and-architecture).
- **[STG-112]** Spec-pack evidence MUST map every functional and non-functional requirement to an implementation slice and verification method.
- **[STG-113]** Spec pack MUST halt on an unresolved decision that would materially change architecture, data, public behavior, authority, or release risk.
- **[STG-114]** Spec-pack self-refutation MUST ask whether an implementer could build a conflicting but specification-compliant product.

### Build

- **[STG-120]** Build MUST take one approved engineering slice or non-code drafting unit and MUST output only the artifacts and contract changes required by that unit.
- **[STG-121]** Build MUST follow the selected track contract in [code and non-code tracks](code-non-code-tracks.md#track-selection).
- **[STG-122]** Build evidence MUST identify changed artifacts, the requirement IDs they implement, and the smallest relevant checks completed before Test.
- **[STG-123]** Build MUST halt on missing gated specifications, lost ownership, a changed namespace, scope expansion, or required authority that is absent or expired.
- **[STG-124]** Build self-refutation MUST ask whether each change is necessary for the declared slice and whether it damages unrelated behavior.

### Test

- **[STG-130]** Test MUST derive checks from the done gate, requirement IDs, changed behavior, failure paths, and applicable track contract.
- **[STG-131]** Test MUST output reproducible evidence records and issue-ledger entries for every surviving defect.
- **[STG-132]** Test MUST attempt the normal path, relevant boundary and failure paths, permission denial, interruption or recovery path, and truthful unsupported state when applicable.
- **[STG-133]** Test MUST mark any unexecuted required check as unverified and MUST halt green promotion.
- **[STG-134]** Test self-refutation MUST attempt to reproduce each claimed defect and to break each claimed pass before reporting it.

### Resolve

- **[STG-140]** Resolve MUST take one or more owned, reproducible issues and MUST output the minimum changes required to address them plus a regression procedure.
- **[STG-141]** Resolve MUST NOT close its own issue; it SHALL move a changed issue to `verification_pending` for Test.
- **[STG-142]** Resolve MUST preserve the original failure evidence and link the repair and regression evidence to the same issue.
- **[STG-143]** Resolve MUST halt when the same issue reopens after one attempted closure or when Test remains red after three resolve passes.
- **[STG-144]** Resolve self-refutation MUST rerun the original reproduction and inspect for a narrower cause or a regression hidden by the fix.

### Close

- **[STG-150]** Close MUST summarize the objective, delivered artifacts, evidence outcomes, issue state, authority used, unresolved gates, and exact current run status.
- **[STG-151]** Close MUST emit `complete` only when [STG-025](#lifecycle-ordering) is satisfied; otherwise it MUST emit the exact applicable run-schema status and reason.
- **[STG-152]** Close MUST provide a portable handoff with the next safe action and reproduction steps for every unresolved item.
- **[STG-153]** Close self-refutation MUST compare the final claim with the authoritative evidence and issue ledger rather than the worker narrative.

## Feeder contracts

- **[STG-160]** Health-check MUST begin from an observed symptom or requested surface, MUST produce reproducible diagnostic evidence, and MUST route discovered implementation defects into Test or the issue ledger without silently fixing them.
- **[STG-161]** Audit MUST compare the declared contracts with observed artifacts and behavior, MUST record drift as evidence-backed issues, and MUST preserve the distinction between sampled and complete coverage.
- **[STG-162]** A feeder MUST NOT advance a lifecycle stage or claim green; it SHALL return a bounded entry packet for the appropriate stage.

## Failure and halt behavior

- **[STG-172]** A halt output MUST include a stable reason code, human-readable explanation, last completed action, pending or unknown operation state, evidence gaps, and the exact authority or decision needed to continue.
- **[STG-173]** A fallback output MUST disclose that the bundled provider ran, why installed candidates were rejected, and whether the fallback has the same evidence coverage as the preferred route.

## Evidence

- **[STG-170]** Evidence used to pass a done gate or advance a stage MUST resolve to a persisted record conforming to [`evidence.schema.json`](../schemas/evidence.schema.json). An observation awaiting persistence MAY appear only in a truthful halted or unverified handoff and MUST NOT satisfy a gate.
- **[STG-171]** A stage issue reference MUST resolve to an item conforming to [`issue-ledger.schema.json`](../schemas/issue-ledger.schema.json).

## Cross-references

| Protocol range | Source contract |
| --- | --- |
| STG-001–014 | [PRD FR-010, FR-013, FR-023–026](../docs/specs/prd.md#functional-requirements), [App flow: Routing](../docs/specs/app-flow.md#routing-journey) |
| STG-020–026 | [App flow: Attended Loop and Auto](../docs/specs/app-flow.md#attended-loop-journey) |
| STG-100–153 | [PRD FR-020–026](../docs/specs/prd.md#lifecycle) |
| STG-160–162 | [PRD v0.1 kernel](../docs/specs/prd.md#v01-kernel) |
| STG-170–173 | [Evidence schema](../schemas/evidence.schema.json), [Issue-ledger schema](../schemas/issue-ledger.schema.json), [Backend audit contract](../docs/specs/backend-schema.md#audit-event) |
