# Per-skill provenance records

## Evidence legend

- Vault A contains the private Loop workflow sources.
- Vault B contains the private general skill sources.
- `none` means no candidate artifact was found in the audited roots.
- A checksum identifies the reviewed canonical content without publishing it.
- Existing artifacts have no applicable declared shipping licence.

## Records

| Candidate | Evidence | Public classification | Current artifact decision | v0.1 | Confidence |
| --- | --- | --- | --- | --- | --- |
| `the-loop-setup` | none | system-error-original | Design from public spec. | include | High |
| `the-loop-doctor` | none | system-error-original | Design from public spec. | include | High |
| `the-loop-skill-planner` | none | system-error-original | Design later from public spec. | defer | High |
| `the-loop-skill-creator` | Official creator skills exist in target harnesses. | upstream-dependency | Detect and invoke upstream; independently write only the orchestration wrapper and fallback contract. | defer | High |
| `the-loop-autonomy` | none | system-error-original | Design later from public spec; v0.1 ships only its protocol layer. | defer | High |
| `the-loop-control` | none | system-error-original | Design later from public spec. | defer | High |
| `the-loop-watch` | none; private watcher helpers were audited. | system-error-original | Exclude private helpers; design later from public contract. | defer | High |
| `the-loop` | Vault A, first recorded `3653462` (2026-07-02), SHA-256 `b12ea063143475eef21b24a47237a4f0e1512ff778c1c3333482abc7314386c4` | system-error-rewrite | Exclude verbatim; private paths, registry assumptions and harness coupling. | include | High |
| `the-loop-auto` | Vault A, first recorded `3653462` (2026-07-02), SHA-256 `7982ffbf73288cd923085574beba2cdd68482c9b5f9cbe5f0589587e137acd65` | system-error-rewrite | Exclude verbatim; private watcher, state and incident assumptions. | include | High |
| `the-loop-parallel` | Vault A, first recorded `7b7e1db` (2026-08-12), SHA-256 `56517198496a6bd3f8545502a3dce2a697a07850149e7d02197c1274b6fb848d` | system-error-rewrite | Exclude verbatim; private orchestration and harness coupling. | defer | High |
| `the-loop-cloud` | Vault A, first recorded `ce9edf7` (2026-07-12), SHA-256 `623aa47eb829d04e0f5db94912bac3d1d106b7ab1beeaf37de83bc9d9b64753e` | system-error-rewrite | Exclude verbatim; private remote infrastructure details. | defer | High |
| `the-loop-endless` | none | system-error-original | Design only after the v0.1 safety kernel is proven. | defer | High |
| `strategize` | Vault A, first recorded `3653462` (2026-07-02), SHA-256 `41d6ca7d8b379f9cedd9b3d93d7d892ff7f87c2b43ae29f6e9af637fcb2d691f` | system-error-rewrite | Exclude verbatim; rewrite its output contract. | include | High |
| `spec-pack` | Vault A, first recorded `7a6a965` (2026-08-04), SHA-256 `7447c4985aaf2252675854f724330d8d3ee1a8584347834283cb7e9344250a0f` | system-error-rewrite | Exclude verbatim; rewrite templates and gating behavior. | include | High |
| `build` | Vault A, first recorded `3653462` (2026-07-02), SHA-256 `00d1e9d657239d8491710f5c4318446a5c9afa19df97b41d69d61722639ad0b9` | system-error-rewrite | Exclude verbatim; rewrite slice and evidence contract. | include | High |
| `test` | Vault A, first recorded `3653462` (2026-07-02), SHA-256 `179f0bdfea316e65bbdfb674ff6b3719368e7b4fdf6d463f10e50d39b6bcf9e0` | system-error-rewrite | Exclude verbatim; rewrite evidence and issue behavior. | include | High |
| `resolve` | Vault A, first recorded `3653462` (2026-07-02), SHA-256 `2cd0d687e1d1a15ad6fba73bf213c68bca10bcaf7cb8feed5249b8db2d1b1c7f` | system-error-rewrite | Exclude verbatim; rewrite ledger behavior. | include | High |
| `health-check` | Vault A, first recorded `3653462` (2026-07-02), SHA-256 `60717d813edc00188a80b561c684a93517dd3ecc6360cde971b2f0bd405c922c` | system-error-rewrite | Exclude verbatim; rewrite reactive feeder contract. | include | High |
| `audit` | Vault A, first recorded `3653462` (2026-07-02), SHA-256 `08625e151708df6c058ad5b4592b25bcb89d3a40b85c1e9a4e653ec353edfbc5` | system-error-rewrite | Exclude verbatim; rewrite proactive feeder contract. | include | High |
| `portfolio-review` | Vault A, first recorded `6692289` (2026-07-13), SHA-256 `5935acfed6a35bcfbce9d728ac853064c2f2e14438f0cb351e478f32f8d460b4` | system-error-rewrite | Exclude verbatim; contains private portfolio logic. | defer | High |
| `live-state-preflight` | none | system-error-original | Design later from public, configurable providers. | defer | High |
| `idea-to-brief` | Vault B, first recorded `5182386` (2026-08-02), SHA-256 `9696b0a90eee39b9ce8fddd343ffb9b7239091382e4541574e0ec2950f8c9724` | system-error-rewrite | Exclude verbatim; write a neutral later fallback. | defer | High |
| `stack-summary` | Vault B, imported in initial sync `8b561c3` (2026-04-20), SHA-256 `0769b6926a6f7d2df1ca9604c13fe4ef68dba14ed21a543d23bec18fc19c88ee` | system-error-rewrite | Exclude current artifact because original authorship and licence are not proven. | defer | Medium |
| `bootstrap-agent-context` | none | system-error-original | Design later from the common harness capability map. | defer | High |
| `pre-commit-review` | Vault B, imported in initial sync `8b561c3` (2026-04-20), SHA-256 `aa15576bf3fe645f6d049a0e6ab7c7d906d831c80ee29fd4d334e49659d516b6` | system-error-rewrite | Exclude current artifact because original authorship and licence are not proven. | defer | Medium |
| `feature-tracker` | Vault B, first recorded `af74d63` (2026-07-11), SHA-256 `6cf0f1f314457e3ad22362b4f8333f021c8cb70ea814dd2a7f362b8d852cc78e` | system-error-rewrite | Exclude verbatim; history does not establish a reusable licence. | defer | Medium |
| `decision-log` | Vault B, imported in initial sync `8b561c3` (2026-04-20), SHA-256 `f2d4991f441841b5b89219661962fa4063ee6e5bb1ab8064098f78c8882c99a3` | system-error-rewrite | Exclude current artifact because original authorship and licence are not proven. | defer | Medium |
| `handoff` | Vault B, first recorded `0e9cb47` (2026-07-21), SHA-256 `bc9ce63ba1a500db76a1b0e46c58c4c2dc3d3d385fcc673ba10113f0ecc8a6c5` | system-error-rewrite | Exclude verbatim; private memory and tool assumptions. | defer | High |
| `retrospective` | Vault B, imported in initial sync `8b561c3` (2026-04-20), SHA-256 `f49a7b634d9a477f798e01eda6063cc0a6d59733d8c15a6689579e435cc07d26` | system-error-rewrite | Exclude current artifact because original authorship and licence are not proven. | defer | Medium |
| `session-summary` | Vault B, imported in initial sync `8b561c3` (2026-04-20), SHA-256 `c2ea0d63717e9eb695f4b6e685b88bb98edcfb82c2826a97b40c4b4d30db581e` | system-error-rewrite | Exclude current artifact because original authorship and licence are not proven. | defer | Medium |
| `close` | Vault B, first recorded `e2c9cd5` (2026-08-09), SHA-256 `b74110f10051032ccd2110f90ed461f065e7e1fe960058e59dca5d834a7bf84a` | system-error-rewrite | Exclude verbatim; private memory, registry and hook assumptions. | include | High |

