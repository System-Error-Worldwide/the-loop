# Engineering and release plan

## Delivery rule

No Phase 2 product implementation begins until:

1. This Phase 1 pack is committed and internally consistent.
2. The `System-Error-Worldwide` organisation and `the-loop` repository exist.
3. The Phase 0 and Phase 1 commits are backed up to that remote.
4. Live remote state, branch protection, open pull requests and CI are checked.

This entry gate was satisfied before bounded Phase 2 kernel implementation began. The
root README is the source of truth for current implementation and release status.

## Branch and backup strategy

- Default branch: `main`.
- Unattended work: `loop/<asset>-<date>`.
- Product slices: `feature/<slice>` after the remote exists.
- Each green slice receives one focused commit.
- Before every multi-file commit: inspect the staged diff, run targeted validation, scan for secrets and private identifiers, then commit.
- Push every completed stage during the currently authorised session once the remote exists.
- Deployment is never implied by a push.

## Phase 0: provenance and boundary

Status: complete locally.

### Deliverables

- 31-candidate inventory.
- Per-skill Git, checksum, licence and privacy decisions.
- Public and private boundary.
- Exact v0.1 shipping manifest.
- Risks and human gates.

### Done gate

- Exactly 31 candidate records exist.
- No audited private file is approved for verbatim reuse.
- Every v0.1 candidate has one public classification.
- Private scanners return no unexplained finding.

### Evidence

- Commit `3fc39e5` in the local repository.
- Full source checksums in the provenance record.

## Phase 1: specification and architecture

Status: this pack.

### Deliverables

- PRD.
- Technical design.
- Full workflow and failure flows.
- Product-output design brief and external landing-page integration contract.
- Local backend and state schema.
- This engineering and release plan.

### Done gate

- All six documents exist.
- Every v0.1 requirement maps to a build or verification slice.
- Run state, authority, lease, evidence, issue and kill-switch behavior agree across documents.
- The external landing page is represented by a launch-data contract, returned-evidence gate and separate deploy approval.
- No product code or copied private skill enters the commit.

### Evidence

- Markdown structure, link, term and consistency checks.
- Staged-diff secret and private-content scans.
- A focused Phase 1 commit.

## Phase 2: v0.1 kernel

Estimated agent execution time: 8 to 12 hours across focused slices, excluding user approval and external service waits.

### Slice 2.1: repository policy and validation shell

Estimate: 30 to 45 minutes.

Deliver:

- MIT licence for original repository work.
- Contribution, security and support boundaries.
- Repository checks for frontmatter, names, provenance coverage, private content and secrets.
- CI skeleton that performs only read-only validation.

Done gate:

- A synthetic bad skill fails for each policy class.
- The clean scaffold passes locally and in CI.
- No release job or deployment credential exists.

### Slice 2.2: schemas and state library

Estimate: 75 to 120 minutes.

Deliver:

- JSON Schemas for config, install receipt, run, lease, grant, route, evidence, issues and events.
- Standard-library validation helpers.
- Atomic projection writes and append-only event handling.
- Safe path and permission checks.

Done gate:

- Valid fixtures pass every schema.
- Invalid enum, transition, owner, invariant and path fixtures fail with precise errors.
- Interrupted-write test preserves the last valid projection.

### Slice 2.3: leases, heartbeat, budgets and kill switch

Estimate: 75 to 120 minutes.

Deliver:

- Exclusive lease acquisition and renewal.
- Generation-based explicit recovery.
- Heartbeat status.
- Time, attempt, mutation, external-action and optional cost budgets.
- Repository and external kill-switch checks.
- Authoritative audit after-state snapshots and deterministic run/lease projection repair.
- Durable pre-callback operation intents, exact semantic completion and non-replaying unknown-outcome reconciliation.
- Stable per-grant authority linearization across mutation intents and official revocation.
- Exact known-not-started reservation rollback, with unknown crash reservations retained.
- Durable project/control/state-root namespace identity binding at every public and side-effect boundary.

Done gate:

- Two writers cannot mutate one run.
- An expired lease cannot silently resume.
- A detected stop prevents the next mutation.
- Every exhausted budget produces the correct truthful state.
- Per-stage attempts and validated lease-interval duration survive restart without reset or double counting.
- A stale or missing projection is repaired from the latest valid event before mutation; a corrupt chain blocks mutation.
- Kill-switch control remains effective and auditable without a valid worker lease.
- Revoke-wins and intent-wins barriers pass across two runs sharing one grant.
- Revocation retries repair pre-append gaps, recognize canonical post-commit success, reject unverifiable state, and create one marker per run sharing the grant without restoring it.
- STOP and indeterminate probes at exact mutation, outward-action, cost and stage-attempt limits remain recoverable without replay or stranded budget state.
- Same-path project and state-root replacements fail for existing and freshly constructed runtimes without creating a second history.
- A hard interruption after intent cannot lose or replay the side effect: local unknown outcomes become `failed`, external unknown outcomes become `waiting_external`, and mismatched or duplicate completions are rejected.

