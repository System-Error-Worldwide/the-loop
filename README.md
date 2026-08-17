# SYSTEM ERROR'S THE LOOP

An autonomous agentic skill pack for Codex, Claude Code, Kimi Code, and OpenCode.
The official DeepSeek Harness is under isolated compatibility evaluation.

Created and maintained by Moses Mawila through System Error Worldwide.

> **The full 31-skill pack is included and installable.** Setup installs the skills
> with their offline toolkit, Doctor verifies the resulting pack, and bundled
> fallbacks keep every capability available when no qualified specialist is detected.
> Harness support remains evidence-gated: installation compatibility alone is not
> presented as proof of live behavior.

## What THE LOOP is

THE LOOP is designed to run one evidence-led lifecycle:

`Strategize -> Spec-pack -> Build -> Test <-> Resolve -> Close`

It detects installed skills by capability and behavior evidence, selects a qualified
specialist when one is available, and retains a bundled fallback for every packaged
capability. The bounded Auto mode drives one declared asset to green or to a visible
gate. Parallel, Cloud, Endless, Watch, Control, Autonomy, skill planning and creation,
portfolio review, grounding, quality and handoff utilities are included in this
candidate. Expansion packages must reuse, not bypass, the kernel's state, lease,
authority, evidence, budget and kill-switch contracts.

## Current repository contents

- A completed [provenance and public-boundary review](PROVENANCE.md).
- The six-document [product specification pack](docs/specs/README.md).
- Ten normative [shared protocol contracts](protocols/README.md).
- Versioned JSON Schemas for config, run state, leases, grants, routing, evidence,
  issues, install receipts, and audit events.
- A Python standard-library runtime kernel for validated state, bounded missions,
  leases, authority, budgets, recovery, and append-only audit history.
- Thirty-one portable `SKILL.md` packages with bundled fallback contracts.
- Safe Setup and read-only Doctor commands with receipts and rollback.
- Four thin harness adapters that preserve host permission denial.
- Synthetic code and non-code examples plus a 4-by-12 contract matrix.
- Adversarial unit and contract tests for the current release candidate.

The exact 31-package candidate and its maturity classes are listed in the
[shipping manifest](docs/provenance/v0.1-shipping-manifest.md).

## Quickstart

Prerequisites: Python 3.9 or newer and at least one target harness executable.
The default installation is repository-local and uses copies. It installs all 31
skills plus a namespaced offline toolkit at `.the-loop/toolkit`, so the target does
not depend on the checkout or a network connection after installation.

```sh
git clone https://github.com/System-Error-Worldwide/the-loop.git
cd the-loop
mkdir -p /path/to/project

# 1. Read-only plan. Choose codex, claude_code, kimi_code, or opencode.
python3 scripts/the_loop_setup.py \
  --target-root /path/to/project \
  --harness codex \
  --json

# 2. Apply exactly that collision-free plan and write a private receipt.
python3 scripts/the_loop_setup.py \
  --target-root /path/to/project \
  --harness codex \
  --apply \
  --actor local-user \
  --source-version 0.1.0 \
  --json

# 3. Read-only diagnosis from the installed offline toolkit.
python3 /path/to/project/.the-loop/toolkit/scripts/the_loop_doctor.py \
  --project-root /path/to/project \
  --json
```

The canonical remote is private during pre-release. The clone command becomes the
public quickstart only after an approved visibility change; until then it requires
authorised repository access.

Setup refuses a differing pre-existing skill unless its exact destination is repeated
with `--approve-destination`. Doctor can exit `1` while discovery is valid but live
behavior is still unverified; its JSON report distinguishes that warning from a
blocked installation. Setup and Doctor do not send telemetry or capture prompts.

To remove only unchanged files owned by one receipt:

```sh
python3 /path/to/project/.the-loop/toolkit/scripts/the_loop_setup.py \
  --rollback-receipt /path/to/project/.the-loop/installs/RECEIPT_ID.json \
  --target-root /path/to/project \
  --json
```

Changed installed files are preserved and reported as a partial rollback.

For a user-level install, use the same dry-run and apply sequence with
`--scope user --target-root "$HOME"`. Setup chooses one preferred documented root
per harness: the shared `.agents/skills` root where supported, otherwise the
harness-specific root. It does not copy the same package into every search root.

### Invoke the installed skill

| Harness | Explicit v0.1 invocation |
| --- | --- |
| Codex | Select or mention `$the-loop` |
| Claude Code | Run `/the-loop` |
| Kimi Code | Run `/skill:the-loop` |
| OpenCode | Ask the agent to load `skill(the-loop)` |

Start with attended `the-loop`. Use `the-loop-auto` only for one declared asset with
an exact done gate, frozen budgets, visible authority and a working kill switch.

