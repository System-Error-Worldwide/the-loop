# Risks and human gates

## Current human gates

| Gate | Why it needs a person | Blocks |
| --- | --- | --- |
| Independent final reviewer | The provenance gate requires a reviewer who did not author the public rewrite. | Support claim and release approval |
| Codex isolation | The frozen live probe loaded private host context despite project-only controls. A genuinely isolated authenticated execution path must be proven before another behavior probe. | Codex support claim and Phase 3 completion |
| Claude Code authentication | Model execution stopped at the harness login gate. | Claude Code behavior evidence |
| Kimi Code authentication and model | Model execution stopped because no authenticated default model was configured. | Kimi Code behavior evidence |
| OpenCode runtime | Both skill and no-skill isolated smoke tests failed with `InstanceRef not provided`. | OpenCode behavior evidence |
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

Phase 0, Phase 1 and the bounded Phase 2 implementation are complete. The 2026-08-16
frozen candidate passed Setup and Doctor on all four target harnesses, but live
behavior passed on none. The repository remains private and is not a v0.1 release.
Phase 3 remains blocked by the four named environment gates above.

Phase 4 is the full-product extension track, not an exclusion list. Its components are
sequenced after the kernel because Parallel, Cloud, Watch, Control, user-facing
Autonomy, Portfolio Review, the skill-planner/creator line, supporting handoff/quality
utilities, and Endless must inherit the proven safety contracts rather than create
alternate control paths.

The landing page is implemented and tested only in its separate dedicated website
session. This repository owns the launch-data contract and acceptance gate, not the
page implementation. Deployment still requires separate explicit approval.
