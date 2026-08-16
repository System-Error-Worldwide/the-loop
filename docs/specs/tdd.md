# Technical design document

## Architecture summary

THE LOOP is a portable instruction and state protocol with small local utilities. It is not a hosted agent runtime.

```text
User intent
  -> harness adapter
  -> mode contract
  -> run state and authority check
  -> stage contract
  -> capability router
       -> approved installed specialist
       -> bundled fallback
  -> evidence and issue ledger
  -> next stage, recovery or halt
```

The portable core defines behavior. Harness adapters translate discovery, invocation, permissions and optional delegation without changing the lifecycle semantics.

## Repository layout

```text
the-loop/
  .agents/skills/              canonical portable skill packages
  adapters/
    codex/
    claude_code/
    kimi_code/
    opencode/
  protocols/                   normative Markdown contracts
  schemas/                     JSON Schema files
  scripts/                     setup, doctor and validation utilities
  tests/
    fixtures/                  synthetic repositories and skills
    conformance/               shared behavior scenarios
    harnesses/                 harness launch and discovery probes
  docs/
    specs/
    provenance/
  examples/
    code/
    non-code/
```

`.agents/skills` is the canonical portable source because Codex, Kimi Code and OpenCode document project-level discovery there. Claude Code uses a thin adapter that exposes the same packages through `.claude/skills` or an optional Claude plugin layout. The installer must not maintain divergent copies.

For each selected harness and scope, Setup installs to one preferred root rather than
every root the harness can search. It prefers `.agents/skills` when supported and uses
the first harness-specific root otherwise. Doctor still inspects every documented root
so pre-existing shadows and cross-harness collisions remain visible.

## Technology choices

### Core

- Markdown for skill instructions and protocol contracts.
- JSON for user configuration and runtime state.
- JSON Schema draft 2020-12 for machine validation.
- Python 3.9 or newer, standard library only, for setup, doctor, atomic state handling and conformance utilities.
- POSIX shell only for small entry shims where unavoidable.

### Why Python standard library

It provides atomic file operations, process management, JSON parsing and cross-platform path handling without a package install. It keeps the v0.1 trust and supply-chain surface small.

### Rejected alternatives

- Node.js runtime: capable, but adds a package manager and dependency tree for a Markdown-first pack.
- Shell-only implementation: too fragile for atomic JSON state, locking and portable error handling.
- Hosted database: unnecessary for one local bounded mission and harmful to the no-account promise.
- One universal harness command: the four harnesses do not expose identical invocation or permission APIs.
- Vendored specialist library: conflicts with the provenance and upstream-dependency policy.

## Components

### Setup

Setup performs a read-only discovery pass, constructs an install plan, asks for approval where files would change, applies only the accepted operations and emits a receipt.

Copy mode also installs one receipt-owned `.the-loop/toolkit` containing the canonical
skill source, adapters, protocols, schemas, CLIs and standard-library runtime. This
keeps the installed target operable without the original checkout or network access.
Toolkit replacement and rollback use the same collision, digest and unchanged-output
rules as skill packages.

It must support:

- Repository-local installation into a target repository.
- User-level installation into a selected harness's documented directory.
- Dry-run and non-interactive modes.
- Copy mode as the universal fallback.
- Copy mode is the supported v0.1 shipping mode. Link planning fails closed whenever
  the portable package needs documentation-link transformation, which the shipping
  pack does; the lower-level link path remains covered only for unchanged synthetic
  packages with explicit same-filesystem proof.
- Uninstall from the recorded receipt without deleting files it did not create.

### Doctor

Doctor is read-only. It checks:

- Harness executable and version.
- Skill roots and precedence.
- Frontmatter validity.
- Duplicate names and shadowing.
- Adapter availability.
- File and directory permissions.
- Runtime version.
- Repository state directory safety.
- Kill-switch visibility.
- Complete 12-package identity bound to an unchanged Setup receipt, every installed
  package digest, and the full offline-toolkit digest.
- Optional typed behavior evidence when a library caller permits harness execution;
  verified evidence must match the exact portable invocation capability and the
  Doctor-derived environment fingerprint.

