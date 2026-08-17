# Compatibility update: 2026-08-17

## Scope

This historical report records the 31-package baseline at code revision
`bff48338e74c59b8b2a1c558a4ccd3a3d5f8bc5e` and a bounded evaluation of the official
DeepSeek Harness. It does not replace the frozen four-adapter behavior matrix from
[2026-08-16](live-compatibility-2026-08-16.md).

## Adapter context at the time

At the time, the implemented adapter set was Codex, Claude Code, Kimi Code and
OpenCode. The DSH work below was exploratory evidence that informed the first-class
DeepSeek Harness adapter shipped in v0.1. It is not the current support matrix.

## DeepSeek Harness evaluation

| Check | Result | Boundary |
| --- | --- | --- |
| Source | `deepseek-ai/deepseek-harness` at `47f943859bef60e4160492346772ded9b24f765a` | Official upstream clone inspected read-only |
| Installed CLI | `@deepseek-ai/dsh` `0.1.0-rc.6` | Installed under a disposable directory with lifecycle scripts disabled |
| Isolated profile | passed | Fresh `HOME` and `DSH_HOME`; telemetry hard-disabled |
| Skill format and search roots | compatible by upstream contract | DSH documents `.dsh/skills` and shared `.agents/skills` project roots |
| THE LOOP Setup | not present at this revision | `--harness dsh` was not yet implemented |
| Shared-root installation | passed | All 31 packages and the offline toolkit were installed into an isolated project through the existing `.agents/skills` path |
| THE LOOP Doctor | not present at this revision | Doctor did not yet have a DSH manifest or probe |
| Keyless headless start | truthful credential halt | DSH stopped with `MISSING_CREDENTIAL` before model execution |
| Authenticated DeepSeek behavior | not tested | The 1Password CLI could not connect to the signed-out desktop app |

Installing through the existing Codex selection exercised a shared filesystem root. It
did not prove a DSH adapter, DSH discovery precedence, invocation, permission denial,
fallback, Close behavior or native DeepSeek endpoint compatibility.

## Authenticated-probe design recorded at the time

Official DSH includes a dormant `llm-pi-ai` route for OpenRouter. The bounded probe uses
`OPENROUTER_API_KEY` from 1Password, a disposable workspace, a fresh `HOME` and
`DSH_HOME`, `DSH_TELEMETRY_DISABLED=1`, `DSH_PERMISSION_MODE=read-only` and a curated
environment. The model target is `deepseek/deepseek-v4-flash`.

That probe can prove DSH, its pi-ai adapter and a DeepSeek model routed through
OpenRouter. It cannot prove the native `deepseek-official` adapter or direct DeepSeek
API endpoint. The key is never written to the repository, overlay, arguments or retained
evidence.

DSH's write sandbox does not confine reads, network access or process visibility. A live
probe therefore remains restricted to a disposable workspace with no host credentials,
private memory or unrelated repositories in scope.

## Historical conclusion

This evaluation established the isolation and credential-handling requirements used
for subsequent DSH integration. v0.1 now ships DeepSeek Harness as its fifth
first-class adapter; the current shipping manifest supersedes this early conclusion.