| Package class | Current maturity |
| --- | --- |
| Setup, Doctor, Loop, Auto, lifecycle, feeders and Close | Runtime-backed bounded kernel and full fallback contracts |
| Parallel | Portable package plus tested lane primitives; live harness behavior remains unverified |
| Cloud, Endless, Watch, Control and Autonomy | Packaged fallback contracts; supervisor/control integrations remain pre-release |
| Skill Planner, Skill Creator, Portfolio Review, grounding, quality and handoff utilities | Packaged portable fallback contracts; live routing evidence remains unverified |

Shipping a package means the public skill is installed, integrity-pinned and covered
by repository contracts. It does not upgrade an untested runtime mode or harness path
to supported status. The dependency order remains documented in the
[engineering plan](docs/specs/engineering-plan.md#phase-4-full-product-extensions).

### Contract conformance

The deterministic runner installs and diagnoses all 31 packages in four synthetic
projects, validates the 12 locked scenario contracts per implemented adapter, and
fails on any altered artifact, fallback body, support component, or safety assertion. Its report names
expected artifacts separately from the checks it actually performed. It never invokes
a model and therefore does not claim that those scenarios passed live behavior:

```sh
mkdir -p /tmp/the-loop-contract-check
python3 scripts/run_conformance.py \
  --project-root /tmp/the-loop-contract-check
```

See the [synthetic code example](examples/code/README.md) and
[synthetic non-code example](examples/noncode/README.md).

## Current compatibility evidence

The frozen 2026-08-16 candidate passed Setup and Doctor on all four target harnesses.
Live behavior passed on none, so all four remain unsupported for release purposes.

| Harness | Setup and Doctor | Live behavior | Blocking evidence |
| --- | --- | --- | --- |
| Codex 0.144.1 | passed | blocked | The host loaded private global context during an implicit probe, so the result is not privacy-clean evidence. |
| Claude Code 2.1.221 | passed | blocked | Authentication is required before model execution. |
| Kimi Code 0.36.1 | passed | blocked | Authentication and a configured model are required before model execution. |
| OpenCode 1.15.1 | passed | blocked | An isolated no-skill smoke test fails with `InstanceRef not provided`, so the failure is not THE LOOP-specific. |

Compatibility is a release target, not a current support claim. A harness is marked
supported only after installation, discovery, invocation, denial, fallback, and close
behavior pass the release matrix. See the
[dated compatibility report](docs/release/live-compatibility-2026-08-16.md).

The official DeepSeek Harness `0.1.0-rc.6` was also installed in a disposable home.
Its keyless headless profile and documented `.agents/skills` search path were verified,
and the 31-package pack was copied into an isolated project through that shared root.
THE LOOP does not yet ship a DSH adapter, so Setup and Doctor reject `dsh` as an
unsupported harness. Authenticated behavior through a DeepSeek model on OpenRouter is
still pending. This is evaluation evidence, not a fifth support claim. See the
[2026-08-17 compatibility update](docs/release/live-compatibility-2026-08-17.md).

## Safety model

- Outward actions, strategic expansion, and self-modification require approval by
  default.
- Any elevated authority must identify its actor, scope, confirmation time, expiry,
  and reversal path.
- Audit logging, evidence requirements, run ownership, leases, visible authority,
  truthful failure reporting, and the external kill switch remain mandatory at every
  autonomy level.
- Auto is one bounded mission. The Endless package is included, but its supervisor
  runtime remains ineligible until bounded Auto, state, leases, heartbeat,
  permissions, budgets, kill-switch recovery and empty-queue behavior are proven in
  live harnesses.

## Repository map

- [Provenance policy](PROVENANCE.md)
- [v0.1 shipping manifest](docs/provenance/v0.1-shipping-manifest.md)
- [Phase 1 specification pack](docs/specs/README.md)
- [Shared protocol contracts](protocols/README.md)
- [Schemas](schemas/README.md)
- [Contributing](CONTRIBUTING.md)
- [Security policy](SECURITY.md)

## Development validation

```sh
python3 scripts/validate_repository.py
python3 scripts/validate_protocols.py
python3 -m unittest discover -s tests -p 'test_*.py'
python3 scripts/run_conformance.py --project-root /tmp/the-loop-contract-check
```

The repository validator scans the public tree, Git index, reachable history, commit
metadata, and symlink targets for blocked private material and credential patterns.

## Release gates

A tagged release requires the installable 31-package manifest, passing behavior
evidence on all four implemented adapters, zero blocking issues, a clean provenance scan, and an independent
final review. The separate `systemerror.app/the-loop` landing page is a launch asset,
not part of this repository's implementation scope. It currently returns `404` and
therefore remains a public-launch blocker.

## Licence and security

All clean-room work authored for this repository, including both
`system-error-original` and `system-error-rewrite` files, is released under the
[MIT License](LICENSE). The classification records lineage, not different ownership.
Third-party dependencies remain subject to their own licences and are not copied into
this repository without an approved provenance record. Report vulnerabilities through
the process in [SECURITY.md](SECURITY.md); do not publish credentials or private
infrastructure details in an issue.
