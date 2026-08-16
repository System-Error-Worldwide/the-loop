# Provenance policy

SYSTEM ERROR'S THE LOOP is a clean public product. Its architecture was informed by private operational experience, but private source files are not a shipping source tree.

Every skill and protocol must pass these gates before release:

1. Trace its local history and record a content checksum.
2. Compare its purpose and text against known upstream sources.
3. Establish a compatible licence for every included file.
4. Audit for private paths, people, credentials, infrastructure, customers, incidents and vertical intelligence.
5. Write a clean, harness-neutral System Error implementation when reuse is not proven safe.
6. Test discovery, triggering, behavior and failure reporting in Codex, Claude Code, Kimi Code and OpenCode.
7. Obtain an independent final review.

## Classification

- `system-error-original`: designed and written cleanly for this repository.
- `system-error-rewrite`: preserves an abstract capability but does not copy the audited private artifact.
- `upstream-dependency`: detected and invoked from its maintained upstream source; never vendored here.
- `excluded`: not shipped because provenance, licence or privacy requirements are not satisfied.

Rewording does not remove licence obligations. A missing licence is a failed reuse gate, not permission to copy.

## Current decision

No audited private skill or helper is approved for verbatim inclusion. Existing candidates either require a clean System Error rewrite or remain excluded. The exact v0.1 set is recorded in [docs/provenance/v0.1-shipping-manifest.md](docs/provenance/v0.1-shipping-manifest.md).

Original System Error work created for this repository is licensed under MIT. That repository licence does not change the rights or reuse status of audited private, vendor or community artifacts.

## Evidence handling

The public record uses redacted source labels, commit identifiers and SHA-256 checksums. Private paths, repository URLs, incident details and infrastructure identifiers stay in the private audit record.
