# Release handoff

[`launch-manifest.json`](launch-manifest.json) is the machine-readable interface
between the skill pack and the separately owned `systemerror.app/the-loop` landing
page. It remains explicitly `pre_release` and all harness behavior remains
blocked or unverified until the independent live matrix passes. The current dated
result is recorded in
[`live-compatibility-2026-08-16.md`](live-compatibility-2026-08-16.md): Setup and
Doctor passed on four of four target harnesses, while valid live behavior passed on
zero of four.

Changing repository visibility, creating a tag or release, or deploying the landing
page are separate outward actions that require explicit approval.

The canonical GitHub repository is currently private. The launch manifest must be
updated again after any later behavior rerun, tag, release or visibility change.

The publish candidate is also gated by
[`release-integrity.json`](../provenance/release-integrity.json), which pins every
file copied into the offline toolkit. It does not replace the separate live
four-harness evidence gate.
