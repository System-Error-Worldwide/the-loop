# Per-skill provenance records

## Evidence legend

- Vault A contains the private Loop workflow sources.
- Vault B contains the private general skill sources.
- `none` means no candidate artifact was found in the audited roots.
- A checksum identifies the reviewed canonical content without publishing it.
- Existing artifacts have no applicable declared shipping licence.

`system-error-rewrite` identifies a clean public implementation of a capability from a
private System Error predecessor. It remains System Error-authored work; the label does
not imply third-party ownership or verbatim reuse. `system-error-original` means the
public capability had no predecessor artifact. The final column records bounded v0.1
scope only, not the complete product roadmap.

## Records

| Candidate | Evidence | Public classification | Current artifact decision | v0.1 scope | Confidence |
| --- | --- | --- | --- | --- | --- |
| `the-loop-setup` | none | system-error-original | Design from public spec. | include | High |
| `the-loop-doctor` | none | system-error-original | Design from public spec. | include | High |
| `the-loop-skill-planner` | none | system-error-original | Build from the public spec in the post-v0.1 roadmap. | planned extension | High |
| `the-loop-skill-creator` | Official creator skills exist in target harnesses. | upstream-dependency | Detect and invoke upstream; independently write only the orchestration wrapper and fallback contract. | planned extension | High |
| `the-loop-autonomy` | none | system-error-original | Build from the public spec after the protocol and revocation gates; v0.1 ships its protocol layer. | planned extension | High |
| `the-loop-control` | none | system-error-original | Build from the public spec after the runtime control plane is live-proven. | planned extension | High |
| `the-loop-watch` | none; private watcher helpers were audited. | system-error-original | Exclude private helpers; build from the public watcher contract. | planned extension | High |
| `the-loop` | Vault A, first recorded `3653462` (2026-07-02), SHA-256 `b12ea063143475eef21b24a47237a4f0e1512ff778c1c3333482abc7314386c4` | system-error-rewrite | Exclude verbatim; private paths, registry assumptions and harness coupling. | include | High |
| `the-loop-auto` | Vault A, first recorded `3653462` (2026-07-02), SHA-256 `7982ffbf73288cd923085574beba2cdd68482c9b5f9cbe5f0589587e137acd65` | system-error-rewrite | Exclude verbatim; private watcher, state and incident assumptions. | include | High |
| `the-loop-parallel` | Vault A, first recorded `7b7e1db` (2026-08-12), SHA-256 `56517198496a6bd3f8545502a3dce2a697a07850149e7d02197c1274b6fb848d` | system-error-rewrite | Exclude verbatim; build the public version after lane ownership and isolation are proven. | planned extension | High |
| `the-loop-cloud` | Vault A, first recorded `ce9edf7` (2026-07-12), SHA-256 `623aa47eb829d04e0f5db94912bac3d1d106b7ab1beeaf37de83bc9d9b64753e` | system-error-rewrite | Exclude verbatim; build a generic version without private remote infrastructure details. | planned extension | High |
| `the-loop-endless` | none | system-error-original | Design only after the v0.1 safety kernel is proven live. | planned extension | High |
| `strategize` | Vault A, first recorded `3653462` (2026-07-02), SHA-256 `41d6ca7d8b379f9cedd9b3d93d7d892ff7f87c2b43ae29f6e9af637fcb2d691f` | system-error-rewrite | Exclude verbatim; rewrite its output contract. | include | High |
| `spec-pack` | Vault A, first recorded `7a6a965` (2026-08-04), SHA-256 `7447c4985aaf2252675854f724330d8d3ee1a8584347834283cb7e9344250a0f` | system-error-rewrite | Exclude verbatim; rewrite templates and gating behavior. | include | High |
| `build` | Vault A, first recorded `3653462` (2026-07-02), SHA-256 `00d1e9d657239d8491710f5c4318446a5c9afa19df97b41d69d61722639ad0b9` | system-error-rewrite | Exclude verbatim; rewrite slice and evidence contract. | include | High |
| `test` | Vault A, first recorded `3653462` (2026-07-02), SHA-256 `179f0bdfea316e65bbdfb674ff6b3719368e7b4fdf6d463f10e50d39b6bcf9e0` | system-error-rewrite | Exclude verbatim; rewrite evidence and issue behavior. | include | High |
| `resolve` | Vault A, first recorded `3653462` (2026-07-02), SHA-256 `2cd0d687e1d1a15ad6fba73bf213c68bca10bcaf7cb8feed5249b8db2d1b1c7f` | system-error-rewrite | Exclude verbatim; rewrite ledger behavior. | include | High |
| `health-check` | Vault A, first recorded `3653462` (2026-07-02), SHA-256 `60717d813edc00188a80b561c684a93517dd3ecc6360cde971b2f0bd405c922c` | system-error-rewrite | Exclude verbatim; rewrite reactive feeder contract. | include | High |
| `audit` | Vault A, first recorded `3653462` (2026-07-02), SHA-256 `08625e151708df6c058ad5b4592b25bcb89d3a40b85c1e9a4e653ec353edfbc5` | system-error-rewrite | Exclude verbatim; rewrite proactive feeder contract. | include | High |
| `portfolio-review` | Vault A, first recorded `6692289` (2026-07-13), SHA-256 `5935acfed6a35bcfbce9d728ac853064c2f2e14438f0cb351e478f32f8d460b4` | system-error-rewrite | Exclude verbatim; build a generic public version without private portfolio logic. | planned extension | High |
| `live-state-preflight` | none | system-error-original | Build from public, configurable providers. | planned extension | High |
| `idea-to-brief` | Vault B, first recorded `5182386` (2026-08-02), SHA-256 `9696b0a90eee39b9ce8fddd343ffb9b7239091382e4541574e0ec2950f8c9724` | system-error-rewrite | Exclude verbatim; write a neutral public fallback. | planned extension | High |
| `stack-summary` | Vault B, imported in initial sync `8b561c3` (2026-04-20), SHA-256 `0769b6926a6f7d2df1ca9604c13fe4ef68dba14ed21a543d23bec18fc19c88ee` | system-error-rewrite | Exclude current artifact because original authorship and licence are not proven; write a clean fallback if included. | planned extension | Medium |
| `bootstrap-agent-context` | none | system-error-original | Build from the common harness capability map. | planned extension | High |
| `pre-commit-review` | Vault B, imported in initial sync `8b561c3` (2026-04-20), SHA-256 `aa15576bf3fe645f6d049a0e6ab7c7d906d831c80ee29fd4d334e49659d516b6` | system-error-rewrite | Exclude current artifact because original authorship and licence are not proven; write a clean fallback if included. | planned extension | Medium |
| `feature-tracker` | Vault B, first recorded `af74d63` (2026-07-11), SHA-256 `6cf0f1f314457e3ad22362b4f8333f021c8cb70ea814dd2a7f362b8d852cc78e` | system-error-rewrite | Exclude verbatim; write a clean public version from the contract. | planned extension | Medium |
| `decision-log` | Vault B, imported in initial sync `8b561c3` (2026-04-20), SHA-256 `f2d4991f441841b5b89219661962fa4063ee6e5bb1ab8064098f78c8882c99a3` | system-error-rewrite | Exclude current artifact because original authorship and licence are not proven; write a clean fallback if included. | planned extension | Medium |
| `handoff` | Vault B, first recorded `0e9cb47` (2026-07-21), SHA-256 `bc9ce63ba1a500db76a1b0e46c58c4c2dc3d3d385fcc673ba10113f0ecc8a6c5` | system-error-rewrite | Exclude verbatim; build a portable version without private memory or tool assumptions. | planned extension | High |
| `retrospective` | Vault B, imported in initial sync `8b561c3` (2026-04-20), SHA-256 `f49a7b634d9a477f798e01eda6063cc0a6d59733d8c15a6689579e435cc07d26` | system-error-rewrite | Exclude current artifact because original authorship and licence are not proven; write a clean fallback if included. | planned extension | Medium |
| `session-summary` | Vault B, imported in initial sync `8b561c3` (2026-04-20), SHA-256 `c2ea0d63717e9eb695f4b6e685b88bb98edcfb82c2826a97b40c4b4d30db581e` | system-error-rewrite | Exclude current artifact because original authorship and licence are not proven; write a clean fallback if included. | planned extension | Medium |
| `close` | Vault B, first recorded `e2c9cd5` (2026-08-09), SHA-256 `b74110f10051032ccd2110f90ed461f065e7e1fe960058e59dca5d834a7bf84a` | system-error-rewrite | Exclude verbatim; private memory, registry and hook assumptions. | include | High |

