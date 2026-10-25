# Maintenance contract — SYSTEM ERROR'S THE LOOP public skill pack

Checked: 2026-10-23 · Documentation refresh: S0 (non-code deliverable) · Product readiness: not reassessed.

## Baseline and authority

Assessed tree: `origin/main` at `e53bda761fc0f2467e5f686b0e1d9e2b773ab870`. This is a fetched revision snapshot, not a claim that every checkout or deployed host is current. Source-checkout drift, upstream comparison, open PRs, custody and deployment observations remain in the dated portfolio assessment; the fetched ref does not hide stale or divergent checkouts.

Registry Testing. Public packaged protocols/provenance differ from private development guidance. Current private journey policy is a maintenance requirement, not proof packaged skills already implement it.

Classes considered: Packaged developer CLI/runtime product. Upstream authority is the current spec-pack skill, journey-contract, templates and matching app-class rosters (2026-10-23). These remain shared guidance; their full text is not copied into product Git. This document is a maintenance baseline, not a retrospective full S2 pack or product acceptance receipt.

## Canonical documentation map

| Existing artifact | Responsibility / limit |
|---|---|
| [README.md](../../README.md) | Canonical existing source; retain its original scope/date |
| [docs/specs/README.md](README.md) | Canonical existing source; retain its original scope/date |
| [docs/specs/tdd.md](tdd.md) | Canonical existing source; retain its original scope/date |
| [docs/specs/backend-schema.md](backend-schema.md) | Canonical existing source; retain its original scope/date |
| [docs/specs/engineering-plan.md](engineering-plan.md) | Canonical existing source; retain its original scope/date |
| [protocols/evidence-contract.md](../../protocols/evidence-contract.md) | QA/evidence |
| [protocols/stage-contracts.md](../../protocols/stage-contracts.md) | Canonical existing source; retain its original scope/date |
| [docs/release/README.md](../release/README.md) | Canonical existing source; retain its original scope/date |

Architecture/API/data/access facts come from the existing technical/schema docs above and implementation paths below. Operations/release and QA artifacts retain their original candidate, host and date. Missing current deployment SHA, backend/auth coverage or restore receipt is **unverified**, not a broken-system finding. No provider credentials, production config or personal facts are inferred.

## Journey inventory and readiness

The following is deliberately one bounded maintenance path. It does not inventory every exposed control or supersede existing journey names. New IDs `J901` / `A901` are local cross-reference anchors; existing IDs retain their meaning.

| Journey | Actor | Outcome | Normal discovery | Capability / requirement linkage | Completion criterion |
|---|---|---|---|---|---|
| J901 | Existing authorized operator/user for this surface | Operator plans installation and checks host compatibility without starting product work | README setup instructions → setup plan → Doctor | Preserve the cited existing behavior; No C-ID is assigned by this maintenance refresh; use the owning existing ledger when available. Missing ledger/index coverage is migration debt, not an invented shipped row. | A901 reaches the stated visible outcome or honest recovery; effects checked only where required |

| Gate | Required journey set | Current evidence / blocker |
|---|---|---|
| slice | J901/A901 for a future change limited to this path, plus any newly touched controls | Source/spec mapping only; proposed check below has not been exercised by this docs refresh |
| internal-test | J901 plus all applicable operator, failure/retry, auth/role and recovery journeys | Full set remains to be enumerated in the owning brief/pack; no readiness promotion |
| beta | internal-test set plus exposed onboarding/account/provider/handoff paths | Missing exact set/evidence blocks beta claim; single-operator tools explicitly decide external-beta applicability |
| public-release | beta set plus all public navigation, content, support, ops/rollback and required external gates | Not declared ready; historical release evidence must match the intended candidate and scope |

Disposition, implementation, independent verification, integration and deployment are separate states. A source file, registry Live/Specced label, ledger `shipped` claim or a successful docs check does not establish all five.

## Action contract

| Action | Journey / actor | Discovery and prerequisites | Handler / behavior | Authoritative effect | Visible success | Recovery / continuation | Acceptance |
|---|---|---|---|---|---|---|---|
| A901 — exercise the bounded existing action | J901; actor/role already permitted by the existing surface | README setup instructions → setup plan → Doctor; existing auth/state/provider prerequisites apply, no new authority | scripts/the_loop_setup.py (plan is default; --apply mutates target); scripts/the_loop_doctor.py | Plan/diagnostic reads; reviewed apply is a separate action outside this maintenance baseline | Plan/compatibility result with collisions and unavailable capability honestly reported | Cancel or resolve collisions; never auto-overwrite or install into a real harness for docs verification | Proposed check below; not run for this documentation refresh |

No new application capability or authorization is introduced. Navigation/read-only effects explicitly say **none**. Side effects such as email, audit append or file acceptance must use their actual authoritative evidence rather than a screenshot alone.

## Checks and evidence

**Next relevant behavior check (proposed, not executed):** Synthetic setup/Doctor fixtures and existing repository validator: non-mutating plan, collision refusal and unsupported capability state. Product runtime behavior is unchanged.

