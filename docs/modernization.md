# Public instruction modernization

This note describes the public documentation and skill-instruction layer in this repository. It does not claim a live harness capability proof or a particular runtime implementation beyond what the shipped Python toolkit and conformance suite already test.

## Scope

- Updates apply to README, shared protocols under `protocols/`, bundled `SKILL.md` packages and selected product specs.
- The public Python runtime, JSON schemas, adapters and locked conformance scenarios remain authoritative for machine behavior.
- Private harness configuration, host paths and non-public measurements are out of scope.

## What changed

- Shared execution contract in [protocols/README.md](../protocols/README.md): goal, observed start, scoped execution, done gate, evidence and refutation.
- Route-first execution: qualified routing and guard caps precede native collaboration, guarded process delegation or serial topology.
- Active injected capability catalog before supplemental discovery, with context-scoped caching.
- Spec depth tiers S0, S1 and S2 aligned with [stage contracts](../protocols/stage-contracts.md) without weakening [STG-111](../protocols/stage-contracts.md) for qualifying S2 work.
- Cloud and Test instruction alignment: execute real checks when observed; independent evaluation and git checkpoint custody separate from deploy or publish authority.
- Completion signals, supervisor recovery, safe-boundary context rotation and Endless queue semantics documented in protocols and mode skills.
- Observed Codex and Claude adapter notes in [harness capabilities](harness-capabilities.md), linked from [harness capability map](../protocols/harness-capability-map.md).

## Limitations

- Instructions are contracts for agents and maintainers; they do not replace adapter probes or doctor output on a host.
- No new model or provider configuration is introduced here; ranking and external-first defaults in the public router are unchanged.
- Roll back instruction changes by reverting the branch or reinstalling from a prior release receipt; the setup rollback receipt path is unchanged and no separate archive tool ships in this repository.

## Preserved gates

Authority, lease, evidence, issue ledger, kill switch, callback namespace rules, unknown-outcome handling, budget accounting, three-red Resolve cap, reopened-issue halt, AUT-031 outward boundary and TRK-106 outward Git or deploy gates are unchanged in meaning.
