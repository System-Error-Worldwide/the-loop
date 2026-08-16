# Autonomy policy

## Purpose

This protocol defines visible, expiring, revocable authority for attended and autonomous work. It implements [PRD FR-040 through FR-045](../docs/specs/prd.md#autonomy), the [authority elevation journey](../docs/specs/app-flow.md#authority-elevation-journey), [`grant.schema.json`](../schemas/grant.schema.json), and the runtime authority boundary in the [TDD](../docs/specs/tdd.md#autonomy-model).

RFC 2119 terms are normative only in numbered requirements. Each normative requirement has one stable `AUT` identifier.

## Normative requirements

## Default authority

- **[AUT-001]** Authority MUST default to attended or bounded local, reversible work inside one declared asset and frozen budget.
- **[AUT-002]** Outward actions, autonomous strategic expansion, and self-modification MUST require explicit scope by default.
- **[AUT-003]** Missing, ambiguous, expired, revoked, conflicting, or unverifiable authority MUST deny the action and produce a precise waiting or failure state.
- **[AUT-004]** A harness permission MAY narrow a grant; a grant MUST NOT override a harness denial or operating-system control.
- **[AUT-005]** Authority MUST NOT be inferred from prior sessions, user identity, repository access, available credentials, tool presence, or a provider's claimed capability.

## Authority levels

- **[AUT-010]** The runtime SHALL enforce the following level semantics exactly:

| Level | Local reversible work | Outward actions | Strategic expansion | Self-modification |
| --- | --- | --- | --- | --- |
| `attended` | meaningful gates are confirmed | explicit approval | explicit approval | explicit approval |
| `bounded` | allowed inside declared asset and budget | explicit approval | explicit approval | explicit approval |
| `scoped` | exact confirmed scope | exact confirmed scope | exact confirmed scope | explicit scope |
| `operational` | named operations within expiry | named confirmed operations | explicit approval | explicit approval |
| `full` | broad only inside declared environment | only explicitly confirmed scope | only explicitly confirmed scope | only explicitly confirmed scope |

- **[AUT-011]** `full` MUST NOT mean unrestricted, invisible, permanent, or invariant-free authority.
- **[AUT-012]** A child worker or nested mission MUST NOT receive a higher level or broader scope than its parent grant.

## Grant creation and visibility

- **[AUT-020]** Every grant MUST conform to [`grant.schema.json`](../schemas/grant.schema.json) and record grant ID, level, actor, assets, actions, destinations, exclusions, risks shown, confirmation text, confirmation time, expiry, revocation state, and all permanent invariants.
- **[AUT-021]** Elevation MUST present the exact added authority, affected assets and destinations, realistic failure and privacy risks, expiry, revocation method, and permanent invariants before confirmation.
- **[AUT-022]** Elevation MUST require a typed confirmation that identifies the requested grant; passive continuation or conversational momentum MUST NOT count as confirmation.
- **[AUT-023]** Startup, runtime status, affected action boundaries, digests, and Close MUST display an elevated grant's level, material scope, expiry, and revocation state.
- **[AUT-024]** Exclusions MUST take precedence over wildcard or explicit allowances for the same asset, action, or destination.
- **[AUT-025]** Grant scope MUST be no broader than the declared mission and MUST use an expiry appropriate to that mission.
- **[AUT-026]** Changing level, scope, expiry, actor, or exclusions MUST create a new confirmed grant or explicit recovery record; it MUST NOT mutate authority silently.

## Action boundary

- **[AUT-030]** Immediately before every state-changing action, the runtime MUST validate authoritative state, kill switch, clock, owner and lease generation, grant validity and exclusions, destination, action type, asset boundary, and remaining budget.
- **[AUT-031]** Sending, publishing, deploying, merging, pushing, purchasing, deleting external data, changing remote configuration, or communicating as the user MUST be classified as outward actions.
- **[AUT-032]** Strategy expansion MUST include adding an undeclared asset, objective, audience, work queue item, integration, or materially broader success condition.
- **[AUT-033]** Self-modification MUST include changing installed skills, protocols, adapters, routing policy, authority policy, supervisor behavior, or the agent's own executable instructions.
- **[AUT-034]** A detected or indeterminate kill switch MUST prevent callback entry, record a truthful halted state, and require explicit recovery after the switch clears.
- **[AUT-035]** A side-effecting callback MUST hold the shared grant lock through final validation and durable intent; official revocation MUST hold the exclusive grant lock through its durable update and audit marker.
- **[AUT-036]** An intent that linearizes before revocation MAY complete exactly once; a revocation that linearizes first MUST prevent a new intent.
- **[AUT-037]** Ordinary budget exhaustion at reservation or successful completion MUST produce the exact failed state and primary budget reason defined by the [backend run contract](../docs/specs/backend-schema.md#run-record); when an unknown operation outcome also exhausts a budget, the unknown-outcome status and reason MUST retain precedence and every exhausted budget MUST remain visible through the deterministic markers required by [RUN-077](run-state-leases.md#budgets-and-stop-control).

## Revocation and recovery

- **[AUT-040]** Revocation MUST be available through one documented user action and MUST block new affected intents immediately after its authority linearization point.
- **[AUT-041]** A revoked grant MUST remain revoked; audit repair MUST NOT restore, replace, or broaden it.
- **[AUT-042]** Each run using a revoked shared grant MUST record exactly one matching `authority_revoked` marker from persisted revocation actor and time before denying supported mutation under that grant.
- **[AUT-043]** A retry MUST repair a verified missing revocation marker, MUST accept a verified committed marker without duplication, and MUST halt with `audit_pending` or `committed_state_unknown` when audit state cannot be safely established.
- **[AUT-044]** Expired or revoked authority on a leased or otherwise recoverable run MUST require a new grant and explicit recovery before mutation resumes.
- **[AUT-045]** Removing a kill switch MUST NOT resume work; recovery MUST revalidate state, authority, budget, ownership, and lease generation.
- **[AUT-046]** A ready run with no lease whose bound grant expires or is revoked MUST retain its ready asset projection and MUST reject acquisition; a revoked grant still requires its per-run audit marker. Because v0.1 has no pre-lease authority-replacement transition, continuation MUST use a new run created under a current grant.
- **[AUT-047]** Authority revocation MUST remain recordable as a safety-reducing control when a kill switch is present or indeterminate, or the run is already kill-halted; the final run projection MUST remain `halted_kill_switch`, and the audit chain MUST retain both the persisted revocation truth and the kill-switch truth without granting work authority.

## Permanent invariants

- **[AUT-100]** Authority level and material scope MUST remain visible.
- **[AUT-101]** Important decisions and state transitions MUST remain audit logged.
- **[AUT-102]** Completion MUST remain evidence-gated.
- **[AUT-103]** Every active run or lane MUST retain explicit ownership.
- **[AUT-104]** Every writing worker MUST retain a valid lease.
- **[AUT-105]** An external kill switch MUST remain effective.
- **[AUT-106]** Failure, denial, uncertainty, and unsupported behavior MUST remain faithfully reported.
- **[AUT-107]** Permission elevation MUST never occur silently.
- **[AUT-108]** No authority level, including `full`, MUST disable any requirement from AUT-100 through AUT-107.
- **[AUT-109]** Closing an intent that committed under a then-valid lease after that lease expires MUST be treated only as truthful completion or reconciliation of the already-authorized operation under [RUN-039](run-state-leases.md#lease-lifecycle); it MUST NOT grant a writing worker authority for any new action or leave the run active.

## Autonomous modes

- **[AUT-120]** Bounded Auto MUST run one declared asset toward one done gate and MUST halt on any authority, budget, scope, evidence, retry, or human-decision gate.
- **[AUT-121]** Auto MUST NOT select unrelated work, extend its own lifetime, or turn an empty queue into invented work.
- **[AUT-122]** Parallel, remote, and continuous modes MUST remain unavailable until their additional ownership, isolation, heartbeat, budget, and kill-switch contracts are verified.
- **[AUT-123]** A continuous supervisor MAY propose a skill or workflow improvement for repeated gaps, but it MUST NOT install or apply the proposal without a separate grant.

## Failure and halt behavior

- **[AUT-130]** An authority failure MUST halt before callback entry and MUST record whether authority is missing, denied, expired, revoked, excluded, outside asset, outside action, or outside destination.
- **[AUT-131]** A revocation audit gap MUST retain the revoked grant and MUST report `audit_pending` or `committed_state_unknown` without claiming repair.
- **[AUT-132]** A requested elevation that lacks explicit confirmation MUST remain `waiting_approval` and MUST NOT consume the proposed grant.
- **[AUT-133]** A legal, security, privacy, money, destructive, or materially strategic judgment outside recorded scope MUST halt for a person.

## Evidence

- **[AUT-140]** Authority evidence MUST include the grant record, visible scope and exclusions, confirmation event, runtime checks, expiry or revocation state, and affected intent or denial event.
- **[AUT-141]** Elevated execution evidence MUST show that startup, action-boundary, status, digest, and Close warnings remained visible.
- **[AUT-142]** Revocation evidence MUST show persisted actor and time, exactly one matching marker per affected run, denial of new intents, and no grant restoration.
- **[AUT-143]** Permanent-invariant evidence MUST cover every invariant from AUT-100 through AUT-107 at each release gate.

## Cross-references

| Protocol range | Source contract |
| --- | --- |
| AUT-001–012 | [PRD FR-040 and TDD autonomy table](../docs/specs/tdd.md#autonomy-model) |
| AUT-020–026 | [Grant schema](../schemas/grant.schema.json), [App flow: Authority elevation](../docs/specs/app-flow.md#authority-elevation-journey) |
| AUT-030–037 | [TDD run manager safety order](../docs/specs/tdd.md#run-manager), `FR-037` and `FR-038` in [PRD state requirements](../docs/specs/prd.md#state-ownership-and-recovery) |
| AUT-040–047 | [Backend authority revocation contract](../docs/specs/backend-schema.md#audit-event) |
| AUT-100–109 | [PRD FR-031 and FR-045](../docs/specs/prd.md#state-ownership-and-recovery), [`permanent_invariants`](../schemas/grant.schema.json), [Run lease lifecycle](run-state-leases.md#lease-lifecycle) |
| AUT-120–123 | [PRD modes](../docs/specs/prd.md#modes-and-relationship), [App flow: Full-product extensions](../docs/specs/app-flow.md#full-product-extension-journeys) |
