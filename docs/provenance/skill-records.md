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
public capability had no predecessor artifact. All 31 public packages ship in v0.1;
the status column records that release decision.

## Records

| Candidate | Evidence | Public classification | Current artifact decision | v0.1 | Confidence |
| --- | --- | --- | --- | --- | --- |
| `the-loop-setup` | none | system-error-original | Design from public spec. | ship | High |
| `the-loop-doctor` | none | system-error-original | Design from public spec. | ship | High |
| `the-loop-skill-planner` | none | system-error-original | Designed from the public spec. | ship | High |
| `the-loop-skill-creator` | Official creator skills exist in target harnesses. | upstream-dependency | Detect and invoke upstream; independently write only the orchestration wrapper and fallback. | ship | High |
| `the-loop-autonomy` | none | system-error-original | Designed from the public protocol and revocation contracts. | ship | High |
| `the-loop-control` | none | system-error-original | Designed from the public runtime control contract. | ship | High |
| `the-loop-watch` | none; internal watcher helpers were audited. | system-error-original | Exclude internal helpers; use the clean public watcher contract. | ship | High |
| `the-loop` | Vault A, first recorded `3653462` (2026-07-02), SHA-256 `b12ea063143475eef21b24a47237a4f0e1512ff778c1c3333482abc7314386c4` | system-error-rewrite | Exclude verbatim; private paths, registry assumptions and harness coupling. | ship | High |
| `the-loop-auto` | Vault A, first recorded `3653462` (2026-07-02), SHA-256 `7982ffbf73288cd923085574beba2cdd68482c9b5f9cbe5f0589587e137acd65` | system-error-rewrite | Exclude verbatim; private watcher, state and incident assumptions. | ship | High |
| `the-loop-parallel` | Vault A, first recorded `7b7e1db` (2026-08-12), SHA-256 `56517198496a6bd3f8545502a3dce2a697a07850149e7d02197c1274b6fb848d` | system-error-rewrite | Exclude verbatim; use the clean public version with lane primitives. | ship | High |
| `the-loop-cloud` | Vault A, first recorded `ce9edf7` (2026-07-12), SHA-256 `623aa47eb829d04e0f5db94912bac3d1d106b7ab1beeaf37de83bc9d9b64753e` | system-error-rewrite | Exclude verbatim; use a generic version without internal remote infrastructure details. | ship | High |
| `the-loop-endless` | none | system-error-original | Designed from the public safety kernel. | ship | High |
| `strategize` | Vault A, first recorded `3653462` (2026-07-02), SHA-256 `41d6ca7d8b379f9cedd9b3d93d7d892ff7f87c2b43ae29f6e9af637fcb2d691f` | system-error-rewrite | Exclude verbatim; rewrite its output contract. | ship | High |
| `spec-pack` | Vault A, first recorded `7a6a965` (2026-08-04), SHA-256 `7447c4985aaf2252675854f724330d8d3ee1a8584347834283cb7e9344250a0f` | system-error-rewrite | Exclude verbatim; rewrite templates and gating behavior. | ship | High |
| `build` | Vault A, first recorded `3653462` (2026-07-02), SHA-256 `00d1e9d657239d8491710f5c4318446a5c9afa19df97b41d69d61722639ad0b9` | system-error-rewrite | Exclude verbatim; rewrite slice and evidence contract. | ship | High |
| `test` | Vault A, first recorded `3653462` (2026-07-02), SHA-256 `179f0bdfea316e65bbdfb674ff6b3719368e7b4fdf6d463f10e50d39b6bcf9e0` | system-error-rewrite | Exclude verbatim; rewrite evidence and issue behavior. | ship | High |
| `resolve` | Vault A, first recorded `3653462` (2026-07-02), SHA-256 `2cd0d687e1d1a15ad6fba73bf213c68bca10bcaf7cb8feed5249b8db2d1b1c7f` | system-error-rewrite | Exclude verbatim; rewrite ledger behavior. | ship | High |
| `health-check` | Vault A, first recorded `3653462` (2026-07-02), SHA-256 `60717d813edc00188a80b561c684a93517dd3ecc6360cde971b2f0bd405c922c` | system-error-rewrite | Exclude verbatim; rewrite reactive feeder contract. | ship | High |
| `audit` | Vault A, first recorded `3653462` (2026-07-02), SHA-256 `08625e151708df6c058ad5b4592b25bcb89d3a40b85c1e9a4e653ec353edfbc5` | system-error-rewrite | Exclude verbatim; rewrite proactive feeder contract. | ship | High |
| `portfolio-review` | Vault A, first recorded `6692289` (2026-07-13), SHA-256 `5935acfed6a35bcfbce9d728ac853064c2f2e14438f0cb351e478f32f8d460b4` | system-error-rewrite | Exclude verbatim; use a generic public version without internal portfolio logic. | ship | High |
| `live-state-preflight` | none | system-error-original | Designed from public, configurable providers. | ship | High |
| `idea-to-brief` | Vault B, first recorded `5182386` (2026-08-02), SHA-256 `9696b0a90eee39b9ce8fddd343ffb9b7239091382e4541574e0ec2950f8c9724` | system-error-rewrite | Exclude verbatim; use a neutral public fallback. | ship | High |
| `stack-summary` | Vault B, imported in initial sync `8b561c3` (2026-04-20), SHA-256 `0769b6926a6f7d2df1ca9604c13fe4ef68dba14ed21a543d23bec18fc19c88ee` | system-error-rewrite | Exclude the predecessor because original authorship and licence are not proven; use the separately authored clean fallback. | ship | Medium |
| `bootstrap-agent-context` | none | system-error-original | Designed from the common harness capability map. | ship | High |
| `pre-commit-review` | Vault B, imported in initial sync `8b561c3` (2026-04-20), SHA-256 `aa15576bf3fe645f6d049a0e6ab7c7d906d831c80ee29fd4d334e49659d516b6` | system-error-rewrite | Exclude the predecessor because original authorship and licence are not proven; use the separately authored clean fallback. | ship | Medium |
| `feature-tracker` | Vault B, first recorded `af74d63` (2026-07-11), SHA-256 `6cf0f1f314457e3ad22362b4f8333f021c8cb70ea814dd2a7f362b8d852cc78e` | system-error-rewrite | Exclude verbatim; use a clean public version. | ship | Medium |
| `decision-log` | Vault B, imported in initial sync `8b561c3` (2026-04-20), SHA-256 `f2d4991f441841b5b89219661962fa4063ee6e5bb1ab8064098f78c8882c99a3` | system-error-rewrite | Exclude the predecessor because original authorship and licence are not proven; use the separately authored clean fallback. | ship | Medium |
| `handoff` | Vault B, first recorded `0e9cb47` (2026-07-21), SHA-256 `bc9ce63ba1a500db76a1b0e46c58c4c2dc3d3d385fcc673ba10113f0ecc8a6c5` | system-error-rewrite | Exclude verbatim; use a portable version without internal memory or tool assumptions. | ship | High |
| `retrospective` | Vault B, imported in initial sync `8b561c3` (2026-04-20), SHA-256 `f49a7b634d9a477f798e01eda6063cc0a6d59733d8c15a6689579e435cc07d26` | system-error-rewrite | Exclude the predecessor because original authorship and licence are not proven; use the separately authored clean fallback. | ship | Medium |
| `session-summary` | Vault B, imported in initial sync `8b561c3` (2026-04-20), SHA-256 `c2ea0d63717e9eb695f4b6e685b88bb98edcfb82c2826a97b40c4b4d30db581e` | system-error-rewrite | Exclude the predecessor because original authorship and licence are not proven; use the separately authored clean fallback. | ship | Medium |
| `close` | Vault B, first recorded `e2c9cd5` (2026-08-09), SHA-256 `b74110f10051032ccd2110f90ed461f065e7e1fe960058e59dca5d834a7bf84a` | system-error-rewrite | Exclude verbatim; private memory, registry and hook assumptions. | ship | High |

