# Phase 0 provenance audit

Status: complete for the v0.1 architecture, source triage and 31-skill shipping set.
Ongoing release controls are recorded in [risks-and-gates.md](risks-and-gates.md).

This audit covers all 31 shipped packages and their provenance universe, shared
protocol material, installer helpers, hooks, scripts and harness documentation. Every
package is usable as a harness-native instruction. The local runtime and Parallel lane
primitives add automation, but they do not divide the skill set into stronger and
weaker shipping classes.

- [Candidate inventory](candidate-inventory.md)
- [Per-skill records](skill-records.md)
- [Exact release integrity manifest](release-integrity.json)
- [Public and private boundary](public-private-boundary.md)
- [Risks and human gates](risks-and-gates.md)
- [Exact v0.1 shipping manifest](v0.1-shipping-manifest.md)

## Audit method

The review inspected the canonical revisions of two internal System Error source
vaults, their Git history, relevant helpers and official documentation for Codex,
Claude Code, Kimi Code, OpenCode and DeepSeek Harness. Exact-phrase web searches were
used only as negative evidence and never treated as proof of authorship.

## Confidence scale

- High: direct Git history, canonical checksum and current source inspection agree.
- Medium: the source history is available, but the first import does not prove original authorship or a licence.
- Low: no candidate artifact exists or a source comparison is incomplete.
