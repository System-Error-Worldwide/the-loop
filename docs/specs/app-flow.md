# App and workflow flow

## Surfaces

THE LOOP has no custom application UI in v0.1. Users interact through their agent harness, local files and documentation.

| Surface | Purpose |
| --- | --- |
| Setup | Detect harnesses, preview installation, apply approved operations and emit a receipt. |
| Doctor | Read-only compatibility, discovery, collision, permission and behavior report. |
| Loop | Attended lifecycle entry. |
| Auto | One bounded mission entry. |
| Status | Current stage, owner, lease, authority, budget, heartbeat, issues and next gate. |
| Stop | External kill switch and explicit halt command. |
| Close | Final evidence, unresolved gates and handoff. |
| Landing page | Public explanation, trust proof, compatibility status and conversion to GitHub or consulting. |

## First-run journey

1. User clones or downloads the repository.
2. User runs Setup in dry-run mode or invokes `the-loop-setup` through an available harness.
3. Setup detects installed harnesses and their supported skill roots.
4. Setup inventories destination conflicts and presents an operation plan.
5. User approves an exact target and install mode.
6. Setup applies operations atomically and writes an install receipt.
7. Doctor validates file discovery and reports collisions.
8. If a library caller explicitly permits an isolated behavior probe, Doctor validates its typed evidence; the public CLI remains read-only discovery and does not invent a host command.
9. User starts Loop or Auto with an asset and outcome.

### First-run failure and recovery

| Failure | State | Recovery |
| --- | --- | --- |
| No target harness executable found | `setup_blocked` | Install one target harness, or use documentation only. |
| Destination contains unknown files | `approval_required` | Choose another target, copy plan or explicit overwrite. |
| Partial install | `setup_failed` | Roll back operations from the receipt; preserve pre-existing files. |
| Skill discovered twice | `doctor_warning` or `doctor_blocked` | Show precedence and let the user remove, disable or pin the intended source. |
| Behavior probe denied | `unverified` | Continue with discovery-only status or explicitly permit the probe. |

## Attended Loop journey

```text
Intent
  -> create run
  -> confirm asset, track and authority
  -> Strategize
  -> approve strategy gate
  -> Spec-pack when required
  -> approve spec gate
  -> Build one slice
  -> Test
      -> issues found -> Resolve -> Test
      -> no issues and evidence passes -> Close
  -> complete or halted with a truthful handoff
```

At every stage boundary, Loop shows the declared done gate, selected capability provider, current authority and missing evidence. The user can continue, change the route, narrow scope or halt.

## Bounded Auto journey

1. User declares one asset, outcome, acceptance gate, budget and authority.
2. Auto validates that the mission is bounded and records the active grant.
3. Auto acquires a lease and selects the first required stage.
4. Before every stage, it validates the authoritative event chain, reconciles any unmatched pending operation without replaying it, repairs stale run/lease projections from its latest complete after-state, then checks the kill switch, clock, lease, authority and budget.
5. It routes to a qualified installed skill or the bundled fallback.
6. Before each side-effecting callback it holds the grant's shared authority lock across final validation and durable intent, recording the exact semantic event, payload, rollback-capable usage reservation and local/external effect. Success records the exact semantic event and clears the intent; an unknown interruption is reconciled without replay and retains usage. A stop proven before callback entry rolls back only the exact reservation, records the halt and remains explicitly recoverable. It then records outputs, evidence, issues and heartbeat. Stage-attempt usage advances only for that stage, and duration advances only through a validated lease/heartbeat interval.
7. Test and Resolve loop until green, a configured gate, budget exhaustion or the stuck-loop rule. Budget exhaustion records the exact observed usage and leaves the run `failed` with code `budget_reached:<field>`. A run halted by a stop before its first lease can resume only through explicit recovery with a current grant and a fresh generation-zero lease.
8. Close records complete, blocked, failed or halted. It never converts an incomplete mission to complete.

### Auto halt conditions

- Approval is required for an action outside current authority.
- A required external state cannot be verified.
- The kill switch is active.
- The lease is missing, expired or owned by someone else.
- A time, turn, action or cost budget is exhausted.
- An issue reopens after one attempted closure.
- Test remains red after three resolve passes.
- Scope grows beyond the declared asset.
- A security, legal, privacy or money decision requires a person.

### Resume

Resume is explicit. It loads durable state and first resolves an unmatched intent: unknown local work becomes `failed`, while unknown outward work becomes `waiting_external` for human verification, with the reservation retained. The callback is never replayed. A previously recorded `known_not_started` rollback needs no outcome investigation, but any halted run still requires explicit recovery. Resume then checks that the asset and branch still match, records a new authority decision when the old one expired, acquires a new lease and reruns only evidence whose inputs changed.

## Routing journey

1. Stage submits required capabilities.
2. Router reads the discovered catalog and user pins.
3. Router removes unavailable, denied or incompatible candidates.
4. Router scores explicit capability metadata and verified description evidence.
5. Router selects the highest qualified candidate.
6. If none qualifies, router selects the bundled fallback.
7. Router writes a decision event with selection and rejection reasons.
8. Stage validates the provider's output against the common contract.

A provider failure does not silently promote another provider. The event records failure, then the stage may route again under the same authority and budget.

