# Release controls and residual risks

## Release controls

| Control | Why it matters | Required evidence |
| --- | --- | --- |
| Independent provenance review | A reviewer checks the classification and clean-room boundary. | Signed review against all 31 records |
| Five-harness compatibility | Each adapter preserves the same skill and safety contract. | Isolated install, discovery and invocation evidence for Codex, Claude Code, Kimi Code, OpenCode and DeepSeek Harness |
| Outward autonomy | Publishing, sending, spending and self-modification stay approval-bound. | Visible scoped grant with actor, expiry and reversal path |

## Principal risks

| Risk | Severity | Control |
| --- | --- | --- |
| Private operating details leak into a clean rewrite | Critical | Forbidden-content scan, synthetic fixtures, independent review |
| A familiar local skill is mistaken for owned source | High | Missing licence means no reuse; compare upstream; record checksums |
| Cross-harness paths drift as CLIs evolve | High | Capability map and release checks on all five adapters |
| Runtime automation is mistaken for the only way to use a skill | Medium | Document direct harness-native invocation and treat the toolkit as optional implementation depth |
| Auto becomes an unbounded supervisor | Critical | Bounded mission contract, budgets, expiry, lease and kill switch |
| Duplicate or shadowed skill names route unpredictably | High | Doctor reports winning source and collisions before a run |
| A stale worker continues after ownership changes | Critical | Expiring leases, heartbeat, ownership check before every state change |
| Evidence is claimed without a reproducible check | High | Typed evidence records and faithful failure states |
| Upstream skills are copied for convenience | High | Dependency detection and invocation only; bundled fallback must be independently written |

## v0.1 boundary

v0.1 ships all 31 portable skills, five adapters, the shared protocols, Setup, Doctor
and the local safety toolkit. Some workflows use more runtime automation than others;
every skill remains fully usable through native harness instruction loading.

This repository owns the launch-data contract consumed by the separately managed
product page. Website code and deployment are outside this repository.
