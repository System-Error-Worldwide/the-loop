# Skill routing

## Purpose

This protocol defines deterministic, harness-neutral provider selection for a requested capability. It implements [PRD FR-010 through FR-015](../docs/specs/prd.md#routing), the [routing journey](../docs/specs/app-flow.md#routing-journey), and [`route.schema.json`](../schemas/route.schema.json).

RFC 2119 terms are normative only in numbered requirements. Each normative requirement has one stable `RTE` identifier.

## Normative requirements

## Capability request

- **[RTE-001]** A routing request MUST identify a namespaced capability, stage requirement IDs, track, active harness, relevant environment digest, required inputs and outputs, evidence obligations, authority constraints, and fallback capability.
- **[RTE-002]** A capability identifier MUST use the format accepted by [`route.schema.json`](../schemas/route.schema.json); a provider name MUST NOT substitute for a capability identifier.
- **[RTE-003]** A stage MUST submit the smallest sufficient capability set and MUST NOT route broad access when a narrower capability satisfies the contract.

## Candidate catalog

- **[RTE-010]** The router MUST build a current candidate catalog from discoverable installed providers and the bundled fallback before each decision.
- **[RTE-011]** Each candidate MUST record provider identifier, installed or bundled source, compatible harnesses, capability evidence, description score, behavior status, typed behavior observations, rejection reasons, and provenance type; every observation MUST identify capability, harness, track, environment digest, outcome, observation time, and evidence ID.
- **[RTE-012]** Discovery MUST distinguish absent, undiscoverable, denied, incompatible, failed, and unverified states.
- **[RTE-013]** A name match alone MUST NOT count as capability evidence.
- **[RTE-014]** Imported provider instructions MUST NOT be copied into the project merely to satisfy routing; an approved upstream dependency SHALL be linked or invoked under its own terms.
- **[RTE-015]** A candidate classified as excluded MUST NOT be selected.
- **[RTE-016]** A candidate with unknown or incompatible provenance MUST NOT outrank the bundled fallback.

## Qualification and ranking

- **[RTE-020]** The router MUST remove candidates that are unavailable, denied, incompatible with the active harness or track, outside authority, missing required inputs, unable to return the required evidence shape, or have a current capability-scoped `behavior_status: failed`. A failed behavior result MUST remain disqualifying unless the unique latest observation matching the route's capability, harness, track, and environment digest is newer and `passed`; machine validation MUST reject a selected failed candidate, a missing or mismatched observation, conflicting observations at the latest matching time, and any latest matching outcome other than `passed`.
- **[RTE-021]** A user pin MUST take precedence only after the pinned candidate passes [RTE-020](#qualification-and-ranking).
- **[RTE-022]** Qualified candidates SHALL be ranked in this order: valid user pin, explicit capability evidence, verified harness and track compatibility, description match, fresh behavior proof, then bundled fallback.
- **[RTE-023]** Description similarity and untyped capability-evidence strings MUST be treated as supporting evidence, not proof of behavior.
- **[RTE-024]** A stale behavior result MUST remain visible in typed observation history and MUST NOT be represented as current verification unless the unique latest matching observation passes the full route context.
- **[RTE-025]** A tie that changes authority, output semantics, evidence coverage, or external effects MUST halt for a route decision; other ties SHALL resolve deterministically by provider identifier.

## Route decision

- **[RTE-030]** Every decision MUST produce a record conforming to [`route.schema.json`](../schemas/route.schema.json), including the route harness, track, environment digest, typed behavior observations, and verification time.
- **[RTE-031]** If no installed provider qualifies, the router MUST select the complete bundled fallback and record a non-empty fallback reason.
- **[RTE-032]** A selected installed provider MUST have a null fallback reason; a selected bundled provider MUST identify why installed candidates did not qualify.
- **[RTE-033]** The route record MUST include every considered candidate and its acceptance or rejection evidence; rejected candidates MUST retain precise reasons, and prior matching failed, denied, or unverified observations MUST remain visible when a newer pass supersedes them.
- **[RTE-034]** The route decision MUST be written before provider execution and linked from the run's selected routes.
- **[RTE-035]** The stage MUST disclose the selected provider, source, verification freshness, and material limitations at its boundary.

## Provider execution

- **[RTE-040]** The selected provider MUST receive the common stage envelope from [STG-001](stage-contracts.md#common-stage-envelope) and no broader authority than the parent run.
- **[RTE-041]** Provider output MUST be validated against the stage and track contracts; provider-specific success language MUST NOT override missing evidence or open issues.
- **[RTE-042]** A provider failure MUST be recorded as failed, denied, blocked, or unverified before another route is considered.
- **[RTE-043]** Rerouting MUST create a new route decision under the same frozen mission scope, authority, and budget unless an explicit recovery changes them.
- **[RTE-044]** A provider MUST NOT silently install another provider, elevate permissions, expand scope, act outwardly, or modify its own routing policy.
- **[RTE-045]** Harness-specific invocation syntax MUST remain in the harness adapter; the common route record and capability contract MUST remain harness-neutral.

## Fallback

- **[RTE-050]** Every v0.1 lifecycle capability MUST have a bundled fallback that can accept the same required inputs and produce the same output, evidence, halt, and handoff fields.
- **[RTE-051]** A fallback MAY be less specialized, but it MUST NOT weaken authority, state, evidence, issue, privacy, or faithful-failure requirements.
- **[RTE-052]** A missing optional integration MUST degrade to the fallback or a truthful halt; it MUST NOT make the core lifecycle unavailable.
- **[RTE-053]** Fallback execution MUST remain observable in route, stage, and close outputs.

## Security and privacy

- **[RTE-060]** Discovery and routing MUST NOT transmit project content, prompts, credentials, or provider inventories unless an outward action is explicitly authorized.
- **[RTE-061]** Candidate metadata containing credentials, unsafe paths, or non-public operational details MUST be rejected from public route evidence.
- **[RTE-062]** A provider's own permission model MAY further restrict execution; the router MUST treat that denial as authoritative and MUST NOT bypass it.

## Failure and halt behavior

- **[RTE-070]** Routing MUST halt when no candidate, including the bundled fallback, can satisfy a required input, output, evidence, authority, or safety contract.
- **[RTE-071]** A routing halt MUST record the requested capability, rejected candidates, precise rejection reasons, missing fallback coverage, and the decision or capability needed to continue.
- **[RTE-072]** A denied or failed provider MUST NOT be retried as if it had not run; its outcome and consumed budget MUST remain visible.

## Evidence

- **[RTE-080]** Route evidence MUST include the conforming route record, catalog freshness, route capability, harness, track and environment digest, behavior status and typed observation history, compatibility basis, and provenance type for the selected provider.
- **[RTE-081]** A verified route MUST have exactly one latest typed observation matching capability, harness, track, and environment digest; that observation MUST be `passed`, its evidence ID MUST identify the behavior probe, and route `verified_at` MUST equal its `observed_at`. Otherwise the candidate MUST remain unverified or rejected.
- **[RTE-082]** Close evidence MUST preserve every route used by the run, including fallback and reroute decisions.

## Cross-references

| Protocol range | Source contract |
| --- | --- |
| RTE-001–003 | [Stage contract requirement](../docs/specs/prd.md#routing), [Route schema](../schemas/route.schema.json) |
| RTE-010–025 | [TDD: Capability router](../docs/specs/tdd.md#capability-router) |
| RTE-030–045 | [App flow: Routing journey](../docs/specs/app-flow.md#routing-journey) |
| RTE-050–053 | [PRD FR-014 and product principle 2](../docs/specs/prd.md#product-principles) |
| RTE-060–062 | [PRD NFR-002, NFR-003, NFR-008](../docs/specs/prd.md#non-functional-requirements) |
