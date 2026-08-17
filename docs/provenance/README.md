# Phase 0 provenance audit

Status: complete for architecture, source triage and the installable 31-package
private candidate. Live behavior evidence for the four implemented adapters,
independent approval, public visibility, tag/release and the separate landing-page
delivery remain pending under [risks-and-gates.md](risks-and-gates.md).

This audit covers all 31 included packages and their provenance universe, shared
protocol material, installer helpers, hooks, scripts and harness documentation. The
maturity split is 12 runtime-backed kernel packages, `the-loop-parallel` with
repository-tested lane primitives, and 18 portable contract-only packages whose live
behavior is unverified. Inclusion does not imply equal runtime maturity or harness
support.

- [Candidate inventory](candidate-inventory.md)
- [Per-skill records](skill-records.md)
- [Exact release integrity manifest](release-integrity.json)
- [Public and private boundary](public-private-boundary.md)
- [Risks and human gates](risks-and-gates.md)
- [Exact v0.1 pre-release shipping manifest](v0.1-shipping-manifest.md)

## Audit method

The review inspected the current canonical revisions of two private System Error source vaults, their Git history, relevant helpers and the current official skill documentation for all four implemented target adapters. Exact-phrase web searches were used only as negative evidence and never treated as proof of authorship. The official DeepSeek Harness 0.1.0-rc.6 was separately evaluated, but no DSH adapter or Setup/Doctor support exists in this candidate.

## Confidence scale

- High: direct Git history, canonical checksum and current source inspection agree.
- Medium: the source history is available, but the first import does not prove original authorship or a licence.
- Low: no candidate artifact exists or a source comparison is incomplete.
