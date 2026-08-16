# Design brief

## Scope

This brief covers the skill pack's user-facing documentation, skill prompts, setup plans, Doctor reports, run status and release handoff.

The public page at `https://systemerror.app/the-loop` is a separate launch asset owned by a dedicated landing-page session. This repository defines the facts and evidence that page must consume. It does not design, implement, test, deploy or own the page.

## Product expression

THE LOOP should read as a technical operating system for bounded work, not as an agent personality.

The presentation must make five things clear:

1. What asset is being worked on.
2. What stage is active.
3. What authority is in force.
4. What evidence exists.
5. Why the run completed, halted or failed.

## Documentation hierarchy

The repository README should follow this order:

1. Precise one-sentence promise.
2. Supported harnesses and current verification status.
3. Fastest safe installation path.
4. Setup and Doctor.
5. Attended Loop and bounded Auto.
6. Lifecycle and feeders.
7. Installed-skill routing and bundled fallbacks.
8. Autonomy levels and permanent invariants.
9. Code and non-code examples.
10. Provenance, licence, security and privacy.
11. Deferred modes and honest limitations.
12. Support, consulting and contribution paths.

Quickstart instructions must be versioned, executable from a clean environment and short enough to verify without marketing interpretation.

## Skill and protocol documents

- One visible purpose per file.
- Put trigger conditions and required inputs before long instructions.
- Separate normative requirements from examples and explanation.
- Use stable requirement identifiers in protocols.
- Keep `SKILL.md` focused and move schemas, templates and extended examples to referenced files.
- Use relative paths and synthetic examples.
- Never embed a private path, host, repository or project name.
- Do not claim an optional provider is available until Doctor verifies it.

## Status language

The same words must mean the same thing in every harness:

| Label | Meaning |
| --- | --- |
| `VERIFIED` | The named check ran and passed with recorded evidence. |
| `FAILED` | The named check ran and did not pass. |
| `BLOCKED` | A known gate prevents the check or next action. |
| `DENIED` | Required authority or tool permission was refused. |
| `UNVERIFIED` | The check did not run or its evidence is stale. |
| `UNSUPPORTED` | The current version deliberately does not support the capability. |
| `PLANNED` | The capability is in product architecture but not shipped. |
| `COMPLETE` | All done-gate evidence passed and no blocking issue remains. |

Color, emoji or iconography may reinforce status but cannot replace the text label.

## Setup plan

Before installation, Setup presents:

- Detected harness and version.
- Target scope and destination.
- Every planned copy, link, directory creation, skip or overwrite.
- Existing conflicts and precedence consequences.
- Required approval.
- Rollback behavior.

Dry-run output and applied output use the same operation order. Non-interactive output remains readable as plain text and serialisable as JSON.

## Doctor report

Doctor leads with an overall status, then one section per harness:

- Installation and version.
- Skill roots inspected.
- Discovery result.
- Behavior result.
- Name collisions and winning precedence.
- Permission limits.
- Required runtime and filesystem checks.
- Kill-switch visibility.
- Exact corrective action for each surviving problem.

Discovery and behavior are separate rows. A found file does not receive a behavior check mark.

## Run status and digest

Every status view displays:

- Run ID and asset.
- Mode, track and current stage.
- Owner, lease generation and expiry.
- Authority level, scope and expiry.
- Budget and usage.
- Latest heartbeat and whether it is stale.
- Selected capability provider and fallback reason.
- Evidence summary.
- Open blocking issues.
- Last completed action, current gate and next safe action.

Elevated authority receives a persistent plain-text warning. A terminal digest never buries failure or unverified coverage below a success summary.

## Code and non-code examples

The two required examples share one presentation schema:

1. Intent and bounded asset.
2. Track-specific done gate.
3. Capability route.
4. Build or drafting action.
5. Evidence.
6. Surviving issue and resolution.
7. Final state and limitations.

The code example shows executable checks and branch isolation. The non-code example shows source quality, factuality and review evidence. Both use synthetic content.

## Voice

