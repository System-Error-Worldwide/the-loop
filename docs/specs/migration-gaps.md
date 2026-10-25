# Spec migration gaps — SYSTEM ERROR'S THE LOOP public skill pack

Checked 2026-10-23 against `e53bda761fc0f2467e5f686b0e1d9e2b773ab870`. Exact heading candidates below require content refutation; missing heading names do not prove missing equivalent prose. No full-compliance or readiness verdict is implied.

Main pack links added by this refresh cover only the bounded J901/A901 baseline. Secondary packs remain individually incomplete until their own scope is reconciled.

## docs/specs/

| Document role / path | Current structural gap | Concrete next action |
|---|---|---|
| [docs/specs/prd.md](prd.md) | Heading candidates absent: `Journey inventory`, `Journey outcomes`, `Constraints`, `Decisions`, `Assumptions` | Refute against existing content; bind missing fields to actual C/J/A/handler/effect/evidence and cite equivalent sections |
| [docs/specs/tdd.md](tdd.md) | Heading candidates absent: `Stack`, `Key technical decisions`, `Non-functional`, `State, API, and journey linkage`, `Integrations`, `Decisions`, `Assumptions` | Refute against existing content; bind missing fields to actual C/J/A/handler/effect/evidence and cite equivalent sections |
| [docs/specs/app-flow.md](app-flow.md) | Heading candidates absent: `Action contract`, `Route`, `User journeys`, `Branch conditions`, `Handoffs`, `Decisions`, `Assumptions` | Refute against existing content; bind missing fields to actual C/J/A/handler/effect/evidence and cite equivalent sections |
| [docs/specs/design-brief.md](design-brief.md) | Heading candidates absent: `Positioning`, `References`, `Colour`, `Typography`, `Spacing`, `Functional acceptance`, `Component`, `Anti-patterns`, `Decisions`, `Assumptions` | Refute against existing content; bind missing fields to actual C/J/A/handler/effect/evidence and cite equivalent sections |
| [docs/specs/backend-schema.md](backend-schema.md) | Heading candidates absent: `Entity`, `Collections`, `Relations`, `Access`, `Migrations`, `API surface`, `Data lifecycle`, `Decisions`, `Assumptions` | Refute against existing content; bind missing fields to actual C/J/A/handler/effect/evidence and cite equivalent sections |
| [docs/specs/engineering-plan.md](engineering-plan.md) | Heading candidates absent: `Build slices`, `Sequencing`, `External dependencies`, `Economics`, `Risks`, `Deployment`, `Manual`, `Decisions`, `Assumptions` | Refute against existing content; bind missing fields to actual C/J/A/handler/effect/evidence and cite equivalent sections |
| docs/specs/capability-ledger.md | Absent for this pack | Preserve dispositions; verify every required C row and dependency; current strict generator must resolve errors and disposition warnings before dependent Build |
| docs/specs/system-map.md | Absent for this pack | Regenerate only from corrected ledger/plan with current --strict true; never hand-edit map output |

Additional cross-document fields to verify: ledger Journey/action index; PRD declared slice/internal-test/beta/public-release J sets; per-action prerequisites/discovery/continuation; reload-visible data effects; full API error/auth/state contract; dependencies/owners and walking-skeleton gate; rollback per slice; Decisions and Assumptions with provenance. This refresh does not establish them by section-name presence.
