# Workflow dispatch

## Purpose

This protocol defines harness-neutral delegation, concurrency, and handoff. It does
not require a particular subagent or workflow API. The Parallel and remote packages
are included, but their runtime modes remain capability-gated; the bounded lifecycle
can execute every contract serially with bundled providers.

RFC 2119 terms are normative only in numbered requirements. Each normative requirement has one stable `DSP` identifier.

## Normative requirements

## Dispatch packet

- **[DSP-001]** A dispatch packet MUST include run and parent identifiers, stage, track, objective, approved slice, asset and write boundaries, required capability, done gate, input references, authority reference, owner and lease expectations, budgets, evidence obligations, halt conditions, and return schema.
- **[DSP-002]** A dispatcher MUST resolve the capability through [skill routing](skill-routing.md#route-decision) before assigning work.
- **[DSP-003]** A child worker MUST receive no broader scope, authority, budget, lifetime, or destination access than its parent run.
- **[DSP-004]** A dispatch packet MUST identify which actor owns mutation, integration, issue transitions, and final acceptance.
- **[DSP-005]** A worker MUST reject an incomplete or contradictory packet rather than infer authority, ownership, or scope.

## Execution selection

- **[DSP-010]** The dispatcher MUST select serial execution when independence, isolation, ownership, or harness concurrency cannot be proven.
- **[DSP-011]** Independent dispatch MAY be used only when work units have disjoint write boundaries, separately testable outputs, explicit integration ownership, and supported worker isolation.
- **[DSP-012]** Two workers MUST NOT mutate the same file, state projection, issue record, or undeclared shared resource concurrently.
- **[DSP-013]** A harness that lacks verified concurrent delegation MUST use serial or inline execution and record the capability fallback.
- **[DSP-014]** The bundled inline fallback MUST accept the same packet and return the same result envelope as a delegated provider.
- **[DSP-015]** Parallel runtime mode MUST NOT be simulated by unsafe background work; the package and lane primitives SHALL NOT be presented as live-supported until lane ownership and isolation contracts are implemented and verified in the active harness.

## Ownership and liveness

- **[DSP-020]** A writing worker MUST hold the valid run or lane lease defined by the state protocol before every mutation.
- **[DSP-021]** A dispatcher MUST NOT treat process existence, elapsed time, or a claimed status message as proof of progress.
- **[DSP-022]** Long-running work MUST emit observable heartbeat state at configured intervals and stage boundaries.
- **[DSP-023]** A dispatcher MUST define a stale threshold and recovery action before background execution begins.
- **[DSP-024]** Stale heartbeat status MUST trigger observation, notification, or escalation but MUST NOT by itself revoke an unexpired matching lease. On lost, expired, replaced, or conflicting ownership, the worker MUST stop mutation and return or persist a truthful halt.
- **[DSP-025]** A replacement worker MUST use explicit recovery and a fresh lease generation; it MUST NOT inherit an unverified in-memory claim from the prior worker.
- **[DSP-026]** A kill-switch signal MUST take precedence over dispatch completion and MUST prevent the next state-changing action under [AUT-034](autonomy-policy.md#action-boundary).

## Side-effect boundary

- **[DSP-030]** A dispatched side-effecting callback MUST use the same durable intent, authority linearization, namespace, and exact completion rules as inline execution.
- **[DSP-031]** A worker MUST classify effects as local or external before intent and MUST reserve the corresponding usage before callback entry.
- **[DSP-032]** An unknown interrupted operation MUST be reconciled without replay; local work SHALL become failed and outward work SHALL wait for external verification.
- **[DSP-033]** A worker MAY roll back a reservation only when the same live process proves the callback did not begin, as defined by `FR-038` in the [backend audit contract](../docs/specs/backend-schema.md#audit-event).

## Result envelope

- **[DSP-040]** A worker result MUST include worker identity, route reference, started and finished times, status, produced or changed artifacts, evidence references, issue references, usage, last completed action, pending or unknown effects, and handoff or halt reason.
- **[DSP-041]** A worker MUST distinguish complete, failed, blocked, denied, unverified, cancelled, stale, and halted outcomes.
- **[DSP-042]** A dispatcher MUST validate the result against [stage contracts](stage-contracts.md#common-stage-envelope) and the selected [track contract](code-non-code-tracks.md#track-selection) before accepting it.
- **[DSP-043]** The integration owner MUST independently verify combined output and MUST be the only worker allowed to advance a parent run after parallel work.
- **[DSP-044]** Missing, malformed, contradictory, or unverifiable worker output MUST halt acceptance and open an issue when it affects the done gate.

## Failure and halt behavior

- **[DSP-050]** Dispatch failure MUST be recorded before retry, reroute, or inline fallback.
- **[DSP-051]** A retry MUST preserve the same bounded objective, authority, budget accounting, issue history, and evidence history unless explicit recovery records a change.
- **[DSP-052]** A provider failure MUST NOT silently trigger a different provider; rerouting SHALL follow [RTE-043](skill-routing.md#provider-execution).
- **[DSP-053]** A retry MUST NOT replay an operation with an unknown outcome.
- **[DSP-054]** Repeated reopening after one attempted closure or three red Test/Resolve passes MUST halt for a human gate.
- **[DSP-055]** A dispatcher MUST cancel or halt remaining workers when their outputs become invalidated by a kill switch, scope change, lost authority, failed shared prerequisite, or terminal parent state.

## Boundaries for expansion-package runtimes

- **[DSP-060]** Parallel work MUST use disjoint lane ownership and a single declared integration owner before it can claim conformance.
- **[DSP-061]** Remote or restricted work MUST use only material present and authorized in that environment and MUST hand off when required protected state is unavailable.
- **[DSP-062]** A continuous supervisor MUST select only approved queue items, MUST run each as a bounded mission, and MUST monitor rather than invent work when the queue is empty.
- **[DSP-063]** A worker or supervisor MUST NOT silently create, install, or modify its own skills, protocols, authority, or work queue.

## Evidence

- **[DSP-070]** Dispatch evidence MUST preserve the dispatch packet, route record, worker identity, lease or ownership reference, heartbeat observations, result envelope, and acceptance decision.
- **[DSP-071]** Concurrency evidence MUST identify disjoint write boundaries, isolation mechanism, integration owner, and combined verification.
- **[DSP-072]** A fallback dispatch MUST record the missing harness capability and prove that the inline result passed the same stage and track contract.

## Cross-references

| Protocol range | Source contract |
| --- | --- |
| DSP-001–015 | [PRD portability and routing](../docs/specs/prd.md#routing), [Engineering plan Slice 2.4](../docs/specs/engineering-plan.md#slice-24-ten-protocol-contracts) |
| DSP-020–026 | [PRD FR-030–035](../docs/specs/prd.md#state-ownership-and-recovery) |
| DSP-030–033 | [Backend audit event contract](../docs/specs/backend-schema.md#audit-event) |
| DSP-040–055 | [App flow: Auto halt and Resume](../docs/specs/app-flow.md#auto-halt-conditions) |
| DSP-060–063 | [App flow: Expansion packages](../docs/specs/app-flow.md#expansion-package-journeys) |
