# Release evidence

This directory carries the machine-readable handoff between the private pre-release
repository and the separately owned `systemerror.app/the-loop` landing page.

The current candidate contains all 31 public skill packages. The release manifest
separates the 12-package bounded kernel, the Parallel runtime preview and 18 included
fallback contracts whose live behavior remains unverified. Four harness adapters are
implemented. The official DeepSeek Harness is recorded separately as an evaluated
candidate because THE LOOP does not yet provide its adapter, Setup path or Doctor path.

- [`launch-manifest.json`](launch-manifest.json) is the current source of public release
  facts and limitations.
- [`live-compatibility-2026-08-16.md`](live-compatibility-2026-08-16.md) is frozen
  historical evidence for commit `8029ff05fd2720627fe3137cbce01ad98150152d` and its
  12-package, four-adapter matrix.
- [`live-compatibility-2026-08-17.md`](live-compatibility-2026-08-17.md) records the
  31-package baseline and the bounded DeepSeek Harness evaluation.

Changing repository visibility, creating a tag or release, promoting an evaluated
harness to the compatibility matrix, or deploying the landing page remains an explicit
human gate.