### Slice 2.4: ten protocol contracts

Estimate: 90 to 150 minutes.

Deliver clean public versions of:

- Stage contracts.
- Skill routing.
- Code and non-code tracks.
- Workflow dispatch.
- Autonomy policy.
- Run state and leases.
- Issue ledger.
- Evidence contract.
- Watcher contract.
- Harness capability map.

Done gate:

- Every normative requirement has a stable identifier.
- Cross-references resolve.
- No protocol mentions a private host, path, repository, incident or portfolio project.
- A contradiction review finds no conflicting authority or completion rule.

### Slice 2.5: bundled fallback skills

Estimate: 2 to 3 hours.

Deliver clean public implementations of `the-loop`, `the-loop-auto`, `strategize`, `spec-pack`, `build`, `test`, `resolve`, `health-check`, `audit` and `close`.

Done gate:

- Each skill uses only portable frontmatter.
- Each stage names inputs, outputs, gate, evidence, self-refutation and halt conditions.
- A no-third-party fixture completes an attended run and a bounded Auto run.
- Auto cannot enter an unbounded monitor or work-selection loop.

### Slice 2.6: Setup and Doctor

Estimate: 90 to 150 minutes.

Deliver:

- Dry-run installation plan.
- Copy and proven-safe link modes.
- Install receipts and rollback.
- Read-only harness discovery and collision report.
- Optional isolated behavior probes.

Done gate:

- Setup never overwrites an unknown destination without exact approval.
- Rollback removes only unchanged files owned by its receipt.
- Doctor distinguishes discovery, behavior, denial and unverified states.
- All four harness paths match current official documentation.

### Slice 2.7: four thin adapters

Estimate: 60 to 120 minutes.

Deliver:

- Codex adapter.
- Claude Code adapter.
- Kimi Code adapter.
- OpenCode adapter.
- Sequential fallback when delegation is unavailable.

Done gate:

- Portable stage behavior is unchanged across adapters.
- Harness-only fields do not enter portable skill files.
- Unsupported permissions or delegation produce a named capability gap, not an invented fallback API.

### Slice 2.8: conformance suite and examples

Estimate: 2 to 3 hours.

Deliver:

- Synthetic code and non-code repositories.
- Routing, fallback, authority, state, lease, evidence, issue, recovery and kill-switch scenarios.
- One code example and one non-code example for documentation and the landing page.

Done gate:

- Shared scenarios pass without an optional specialist.
- A verified specialist can replace a fallback without changing outputs or safety gates.
- Failure injection never produces false green.

## Phase 3: independent four-harness verification

Estimated agent execution time: 2 to 4 hours, excluding installation or authentication waits.

For each harness:

1. Create a clean temporary repository.
2. Install with Setup.
3. Run Doctor discovery.
4. Test explicit invocation.
5. Test implicit description-based routing.
6. Deny one required permission and verify faithful reporting.
7. Run one bundled fallback mission.
8. Activate the kill switch before a planned mutation.
9. Resume explicitly and close with evidence.
10. Record version, environment, results and artifact digests.

### Done gate

- All required scenarios pass in all four harnesses.
- Every failure or skipped probe is explicit.
- No open blocking issue remains.
- A reviewer who did not author the implementation approves the evidence and provenance records.

## Phase 4: later modes and controls

Order is fixed:

1. User-facing Autonomy and Control.
2. Watch using the proven watcher contract.
3. Parallel with disjoint lane leases and integration ownership.
4. Cloud with generic restricted-environment behavior.
5. Portfolio review with no bundled private portfolio intelligence.
6. Adaptive skill planner and upstream-aware creator.
7. Supporting grounding, quality and handoff utilities.
8. Endless only after all prerequisites below pass.

### Endless entry gate

- Bounded Auto proven in all four harnesses.
- Durable state and schema migration proven.
- Exclusive leases and recovery proven.
- Heartbeat and stale detection proven.
- Authority grant, expiry and one-command reversal proven.
- All budgets enforced.
- External kill switch proven during a real harness run.
- Empty queue monitor behavior proven.
- Skill proposals cannot modify installed skills without a separate grant.

## External launch asset contract: `systemerror.app/the-loop`