## Upstream comparison result

Current official documentation confirms that all four target harnesses discover `SKILL.md` packages but use different paths, invocation syntax and permission behavior. That format compatibility does not grant rights to copy any vendor skill. Vendor and community skills remain external dependencies unless their exact source and licence pass review.

Exact-phrase searches for several weak-history Vault B artifacts returned no clear public source match. This lowers the chance of a direct public copy but does not prove System Error authorship, so the licence gate remains failed.

## v0.1 release-candidate files

These hashes cover the clean-room release-candidate files authored in this repository.
`partial` means installation and discovery passed but the behavior matrix did not;
`blocked` means valid live behavior evidence was not completed. Neither satisfies a
support claim or tagged-release gate.

| Skill | Public file | SHA-256 | Licence | Authoring commit | Live evidence |
| --- | --- | --- | --- | --- | --- |
| `the-loop-setup` | `.agents/skills/the-loop-setup/SKILL.md` | `6ef33ec021ae3bd38667b0feb5f8bb088c1443c24be10c642948a4e3e68f9e06` | MIT | `7e31448` | partial: 4/4 install; [matrix](../release/live-compatibility-2026-08-16.md) |
| `the-loop-doctor` | `.agents/skills/the-loop-doctor/SKILL.md` | `00f4afd969aa263bc248cbac2a21be406b1dbf0ea6d2d67f6fae357e67076bc3` | MIT | `7e31448` | partial: 4/4 discovery; [matrix](../release/live-compatibility-2026-08-16.md) |
| `the-loop` | `.agents/skills/the-loop/SKILL.md` | `402c254ca886757b952fa5a0bc7f147847f949f3ab81c840fcc6f6682ad6ad3e` | MIT | `cdd7618` | blocked: live behavior incomplete; [matrix](../release/live-compatibility-2026-08-16.md) |
| `the-loop-auto` | `.agents/skills/the-loop-auto/SKILL.md` | `fa752bf5002e576a285d87da5317411d524dee02952be1b87c2029c88b0e5806` | MIT | `cdd7618` | blocked: live behavior incomplete; [matrix](../release/live-compatibility-2026-08-16.md) |
| `strategize` | `.agents/skills/strategize/SKILL.md` | `ee0b715247d2c8ae82c534d9e0ab97e3bb4f5b0b1046aecd6d06a164748f1398` | MIT | `cdd7618` | blocked: live behavior incomplete; [matrix](../release/live-compatibility-2026-08-16.md) |
| `spec-pack` | `.agents/skills/spec-pack/SKILL.md` | `456d26c104e571daccb23ef31230d978082f13636683c87030eae55e5457fadf` | MIT | `cdd7618` | blocked: live behavior incomplete; [matrix](../release/live-compatibility-2026-08-16.md) |
| `build` | `.agents/skills/build/SKILL.md` | `b85ce34b49405c1920f00c272ee88a3c288bdf7b0ed9027c3cd2954cf2bc6974` | MIT | `cdd7618` | blocked: live behavior incomplete; [matrix](../release/live-compatibility-2026-08-16.md) |
| `test` | `.agents/skills/test/SKILL.md` | `ff405eb608a670b585445bc367afb2888c2de03afbe0aaaea4cd25ce780ef1a1` | MIT | `cdd7618` | blocked: live behavior incomplete; [matrix](../release/live-compatibility-2026-08-16.md) |
| `resolve` | `.agents/skills/resolve/SKILL.md` | `8d5d4e257314f32b5f0b366eb5f94d88e2b770ed06be15a1a1259c960965fd26` | MIT | `cdd7618` | blocked: live behavior incomplete; [matrix](../release/live-compatibility-2026-08-16.md) |
| `health-check` | `.agents/skills/health-check/SKILL.md` | `9dbb14a24ec80572869684afd3aba8ca59fe756530c2f3d7cf3be64d19876aac` | MIT | `cdd7618` | blocked: live behavior incomplete; [matrix](../release/live-compatibility-2026-08-16.md) |
| `audit` | `.agents/skills/audit/SKILL.md` | `71444831f1530287ccdc29c3300468d11d84dc9233553ec221f2f36f18645bcf` | MIT | `cdd7618` | blocked: live behavior incomplete; [matrix](../release/live-compatibility-2026-08-16.md) |
| `close` | `.agents/skills/close/SKILL.md` | `c94672867df06abcb5d6d102f600bb2f5e0c2823bab74da12ae96d7697f8836b` | MIT | `cdd7618` | blocked: live behavior incomplete; [matrix](../release/live-compatibility-2026-08-16.md) |

## Remaining release update

Replace a `partial` or `blocked` cell only with reviewed passing evidence for the exact
harness, version, installation scope and behavior matrix. Any skill edit changes its
hash and reopens this gate.