- Direct, specific and calm.
- Prefer “one bounded mission” to broad autonomy claims.
- Prefer `UNVERIFIED` to a compatibility claim without evidence.
- State the user action required at a gate.
- Avoid vendor endorsement implications.
- Avoid inflated terms such as “revolutionary,” “next-generation,” “seamless” and “supercharge.”

## Accessibility of product output

- Plain text remains the canonical representation.
- Heading and list structure remains meaningful in Markdown renderers and terminal output.
- Tables have a readable list fallback for narrow terminals.
- Long paths and commands wrap or remain inside their own scrollable code region.
- Status is never conveyed by color alone.
- Interactive setup prompts include a safe default and accept keyboard input.
- JSON output is available for automation but never required to understand a human-facing failure.

## Landing-page integration contract

The separate landing-page asset must receive only release-approved public facts. The skill pack owns the source data, not the page treatment.

### Required release data

- Product name and one-sentence promise.
- Creator attribution to Moses Mawila through System Error Worldwide.
- Tagged version and release date.
- Public repository and versioned quickstart URLs.
- Supported harness list and dated compatibility results.
- Shipped, preview, planned and gated mode status.
- Relationship between Setup, Loop, Auto, Parallel, Cloud and Endless.
- Installed-skill capability detection and bundled fallback explanation.
- Autonomy levels, visible warnings and permanent invariants.
- Provenance policy, public licence and upstream-dependency rules.
- One approved code example and one approved non-code example.
- Primary GitHub CTA and final consulting CTA destination.
- Known limitations and unverified environments.

### Landing asset constraints

- Canonical URL: `https://systemerror.app/the-loop`.
- Extend the existing System Error Software visual system.
- Preserve the current static, no-JavaScript CSP baseline unless a separate security review and explicit approval authorise a change.
- Include SEO, Open Graph, structured data and self-canonical metadata.
- Use no analytics by default. Any later measurement requires a separate privacy decision.
- Meet the separate session's responsive and WCAG 2.2 AA delivery gate.
- Do not deploy or publish without Moses's explicit approval.

### Handoff artifact

The release candidate should generate or maintain a public launch manifest containing:

- `product_version`.
- `repository_url`.
- `quickstart_url`.
- `release_date`.
- `harness_status` with evidence URLs and verification dates.
- `mode_status`.
- `autonomy_levels` and permanent invariants.
- `provenance_url` and `license`.
- Approved example URLs.
- Primary and secondary CTA URLs.
- Known limitations.

The separate landing session may transform this data into page content but may not upgrade `PLANNED`, `UNVERIFIED` or `UNSUPPORTED` to a stronger claim.

### Acceptance evidence returned by the separate session

Before the product launch can close, the landing-page owner supplies:

- Preview or production URL and exact source revision.
- Content-to-launch-manifest comparison.
- Working repository, quickstart and consulting links.
- Canonical, SEO, Open Graph and structured-data validation.
- CSP and security-header comparison.
- Responsive, keyboard, 200% zoom, long-content, code-overflow and accessibility evidence.
- Broken-link, install-error and unsupported-harness state evidence.
- A delivery verdict that marks unexecuted checks `not tested` and treats any stop-ship defect as Red.
- Deployment approval record and rollback plan when production publication is requested.

Static screenshots are visual evidence only. They do not prove task completion, semantics, keyboard behavior, zoom, link reliability or installation recovery.

The skill-pack session verifies that the returned facts match the release. It does not perform or own the page tests.

## Assumption ledger

| Assumption | Class | Consequence if wrong |
| --- | --- | --- |
| Plain Markdown and terminal text are sufficient product surfaces for v0.1. | safe default | Add a renderer later without changing the underlying status schema. |
| A public launch manifest is the cleanest interface to the separate landing asset. | safe default | Provide an equivalent versioned handoff document if machine-readable data is deferred. |
| Original public source uses the MIT licence. | locked | Change only through an explicit maintainer decision and update all public launch data. |
| The consulting CTA URL is `https://systemerror.app/services/`. | locked | Change only through a maintainer release decision. |
