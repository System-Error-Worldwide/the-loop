# Risks and human gates

## Current human gates

| Gate | Why it needs a person | Blocks |
| --- | --- | --- |
| Independent final reviewer | The provenance gate requires a reviewer who did not author the public rewrite. | Release candidate approval |
| Outward autonomy defaults | Any relaxation of approval for publishing, sending, spending or self-modification must be explicitly confirmed and scoped. | Elevated autonomy modes |
| Landing page deployment | `systemerror.app/the-loop` is an outward-facing production change and currently returns 404. | Public launch |

## Principal risks

| Risk | Severity | Control |
| --- | --- | --- |
| Private operating details leak into a clean rewrite | Critical | Forbidden-content scan, synthetic fixtures, independent review |
| A familiar local skill is mistaken for owned source | High | Missing licence means no reuse; compare upstream; record checksums |
| “Cross-harness” means only file discovery, not equivalent behavior | High | Capability map and behavior tests on all four harnesses |
| Auto becomes an unbounded supervisor | Critical | Bounded mission contract, budgets, expiry, lease and kill switch |
| Duplicate or shadowed skill names route unpredictably | High | Doctor reports winning source and collisions before a run |
| A stale worker continues after ownership changes | Critical | Expiring leases, heartbeat, ownership check before every state change |
| Evidence is claimed without a reproducible check | High | Typed evidence records and faithful failure states |
| Upstream skills are copied for convenience | High | Dependency detection and invocation only; bundled fallback must be independently written |

## Non-blocking decisions before release

- Confirm whether `THE LOOP` is the final display name while keeping package and repository names lowercase.

## Phase boundary

Phase 0 and Phase 1 are complete. The bounded Phase 2 runtime kernel is implemented,
but the repository is not a v0.1 release until every package in the shipping manifest,
four-harness behavior evidence and the independent final review are complete.

The landing page may be specified and implemented in a later authorised slice, but it must not be deployed without a separate explicit approval.