## Upstream comparison result

Current official documentation confirms that all five target harnesses discover
`SKILL.md` packages but use different paths, invocation syntax and permission
behavior. Format compatibility does not grant rights to copy vendor skill text.
Vendor and community skills remain external dependencies unless their exact source
and licence pass review.

Exact-phrase searches for several weak-history Vault B artifacts returned no clear public source match. This lowers the chance of a direct public copy but does not prove System Error authorship, so the licence gate remains failed.

## v0.1 shipping files

These hashes cover all 31 clean public package files. The final column records the
shipping check for the exact bytes, separate from dated environment reports.

| Skill | Public file | SHA-256 | Licence | Authoring commit | Shipping evidence |
| --- | --- | --- | --- | --- | --- |
| `the-loop-setup` | `.agents/skills/the-loop-setup/SKILL.md` | `d6ede7fb7dde565d4985629d5cba333bafa4161aa82f9b9c73a44219e35f6b8c` | MIT | `7e31448` | passed: hash and provenance verified |
| `the-loop-doctor` | `.agents/skills/the-loop-doctor/SKILL.md` | `c276f1dc363dfb2959621566449448aaa23a1b27219494a157078c202cba0978` | MIT | `7e31448` | passed: hash and provenance verified |
| `the-loop` | `.agents/skills/the-loop/SKILL.md` | `4d515e6f8b45530e15361d36c1b075e2a21cee95150442bf553c4fbecdcb4c7a` | MIT | `cdd7618` | passed: hash and provenance verified |
| `the-loop-auto` | `.agents/skills/the-loop-auto/SKILL.md` | `ee84ba5ccdc7f81743f025ef9cb6cd6a0b9f69527a9f3b14e8d4631abd86ea6a` | MIT | `cdd7618` | passed: hash and provenance verified |
| `strategize` | `.agents/skills/strategize/SKILL.md` | `8d63ea644f9555ef031485a755a8a1d10ca4edd926916e9d5147336019b0df89` | MIT | `cdd7618` | passed: hash and provenance verified |
| `spec-pack` | `.agents/skills/spec-pack/SKILL.md` | `c27d65b1e9c4cdbb42897df1c5c05dfb170e4cda05be344fbd2dd7e6e20172f4` | MIT | `cdd7618` | passed: hash and provenance verified |
| `build` | `.agents/skills/build/SKILL.md` | `99cd3b065f237f749a7f1b5665629bababf45676092ad11f6575bd3de7fca74f` | MIT | `cdd7618` | passed: hash and provenance verified |
| `test` | `.agents/skills/test/SKILL.md` | `8287f86bc0b1b353bc50e5cced764ef3b796c7f91db095c93a1494da54f29cf6` | MIT | `cdd7618` | passed: hash and provenance verified |
| `resolve` | `.agents/skills/resolve/SKILL.md` | `cf0ea1fe673a54b2b9d48bc86ad9a85005c40b53767b3532b4dd5769430354d0` | MIT | `cdd7618` | passed: hash and provenance verified |
| `health-check` | `.agents/skills/health-check/SKILL.md` | `ebcaa59bde6b1b7341db436b63343cfde028935f3969c622ad3e0918cd0c9692` | MIT | `cdd7618` | passed: hash and provenance verified |
| `audit` | `.agents/skills/audit/SKILL.md` | `41fcff5ece6850e93234cd459d84a6d1f53901656c99919761c1e52f51a05de5` | MIT | `cdd7618` | passed: hash and provenance verified |
| `close` | `.agents/skills/close/SKILL.md` | `ab867a3b7c7474ba77d73c5d3153852e468b574696be95d5b7f026c8510836b2` | MIT | `cdd7618` | passed: hash and provenance verified |
| `the-loop-parallel` | `.agents/skills/the-loop-parallel/SKILL.md` | `f007cf98af1313c7e4a19b7c490a8e0e74e3ffd29c6e8fb9bb56c08569ac1ded` | MIT | `f9ff8b4` | passed: hash and provenance verified |
| `the-loop-skill-planner` | `.agents/skills/the-loop-skill-planner/SKILL.md` | `1e2badc6652d0b8ced2a64664b735411fe63f01ed7bc1abb4cd8aa83dd2b3754` | MIT | `f9ff8b4` | passed: hash and provenance verified |
| `the-loop-skill-creator` | `.agents/skills/the-loop-skill-creator/SKILL.md` | `dc326ad5a8671839125b4c71c0cd53e6024a3c557fed333309b67655b646df91` | MIT | `f9ff8b4` | passed: hash and provenance verified |
| `the-loop-autonomy` | `.agents/skills/the-loop-autonomy/SKILL.md` | `5f4b4906d7d566a036f105b1355489278146a7849f5f4f69601f76c5a0810ccd` | MIT | `f9ff8b4` | passed: hash and provenance verified |
| `the-loop-control` | `.agents/skills/the-loop-control/SKILL.md` | `5ce8df763befeb1030ad1df6b5c4bd05339977efff81db1696c27b6609d759e9` | MIT | `f9ff8b4` | passed: hash and provenance verified |
| `the-loop-watch` | `.agents/skills/the-loop-watch/SKILL.md` | `7968f6ae27ff83127ee3fefd5c51a7d712c9d3fa73565c3685869d1ff5569c0f` | MIT | `f9ff8b4` | passed: hash and provenance verified |
| `the-loop-cloud` | `.agents/skills/the-loop-cloud/SKILL.md` | `c18e10b426e27870ffbd1fb2a50ecc3eafd5a864fb4750ef017246b88ee68225` | MIT | `f9ff8b4` | passed: hash and provenance verified |
| `the-loop-endless` | `.agents/skills/the-loop-endless/SKILL.md` | `045047f8f74136bc784e0cc57a73900b51cf9f90ac95dbe8932ca5dd0ac76aeb` | MIT | `f9ff8b4` | passed: hash and provenance verified |
| `portfolio-review` | `.agents/skills/portfolio-review/SKILL.md` | `d1d85c84d6cb0ff65ea15eec58384870b52a25e192a7543f65bb477432dfc572` | MIT | `f9ff8b4` | passed: hash and provenance verified |
| `live-state-preflight` | `.agents/skills/live-state-preflight/SKILL.md` | `50b05ef703a38fef3bee64c84cc2ab036a970c9917552727fa3d597fcf5c21f5` | MIT | `f9ff8b4` | passed: hash and provenance verified |
| `idea-to-brief` | `.agents/skills/idea-to-brief/SKILL.md` | `9cd16299e50898bd3ea904be502c96561f3eeeca03849e58e986bee13f22f01d` | MIT | `f9ff8b4` | passed: hash and provenance verified |
| `stack-summary` | `.agents/skills/stack-summary/SKILL.md` | `75fab99e6cf35f320278da2963d2bd2dbeca5729868fcb36739733e8dd3007ad` | MIT | `f9ff8b4` | passed: hash and provenance verified |
| `bootstrap-agent-context` | `.agents/skills/bootstrap-agent-context/SKILL.md` | `266ea0817ae8e12bb9814e7db86d8bf052bc3e048f0ea1a75bbba32075284ab3` | MIT | `f9ff8b4` | passed: hash and provenance verified |
| `pre-commit-review` | `.agents/skills/pre-commit-review/SKILL.md` | `b07c62c024436c92c78c95ee6c6e4e23e1b35de99cadd4b01fd00b7784bebed0` | MIT | `f9ff8b4` | passed: hash and provenance verified |
| `feature-tracker` | `.agents/skills/feature-tracker/SKILL.md` | `67f54ebe326ded1c1a9e0450d97adb34855fd0ac3efbc3058282e396bcb0d3b5` | MIT | `f9ff8b4` | passed: hash and provenance verified |
| `decision-log` | `.agents/skills/decision-log/SKILL.md` | `58916f5376965164d6502c8311ea18721cfb8d813c2e22b3ac81daa8f28339d8` | MIT | `f9ff8b4` | passed: hash and provenance verified |
| `handoff` | `.agents/skills/handoff/SKILL.md` | `d623a16571e056f1ed6ec2bdb87ad011ac38e851b8cc61efdb4378e192644a93` | MIT | `f9ff8b4` | passed: hash and provenance verified |
| `retrospective` | `.agents/skills/retrospective/SKILL.md` | `ba84f2c57a5ec20acae6bd1088afec7f91be18f125e6f84395ac64356c29e659` | MIT | `f9ff8b4` | passed: hash and provenance verified |
| `session-summary` | `.agents/skills/session-summary/SKILL.md` | `4dfbcbeb966f89a1707f7025b62d966134f7327b562600128706dd7eed0255e5` | MIT | `f9ff8b4` | passed: hash and provenance verified |

Any skill edit changes its recorded hash and reopens the file-level shipping check.
