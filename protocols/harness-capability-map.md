# Harness capability map protocol

## Purpose

This protocol separates portable product behavior from host-specific discovery,
invocation, permission and delegation APIs. The canonical target harness identifiers
are `codex`, `claude_code`, `kimi_code` and `opencode`. Capability and support claims
are evidence-scoped and require release-time revalidation.

The official DeepSeek Harness 0.1.0-rc.6 is an evaluated candidate only. Its
documented `.agents/skills` root is format-compatible, but THE LOOP has no DSH
adapter, Setup/Doctor option or schema identifier. DSH is therefore outside the
canonical baseline and cannot receive a support claim from shared-root discovery.

## Baseline map

| Capability | Codex | Claude Code | Kimi Code | OpenCode |
| --- | --- | --- | --- | --- |
| Portable package | `<name>/SKILL.md` | `<name>/SKILL.md` | `<name>/SKILL.md` | `<name>/SKILL.md` |
| Portable project root | `.agents/skills` | adapter to `.claude/skills` | `.agents/skills` | `.agents/skills` |
| Native project root | `.agents/skills` | `.claude/skills` | `.kimi-code/skills` | `.opencode/skills` |
| Portable metadata | `name`, `description` | portable subset through adapter | `name`, `description` | `name`, `description` |
| Explicit invocation | skill selector or `$name` | `/name` | `/skill:name` | native `skill` tool |
| Permission surface | sandbox and tool approval | allowed tools and permission mode | approval mode and available tools | pattern-based skill and tool permissions |
| Delegation | optional, host capability | optional subagent capability | optional agent capability | optional task/subagent capability |

The baseline is a release input, not proof. A current compatibility record and harness-probe evidence determine actual status.

## Normative requirements

### Capability records

- **[CAP-001]** A harness record MUST use the canonical harness identifier and record installation, version, discovery status, behavior status, discovered skill roots, collisions, check time and optional evidence ID.
- **[CAP-002]** Discovery and behavior status MUST be exactly `verified`, `failed`, `denied` or `unverified`; absence MUST be represented separately by `installed: false`.
- **[CAP-003]** A `verified` status MUST link current evidence for the exact harness, version, installation scope and probe behavior.
- **[CAP-004]** A denied probe MUST remain `denied`, an unrun or inconclusive probe MUST remain `unverified`, and neither MUST be promoted to verified by documentation or name match.
- **[CAP-005]** Skill roots and collisions MUST be reported as observed without silently changing precedence, overwriting a package or deleting a collision.
- **[CAP-006]** Harness capability evidence MUST be rechecked for each release candidate before publishing compatibility claims.

### Portable package and adapter boundary

- **[CAP-010]** Common skill behavior MUST live in a standard `<name>/SKILL.md` package using portable `name` and `description` metadata.
- **[CAP-011]** A core skill MUST NOT depend on a private absolute path, host-only command, host-only frontmatter key or a delegation API.
- **[CAP-012]** Harness-only metadata, path discovery, invocation syntax and permission translation MUST remain in the thin adapter for that harness.
- **[CAP-013]** An adapter MUST preserve the common stage inputs, outputs, evidence, halt, authority, lease and failure contracts.
- **[CAP-014]** An adapter MUST NOT grant authority, weaken a permanent invariant or translate a denied host permission into success.
- **[CAP-015]** Optional delegation MUST be capability-gated; when absent or denied, the adapter MUST use sequential execution or report a named gap.
- **[CAP-016]** A missing host API MUST NOT be replaced with an invented command or undocumented permission bypass.

### Discovery and routing

