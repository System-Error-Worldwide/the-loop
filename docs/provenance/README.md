# Phase 0 provenance audit

Status: complete for architecture and source triage. Release approval remains blocked by the human gates in [risks-and-gates.md](risks-and-gates.md).

This audit covers the 31 product candidates, shared protocol material, installer helpers, hooks, scripts and harness documentation relevant to the first public release.

- [Candidate inventory](candidate-inventory.md)
- [Per-skill records](skill-records.md)
- [Exact release integrity manifest](release-integrity.json)
- [Public and private boundary](public-private-boundary.md)
- [Risks and human gates](risks-and-gates.md)
- [Recommended v0.1 shipping manifest](v0.1-shipping-manifest.md)

## Audit method

The review inspected the current canonical revisions of two private System Error source vaults, their Git history, relevant helpers and the current official skill documentation for all four target harnesses. Exact-phrase web searches were used only as negative evidence and never treated as proof of authorship.

## Confidence scale

- High: direct Git history, canonical checksum and current source inspection agree.
- Medium: the source history is available, but the first import does not prove original authorship or a licence.
- Low: no candidate artifact exists or a source comparison is incomplete.
