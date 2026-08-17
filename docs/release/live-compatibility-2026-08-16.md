# Live compatibility report: 2026-08-16

> Historical frozen report for commit `8029ff05fd2720627fe3137cbce01ad98150152d`.
> The current 31-package and DeepSeek Harness evaluation is recorded in the
> [2026-08-17 update](live-compatibility-2026-08-17.md).

## Verdict

Frozen candidate `8029ff05fd2720627fe3137cbce01ad98150152d` is installable but
does not support a public compatibility claim. Setup and Doctor passed on all four
target harnesses. Live behavior passed on none.

## Matrix

| Harness | Version | Setup and Doctor | Live behavior | Result |
| --- | --- | --- | --- | --- |
| Codex | 0.144.1 | passed | blocked | `BLOCKED_ISOLATION` |
| Claude Code | 2.1.221 | passed | blocked | `BLOCKED_AUTH` |
| Kimi Code | 0.36.1 | passed | blocked | `BLOCKED_AUTH` |
| OpenCode | 1.15.1 | passed | blocked | `BLOCKED_RUNTIME` |

Each dry run exited successfully without changing its clean project. Each apply
completed, installed all 12 skills plus the offline toolkit, and remained bound to the
frozen source. Doctor reported a complete pack, verified discovery of all 12 skills
and unverified behavior. Its warning exit was therefore truthful.

## Behavior boundaries

- Codex explicit loading returned the project contract, but that result is not valid
  privacy-clean proof. During implicit routing the host loaded private global
  instruction and memory context into the provider despite project-only controls.
  Further Codex provider calls stopped. No credentials were observed.
- Claude Code discovered all 12 project skills but stopped before model execution
  because the harness was not logged in.
- Kimi Code installed and discovered the pack but stopped before model execution
  because no authenticated default model was configured.
- OpenCode failed explicit, implicit, denial and no-tool isolated smoke tests with
  `InstanceRef not provided`. The no-tool failure shows that this is not specific to
  THE LOOP. A first non-isolated smoke also wrote one harness error log to the host's
  normal user-data directory; the isolated rerun confined later state.

All denial canaries remained absent. No live provider-failure fallback, attended
lifecycle, Auto, recovery or Close mission completed.

## Scenario accounting

The locked live matrix contains 48 scenarios:

- 8 passed Setup/Doctor checks.
- 11 behavior checks blocked before valid evidence.
- 29 behavior checks not tested because their prerequisite harness gate failed.

Deterministic contract conformance is not counted as live behavior evidence.

## Required closure

- Codex: prove a genuinely isolated authenticated execution path before another
  provider probe.
- Claude Code: authenticate interactively, then rerun the bounded matrix.
- Kimi Code: authenticate and configure the approved default model, then rerun.
- OpenCode: resolve the local runtime failure and first pass an isolated no-skill
  smoke test.

Until all required scenarios pass and independent review accepts their evidence, the
repository remains a private pre-release and every harness remains unsupported.