## Upstream comparison result

Current official documentation confirms that all four target harnesses discover `SKILL.md` packages but use different paths, invocation syntax and permission behavior. That format compatibility does not grant rights to copy any vendor skill. Vendor and community skills remain external dependencies unless their exact source and licence pass review.

Exact-phrase searches for several weak-history Vault B artifacts returned no clear public source match. This lowers the chance of a direct public copy but does not prove System Error authorship, so the licence gate remains failed.

## Final public shipping files

These hashes cover the clean public files authored in this repository. `pending` means
the file has passed repository contract tests but does not yet have the independent
live four-harness evidence required for a support claim or tagged release.

| Skill | Public file | SHA-256 | Licence | Authoring commit | Live evidence |
| --- | --- | --- | --- | --- | --- |
| `the-loop-setup` | `.agents/skills/the-loop-setup/SKILL.md` | `f8cd5c3268c030af944e90d33d8f4f5a5c0f5aedee9c9068a4df5cb8f6edf252` | MIT | `7e31448` | pending |
| `the-loop-doctor` | `.agents/skills/the-loop-doctor/SKILL.md` | `41beae44d5125f479b1df84f1903f915744b624c96577cb0f98d1167b152f71f` | MIT | `7e31448` | pending |
| `the-loop` | `.agents/skills/the-loop/SKILL.md` | `4ff795a26344ed87d3f898dde03e368cef4b6d647f51748c178ee78821a34c63` | MIT | `cdd7618` | pending |
| `the-loop-auto` | `.agents/skills/the-loop-auto/SKILL.md` | `61dfbe23d159cba3ffe24296d4d2c052f06aebafc0867c2aeffcc432cc966b7c` | MIT | `cdd7618` | pending |
| `strategize` | `.agents/skills/strategize/SKILL.md` | `e5149b34bbac58225e6b66b1505c437289b3ecef46bbdb8c130fc88b50e02956` | MIT | `cdd7618` | pending |
| `spec-pack` | `.agents/skills/spec-pack/SKILL.md` | `a1dd759812d4d1d7280d6868c4de409a5615b8a05710c1e91caefa2913f229a4` | MIT | `cdd7618` | pending |
| `build` | `.agents/skills/build/SKILL.md` | `82f00e41b70abbb4b3ab286dd08574eac0d3fac8c2b06b5822e25d810f50d8bd` | MIT | `cdd7618` | pending |
| `test` | `.agents/skills/test/SKILL.md` | `fc1525473a9d0a950842177244d9cdfad54d7a8b464dbf91928dc3ea7a01c32c` | MIT | `cdd7618` | pending |
| `resolve` | `.agents/skills/resolve/SKILL.md` | `8bd9d8e0ce8c1b80ba87b3b9a03b9b316f118e5d1f5bed39c15e8223dd2e1a3b` | MIT | `cdd7618` | pending |
| `health-check` | `.agents/skills/health-check/SKILL.md` | `e5b047147102c5cfbd9880aa43393c1f0c260e3990c92d04f3c09404fa0acf66` | MIT | `cdd7618` | pending |
| `audit` | `.agents/skills/audit/SKILL.md` | `acfa739d7b5dabc28bfe2a808656fe7759f232bdc830712889cb5a5fca1b6b66` | MIT | `cdd7618` | pending |
| `close` | `.agents/skills/close/SKILL.md` | `a4ab055d42a65bc7c89a02f145b2bc96a735391fdc1e6f2865c75aa255732ec9` | MIT | `cdd7618` | pending |

## Remaining release update

Replace each `pending` cell only with the reviewed evidence reference for the exact
harness, version, installation scope and behavior matrix. Any skill edit changes its
hash and reopens this gate.
