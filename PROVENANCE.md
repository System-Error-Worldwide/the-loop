# Provenance policy

SYSTEM ERROR'S THE LOOP is a clean-room pre-release candidate intended for public
release. Its architecture was informed by private operational experience, but private
source files are not a shipping source tree. The canonical remote currently remains
private.

Every skill and protocol must pass these gates before a support claim or tagged release:

1. Trace its local history and record a content checksum.
2. Compare its purpose and text against known upstream sources.
3. Establish a compatible licence for every included file.
4. Audit for private paths, people, credentials, infrastructure, customers, incidents and vertical intelligence.
5. Write a clean, harness-neutral System Error implementation when reuse is not proven safe.
6. Test discovery, triggering, behavior and failure reporting in Codex, Claude Code, Kimi Code and OpenCode.
7. Obtain an independent final review.

## Classification

- `system-error-original`: new System Error work designed and written for this public repository without a predecessor artifact.
- `system-error-rewrite`: new public System Error work that implements a capability previously present in a private System Error predecessor, without copying that private artifact.
- `upstream-dependency`: detected and invoked from its maintained upstream source; never vendored here.
- `excluded`: not shipped because provenance, licence or privacy requirements are not satisfied.

Both `system-error-original` and `system-error-rewrite` are System Error-authored public
work. The distinction records lineage and the clean-public-boundary method; it does not
mean that a rewrite is third-party work, has weaker ownership, or is a lightly reworded
copy. Where the predecessor's original authorship or licence cannot be proven, that
predecessor remains excluded even if a separate public fallback is later written.

Rewording does not remove licence obligations. A missing licence is a failed reuse gate, not permission to copy.

## Current decision

No audited private skill or helper is approved for verbatim inclusion. All 31 public
packages are included in the current private, untagged candidate: 9 are
`system-error-original`, 21 are clean `system-error-rewrite` implementations of
capabilities with private System Error predecessors, and 1 is an
`upstream-dependency` orchestration wrapper. The classification records lineage, not
package maturity. The exact package, maturity and checksum set is recorded in
[docs/provenance/v0.1-shipping-manifest.md](docs/provenance/v0.1-shipping-manifest.md)
and [docs/provenance/skill-records.md](docs/provenance/skill-records.md).

The 12-package bounded kernel is runtime-backed. `the-loop-parallel` additionally has
repository-tested lane primitives. The other 18 expansion packages are portable
fallback contracts whose live routing and harness behavior remain unverified. Four
harness adapters are implemented, but none has approved live behavior evidence. The
official DeepSeek Harness 0.1.0-rc.6 has been evaluated in isolation; THE LOOP does
not yet provide its adapter or Setup/Doctor support, so it is not a fifth target or
support claim.

Original System Error work created for this repository is licensed under MIT. That repository licence does not change the rights or reuse status of audited private, vendor or community artifacts.

## Evidence handling

The public record uses redacted source labels, commit identifiers and SHA-256 checksums. Private paths, repository URLs, incident details and infrastructure identifiers stay in the private audit record.
