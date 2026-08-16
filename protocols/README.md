# Shared protocols

These ten Markdown contracts define the harness-neutral behavior of THE LOOP. Harness adapters translate local discovery and invocation details into these contracts; they do not change the contracts themselves.

## Contract index

| Contract | Purpose | Requirement prefix |
| --- | --- | --- |
| [Stage contracts](stage-contracts.md) | Common stage inputs, outputs, done gates and halt rules | `STG` |
| [Skill routing](skill-routing.md) | Capability detection, ranking, rejection and bundled fallback selection | `RTE` |
| [Code and non-code tracks](code-non-code-tracks.md) | Track-specific preparation and evidence under shared safety rules | `TRK` |
| [Workflow dispatch](workflow-dispatch.md) | Lifecycle selection, handoffs and completion boundaries | `DSP` |
| [Autonomy policy](autonomy-policy.md) | Default authority, elevation, warnings, revocation and invariants | `AUT` |
| [Run state and leases](run-state-leases.md) | Ownership, authoritative state, recovery, budgets and kill switches | `RUN` |
| [Issue ledger](issue-ledger.md) | Defect lifecycle, blocking rules and regression closure | `ISS` |
| [Evidence contract](evidence-contract.md) | Reproducible proof, outcomes and environment records | `EVD` |
| [Watcher contract](watcher-contract.md) | Read-only monitoring, staleness and escalation | `WAT` |
| [Harness capability map](harness-capability-map.md) | Discovery and behavior status across supported harnesses | `CAP` |

## Normative language

`MUST`, `MUST NOT`, `REQUIRED`, `SHALL` and `SHALL NOT` are normative. Each normative statement carries a stable identifier in square brackets. `SHOULD`, `SHOULD NOT` and `MAY` are guidance unless a referenced requirement makes them mandatory.

The JSON Schemas in [`schemas/`](../schemas/README.md) are the machine-readable record shapes. These protocols define cross-record and workflow semantics that schema validation alone cannot express. If a schema and protocol appear to disagree, execution fails closed and the conflict is recorded as an issue; adapters do not choose a convenient interpretation.

## Versioning

Requirement identifiers remain stable after release. A behavioral replacement receives a new identifier and the superseded rule stays discoverable in Git history. Contract changes require repository validation, contradiction review and the same evidence discipline as code changes.
