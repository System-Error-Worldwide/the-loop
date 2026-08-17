# Release evidence

This directory carries the machine-readable handoff between the v0.1 repository and
the separately owned `systemerror.app/the-loop` landing page.

v0.1 contains all 31 portable skills and first-class adapters for Codex, Claude Code,
Kimi Code, OpenCode and DeepSeek Harness. The toolkit adds deterministic installation,
diagnosis and runtime automation without changing which skills ship.

- [`launch-manifest.json`](launch-manifest.json) is the current source of public release
  facts and limitations.
- [`live-compatibility-2026-08-16.md`](live-compatibility-2026-08-16.md) is frozen
  historical evidence for commit `8029ff05fd2720627fe3137cbce01ad98150152d` and its
  12-package, four-adapter matrix.
- [`live-compatibility-2026-08-17.md`](live-compatibility-2026-08-17.md) records an
  early isolated DeepSeek Harness evaluation that informed the fifth adapter.

The dated reports document the environments tested at that time. They do not override
the current five-adapter shipping manifest.
