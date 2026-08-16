# SYSTEM ERROR'S THE LOOP

An autonomous agentic skill pack for Codex, Claude Code, Kimi Code, and OpenCode.

Created and maintained by Moses Mawila through System Error Worldwide.

> **Pre-release development repository.** The provenance review, specification pack,
> shared protocols, schemas, and bounded runtime kernel are present. Installable skill
> packages, harness adapters, and four-harness release evidence are still in progress.
> There is no supported installation command or tagged release yet.

## What THE LOOP is

THE LOOP is designed to run one evidence-led lifecycle:

`Strategize -> Spec-pack -> Build -> Test <-> Resolve -> Close`

It detects installed skills by capability and behavior evidence, selects a qualified
specialist when one is available, and retains a complete bundled fallback for every
core stage. The bounded Auto mode drives one declared asset to green or to a visible
gate. Parallel, Cloud, and Endless are later layers and cannot bypass the same state,
lease, authority, evidence, budget, and kill-switch contracts.

## Current repository contents

- A completed [provenance and public-boundary review](PROVENANCE.md).
- The six-document [product specification pack](docs/specs/README.md).
- Ten normative [shared protocol contracts](protocols/README.md).
- Versioned JSON Schemas for config, run state, leases, grants, routing, evidence,
  issues, install receipts, and audit events.
- A Python standard-library runtime kernel for validated state, bounded missions,
  leases, authority, budgets, recovery, and append-only audit history.
- Adversarial unit and contract tests for the current kernel.

The intended v0.1 skill packages are listed in the
[shipping manifest](docs/provenance/v0.1-shipping-manifest.md). They are not yet
present as installable `SKILL.md` packages.

## Target compatibility

| Harness | Target discovery | Release evidence |
| --- | --- | --- |
| Codex | `.agents/skills` | Not yet completed |
| Claude Code | Thin adapter over the portable package | Not yet completed |
| Kimi Code | `.agents/skills` or `.kimi-code/skills` | Not yet completed |
| OpenCode | `.agents/skills` or `.opencode/skills` | Not yet completed |

Compatibility is a release target, not a current support claim. A harness is marked
supported only after installation, discovery, invocation, denial, fallback, and close
behavior pass the release matrix.

## Safety model

- Outward actions, strategic expansion, and self-modification require approval by
  default.
- Any elevated authority must identify its actor, scope, confirmation time, expiry,
  and reversal path.
- Audit logging, evidence requirements, run ownership, leases, visible authority,
  truthful failure reporting, and the external kill switch remain mandatory at every
  autonomy level.
- Auto is one bounded mission. Endless is explicitly deferred until bounded Auto,
  state, leases, heartbeat, permissions, budgets, and kill-switch recovery are proven.

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
```

The repository validator scans the public tree, Git index, reachable history, commit
metadata, and symlink targets for blocked private material and credential patterns.

## Release gates

A tagged release requires the installable v0.1 manifest, passing behavior evidence on
all four harnesses, zero blocking issues, a clean provenance scan, and an independent
final review. The separate `systemerror.app/the-loop` landing page is a launch asset,
not part of this repository's implementation scope.

## Licence and security

Original work in this repository is released under the [MIT License](LICENSE).
Third-party dependencies remain subject to their own licences and are not copied into
this repository without an approved provenance record. Report vulnerabilities through
the process in [SECURITY.md](SECURITY.md); do not publish credentials or private
infrastructure details in an issue.