The landing page is designed, implemented, tested and deployed in a separate dedicated session. This repository does not own a website branch or landing-page delivery slice.

The skill-pack release supplies:

- A tagged release and public repository.
- A versioned launch manifest with approved product facts, mode status, compatibility evidence, quickstart, provenance, licence, examples, limitations and CTA destinations.
- A content requirements checklist covering WEB-001 through WEB-016.

The separate landing-page owner returns:

- The source revision and preview or production URL.
- A launch-manifest comparison proving that public claims match the release.
- Metadata, security-header, responsive, accessibility, link, failure-state and recovery evidence.
- An explicit delivery verdict with every unexecuted check marked `not tested` and any stop-ship defect marked Red.
- A rollback plan and deployment approval record if production publication is requested.

### Skill-pack acceptance gate

- The public page uses the tagged repository and quickstart URLs.
- Harness and mode status exactly match the launch manifest.
- Provenance, licence, autonomy invariants and limitations are not weakened or omitted.
- Both CTA destinations work.
- The separate delivery evidence has no Red verdict or untested critical path.
- Moses explicitly approved any production deployment.

The skill-pack release may verify these returned facts before closing launch. It does not perform the landing-page implementation or tests.

## Phase 5: public release

Estimated agent execution time after approvals: 30 to 60 minutes.

### Release gate

- Public licence confirmed and present.
- All v0.1 files have full provenance records.
- Four-harness evidence approved.
- CI green and issue ledger empty.
- README quickstart tested from a clean environment.
- Security and privacy scans clean.
- Public repository visibility confirmed.
- Landing page content matches the tagged release.
- Production deployment separately approved.

### Release actions

1. Tag the approved commit.
2. Publish release notes with supported and unverified boundaries.
3. Verify installation from the public tag.
4. Receive the separate landing-page delivery evidence and explicit deployment record.
5. Verify that production facts, metadata and CTAs match the tagged release.
6. Record release evidence and close.

## Requirement traceability

| Requirement group | Build slice | Verification |
| --- | --- | --- |
| FR-001 to FR-006 | 2.6, 2.7 | setup and doctor harness tests |
| FR-010 to FR-015 | 2.4, 2.5, 2.7 | routing and fallback conformance |
| FR-020 to FR-026 | 2.4, 2.5 | attended and Auto lifecycle scenarios |
| FR-030 to FR-038 | 2.2, 2.3 | projection repair, concurrency, recovery, pending-operation, budget and kill-switch tests |
| FR-040 to FR-045 | 2.2, 2.3, 2.4 | grant, expiry, warning and revocation tests |
| FR-050 to FR-053 | 2.4, 2.8 | code and non-code examples |
| FR-060 to FR-063 | 2.1, Phase 3 | release scans and independent review |
| WEB-001 to WEB-016 | external launch manifest and handoff | separate landing session returns content, security, accessibility and production evidence |
| NFR-001 to NFR-010 | 2.1 to 2.8 plus external handoff | CI, conformance, security and returned launch evidence |

## Test and resolve loop

Every slice follows:

1. State the slice done gate and evidence.
2. Implement only the slice.
3. Run targeted tests and attack each finding.
4. Open surviving defects in the issue ledger.
5. Resolve one owned issue at a time.
6. Rerun the regression check and affected suite.
7. Stop after three red passes or one reopened issue.
8. Review the staged diff, then commit and push the green milestone.

## Rollback

- Local skill installation: replay the receipt and remove only unchanged owned files.
- State migration: retain and restore the previous complete state tree.
- Repository change: revert the focused milestone commit, never reset unrelated work.
- Landing page: the separate asset owner provides and executes its rollback plan under explicit authority.
- Authority elevation: revoke the grant and activate the external kill switch if work is active.

## Unresolved human gates

1. Name the independent final reviewer before release candidate.
2. Supply the final Agent Workflow Audit or consulting CTA URL.
3. Approve the landing page preview before production deployment.

## Assumption ledger

| Assumption | Class | Consequence if wrong |
| --- | --- | --- |
| The user wants milestone pushes during this session once the remote exists. | locked for current session | Ask again in a future session rather than carrying the grant forward. |
| Repository administrators may bypass pull-request protection for emergency recovery, with the action remaining visible in Git history and the audit log. | safe default | Remove the bypass if a second maintainer makes mandatory review practical. |
| Landing implementation belongs to a separate dedicated session and website repository. | corrected scope | This session supplies only launch data and acceptance requirements. |
| A tagged release should exist before the landing page is deployed. | safe default | If preview comes earlier, label every status as pre-release and keep production blocked. |