## Issue lifecycle

```text
open -> acknowledged -> resolving -> verification_pending -> closed
  |          |              |                  |
  +--------> deferred       +---------------> reopened
```

- Test opens an issue with severity, evidence and reproduction.
- Resolve moves only an owned issue to `resolving`.
- A change moves it to `verification_pending`.
- Test closes it only after the recorded regression check passes.
- A failed regression moves it to `reopened` and triggers the stuck-loop rule.
- A blocking deferred issue prevents green.

## Authority elevation journey

1. The agent proposes an exact grant.
2. The interface lists allowed actions, excluded actions, affected assets, risks and expiry.
3. The user types the required confirmation phrase.
4. The system records actor, phrase digest, scope, start and expiry.
5. Elevated status appears at startup, in status, before affected actions and in Close.
6. The user revokes with one command or creates the configured revocation file.
7. Revocation blocks new affected actions immediately and is written to the audit log.

No elevation can disable permanent invariants.

## Kill-switch journey

1. User creates `.the-loop/STOP` or activates another configured external switch.
2. The next pre-mutation check detects it, even when the worker lease is missing or expired.
3. The active action finishes only if stopping it would corrupt the asset; otherwise it is interrupted safely.
4. A lease-independent safety-control event records the complete resulting projection and run state becomes `halted_kill_switch`.
5. The lease is released or allowed to expire.
6. Status and Close explain the last completed action and any uncertain state.
7. Removing the switch does not resume work. The user explicitly resumes.

## Full-product extension journeys

These journeys remain part of THE LOOP's product architecture. They are sequenced
after the bounded v0.1 kernel so they reuse its authority, state, evidence and recovery
contracts. They are not canceled or treated as optional substitutes for the full
product.

### Parallel

The planner creates independent lanes with disjoint ownership, done gates and leases. Shared-file work remains sequential. A coordinator validates each lane, resolves integration issues and alone may advance the parent run.

### Cloud

Cloud accepts only material available in the remote environment. It plans, drafts and hands off when production, private backend or protected state cannot be reached. It never embeds private supervisor details.

### Endless

Endless reads an approved queue, selects one eligible item, creates a bounded Auto mission and waits for its terminal state. It may select another approved item only after reconciliation. An empty queue enters monitor state. It never invents work. Repeated capability gaps may produce a skill proposal, never a silent self-modification.

## External landing-page content journey

This journey defines the product information contract for the separate landing-page session. It is not an implementation flow owned by the skill pack.

1. Visitor arrives at `systemerror.app/the-loop` from search, GitHub, a shared link or System Error Software navigation.
2. Hero states what THE LOOP does, who made it and the four target harnesses with
   their current evidence-backed status.
3. Primary CTA opens the public repository or installation section.
4. A compact “how it works” section explains Setup, Loop and Auto first, then labels Parallel, Cloud and Endless by release status.
5. Capability section shows installed-specialist routing plus bundled fallbacks.
6. Safety section shows autonomy levels, visible warnings and permanent invariants.
7. Trust section explains provenance, licence status and upstream dependency handling.
8. Compatibility matrix states shipped, preview, planned or unverified for every mode and harness.
9. Examples show one code mission and one non-code mission.
10. Quickstart links to the matching tagged repository documentation.
11. Primary CTA repeats at the close. Secondary CTA links to the Agent Workflow Audit or consulting offer.

### Landing states

| State | Required behavior |
| --- | --- |
| Repository not public | Do not deploy the page with a dead or private CTA. |
| Release not published | Label status honestly and link to the current public branch only if intentionally public. |
| JavaScript disabled | No loss of content or navigation; v1 uses no client-side script. |
| Narrow viewport | Single-column reading order, no horizontal overflow, minimum touch target 44 by 44 CSS pixels. |
| Reduced motion | No required animation; any CSS transition is non-essential and removed or reduced. |
| External CTA unavailable | Deployment fails link verification. |
| Analytics absent or blocked | Full page functionality remains unchanged. |

## Run states

| State | Meaning | May mutate? |
| --- | --- | --- |
| `draft` | Inputs are incomplete. | no |
| `ready` | Asset, gate, authority and budget are valid. | no |
| `active` | An owner holds a valid lease. | yes, within authority |
| `waiting_approval` | Exact human authority is missing. | no |
| `waiting_external` | Required outside state is not ready. | no |
| `blocked` | A named gate prevents progress. | no |
| `failed` | Required action or evidence failed. | no until explicit recovery |
| `halted_kill_switch` | External stop was detected. | no |
| `complete` | Done gate passed and blocking issue count is zero. | no |
| `cancelled` | User ended the mission. | no |

## Assumption ledger

| Assumption | Class | Consequence if wrong |
| --- | --- | --- |
| Harness chat is sufficient for all v0.1 interaction. | safe default | Add a terminal status renderer without changing state contracts. |
| Explicit resume is preferable to automatic restart. | safe default | Keep safety invariant; add configurable prompts, never silent resume. |
| The landing page needs no interactive demo in v1. | safe default | Add only after conversion evidence and CSP review. |
| The Agent Workflow Audit URL is `https://systemerror.app/services/`. | locked | Any production change must keep the route visible and functional before approval. |
