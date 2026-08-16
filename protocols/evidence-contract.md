# Evidence contract

## Purpose

Evidence connects a requirement to an observed result. It is not a narrative confidence score. The record shape is defined by [`evidence.schema.json`](../schemas/evidence.schema.json); `evidence_recorded` links the record into authoritative run history.

## Normative requirements

### Required record

- **[EVD-001]** Every evidence record MUST use a unique UUIDv4 `evidence_id`, match the current `run_id`, name one lifecycle stage and reference at least one requirement ID.
- **[EVD-002]** Evidence type MUST be one of `command`, `file`, `visual`, `source`, `manual` or `harness_probe`.
- **[EVD-003]** Outcome MUST be exactly `passed`, `failed`, `blocked`, `denied` or `unverified`.
- **[EVD-004]** Every record MUST state what was observed, the procedure used, the observing actor, the observation time and an allowlisted, redacted environment description.
- **[EVD-005]** Artifact references MUST use only `file`, `command_output`, `url` or `manual_observation`, and each reference MUST identify a result rather than merely name a planned check.
- **[EVD-006]** A stable byte artifact SHOULD carry its SHA-256 digest; a digest that cannot be computed or would misrepresent a changing resource MUST be null.
- **[EVD-007]** A recorded observation MUST be immutable; a rerun or correction MUST create a new evidence ID and retain the earlier result.

### Passing and failure semantics

- **[EVD-010]** `passed` MUST have a non-empty procedure and at least one result artifact or explicit manual observation.
- **[EVD-011]** `passed` MUST mean the stated procedure satisfied every linked requirement in the recorded environment; partial success MUST NOT be promoted to passed.
- **[EVD-012]** A command check MUST preserve the invoked command or equivalent reproducible operation, exit result and relevant output reference.
- **[EVD-013]** A file check MUST identify the inspected artifact and the property verified; file existence alone MUST NOT prove behavior.
- **[EVD-014]** Visual evidence MUST prove only the captured visual state; a screenshot MUST NOT by itself prove interaction, accessibility, keyboard behavior or responsive behavior outside its viewport.
- **[EVD-015]** Source evidence MUST identify the source and the claim it supports; an unavailable, stale or conflicting source MUST be reported rather than silently accepted.
- **[EVD-016]** Manual evidence MUST name the observation and observer; subjective review MUST NOT substitute for an available deterministic check.
- **[EVD-017]** A denied check MUST identify the denied capability or permission; a blocked check MUST identify the dependency; an unrun or inconclusive check MUST remain `unverified`.
- **[EVD-018]** Failed, blocked, denied and unverified outcomes MUST remain visible in stage and Close summaries.

### Integrity and privacy

- **[EVD-020]** Evidence collection MUST remain within current authority and MUST NOT turn a read-only check into a state-changing or outward action.
- **[EVD-021]** Evidence and environment fields MUST exclude secrets, credentials, access tokens, private customer data and unnecessary machine identifiers.
- **[EVD-022]** A URL reference MUST exclude embedded credentials and MUST NOT imply that mutable remote content is preserved by the record digest.
- **[EVD-023]** A file or command-output reference MUST be relative to the declared public asset or otherwise use a redacted portable label.
- **[EVD-024]** An evidence writer MUST validate the complete record against the current schema before publication to the run state.
- **[EVD-025]** Recording evidence MUST append an `evidence_recorded` event with the same evidence ID and outcome through the durable operation-intent boundary.
- **[EVD-026]** An interrupted evidence write MUST follow pending-operation reconciliation and MUST NOT invent a passing record or replay an uncertain outward probe.

### Gates and reruns

- **[EVD-030]** A stage done gate MUST map each required condition to one or more current evidence records.
- **[EVD-031]** A condition MUST count as passed only when all required evidence outcomes are passed and their inputs still match the state under review.
- **[EVD-032]** Changed code, configuration, source data, environment or harness behavior MUST invalidate affected prior evidence and require a rerun or an explicit unverified status.
- **[EVD-033]** A failing result that survives refutation MUST open or update an issue linked to that evidence.
- **[EVD-034]** Issue closure MUST link new passing regression evidence and MUST NOT overwrite the evidence that originally demonstrated the defect.
- **[EVD-035]** Close MUST refuse green when required evidence is missing, failed, blocked, denied or unverified, or when a blocking issue remains open.
- **[EVD-036]** Harness compatibility MUST be claimed only for the exact installation, discovery, invocation, permission and behavior probes actually evidenced for that harness and environment.

## Failure and halt behavior

Missing, invalid, stale or non-passing required evidence halts green under EVD-031 and EVD-035. Denied, blocked and unverified checks retain those outcomes under EVD-017; they are not converted into success. Interrupted evidence recording follows the non-replay state contract under EVD-026.

## Evidence

Conformance includes schema validation, empty procedures, missing artifacts, manual observations, nonzero command exits, screenshot overclaiming, changed-input invalidation, redaction, immutable reruns, evidence-event linkage and Close with missing or non-passing evidence.

## Cross-references

| Protocol range | Source contract |
| --- | --- |
| EVD-001–018 | [`evidence.schema.json`](../schemas/evidence.schema.json), [Backend evidence record](../docs/specs/backend-schema.md#evidence-record) |
| EVD-020–026 | [`audit-event.schema.json`](../schemas/audit-event.schema.json), [Run state and lease protocol](run-state-leases.md) |
| EVD-030–036 | [PRD FR-023–025](../docs/specs/prd.md#lifecycle), [PRD FR-063](../docs/specs/prd.md#provenance-and-trust), [Issue ledger](issue-ledger.md) |