- [README.md](../../README.md) — inspected source/path; test execution and runtime behavior are **not** asserted by file presence.
- [tests/test_setup_contracts.py](https://github.com/System-Error-Worldwide/the-loop/blob/e53bda761fc0f2467e5f686b0e1d9e2b773ab870/tests/test_setup_contracts.py) — inspected source/path; test execution and runtime behavior are **not** asserted by file presence.
- [tests/test_doctor_contracts.py](https://github.com/System-Error-Worldwide/the-loop/blob/e53bda761fc0f2467e5f686b0e1d9e2b773ab870/tests/test_doctor_contracts.py) — inspected source/path; test execution and runtime behavior are **not** asserted by file presence.
- [tests/test_validate_repository.py](https://github.com/System-Error-Worldwide/the-loop/blob/e53bda761fc0f2467e5f686b0e1d9e2b773ab870/tests/test_validate_repository.py) — inspected source/path; test execution and runtime behavior are **not** asserted by file presence.
- [scripts/the_loop_setup.py](../../scripts/the_loop_setup.py) — inspected source/path; test execution and runtime behavior are **not** asserted by file presence.
- [scripts/the_loop_doctor.py](../../scripts/the_loop_doctor.py) — inspected source/path; test execution and runtime behavior are **not** asserted by file presence.

This refresh checks Markdown links/path existence, required-section mapping and contradictory status wording. It does not run app/native acceptance, send email, call mutation APIs, install to a real harness, trade, deploy or publish. Native app work retains real native interaction, accessibility and inspected screenshot gates.

## Migration gaps and concrete next actions

1. Product six-document pack lacks capability ledger/generated map and complete J/A/readiness tables.
2. Reconcile packaged spec-pack/stage protocols with upstream guidance in a separate approved behavior change; exclude private host paths, policies and business records from public package.
3. Bind setup/apply/Doctor, attended/auto resume/kill and release checks to concrete handlers/state/evidence before next runtime release.

See [migration-gaps.md](migration-gaps.md) for exact existing-pack file/heading gaps. It is a structural audit against current outlines, not a verdict that differently named equivalent content is absent. Refute each gap against its cited artifact before expanding the document; add an equivalence reference where the content already exists. No new S2 ledger or map is authored here.

## Tier policy

- **S0:** documentation/copy/config fix or contained bug without changed data/access/subsystem boundary. Record changed behavior/touched callers and one proportionate check; reference existing IDs where present. No new pack required.
- **S1:** contained feature within existing data/access boundaries. One implementation brief with outcome, in/out scope, actual capability rows/dispositions, compact J/A contract, normal entry, prerequisites, handler/effect, recovery, falsifiable checks, visual direction when applicable, risks, rollback and ordered slices.
- **S2:** new product/site, material data/access/security boundary, new surface plus backend or cross-subsystem feature. Coverage-first ledger plus six existing-document roles and index; C→J→A→handler/effect→check links, dependency owners/gates, required journey sets and stack decision where material. Generate the map with current `--strict true`; resolve structural errors and disposition warnings before Build. Preserve existing requirement IDs and original decisions.

A paperwork waiver does not waive behavior or QA. Existing stack remains selected for routine maintenance. New material stack choices require an explicit recorded selection; historical template defaults are not approval.

## Future change checklist

1. Run Git freshness gate; resolve canonical repo, active runtime, source SHA and nearest instructions. Preserve other sessions, dirty files, backups and leases. Acquire exact continuity before product mutation and use its owned checkout.
2. Classify blast radius and record scope/done gate plus worker route or allowed S0 exception. Read existing source/callers/tests/docs; do not infer product completion from registry stage.
3. In the existing brief/pack, trace requirement → real capability → J/step → A/control → prerequisites/handler → effect → visible result → exact acceptance evidence. Discover controls through normal navigation; include failure/retry/cancel/back, roles, persistence/reopen and external return where relevant.
4. Update architecture/schema/API/access/ops docs only where the change actually affects them. Retain explicit external gates, owner and fallback; no unsupported legal/security/financial conclusion.
5. Run the smallest changed-surface checks and required independent exact-candidate acceptance. Record missing coverage and gate blockers. Audit the staged diff before multi-file push.
6. Checkpoint under owning lease, use repository-approved PR integration, read back remote default branch and separately reconcile project state. Record deployment only from a deployment receipt; release/outward actions require their own authority.

## Rollback and refresh triggers

Documentation rollback is a reviewed revert of this documentation commit, preserving any later edits; it has no database/runtime migration. Product rollback follows the existing operations artifact for that exact candidate; if absent, write and rehearse it in an authorized sandbox before a risky change. Never assume an old binary can open a newer schema.

Refresh this contract and owning artifact when routes/controls, handler effects, schema/access/roles, enabled modules, providers/cost, native lifecycle, runtime/deploy root, restore process, public claims, required journey set or shared spec guidance changes. A reopened finding or source/runtime contradiction triggers reconciliation before another green claim.

## Decisions

`safe-default` — preserve current behavior/stack, use existing product documents, scope the baseline to one evidenced path, and keep unsupported migration work explicit. No historical user decision or readiness approval is reconstructed.

## Assumptions and open questions

Current runtime/backend/auth, unexecuted proposed behavior checks and exact wider readiness sets remain unverified. Resolve them in the owning change; this document grants no outward action or broadened authority.