- **[CAP-020]** Discovery MUST inspect the documented project roots for the active harness and MAY inspect configured user roots only within current authority.
- **[CAP-021]** Doctor output MUST distinguish not installed, not discoverable, collision, permission denied, behavior failed and behavior unverified.
- **[CAP-022]** A stage capability MUST use a namespaced identifier such as `lifecycle.test` and MUST declare requirements before provider selection.
- **[CAP-023]** Candidate ranking MUST consider, in order, a user pin, explicit recognized capability evidence, verified route harness and track compatibility, description match, the unique latest behavior observation matching the route capability and environment digest, then the bundled fallback.
- **[CAP-024]** A provider name, description match, or untyped capability-evidence string alone MUST NOT satisfy behavior proof or produce verified behavior status.
- **[CAP-025]** Disabled, denied, unavailable, incompatible, excluded, provenance-rejected or currently capability-scoped `behavior_status: failed` candidates MUST be removed or rejected with recorded reasons. A failure MAY be superseded only when the unique latest observation matching the route capability, harness, track, and environment digest is `passed`; machine validation MUST reject selected failures, missing or mismatched proof, same-time conflicts, and a latest matching denied, failed, or unverified outcome.
- **[CAP-026]** If no installed provider satisfies the contract, the complete bundled fallback MUST be selected without expanding scope or authority.
- **[CAP-027]** Route selection MUST record route capability, harness, track and environment digest, all candidates and typed observations, rejection reasons, selected provider and source, reason, verification time, and fallback reason in the route decision.
- **[CAP-028]** A provider failure MUST be recorded and MUST NOT silently promote another provider; rerouting requires a new decision under the same current authority and budget.
- **[CAP-029]** Installed upstream skills MAY be detected, linked or invoked when compatible, but vendor or community skill text MUST NOT be copied into the pack without provenance and licence approval.

### Behavior conformance

- **[CAP-030]** Each harness claimed as supported MUST be tested in an isolated synthetic repository for installation, discovery, explicit invocation, implicit trigger, permission denial, bundled fallback and truthful Close behavior.
- **[CAP-031]** Behavior-probe evidence MUST record harness version, installation scope, invoked capability, permission state, result, and evidence ID; its typed route observation MUST record capability, canonical harness, `code` or `noncode` track, environment digest, `passed`, `failed`, `denied`, or `unverified` outcome, observation time, and that evidence ID.
- **[CAP-032]** A verified harness MAY be usable when another target harness is unavailable; unavailable harnesses MUST be labeled unverified or failed without blocking the verified installed harness.
- **[CAP-033]** Compatibility claims MUST distinguish package discovery from successful behavior; discovery alone MUST NOT prove invocation, permission handling or stage conformance.
- **[CAP-034]** A harness adapter MUST pass the same run-state, lease, authority, kill-switch, pending-operation, issue and evidence scenarios as every other adapter.
- **[CAP-035]** Any skipped, denied or environment-limited probe MUST remain visible in the compatibility matrix and release evidence.

### Capability status publication

- **[CAP-040]** Public compatibility output MUST identify the release version, harness version or range, tested environment, evidence date and status basis.
- **[CAP-041]** Public status MUST distinguish installed package, runtime-backed, contract only, evaluated, adapter-pending and live-unverified states and MUST NOT imply multi-harness behavior when only package shape or a shared root was inspected.
- **[CAP-042]** Capability-map changes MUST update their evidence references and MUST be reviewed for changes to host documentation, permission behavior and discovery paths.
- **[CAP-043]** Raw skill prompt content, secrets and private environment identifiers MUST NOT be stored in the capability map or route record.

## Failure and halt behavior

Missing, denied, stale or inconclusive capability proof retains a failed, denied or unverified status under CAP-002 through CAP-006. Unsupported host behavior uses sequential fallback or a named gap under CAP-015 and CAP-016. No qualified installed provider selects the bundled fallback under CAP-026; provider failure is recorded before any reroute under CAP-028.

## Evidence

Conformance includes conflicting skill names, multiple roots, missing harnesses, denied discovery, denied invocation, stale probe evidence, optional delegation absent, provider failure, reroute, bundled fallback and a release matrix with one unverified harness.

## Cross-references

| Protocol range | Source contract |
| --- | --- |
| CAP-001–006 | [`config.schema.json`](../schemas/config.schema.json), [Backend harness status](../docs/specs/backend-schema.md#harness-status) |
| CAP-010–016 | [TDD harness capability map](../docs/specs/tdd.md#harness-capability-map), [Workflow dispatch](workflow-dispatch.md) |
| CAP-020–029 | [`route.schema.json`](../schemas/route.schema.json), [Skill routing](skill-routing.md) |
| CAP-030–043 | [TDD harness conformance](../docs/specs/tdd.md#harness-tests), [PRD NFR-001 and NFR-010](../docs/specs/prd.md#non-functional-requirements) |
