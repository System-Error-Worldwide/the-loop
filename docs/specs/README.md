# Phase 1 specification pack

Status: complete. Implementation proceeds only through the approved slices in the
engineering plan; the root README reports the repository's current implementation and
release status.

1. [Product requirements](prd.md)
2. [Technical design](tdd.md)
3. [App and workflow flow](app-flow.md)
4. [Design brief](design-brief.md)
5. [Backend and state schema](backend-schema.md)
6. [Engineering and release plan](engineering-plan.md)

## Decision state

### Locked

- Public, free project named SYSTEM ERROR'S THE LOOP.
- Canonical repository target: `System-Error-Worldwide/the-loop`.
- Creator and maintainer attribution: Moses Mawila through System Error Worldwide.
- Repository licence: MIT for original work created for this repository.
- First-class adapter targets: Codex, Claude Code, Kimi Code, OpenCode and DeepSeek
  Harness.
- The product routes by capability and description, uses installed specialists when safe, reports real gaps and always retains complete bundled fallback stages.
- v0.1 ships all 31 portable skills. Each is usable as a harness-native instruction;
  the local toolkit adds automation without changing skill status.
- External actions, strategic expansion and self-modification require approval by default.
- Canonical launch page: `https://systemerror.app/the-loop`.
- Landing page deployment requires separate explicit approval.

### Safe defaults assumed

- English is the initial product and documentation language.
- The pack is local-first and sends no telemetry.
- The portable skill source lives under `.agents/skills`; adapters may expose the same files through harness-specific supported paths.
- Portable `SKILL.md` frontmatter uses only `name`, `description`, `license`, `compatibility` and string metadata.
- Runtime data is repository-local by default under `.the-loop/` and ignored by Git.
- v1 of the landing page is static HTML and CSS. It adds no client-side JavaScript and does not weaken the current CSP.
- Examples and fixtures are synthetic.

### Release ownership

- Provenance and release evidence receive independent review.
- Final landing-page copy and its consulting route are owned by the dedicated website
  session.

### Human gates

- Repository publishing operations require current authority and green verification;
  no session-scoped grant is carried forward in this public spec.
- Any production deployment, including the landing page, requires explicit approval.
- Any elevated autonomy grant requires typed confirmation with actor, scope and expiry.