A discovery check is not a behavior check. Doctor reports these separately.

### Stage engine

The stage engine is primarily an instruction protocol. Each stage declares:

- Required inputs.
- Required capabilities.
- Required outputs.
- Done gate.
- Evidence types.
- Self-refutation question.
- Halt and escalation conditions.

It records a stage transition only after validating output and evidence references.

### Capability router

The router builds a catalog from discovered skills. It uses deterministic evidence first and descriptive similarity second.

Ranking inputs, in order:

1. User-pinned provider for the capability.
2. Explicit capability metadata recognized by THE LOOP.
3. Verified compatibility with the active harness and track.
4. Description match against the stage contract.
5. Behavior probe result and freshness.
6. Bundled fallback.

The router records the selected candidate, rejected candidates and reasons. A candidate cannot receive a verified score from its name alone.

### Run manager

The run manager owns state transitions, leases, budgets, heartbeat, kill-switch checks and audit events. Atomic writes use a temporary sibling file, `fsync` where supported, then replace. The digest-chained audit log is authoritative for run-control state. Every event stores the complete resulting run projection, nullable lease projection and nullable pending-operation projection. Before any mutation, the manager validates the chain and projection continuity and repairs stale or missing `run.json` and `lease.json` from the latest valid event; it never treats a conflicting mutable projection as the source of truth.

Side effects use an event-authoritative intent protocol. `operation_intended` is durable before callback invocation, records the exact reservation and prior rollback fields, identifies the exact semantic completion type and payload, and classifies the effect as local or external. Success appends that exact semantic event and clears the pending projection. An uncontrolled interruption retains the reservation and reconciles local work to `failed` or outward work to `waiting_external`, without replay. If the same live process proves a post-intent stop occurred before callback entry, `known_not_started` reconciliation rolls back only that recorded reservation before the halt; it is never inferred after a crash. While an intent is pending, mismatched or interleaved events fail chain validation; without a pending intent, ordinary domain/control events remain valid.

Grant mutation and official revocation use one stable per-grant cooperative lock across runs. Final validation plus intent is the shared critical section; durable revocation update plus audit is exclusive. Revocation is a one-way grant update followed by an idempotent per-run marker: retries use persisted revocation actor/time, verify a post-commit marker as the canonical head, repair a pre-append gap exactly once, and report `audit_pending` or `committed_state_unknown` without restoring authority. Namespace safety is separately bound to the device/inode identities of the project, `.the-loop` and configured state-root components and is rechecked at every public entry and side-effect boundary.

One writer holds one lease per run or declared parallel lane. Lease renewal never changes authority. An expired lease prevents mutation until the run is explicitly recovered.

Mission usage uses a per-stage attempt map. Active duration accrues with microsecond precision across complete validated lease/heartbeat intervals and stops at lease expiry; sub-second intervals are not discarded and unleased downtime never consumes duration. The runtime checkpoints time immediately before and after a callback so handled failures cannot discard elapsed leased time. Every callback reserves one mutation; only `local_write` to `repository` is local in v0.1, and every other action or destination is treated as external and reserves one external action. Cost limits, reservations and usage use canonical fixed-point decimal strings with at most six fractional digits. Exhausting any frozen budget records `budget_reached`, moves the run to `failed`, and uses terminal code `budget_reached:<field>`. A completion that reaches a limit atomically projects the failed state; a missing follow-up budget marker is repaired before the next exclusive command.

Each run-manager command captures an injected, timezone-aware UTC time for preflight; callback commands capture a second monotonic checkpoint at completion or handled failure. Exact expiry is expired. A callback completed at or after expiry preserves its semantic result but atomically fails the run and requires fresh-generation recovery. Naive, unparsable or reversed time blocks mutation rather than being normalized. Safety preflight order is authoritative-chain validation and repair, kill switch, clock, lease/owner/generation, authority, then budget.

### Evidence and issue ledger

Evidence records reference commands, files, checks or manual observations. They record outcome, timestamp, actor and reproducibility information. Large raw outputs remain in ignored local artifacts and are referenced by digest.

