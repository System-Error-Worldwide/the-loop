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
- Supported harnesses: Codex, Claude Code, Kimi Code and OpenCode.
- The product routes by capability and description, uses installed specialists when safe, reports real gaps and always retains complete bundled fallback stages.
- v0.1 proves attended Loop and one bounded Auto mission.
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

### Needs confirmation before release

- Independent final reviewer.
- Final launch copy and consulting destination URL.

### Human gates

- The public repository exists at `System-Error-Worldwide/the-loop`; milestone pushes are approved for this session and must pass the repository's verification gate.
- Any production deployment, including the landing page, requires explicit approval.
- Any elevated autonomy grant requires typed confirmation with actor, scope and expiry.
