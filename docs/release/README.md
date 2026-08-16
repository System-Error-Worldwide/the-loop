# Release handoff

[`launch-manifest.json`](launch-manifest.json) is the machine-readable interface
between the skill pack and the separately owned `systemerror.app/the-loop` landing
page. It remains explicitly `pre_release` and all harness behavior remains
`not_tested` until the independent live matrix has passed and its evidence is linked.

Changing repository visibility, creating a tag or release, or deploying the landing
page are separate outward actions that require explicit approval.

The publish candidate is also gated by
[`release-integrity.json`](../provenance/release-integrity.json), which pins every
file copied into the offline toolkit. It does not replace the separate live
four-harness evidence gate.