Issues are durable and stateful. Test opens issues, Resolve changes them, and Close refuses green while a blocking issue remains open.

### Kill switch

The external kill switch is a repository-local file at `.the-loop/STOP` by default. User config may add another absolute, user-controlled path. Before any mutation, the run manager checks all configured switches. A detected switch records `halted_kill_switch` and prevents new mutations. `kill_switch_detected` may be appended without a valid lease because stopping is a lease-independent safety-control action; it may reduce any recoverable nonterminal ready, active, waiting, blocked or failed run to the halted state, while complete and cancelled runs remain terminal.

Removing the file does not silently resume a run. Recovery requires an explicit resume action, a current grant and a fresh lease. If the stop halted a ready run before initial acquisition, recovery establishes generation zero from `previous_generation: null`; otherwise it increments the previous generation exactly once.

## Autonomy model

| Level | Local reversible work | Outward actions | Strategic expansion | Self-modification |
| --- | --- | --- | --- | --- |
| attended | propose and confirm meaningful gates | ask | ask | ask |
| bounded | allowed inside declared asset and budget | ask | ask | ask |
| scoped | only exact confirmed permissions | exact confirmed scope | exact confirmed scope | ask unless explicitly scoped |
| operational | broader named operations with expiry | named confirmed operations | ask | ask |
| full | broad within declared environment | allowed only as explicitly confirmed | allowed only as explicitly confirmed | allowed only as explicitly confirmed |

Every elevation requires typed confirmation. The grant is visibly warned at startup, in runtime status and in summaries. “Full” never disables audit logs, evidence, ownership, leases, the kill switch, failure reporting or permission visibility.

## Track contracts

### Code

- Verify live repository and remote state.
- Preserve unrelated changes.
- Use branch or equivalent isolation for unattended changes.
- Record build, lint, test and security evidence relevant to touched code.
- Keep deploy, merge, release and other outward actions behind authority checks.

### Non-code

- Record source quality and factuality requirements.
- Define the output format and review method before drafting.
- Capture link, quote, calculation or visual evidence appropriate to the asset.
- Treat sending, publishing and changing external systems as outward actions.

## Harness capability map

The map below is grounded in current official documentation and must be rechecked at release time.

| Capability | Codex | Claude Code | Kimi Code | OpenCode |
| --- | --- | --- | --- | --- |
| Portable package | `<name>/SKILL.md` | `<name>/SKILL.md` | `<name>/SKILL.md` | `<name>/SKILL.md` |
| Project portable root | `.agents/skills` | adapter to `.claude/skills` | `.agents/skills` | `.agents/skills` |
| Native project root | `.agents/skills` | `.claude/skills` | `.kimi-code/skills` | `.opencode/skills` |
| Required portable metadata | name, description | description; portable subset accepted | name and description recommended | name, description |
| Explicit invocation | skill selector or `$name` | `/name` | `/skill:name` | native `skill` tool |
| Permission concern | sandbox and tool approval | allowed tools and permission mode | approval mode and available tools | pattern-based `skill` and tool permissions |
| Delegation | capability-gated, API varies by host | subagents and forked skills available | Agent or AgentSwarm when available | task/subagent support varies by agent config |

Primary sources:

