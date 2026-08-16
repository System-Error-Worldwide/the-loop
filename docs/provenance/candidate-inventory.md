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

## Existing private artifacts

`the-loop`, `the-loop-auto`, `the-loop-parallel`, `the-loop-cloud`, `strategize`, `spec-pack`, `build`, `test`, `resolve`, `health-check`, `audit`, `portfolio-review`, `idea-to-brief`, `stack-summary`, `pre-commit-review`, `feature-tracker`, `decision-log`, `handoff`, `retrospective`, `session-summary` and `close`.

Every existing artifact failed at least one public reuse gate. Common failures were missing licence evidence, private paths and state assumptions, harness-specific commands, private portfolio knowledge or operational incident detail. None is approved for direct copying.

## Missing artifacts

`the-loop-setup`, `the-loop-doctor`, `the-loop-skill-planner`, `the-loop-skill-creator`, `the-loop-autonomy`, `the-loop-control`, `the-loop-watch`, `the-loop-endless`, `live-state-preflight` and `bootstrap-agent-context`.

These names are product architecture only. A missing artifact has no reusable source and must be designed from the public specification.

## Shared material

Four usable concepts exist in private form: stage contracts, capability routing, non-code tracking and workflow dispatch. They all require clean public rewrites. The code track, autonomy policy, run state and leases, issue ledger, evidence contract, watcher contract and harness capability map do not exist as safe public artifacts.

The audited installer, workflow template, heartbeat monitor, hooks and scheduled scripts are excluded as sources. They contain private assumptions or are tied to one harness.
