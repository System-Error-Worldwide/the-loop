# Candidate inventory

## Summary

| Group | Candidates | Existing private artifact | Missing artifact |
| --- | ---: | ---: | ---: |
| Setup and configuration | 7 | 0 | 7 |
| Modes | 5 | 4 | 1 |
| Lifecycle | 5 | 5 | 0 |
| Feeders | 3 | 3 | 0 |
| Grounding | 4 | 2 | 2 |
| Quality | 3 | 3 | 0 |
| Memory and handoff | 4 | 4 | 0 |
| Total | 31 | 21 | 10 |

The 31 records describe the complete architecture and provenance review, and all 31
now have public packages in the current private, untagged candidate. They are not
equally mature: 12 form the runtime-backed bounded kernel,
`the-loop-parallel` adds repository-tested lane primitives, and the remaining 18 are
portable contract-only packages with unverified live behavior.

## Existing private System Error predecessors

`the-loop`, `the-loop-auto`, `the-loop-parallel`, `the-loop-cloud`, `strategize`, `spec-pack`, `build`, `test`, `resolve`, `health-check`, `audit`, `portfolio-review`, `idea-to-brief`, `stack-summary`, `pre-commit-review`, `feature-tracker`, `decision-log`, `handoff`, `retrospective`, `session-summary` and `close`.

Most of these predecessors were built by System Error for private use. That ownership
fact is separate from the public shipping decision. Every artifact still failed at
least one public reuse gate because the audited file contained private paths or state
assumptions, harness-specific commands, private portfolio knowledge, operational
detail, or insufficient file-level licence evidence. None is approved for direct
copying. Their public capabilities were implemented again as clean System Error work.

## Missing artifacts

`the-loop-setup`, `the-loop-doctor`, `the-loop-skill-planner`, `the-loop-skill-creator`, `the-loop-autonomy`, `the-loop-control`, `the-loop-watch`, `the-loop-endless`, `live-state-preflight` and `bootstrap-agent-context`.

These names had no reusable predecessor artifact. Their included public packages were
designed from the public specification rather than derived from an audited source.

## Public classification and maturity

| Classification | Count | Meaning |
| --- | ---: | --- |
| `system-error-original` | 9 | New public System Error work with no predecessor artifact. |
| `system-error-rewrite` | 21 | Clean public System Error work for a capability with a private System Error predecessor; no predecessor body was copied. |
| `upstream-dependency` | 1 | System Error orchestration wrapper that detects/invokes a maintained upstream creator capability and retains an independently written fallback. |

| Maturity | Count | Current claim |
| --- | ---: | --- |
| Runtime-backed bounded kernel | 12 | Repository tests pass; live behavior remains unverified on all four adapters. |
| Parallel package plus lane primitives | 1 | Lane primitives pass repository tests; live harness behavior remains unverified. |
| Portable contract only | 18 | Installable fallback contract; runtime integration and live routing remain unverified. |

## Shared material

Four usable concepts exist in private form: stage contracts, capability routing, non-code tracking and workflow dispatch. They all require clean public rewrites. The code track, autonomy policy, run state and leases, issue ledger, evidence contract, watcher contract and harness capability map do not exist as safe public artifacts.

The audited installer, workflow template, heartbeat monitor, hooks and scheduled scripts are excluded as sources. They contain private assumptions or are tied to one harness.