- [Codex skills](https://developers.openai.com/codex/skills)
- [Claude Code skills](https://code.claude.com/docs/en/skills)
- [Kimi Code skills](https://github.com/MoonshotAI/kimi-code/blob/main/docs/en/customization/skills.md)
- [OpenCode skills](https://opencode.ai/docs/skills)

Adapters must treat optional delegation as a capability, not a requirement. Sequential execution is always a valid fallback.

## Portable frontmatter

Core files use only the common subset:

```yaml
---
name: test
description: Prove an approved asset against its declared done gate and record surviving issues.
license: MIT
compatibility: Codex, Claude Code, Kimi Code and OpenCode
metadata:
  the-loop-capability: lifecycle.test
  the-loop-version: "0.1"
---
```

Metadata values remain strings for cross-harness compatibility. Harness-only fields belong in adapter-owned files and cannot alter normative behavior.

## Security and privacy

- No network access is required for core operation.
- Setup never reads or copies credential files.
- Logs redact environment values and secret-shaped strings.
- Paths stored in public examples are relative and synthetic.
- External commands use argument arrays, not interpolated shell strings.
- Config paths are canonicalised and checked against the declared project root before writes.
- Setup pins target and destination-component namespace identities, uses descriptor-relative mutations, and rejects symlink or replacement races before reporting success.
- Runtime state is ignored by Git by default.
- Release scanning covers tracked content and reachable Git history.
- An elevated authority grant is data, not a bypass around the harness's own permission model.

## Landing page integration

The landing page is an external launch asset, not part of the skill runtime or this repository's delivery ownership. Phase 1 stores its public-data contract and release gate. A separate dedicated session owns any website branch, implementation, tests, preview and deployment.

Live-state check on 2026-08-16 established:

- `/` returns 200 from Vercel.
- The site is static HTML and CSS.
- The title is “System Error Software — Products & digital systems”.
- The CSP includes `script-src 'none'`.
- `/the-loop` returns 404.

The external asset contract therefore requires a static v1 that preserves the existing CSP unless a separate security review and explicit approval authorise a change. The skill pack supplies a versioned launch manifest with approved facts and evidence links. It does not prescribe page code.

## Testing strategy

### Static validation

- Frontmatter schema and name checks.
- No absolute private paths or secret patterns.
- No broken relative references.
- JSON Schema validation for every fixture.
- Licence and provenance record coverage.

### Contract tests

- Route to a verified installed specialist.
- Reject a name-only false positive.
- Fall back when no specialist qualifies.
- Halt when evidence fails.
- Resolve an issue and rerun its regression check.
- Reject a stale or wrong-owner lease.
- Stop before mutation when the kill switch is present.
- Refuse silent authority elevation.
- Recover an interrupted run without claiming skipped checks.

### Harness tests

For each harness, test installation, discovery, explicit invocation, implicit trigger, permission denial, fallback behavior and truthful close. Tests run in isolated temporary repositories with synthetic skills.

### Evidence required from the separate landing-page delivery

- Static HTML validation and internal link check.
- Metadata, canonical and structured-data validation.
- CSP header regression check.
- Keyboard and focus traversal.
- Automated WCAG checks plus manual contrast and reduced-motion review.
- Screenshots at 360, 768, 1024 and 1440 CSS pixels.
- Primary and secondary CTA destination checks.

These checks are performed and owned by the dedicated landing-page session. THE LOOP release review verifies the returned evidence and the accuracy of product claims only.

## Observability

Core observability is local and user-owned:

- Append-only audit events.
- Current run state.
- Human-readable status and digest.
- Optional verbose command output stored locally.

No product telemetry is sent. Landing-page analytics remain absent unless separately approved with documented data fields, retention and legal basis.

## Failure behavior

- Corrupt state: preserve the file, report the parse error and require explicit recovery.
- Lease conflict: halt the losing writer and report current owner and expiry.
- Missing skill root: continue with bundled fallback if available and report the discovery gap.
- Permission denial: record denied, never convert it to failed or passed.
- Harness unavailable: label that harness unverified, do not block use on an installed supported harness.
- External state inaccessible: report the coverage gap and prevent claims that depend on it.
- Landing deployment failure: retain the previous production state and report the failed preview or deployment; never retry by weakening security headers.

## Assumption ledger

| Assumption | Class | Consequence if wrong |
| --- | --- | --- |
| Python 3.11 is an acceptable v0.1 prerequisite on macOS and Linux. | safe default | Replace utilities with a compiled binary or support an older Python after measurement. |
| `.agents/skills` is the best canonical repository root. | safe default | Change adapter manifests while retaining one canonical package source. |
| JSON is acceptable for human-edited config. | safe default | Add a parser adapter without changing normative schemas. |
| Claude-specific plugin packaging is optional in v0.1. | safe default | Add it as an adapter without changing portable skills. |
| The existing website repository can accept a static route without framework migration. | needs live verification | Re-plan only the landing implementation slice after inspecting its repository. |
